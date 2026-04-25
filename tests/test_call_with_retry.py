"""Unit tests for _call_with_retry in srt_translator.gui.ai_config.

Covers exponential-backoff retry on transient OpenAI errors during the
per-language termbase API call. Pre-fix, a single APITimeoutError on a
6-minute call dropped the language silently; this helper retries 2x with
exponential backoff so transient timeouts don't cost the language.
"""

from unittest.mock import MagicMock

import httpx
import pytest
from openai import APIConnectionError, APITimeoutError, RateLimitError

from srt_translator.core.constants import (
    PER_LANGUAGE_RETRY_ATTEMPTS,
    PER_LANGUAGE_RETRY_BACKOFF_BASE_S,
    PER_LANGUAGE_RETRY_BACKOFF_CAP_S,
)
from srt_translator.gui.ai_config import _call_with_retry


def _make_logger():
    return MagicMock()


def _make_sleep():
    """Track sleep durations without actually sleeping."""
    durations: list[float] = []

    def fake_sleep(s):
        durations.append(s)

    return fake_sleep, durations


def _timeout(msg="timeout"):
    # APITimeoutError requires an httpx.Request to construct.
    return APITimeoutError(httpx.Request("POST", "https://api.openai.com/v1/x"))


def _connection_error(msg="connection"):
    return APIConnectionError(request=httpx.Request("POST", "https://api.openai.com/v1/x"))


def _rate_limit():
    # RateLimitError needs a response object.
    response = httpx.Response(429, request=httpx.Request("POST", "https://api.openai.com/v1/x"))
    return RateLimitError("rate limited", response=response, body=None)


def test_returns_result_on_first_success_no_retry():
    create_fn = MagicMock(return_value="ok")
    sleep_fn, durations = _make_sleep()

    result = _call_with_retry(
        create_fn,
        context="en",
        logger=_make_logger(),
        sleep_fn=sleep_fn,
    )

    assert result == "ok"
    assert create_fn.call_count == 1
    assert durations == []


def test_retries_on_timeout_then_succeeds():
    """The original bug pattern: transient timeout, succeed on retry."""
    create_fn = MagicMock(side_effect=[_timeout(), "ok"])
    sleep_fn, durations = _make_sleep()

    result = _call_with_retry(
        create_fn,
        context="ja",
        logger=_make_logger(),
        sleep_fn=sleep_fn,
    )

    assert result == "ok"
    assert create_fn.call_count == 2
    assert durations == [PER_LANGUAGE_RETRY_BACKOFF_BASE_S]


def test_retries_use_exponential_backoff():
    """Retry 1 = base, retry 2 = 2*base (exponential, multiplier=2)."""
    create_fn = MagicMock(side_effect=[_timeout(), _timeout(), "ok"])
    sleep_fn, durations = _make_sleep()

    result = _call_with_retry(
        create_fn,
        context="de",
        logger=_make_logger(),
        sleep_fn=sleep_fn,
        attempts=2,
        base_backoff_s=5.0,
        cap_backoff_s=30.0,
    )

    assert result == "ok"
    assert create_fn.call_count == 3
    # Exponential: attempt 0 fails -> sleep 5s, attempt 1 fails -> sleep 10s, attempt 2 succeeds
    assert durations == [5.0, 10.0]


def test_backoff_is_clamped_to_cap():
    create_fn = MagicMock(side_effect=[_timeout(), _timeout(), _timeout(), _timeout(), "ok"])
    sleep_fn, durations = _make_sleep()

    _call_with_retry(
        create_fn,
        context="fr",
        logger=_make_logger(),
        sleep_fn=sleep_fn,
        attempts=4,
        base_backoff_s=5.0,
        cap_backoff_s=12.0,
    )

    # 5, 10, 20→12, 40→12
    assert durations == [5.0, 10.0, 12.0, 12.0]


def test_raises_after_exhausting_retries():
    """If every attempt fails with a retryable error, the last one
    propagates so the caller can record a real failure rather than
    silently get an empty result."""
    final_err = _timeout("final")
    create_fn = MagicMock(side_effect=[_timeout(), _timeout(), final_err])
    sleep_fn, _ = _make_sleep()

    with pytest.raises(APITimeoutError):
        _call_with_retry(
            create_fn,
            context="es",
            logger=_make_logger(),
            sleep_fn=sleep_fn,
            attempts=2,
        )

    assert create_fn.call_count == 3


def test_retries_on_connection_error():
    create_fn = MagicMock(side_effect=[_connection_error(), "ok"])
    sleep_fn, _ = _make_sleep()

    result = _call_with_retry(create_fn, context="it", logger=_make_logger(), sleep_fn=sleep_fn)

    assert result == "ok"
    assert create_fn.call_count == 2


def test_retries_on_rate_limit_error():
    create_fn = MagicMock(side_effect=[_rate_limit(), "ok"])
    sleep_fn, _ = _make_sleep()

    result = _call_with_retry(create_fn, context="ar", logger=_make_logger(), sleep_fn=sleep_fn)

    assert result == "ok"
    assert create_fn.call_count == 2


def test_does_not_retry_on_non_retryable_exception():
    """Non-transient errors (e.g. 401 auth, malformed JSON) should
    propagate immediately so callers can react instead of silently
    waiting through retries."""
    create_fn = MagicMock(side_effect=ValueError("not retryable"))
    sleep_fn, durations = _make_sleep()

    with pytest.raises(ValueError):
        _call_with_retry(create_fn, context="vi", logger=_make_logger(), sleep_fn=sleep_fn)

    assert create_fn.call_count == 1
    assert durations == []


def test_logs_retry_with_context():
    create_fn = MagicMock(side_effect=[_timeout(), "ok"])
    sleep_fn, _ = _make_sleep()
    logger = _make_logger()

    _call_with_retry(create_fn, context="zh-Hans", logger=logger, sleep_fn=sleep_fn)

    logger.warning.assert_called_once()
    args = logger.warning.call_args.args
    # Format: ("[%s] %s on attempt %d/%d; retrying in %.1fs: %s", lang, type, n, total, backoff, ex)
    assert args[1] == "zh-Hans"  # context appears in log
    assert args[2] == "APITimeoutError"  # exception type name


def test_default_attempts_match_constant():
    """Sanity check that the default attempts matches the configured
    constant, so changing the constant changes runtime behavior."""
    create_fn = MagicMock(side_effect=[_timeout()] * (PER_LANGUAGE_RETRY_ATTEMPTS + 1))
    sleep_fn, _ = _make_sleep()

    with pytest.raises(APITimeoutError):
        _call_with_retry(create_fn, context="tr", logger=_make_logger(), sleep_fn=sleep_fn)

    # PER_LANGUAGE_RETRY_ATTEMPTS=2 means we call 3 times total (initial + 2 retries)
    assert create_fn.call_count == PER_LANGUAGE_RETRY_ATTEMPTS + 1


def test_constants_are_sane():
    """Sanity bounds to catch accidental regressions in the policy values."""
    assert PER_LANGUAGE_RETRY_ATTEMPTS >= 1
    assert PER_LANGUAGE_RETRY_BACKOFF_BASE_S > 0
    assert PER_LANGUAGE_RETRY_BACKOFF_CAP_S >= PER_LANGUAGE_RETRY_BACKOFF_BASE_S
