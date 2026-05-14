"""Friendly GUI error classification utilities.

Each branch returns a dict with this shape:

  {
    "title":       <plain-English window title>,
    "message":     <one sentence the user can act on>,
    "suggestion":  <follow-up hint, may be empty>,
    "recoverable": <bool — "modal with one action" if False;
                   "user can wait & retry" if True>,
    "action_kind": <one of: "open_settings" | "open_url" | "wait_retry"
                    | "cancel_retry" | "retry" | "ok">,
    "action_url":  <only present when action_kind == "open_url">,
  }

The action_kind drives which primary action button `show_translation_error`
renders next to OK.
"""

from __future__ import annotations

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

_BILLING_URL = "https://platform.openai.com/account/billing/overview"


def get_error_details(error: Exception) -> dict:
    """Convert technical exceptions into user-friendly UI messages."""

    # ---------------- Authentication / permission ----------------
    if isinstance(error, AuthenticationError):
        return {
            "title": "Your API key was rejected",
            "message": "The OpenAI API key is invalid.",
            "suggestion": "Check the API key in Settings and try again.",
            "recoverable": False,
            "action_kind": "open_settings",
        }

    if isinstance(error, PermissionDeniedError):
        return {
            "title": "Permission denied",
            "message": "Your OpenAI account cannot access this model.",
            "suggestion": "Choose another model or check your OpenAI plan.",
            "recoverable": False,
            "action_kind": "open_settings",
        }

    if isinstance(error, NotFoundError):
        return {
            "title": "Model not found",
            "message": "The selected translation model does not exist.",
            "suggestion": "Select a valid model in Settings.",
            "recoverable": False,
            "action_kind": "open_settings",
        }

    # ---------------- Rate limit / quota --------------------------
    if isinstance(error, RateLimitError):
        detail = str(error).lower()
        if "quota" in detail or "billing" in detail or "insufficient_quota" in detail:
            return {
                "title": "Your OpenAI account is out of credits",
                "message": "OpenAI rejected the request because the quota is exhausted.",
                "suggestion": "Add billing/credits on platform.openai.com.",
                "recoverable": False,
                "action_kind": "open_url",
                "action_url": _BILLING_URL,
            }
        return {
            "title": "OpenAI is throttling requests",
            "message": "The API is rate limiting translation requests.",
            "suggestion": "Wait a minute, then retry.",
            "recoverable": True,
            "action_kind": "wait_retry",
        }

    # ---------------- Connection / timeout / server --------------
    if isinstance(error, APITimeoutError):
        return {
            "title": "Request timed out",
            "message": "OpenAI did not respond in time.",
            "suggestion": "Check your internet connection and retry.",
            "recoverable": True,
            "action_kind": "cancel_retry",
        }

    if isinstance(error, APIConnectionError):
        return {
            "title": "Internet connection lost",
            "message": "The app could not reach OpenAI.",
            "suggestion": "Reconnect to the internet and retry.",
            "recoverable": True,
            "action_kind": "cancel_retry",
        }

    if isinstance(error, InternalServerError):
        return {
            "title": "OpenAI server issue",
            "message": "OpenAI is currently experiencing server problems.",
            "suggestion": "Wait a few minutes and retry.",
            "recoverable": True,
            "action_kind": "retry",
        }

    # ---------------- Bad request -------------------------------
    if isinstance(error, BadRequestError):
        return {
            "title": "Invalid translation request",
            "message": str(error),
            "suggestion": "Check the translation input and try again.",
            "recoverable": False,
            "action_kind": "ok",
        }

    # ---------------- Invalid model (wrapped) -------------------
    raw = str(error)
    if "Invalid translation model" in raw:
        return {
            "title": "Invalid translation model",
            "message": raw,
            "suggestion": "Select a valid model in Settings.",
            "recoverable": False,
            "action_kind": "open_settings",
        }

    # ---------------- Fallback ----------------------------------
    return {
        "title": "Translation failed",
        "message": raw or "An unexpected error occurred during translation.",
        "suggestion": "Check the logs for more details.",
        "recoverable": False,
        "action_kind": "ok",
    }
