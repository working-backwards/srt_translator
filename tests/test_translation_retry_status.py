import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest
from openai import APIConnectionError, APITimeoutError, RateLimitError

from srt_translator.api import Translator
from srt_translator.core.config.language_config import LanguageConfig
from srt_translator.core.config.models import LogMode, TranslationConfig
from srt_translator.core.constants import (
    TRANSLATION_CONNECTION_RETRY_BASE_S,
    TRANSLATION_CONNECTION_RETRY_CAP_S,
    TRANSLATION_MAX_CONNECTION_RETRIES,
)
from srt_translator.core.translator.translator import SRTTranslator

# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _connection_error() -> APIConnectionError:
    return APIConnectionError(request=httpx.Request("POST", "https://api.openai.com/v1/x"))


def _timeout_error() -> APITimeoutError:
    return APITimeoutError(httpx.Request("POST", "https://api.openai.com/v1/x"))


def _rate_limit_error() -> RateLimitError:
    response = httpx.Response(429, request=httpx.Request("POST", "https://api.openai.com/v1/x"))
    return RateLimitError("rate limited", response=response, body=None)


def _minimal_lang_config() -> LanguageConfig:
    return LanguageConfig(
        {
            "policy_defaults": {
                "target_batch_size": 5,
                "max_batch_size": 10,
                "allow_placeholder_apostrophe": True,
            },
            "languages": {"es": {"name": "Spanish", "cps_cap": 20}},
        }
    )


def _make_translator(callback=None) -> SRTTranslator:
    return SRTTranslator(
        dnt_terms=[],
        termbase={},
        api_key="sk-test",
        logger=logging.getLogger("test.retry_status"),
        translation_model_name="gpt-4o-mini",
        batch_size=5,
        language_config=_minimal_lang_config(),
        retry_status_callback=callback,
    )


# --------------------------------------------------------------------------- #
# _emit_retry_status unit
# --------------------------------------------------------------------------- #


def test_emit_retry_status_invokes_callback_when_set():
    received = []
    t = _make_translator(callback=received.append)
    t._emit_retry_status("hello")
    assert received == ["hello"]


def test_emit_retry_status_is_noop_when_callback_is_none():
    t = _make_translator(callback=None)
    # Must not raise even though there is no callback wired
    t._emit_retry_status("hello")


def test_emit_retry_status_swallows_callback_exception():
    """A broken UI callback must never break the translation loop."""

    def boom(msg):
        raise RuntimeError("ui exploded")

    t = _make_translator(callback=boom)
    # Must not propagate the callback's exception
    t._emit_retry_status("hello")


# --------------------------------------------------------------------------- #
# Cadence: retry messages from the shape-lock except block
# --------------------------------------------------------------------------- #


@pytest.fixture
def no_sleep(monkeypatch):
    """Skip real sleeps so retry-cadence tests run instantly."""
    monkeypatch.setattr("srt_translator.core.translator.translator.time.sleep", lambda _s: None)


def _run_shape_lock_with_failures(translator: SRTTranslator, errors: list[Exception]):
    """Drive `_translate_with_simple_shape_lock` with `_translate_batch_json`
    raising `errors` in order and then succeeding with a one-item result."""
    side_effect = list(errors) + [[{"id": 1, "tgt": "hola"}]]
    translator._translate_batch_json = MagicMock(side_effect=side_effect)
    return translator._translate_with_simple_shape_lock(
        src_items=["hello"],
        target_lang="es",
        termbase={},
        batch_ids=[1],
        logger=logging.getLogger("test.shape_lock"),
    )


def test_retry_callback_fires_on_connection_error_then_clears_on_success(no_sleep):
    received: list[str] = []
    t = _make_translator(callback=received.append)

    result = _run_shape_lock_with_failures(t, [_connection_error(), _connection_error()])

    # Two retries + final empty-string clear
    assert len(received) == 3
    assert all(msg.startswith("Connection issue, retrying in ") for msg in received[:2])
    assert "attempt 1/" in received[0]
    assert "attempt 2/" in received[1]
    assert received[-1] == ""
    # And the call eventually returned the success payload
    assert result == [{"id": 1, "tgt": "hola"}]


def test_retry_callback_fires_on_timeout_and_rate_limit(no_sleep):
    """All three transient classes route through the same handler."""
    received: list[str] = []
    t = _make_translator(callback=received.append)

    _run_shape_lock_with_failures(t, [_timeout_error(), _rate_limit_error()])

    assert sum(1 for m in received if m.startswith("Connection issue")) == 2
    assert received[-1] == ""


def test_retry_uses_new_constants_not_micro_backoff(no_sleep, monkeypatch):
    """The plan's load-bearing fix: real-network retries must use
    CONNECTION_RETRY_* timing, not MICRO_BACKOFF_* (1s cap sized for
    malformed-JSON micro-retries)."""
    durations: list[float] = []
    monkeypatch.setattr(
        "srt_translator.core.translator.translator.time.sleep",
        lambda s: durations.append(s),
    )
    t = _make_translator(callback=lambda _m: None)

    _run_shape_lock_with_failures(t, [_connection_error(), _connection_error(), _connection_error()])

    # Exponential backoff anchored at TRANSLATION_CONNECTION_RETRY_BASE_S, capped at _CAP_S
    assert durations[0] == TRANSLATION_CONNECTION_RETRY_BASE_S
    assert durations[1] == min(TRANSLATION_CONNECTION_RETRY_BASE_S * 2, TRANSLATION_CONNECTION_RETRY_CAP_S)
    assert durations[2] == min(TRANSLATION_CONNECTION_RETRY_BASE_S * 4, TRANSLATION_CONNECTION_RETRY_CAP_S)
    # And the first delay must not be the 1s MICRO_BACKOFF_CAP from the old code
    assert durations[0] > 1.0


