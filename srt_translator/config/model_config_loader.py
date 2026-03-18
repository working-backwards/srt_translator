import json
from pathlib import Path
from typing import Any

from srt_translator.core.constants import MAX_INLINE_TOKENS

CONFIG_FILE = Path(__file__).parent / "model_config.json"

with open(CONFIG_FILE, encoding="utf-8") as f:
    MODEL_CONFIG: dict[str, dict[str, Any]] = json.load(f)


def get_model_config(model_name: str) -> dict[str, Any]:
    """model_name: could be generator model or translator model"""
    return MODEL_CONFIG.get(model_name, {})


def get_max_inline_tokens(generation_model_name: str) -> int:
    """Max transcript tokens to send inline; falls back to the old constant value."""
    return int(get_model_config(generation_model_name).get("max_inline_tokens", MAX_INLINE_TOKENS))


def build_call_params(
    model_name: str,
    *,
    max_completion_tokens: int,
    temperature: float | None = None,
    frequency_penalty: float | None = None,
    presence_penalty: float | None = None,
) -> dict[str, Any]:
    """Build the kwargs dict for client.chat.completions.create(),
    omitting parameters unsupported by the given model and injecting
    model-specific parameters (e.g. reasoning_effort for gpt-5-mini).

    max_completion_tokens is automatically clamped to the model's
    max_output_tokens ceiling so that callers can use large constants
    (sized for reasoning models) without causing API errors on standard
    models whose output ceiling is lower.

    Callers may freely add extra keys (e.g. 'stop', 'response_format')
    to the returned dict after the call.
    """
    cfg = get_model_config(model_name)
    safe_limit = min(max_completion_tokens, cfg.get("max_output_tokens", 16384))
    params: dict[str, Any] = {"max_completion_tokens": safe_limit}

    if cfg.get("supports_temperature", True) and temperature is not None:
        params["temperature"] = temperature

    if cfg.get("supports_sampling_penalties", True):
        if frequency_penalty is not None:
            params["frequency_penalty"] = frequency_penalty
        if presence_penalty is not None:
            params["presence_penalty"] = presence_penalty

    reasoning_effort = cfg.get("reasoning_effort")
    if reasoning_effort is not None:
        params["reasoning_effort"] = reasoning_effort

    return params
