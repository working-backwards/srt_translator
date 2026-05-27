"""Unit tests for srt_translator.core.retry"""

import httpx
import pytest
from openai import APIConnectionError, APITimeoutError, RateLimitError

from srt_translator.core.retry import compute_retry_delay, parse_retry_after

_REQ = httpx.Request("POST", "https://api.openai.com/v1/x")


# --------------------------------------------------------------------------- #
# compute_retry_delay
# --------------------------------------------------------------------------- #


def test_compute_retry_delay_exponential_backoff_anchor():
    """Attempt 1 is the base delay; subsequent attempts double until capped."""
    assert compute_retry_delay(1, base=5, cap=30) == 5
    assert compute_retry_delay(2, base=5, cap=30) == 10
    assert compute_retry_delay(3, base=5, cap=30) == 20
    assert compute_retry_delay(4, base=5, cap=30) == 30  # capped
    assert compute_retry_delay(5, base=5, cap=30) == 30  # stays capped


def test_compute_retry_delay_respects_cap_from_first_attempt():
    """If base already exceeds the cap, the cap wins from attempt 1."""
    assert compute_retry_delay(1, base=100, cap=10) == 10
    assert compute_retry_delay(5, base=100, cap=10) == 10


@pytest.mark.parametrize("attempt", [1, 2, 3, 8])
def test_compute_retry_delay_honors_retry_after_when_longer(attempt):
    """Server's Retry-After overrides exponential backoff when longer."""
    backoff_only = compute_retry_delay(attempt, base=5, cap=30)
    server_hint = backoff_only + 50  # explicitly larger
    delay = compute_retry_delay(attempt, base=5, cap=30, retry_after=server_hint)
    assert delay == server_hint


def test_compute_retry_delay_ignores_retry_after_when_shorter():
    """When server hint is shorter than our backoff, our backoff wins."""
    # Backoff for attempt 4 = min(5*8, 30) = 30; server hints 2s
    delay = compute_retry_delay(4, base=5, cap=30, retry_after=2.0)
    assert delay == 30


def test_compute_retry_delay_max_total_clamps_a_misbehaving_server():
    """A server that returns Retry-After: 9999 must not park us for hours."""
    delay = compute_retry_delay(1, base=5, cap=30, retry_after=9999.0, max_total=60.0)
    assert delay == 60.0


def test_compute_retry_delay_max_total_does_not_shorten_normal_backoff():
    """max_total is an upper clamp; it must not force-shorten a fine delay."""
    delay = compute_retry_delay(2, base=5, cap=30, max_total=60.0)
    assert delay == 10  # exp backoff value, well below 60


def test_compute_retry_delay_retry_after_none_falls_back_to_backoff():
    """retry_after=None is the common case — the helper must work without it."""
    assert compute_retry_delay(3, base=5, cap=30, retry_after=None) == 20


# --------------------------------------------------------------------------- #
# parse_retry_after
# --------------------------------------------------------------------------- #


def test_parse_retry_after_extracts_seconds_from_rate_limit_response():
    """OpenAI's 429 includes Retry-After in seconds; parser returns it as float."""
    response = httpx.Response(429, headers={"retry-after": "42"}, request=_REQ)
    err = RateLimitError("throttled", response=response, body=None)

    assert parse_retry_after(err) == 42.0


def test_parse_retry_after_returns_none_when_header_missing():
    """No Retry-After header → None, so the caller falls back to its own backoff."""
    response = httpx.Response(429, request=_REQ)  # no headers
    err = RateLimitError("throttled", response=response, body=None)

    assert parse_retry_after(err) is None


def test_parse_retry_after_returns_none_when_header_unparseable():
    """HTTP-date format is allowed by the spec but OpenAI doesn't send it; we
    treat any non-numeric value as 'no hint' rather than crash."""
    response = httpx.Response(429, headers={"retry-after": "Mon, 12 May 2026 12:00:00 GMT"}, request=_REQ)
    err = RateLimitError("throttled", response=response, body=None)

    assert parse_retry_after(err) is None


def test_parse_retry_after_returns_none_for_exception_without_response():
    """APIConnectionError doesn't carry a response object."""
    err = APIConnectionError(request=_REQ)

    assert parse_retry_after(err) is None


def test_parse_retry_after_returns_none_for_timeout():
    """APITimeoutError also has no response with headers."""
    err = APITimeoutError(_REQ)

    assert parse_retry_after(err) is None


def test_parse_retry_after_handles_arbitrary_exception_safely():
    """The helper must never crash on an unexpected exception type."""

    class Custom(Exception):
        pass

    assert parse_retry_after(Custom()) is None


def test_parse_retry_after_handles_attribute_error_on_response():
    """Defensive: if .response is set to something without .headers, return None."""
    err = RuntimeError("custom error")
    err.response = object()  # has no headers attr

    assert parse_retry_after(err) is None


def test_parse_retry_after_returns_none_for_empty_string_header():
    """An empty header value should be treated as no hint."""
    response = httpx.Response(429, headers={"retry-after": ""}, request=_REQ)
    err = RateLimitError("throttled", response=response, body=None)

    assert parse_retry_after(err) is None


# --------------------------------------------------------------------------- #
# Combined behavior — the real use case
# --------------------------------------------------------------------------- #


def test_compute_retry_delay_with_parse_retry_after_round_trip():
    """The two helpers are designed to be used together."""
    response = httpx.Response(429, headers={"retry-after": "15"}, request=_REQ)
    err = RateLimitError("throttled", response=response, body=None)

    # attempt 1 backoff = 5; server says 15 → 15 wins
    delay = compute_retry_delay(1, base=5, cap=30, retry_after=parse_retry_after(err))
    assert delay == 15

    # attempt 3 backoff = 20; server says 15 → backoff wins
    delay = compute_retry_delay(3, base=5, cap=30, retry_after=parse_retry_after(err))
    assert delay == 20
