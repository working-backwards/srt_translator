"""Table-driven tests for `gui.utils.error_classifier.get_error_details`."""

import httpx
import pytest
from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
)

from srt_translator.gui.utils.error_classifier import get_error_details

_REQ = httpx.Request("POST", "https://api.openai.com/v1/x")


def _resp(status: int) -> httpx.Response:
    return httpx.Response(status, request=_REQ)


def _auth() -> AuthenticationError:
    return AuthenticationError("bad key", response=_resp(401), body=None)


def _perm() -> PermissionDeniedError:
    return PermissionDeniedError("no access", response=_resp(403), body=None)


def _not_found() -> NotFoundError:
    return NotFoundError("missing model", response=_resp(404), body=None)


def _rate_limit_quota() -> RateLimitError:
    return RateLimitError("insufficient_quota", response=_resp(429), body=None)


def _rate_limit_soft() -> RateLimitError:
    return RateLimitError("too many requests", response=_resp(429), body=None)


def _timeout() -> APITimeoutError:
    return APITimeoutError(_REQ)


def _connection() -> APIConnectionError:
    return APIConnectionError(request=_REQ)


def _server() -> InternalServerError:
    return InternalServerError("oops", response=_resp(500), body=None)


def _bad_request() -> BadRequestError:
    return BadRequestError("input too long", response=_resp(400), body=None)


def _wrapped_invalid_model() -> RuntimeError:
    return RuntimeError("Invalid translation model 'gpt-bogus'. Check Settings.")


CASES = [
    (_auth(), "Your API key was rejected", False, "open_settings"),
    (_perm(), "Permission denied", False, "open_settings"),
    (_not_found(), "Model not found", False, "open_settings"),
    (_rate_limit_quota(), "Your OpenAI account is out of credits", False, "open_url"),
    (_rate_limit_soft(), "OpenAI is throttling requests", True, "wait_retry"),
    (_timeout(), "Request timed out", True, "cancel_retry"),
    (_connection(), "Internet connection lost", True, "cancel_retry"),
    (_server(), "OpenAI server issue", True, "retry"),
    (_bad_request(), "Invalid translation request", False, "ok"),
    (_wrapped_invalid_model(), "Invalid translation model", False, "open_settings"),
    (RuntimeError("something nobody saw coming"), "Translation failed", False, "ok"),
]


@pytest.mark.parametrize(("err", "expected_title", "recoverable", "action"), CASES)
def test_get_error_details_returns_well_formed_dict(err, expected_title, recoverable, action):
    """Every branch must populate title/message/suggestion/recoverable/action_kind."""
    details = get_error_details(err)

    assert isinstance(details, dict), "Classifier must never return None"
    assert details["title"] == expected_title
    assert details["recoverable"] is recoverable
    assert details["action_kind"] == action
    assert details["message"], "message must be non-empty for the dialog"
    # suggestion is allowed to be empty, but the key must exist
    assert "suggestion" in details


def test_quota_branch_includes_billing_url():
    """The "out of credits" branch must point users at the OpenAI billing page."""
    details = get_error_details(_rate_limit_quota())

    assert details["action_kind"] == "open_url"
    assert details["action_url"].startswith("https://platform.openai.com")


def test_fallback_handles_exception_with_empty_str():
    """A raise with no message must still produce a usable dialog, not blank."""

    class Nameless(Exception):
        pass

    details = get_error_details(Nameless())

    assert details["title"] == "Translation failed"
    assert details["message"], "Fallback must substitute a non-empty placeholder"
    assert details["action_kind"] == "ok"


def test_recoverable_flag_drives_icon_choice():
    """Recoverable=True is the contract show_translation_error uses to pick
    QMessageBox.Warning instead of Critical."""
    transient = [_rate_limit_soft(), _timeout(), _connection(), _server()]
    fatal = [_auth(), _perm(), _not_found(), _rate_limit_quota(), _bad_request()]

    assert all(get_error_details(e)["recoverable"] is True for e in transient)
    assert all(get_error_details(e)["recoverable"] is False for e in fatal)
