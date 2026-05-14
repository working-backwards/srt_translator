"""Unit tests for per-language failure tracking in the batch translation loop.

Covers the contract of `core.main.translate_srt_files`:

  - per-language `successful_languages` / `failed_languages` tracking
  - typed-exception abort: auth / permission / bad-model / quota / connection
    re-raise to abort the whole batch (every subsequent language would fail
    for the same reason)
  - soft throttling / generic runtime errors fall through to per-language
    tracking
  - `stop_check` callback halts the loop between languages
  - `cancelled=True` flag on the summary when stopped
  - `on_language_done` callback fires once per successful language
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest
from openai import APIConnectionError, AuthenticationError, PermissionDeniedError, RateLimitError

from srt_translator.core.config.models import LogMode, TranslationConfig
from srt_translator.core.main import translate_srt_files


def _policies() -> dict:
    return {
        "policy_defaults": {
            "target_batch_size": 5,
            "max_batch_size": 10,
            "allow_placeholder_apostrophe": True,
        },
        "languages": {
            "es": {"name": "Spanish", "cps_cap": 20},
            "fr": {"name": "French", "cps_cap": 20},
            "de": {"name": "German", "cps_cap": 20},
        },
    }


def _make_config(tmp_path: Path, target_languages: dict[str, str]) -> TranslationConfig:
    src = tmp_path / "input.srt"
    src.write_text("1\n00:00:01,000 --> 00:00:02,000\nHello\n\n", encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()
    return TranslationConfig(
        target_languages=target_languages,
        output_directory=out,
        api_key="sk-test",
        log_mode=LogMode.STANDARD,
        mode="GUI",
        language_policies=_policies(),
        files=(src,),
    )


def _make_factory(outcomes: dict[str, Exception | None]):
    """Build a SRTTranslator side_effect that maps target_lang -> outcome.

    `None` means success; an Exception instance is raised by translate_file.
    """

    def factory(**_kwargs):
        inst = MagicMock()

        def translate_file(*, input_filepath: str, output_filepath: str, target_lang: str):
            outcome = outcomes.get(target_lang)
            if isinstance(outcome, Exception):
                raise outcome
            Path(output_filepath).parent.mkdir(parents=True, exist_ok=True)
            Path(output_filepath).write_text("ok", encoding="utf-8")

        inst.translate_file.side_effect = translate_file
        return inst

    return factory


def test_all_languages_succeed_yields_empty_failed_list(tmp_path):
    cfg = _make_config(tmp_path, {"Spanish": "es", "French": "fr"})

    with patch("srt_translator.core.main.SRTTranslator", side_effect=_make_factory({"es": None, "fr": None})):
        summary = translate_srt_files(file_paths=[str(next(iter(cfg.files)))], config=cfg)

    assert summary["successes"] == 2
    assert summary["errors"] == 0
    assert [item["code"] for item in summary["successful_languages"]] == ["es", "fr"]
    assert summary["failed_languages"] == []


def test_one_language_failure_does_not_abort_others(tmp_path):
    """Mid-batch RuntimeError must be captured per-language, not crash the run."""
    cfg = _make_config(tmp_path, {"Spanish": "es", "French": "fr", "German": "de"})

    outcomes = {"es": None, "fr": RuntimeError("simulated transient"), "de": None}
    with patch("srt_translator.core.main.SRTTranslator", side_effect=_make_factory(outcomes)):
        summary = translate_srt_files(file_paths=[str(next(iter(cfg.files)))], config=cfg)

    assert {item["code"] for item in summary["successful_languages"]} == {"es", "de"}
    assert len(summary["failed_languages"]) == 1
    failed = summary["failed_languages"][0]
    assert failed["code"] == "fr"
    assert failed["error_type"] == "RuntimeError"
    assert "simulated transient" in failed["message"]


def test_authentication_error_aborts_whole_batch(tmp_path):
    """Auth errors are guaranteed to fail every language — abort instead of
    looping through 11 more identical failures."""
    cfg = _make_config(tmp_path, {"Spanish": "es", "French": "fr"})

    auth_err = AuthenticationError(
        "invalid api key",
        response=httpx.Response(401, request=httpx.Request("POST", "https://api.openai.com/v1/x")),
        body=None,
    )
    outcomes = {"es": auth_err, "fr": None}
    with patch("srt_translator.core.main.SRTTranslator", side_effect=_make_factory(outcomes)):
        with pytest.raises(AuthenticationError):
            translate_srt_files(file_paths=[str(next(iter(cfg.files)))], config=cfg)


def test_permission_denied_error_aborts_whole_batch(tmp_path):
    cfg = _make_config(tmp_path, {"Spanish": "es", "French": "fr"})

    perm_err = PermissionDeniedError(
        "no access to model",
        response=httpx.Response(403, request=httpx.Request("POST", "https://api.openai.com/v1/x")),
        body=None,
    )
    outcomes = {"es": perm_err, "fr": None}
    with patch("srt_translator.core.main.SRTTranslator", side_effect=_make_factory(outcomes)):
        with pytest.raises(PermissionDeniedError):
            translate_srt_files(file_paths=[str(next(iter(cfg.files)))], config=cfg)


def test_invalid_model_runtime_error_aborts_whole_batch(tmp_path):
    """core/translator/translator.py wraps OpenAINotFoundError as
    RuntimeError('Invalid translation model …'). That wrapped form must also
    abort, since every subsequent language will hit the same bad model."""
    cfg = _make_config(tmp_path, {"Spanish": "es", "French": "fr"})

    outcomes = {
        "es": RuntimeError("Invalid translation model 'gpt-bogus'. Check the translator model name."),
        "fr": None,
    }
    with patch("srt_translator.core.main.SRTTranslator", side_effect=_make_factory(outcomes)):
        with pytest.raises(RuntimeError, match="Invalid translation model"):
            translate_srt_files(file_paths=[str(next(iter(cfg.files)))], config=cfg)


def test_generic_runtime_error_is_tracked_not_raised(tmp_path):
    """Non-fatal RuntimeError (no 'Invalid translation model' marker) should
    fall through to per-language tracking, not abort."""
    cfg = _make_config(tmp_path, {"Spanish": "es", "French": "fr"})

    outcomes = {"es": RuntimeError("count mismatch"), "fr": None}
    with patch("srt_translator.core.main.SRTTranslator", side_effect=_make_factory(outcomes)):
        summary = translate_srt_files(file_paths=[str(next(iter(cfg.files)))], config=cfg)

    assert [item["code"] for item in summary["successful_languages"]] == ["fr"]
    assert [item["code"] for item in summary["failed_languages"]] == ["es"]


def test_failed_languages_records_error_type_and_message(tmp_path):
    """Downstream Retry Failed Languages handler filters by error_type, so the
    field must reflect the actual exception class name."""
    cfg = _make_config(tmp_path, {"Spanish": "es"})

    outcomes = {"es": TimeoutError("network slow")}
    with patch("srt_translator.core.main.SRTTranslator", side_effect=_make_factory(outcomes)):
        summary = translate_srt_files(file_paths=[str(next(iter(cfg.files)))], config=cfg)

    assert summary["failed_languages"] == [
        {
            "language": "Spanish",
            "code": "es",
            "error_type": "TimeoutError",
            "message": "network slow",
        }
    ]


# --------------------------------------------------------------------------- #
# Quota / connection fast-abort (the "out of credits" and "internet down"
# Tier 3 dialogs depend on these errors propagating out of translate_srt_files
# instead of being captured per-language).
# --------------------------------------------------------------------------- #


def _rate_limit(detail: str) -> RateLimitError:
    return RateLimitError(
        detail,
        response=httpx.Response(429, request=httpx.Request("POST", "https://api.openai.com/v1/x")),
        body=None,
    )


def test_rate_limit_quota_aborts_whole_batch(tmp_path):
    """Quota exhaustion is permanent — every subsequent language would hit
    the same error, so the loop must re-raise instead of cycling through
    every language and recording 12 identical failures."""
    cfg = _make_config(tmp_path, {"Spanish": "es", "French": "fr"})

    outcomes = {"es": _rate_limit("Error code: 429 - insufficient_quota"), "fr": None}
    with patch("srt_translator.core.main.SRTTranslator", side_effect=_make_factory(outcomes)):
        with pytest.raises(RateLimitError):
            translate_srt_files(file_paths=[str(next(iter(cfg.files)))], config=cfg)


def test_rate_limit_soft_throttle_tracks_per_language(tmp_path):
    """A soft 429 (no quota markers) is a transient burst — it should fall
    through to per-language tracking, NOT abort the whole batch. Otherwise
    a single 1-second throttle would lose the whole run."""
    cfg = _make_config(tmp_path, {"Spanish": "es", "French": "fr"})

    outcomes = {"es": _rate_limit("Rate limit reached. Please retry later."), "fr": None}
    with patch("srt_translator.core.main.SRTTranslator", side_effect=_make_factory(outcomes)):
        summary = translate_srt_files(file_paths=[str(next(iter(cfg.files)))], config=cfg)

    assert [item["code"] for item in summary["successful_languages"]] == ["fr"]
    assert [item["code"] for item in summary["failed_languages"]] == ["es"]
    assert summary["failed_languages"][0]["error_type"] == "RateLimitError"


def test_api_connection_error_aborts_whole_batch(tmp_path):
    """A persistent connection failure (after retries) won't be fixed by
    trying the next language. Abort instead of recording 12 identical
    APIConnectionError failures."""
    cfg = _make_config(tmp_path, {"Spanish": "es", "French": "fr"})

    conn_err = APIConnectionError(request=httpx.Request("POST", "https://api.openai.com/v1/x"))
    outcomes = {"es": conn_err, "fr": None}
    with patch("srt_translator.core.main.SRTTranslator", side_effect=_make_factory(outcomes)):
        with pytest.raises(APIConnectionError):
            translate_srt_files(file_paths=[str(next(iter(cfg.files)))], config=cfg)


# --------------------------------------------------------------------------- #
# Phase 3.1 cancel mechanism — stop_check polled between languages.
# --------------------------------------------------------------------------- #


def test_stop_check_breaks_loop_between_languages(tmp_path):
    """When stop_check() returns True between languages, the loop must break
    and the partial summary must reflect only the languages that completed
    before the cancel was signalled."""
    cfg = _make_config(tmp_path, {"Spanish": "es", "French": "fr", "German": "de"})

    # Simulate: stop_check returns False once (for "es"), then True (cancels
    # before "fr" starts). Languages that already completed stay in the
    # successful_languages list.
    calls = {"n": 0}

    def stop_check() -> bool:
        calls["n"] += 1
        return calls["n"] > 1  # False on the first iteration, True after

    with patch("srt_translator.core.main.SRTTranslator", side_effect=_make_factory({"es": None, "fr": None, "de": None})):
        summary = translate_srt_files(
            file_paths=[str(next(iter(cfg.files)))],
            config=cfg,
            stop_check=stop_check,
        )

    # First language ran, the rest were cancelled
    assert [item["code"] for item in summary["successful_languages"]] == ["es"]
    assert summary["failed_languages"] == []
    assert summary["cancelled"] is True


def test_summary_cancelled_flag_is_false_by_default(tmp_path):
    """When no cancellation occurs, the cancelled flag must be False so the
    main_window can distinguish a clean completion from a cancelled run."""
    cfg = _make_config(tmp_path, {"Spanish": "es"})

    with patch("srt_translator.core.main.SRTTranslator", side_effect=_make_factory({"es": None})):
        summary = translate_srt_files(file_paths=[str(next(iter(cfg.files)))], config=cfg)

    assert summary["cancelled"] is False


# --------------------------------------------------------------------------- #
# Phase 3.2 progress callback — on_language_done fires per successful language.
# --------------------------------------------------------------------------- #


def test_on_language_done_callback_fires_per_success(tmp_path):
    """The worker uses this callback to track progress for the Tier 2 banner's
    'N of M languages translated so far' line. It must fire exactly once per
    successful language and NOT fire for failures."""
    cfg = _make_config(tmp_path, {"Spanish": "es", "French": "fr", "German": "de"})

    calls = {"n": 0}

    def on_language_done():
        calls["n"] += 1

    outcomes = {
        "es": None,                            # success → callback should fire
        "fr": RuntimeError("simulated"),       # failure → callback should NOT fire
        "de": None,                            # success → callback should fire
    }
    with patch("srt_translator.core.main.SRTTranslator", side_effect=_make_factory(outcomes)):
        summary = translate_srt_files(
            file_paths=[str(next(iter(cfg.files)))],
            config=cfg,
            on_language_done=on_language_done,
        )

    assert calls["n"] == 2
    assert len(summary["successful_languages"]) == 2
    assert len(summary["failed_languages"]) == 1


def test_on_language_done_exception_does_not_break_loop(tmp_path):
    """The callback is on the GUI side; a broken callback must not abort the
    translation run. The per-success log records the exception but the loop
    continues."""
    cfg = _make_config(tmp_path, {"Spanish": "es", "French": "fr"})

    def boom():
        raise RuntimeError("GUI exploded")

    with patch("srt_translator.core.main.SRTTranslator", side_effect=_make_factory({"es": None, "fr": None})):
        summary = translate_srt_files(
            file_paths=[str(next(iter(cfg.files)))],
            config=cfg,
            on_language_done=boom,
        )

    # Both languages still complete despite the callback raising each time
    assert len(summary["successful_languages"]) == 2
    assert summary["failed_languages"] == []


# --------------------------------------------------------------------------- #
# Cancel edge cases — what happens at the boundaries.
# --------------------------------------------------------------------------- #


def test_stop_check_called_before_first_language_aborts_with_no_successes(tmp_path):
    """If the user clicks Cancel immediately after Translate, stop_check
    returns True on the very first poll. The loop must exit cleanly with
    zero successful languages and cancelled=True — no half-written outputs."""
    cfg = _make_config(tmp_path, {"Spanish": "es", "French": "fr"})

    def stop_check_always_true() -> bool:
        return True

    with patch("srt_translator.core.main.SRTTranslator", side_effect=_make_factory({"es": None, "fr": None})):
        summary = translate_srt_files(
            file_paths=[str(next(iter(cfg.files)))],
            config=cfg,
            stop_check=stop_check_always_true,
        )

    assert summary["successful_languages"] == []
    assert summary["failed_languages"] == []
    assert summary["cancelled"] is True


def test_stop_check_is_polled_before_every_language(tmp_path):
    """The contract: stop_check must be called at the top of each iteration
    so a click between languages takes effect within one language boundary
    (not after the whole batch finishes)."""
    cfg = _make_config(tmp_path, {"Spanish": "es", "French": "fr", "German": "de"})

    calls = {"n": 0}

    def stop_check() -> bool:
        calls["n"] += 1
        return False

    with patch("srt_translator.core.main.SRTTranslator", side_effect=_make_factory({"es": None, "fr": None, "de": None})):
        translate_srt_files(
            file_paths=[str(next(iter(cfg.files)))],
            config=cfg,
            stop_check=stop_check,
        )

    # 3 languages → 3 stop-check polls (one at the top of each iteration)
    assert calls["n"] == 3


def test_stop_check_none_default_does_not_crash(tmp_path):
    """Backward compat: callers (e.g. CLI) that don't pass stop_check must
    work — the per-language loop must guard the call site against None."""
    cfg = _make_config(tmp_path, {"Spanish": "es"})

    # Explicitly do NOT pass stop_check — defaults to None
    with patch("srt_translator.core.main.SRTTranslator", side_effect=_make_factory({"es": None})):
        summary = translate_srt_files(file_paths=[str(next(iter(cfg.files)))], config=cfg)

    assert summary["cancelled"] is False
    assert len(summary["successful_languages"]) == 1
