"""Shared retry helpers for OpenAI API calls."""

from __future__ import annotations


def parse_retry_after(exception: Exception) -> float | None:
    """Return the `Retry-After` header value (in seconds) from an OpenAI
    exception's response, or None when absent or unparseable.


    The OpenAI Python SDK exposes `.response` on `APIStatusError` subclasses
    (which include `RateLimitError`); other exception types may not have it.
    HTTP allows either delta-seconds or an HTTP-date format — we only parse
    the seconds form because OpenAI's 429 responses use it exclusively.
    """
    try:
        response = getattr(exception, "response", None)
        if response is None:
            return None
        value = response.headers.get("retry-after")
        if not value:
            return None
        return float(value)
    except (AttributeError, TypeError, ValueError):
        return None


def compute_retry_delay(
    attempt: int,
    *,
    base: float,
    cap: float,
    retry_after: float | None = None,
    max_total: float | None = None,
) -> float:
    """Compute the sleep duration before retry number `attempt` (1-indexed).

    Exponential backoff: `base * 2**(attempt-1)`, capped at `cap`. When the
    server provided a `retry_after` hint, we sleep at least that long, but
    we clamp to `max_total` to prevent a misbehaving server from parking
    a long-running batch for minutes.
    """
    backoff = min(cap, base * (2 ** (attempt - 1)))
    delay = max(backoff, retry_after) if retry_after is not None else backoff
    if max_total is not None:
        delay = min(delay, max_total)
    return delay