def test_retry_does_not_bump_consecutive_decode_failures(no_sleep):
    """The plan's accounting fix: rate limits / connection errors must not
    increment the shape-lock decode-failure circuit breaker, or 8 transient
    blips would trip it instead of just retrying the 5 budgeted attempts."""
    t = _make_translator(callback=lambda _m: None)

    _run_shape_lock_with_failures(
        t,
        [_connection_error(), _rate_limit_error(), _timeout_error()],
    )

    assert t._consecutive_decode_failures == 0


def test_retry_exhaustion_raises_after_max_attempts(no_sleep):
    """5 attempts × 30s cap is the silent-retry budget; the next failure
    must propagate so the per-language tracker can record it."""
    received: list[str] = []
    t = _make_translator(callback=received.append)

    too_many = [_connection_error()] * (TRANSLATION_MAX_CONNECTION_RETRIES + 1)
    t._translate_batch_json = MagicMock(side_effect=too_many)

    with pytest.raises(APIConnectionError):
        t._translate_with_simple_shape_lock(
            src_items=["hello"],
            target_lang="es",
            termbase={},
            batch_ids=[1],
            logger=logging.getLogger("test.exhaust"),
        )

    # The final emission before re-raising clears the banner
    assert received[-1] == ""


def test_no_retry_callback_emitted_when_first_call_succeeds(no_sleep):
    """Quiet path: a clean call still emits the empty-string clear once, so
    a stale banner from a prior batch is wiped, but never a 'retrying'
    message."""
    received: list[str] = []
    t = _make_translator(callback=received.append)

    t._translate_batch_json = MagicMock(return_value=[{"id": 1, "tgt": "hola"}])
    t._translate_with_simple_shape_lock(
        src_items=["hello"],
        target_lang="es",
        termbase={},
        batch_ids=[1],
        logger=logging.getLogger("test.quiet"),
    )

    assert received == [""]


def my_callback(_msg: str) -> None:
        pass

# --------------------------------------------------------------------------- #
# Threading: callback flows worker → api.Translator → main → SRTTranslator
# --------------------------------------------------------------------------- #


def test_translate_srt_files_threads_callback_to_srt_translator(tmp_path):
    """The load-bearing wire the worker fix was about: the callback supplied
    to `translate_srt_files` must reach every per-language SRTTranslator."""
    from srt_translator.core.main import translate_srt_files

    src = tmp_path / "input.srt"
    src.write_text("1\n00:00:01,000 --> 00:00:02,000\nHello\n\n", encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()
    cfg = TranslationConfig(
        target_languages={"Spanish": "es"},
        output_directory=out,
        api_key="sk-test",
        log_mode=LogMode.STANDARD,
        mode="GUI",
        language_policies={
            "policy_defaults": {
                "target_batch_size": 5,
                "max_batch_size": 10,
                "allow_placeholder_apostrophe": True,
            },
            "languages": {"es": {"name": "Spanish", "cps_cap": 20}},
        },
        files=(src,),
        retry_status_callback=my_callback,
    )


    received_kwargs = {}

    def factory(**kwargs):
        received_kwargs.update(kwargs)
        inst = MagicMock()
        inst.translate_file.side_effect = lambda **kw: Path(kw["output_filepath"]).parent.mkdir(
            parents=True, exist_ok=True
        ) or Path(kw["output_filepath"]).write_text("ok", encoding="utf-8")
        return inst

    with patch("srt_translator.core.main.SRTTranslator", side_effect=factory):
        translate_srt_files(
            file_paths=[str(src)],
            config=cfg,
            retry_status_callback=my_callback,
        )

    assert received_kwargs.get("retry_status_callback") is my_callback


def test_api_translator_threads_callback_to_translate_srt_files(tmp_path):
    """The other half: api.Translator must thread the callback into
    translate_srt_files, not silently drop it."""
    src = tmp_path / "input.srt"
    src.write_text("1\n00:00:01,000 --> 00:00:02,000\nHello\n\n", encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()
    cfg = TranslationConfig(
        target_languages={"Spanish": "es"},
        output_directory=out,
        api_key="sk-test",
        log_mode=LogMode.STANDARD,
        mode="GUI",
        language_policies={
            "policy_defaults": {
                "target_batch_size": 5,
                "max_batch_size": 10,
                "allow_placeholder_apostrophe": True,
            },
            "languages": {
                "es": {
                    "name": "Spanish",
                    "cps_cap": 20,
                }
            },
        },
        files=(src,),
        retry_status_callback=my_callback,
    )


    fake_summary = {
        "total_files": 1,
        "unique_languages": 1,
        "total_operations": 1,
        "successes": 1,
        "skipped": 0,
        "errors": 0,
        "error_details": [],
        "successful_languages": [{"language": "Spanish", "code": "es", "status": "success"}],
        "failed_languages": [],
        "batch_directory": str(out / "batch"),
    }
    with patch.object(
            TranslationConfig,
            "run",
            return_value=fake_summary,
    ) as patched:
        Translator(cfg).run()

    patched.assert_called_once()
    assert cfg.retry_status_callback is my_callback