# srt_translator/core/services/language_detection.py
import logging

from srt_translator.config.model_config_loader import build_call_params
from srt_translator.core.constants import (
    DEFAULT_DETECTION_MODEL,
    MAX_COMPLETION_TOKENS_LANGUAGE_DETECTION,
)
from srt_translator.prompts.detection import build_language_detection_prompt

# Detection-specific temperature. Low value because this is a deterministic
# classification task — we want the same answer for the same input. Hardcoded
# (not user-tunable) because creators have no basis for choosing it; if the
# detection model is ever swapped to one that ignores temperature, the value
# is silently dropped by build_call_params() and that is fine.
_DETECTION_TEMPERATURE = 0.1

logger = logging.getLogger(__name__)


def detect_source_language(
    text: str,
    *,
    chat,  # object exposing .chat.completions.create(...)
    language_config: object | None = None,
    sample_chars: int = 2000,
) -> dict[str, object]:
    """
    Detect the source language of `text` using DEFAULT_DETECTION_MODEL.

    Detection is intentionally decoupled from the user's generation /
    translation model choice. It is a small classification task that benefits
    from a fast, deterministic, non-reasoning model — paying a reasoning
    model's reasoning-token tax for it is wasted compute and risks empty
    responses when the token budget is small. See model-config-plan.md.

    Returns:
      {
        "detected_code": str|None,     # raw BCP-47 guess (e.g., "en", "es", "zh-Hans", "pt-BR")
        "normalized_code": str|None,   # mapped to app-supported code if language_config provided
        "normalized_name": str|None,   # human-readable name (via language_config)
        "confidence": float,           # 0..1 (model self-report)
        "mixed": bool                  # true if multiple sources detected
      }
    Never raises; returns a safe empty structure on failure (and logs why).
    """
    text = (text or "")[:sample_chars]
    if not text.strip():
        logger.warning("Language detection skipped: empty transcript sample")
        return {
            "detected_code": None,
            "normalized_code": None,
            "normalized_name": None,
            "confidence": 0.0,
            "mixed": False,
        }

    prompt = build_language_detection_prompt(text)

    try:
        params = {
            "model": DEFAULT_DETECTION_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
            **build_call_params(
                DEFAULT_DETECTION_MODEL,
                max_completion_tokens=MAX_COMPLETION_TOKENS_LANGUAGE_DETECTION,
                temperature=_DETECTION_TEMPERATURE,
            ),
        }

        import json

        response = chat.chat.completions.create(**params)
        raw = (response.choices[0].message.content or "").strip()
        if not raw:
            logger.warning(
                "Language detection returned empty content (model=%s); see "
                "MAX_COMPLETION_TOKENS_LANGUAGE_DETECTION and "
                "REASONING_MODEL_COMPLETION_TOKEN_FLOOR if this recurs",
                DEFAULT_DETECTION_MODEL,
            )
        data = json.loads(raw or "{}")
        detected = (data.get("detected_code") or "").strip()
        confidence = float(data.get("confidence") or 0.0)
        mixed = bool(data.get("mixed") or False)

        norm = name = None
        if language_config and detected:
            try:
                norm = language_config.closest_supported_code(detected)  # type: ignore
                if norm:
                    name = language_config.get_language_name(norm)  # type: ignore
            except Exception as ex:
                logger.warning(
                    "Language detection: normalization failed for code=%r: %s",
                    detected,
                    ex,
                )
                norm, name = None, None

        if detected and not norm and language_config:
            logger.warning(
                "Language detection: model returned %r which could not be normalized to a supported language code",
                detected,
            )

        return {
            "detected_code": detected or None,
            "normalized_code": norm,
            "normalized_name": name,
            "confidence": confidence,
            "mixed": mixed,
        }
    except Exception as ex:
        logger.warning(
            "Language detection failed (model=%s): %s: %s",
            DEFAULT_DETECTION_MODEL,
            type(ex).__name__,
            ex,
        )
        return {
            "detected_code": None,
            "normalized_code": None,
            "normalized_name": None,
            "confidence": 0.0,
            "mixed": False,
        }
