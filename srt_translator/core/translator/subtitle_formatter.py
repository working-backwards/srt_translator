"""
Subtitle formatter for applying per-subtitle formatting rules.

This module handles formatting individual subtitles according to language-specific
rules including CPS caps, wrapping, and orphan prevention.
"""

import logging
import re

from srt_translator.core.config.language_config import LanguageConfig


class SubtitleFormatter:
    """Single-cap, warn-only formatting; no reflow, no trimming."""

    def __init__(self, language_config: LanguageConfig):
        self.language_config = language_config
        self.logger = logging.getLogger(__name__)

    def apply_per_subtitle_formatting(
        self, text: str, start_ms: int, end_ms: int, lang: str
    ) -> str:
        """
        Apply per-subtitle formatting rules to translated text.

        This includes:
        - CPS cap enforcement with warning-only policy
        - Space normalization
        - No reflow or trimming

        Args:
            text: Translated text to format
            start_ms: Subtitle start time in milliseconds
            end_ms: Subtitle end time in milliseconds
            lang: Target language code

        Returns:
            Formatted text ready for the subtitle
        """
        if not text.strip():
            return text

        cps_cap = self.language_config.get_cps_cap(lang)
        return format_subtitle_text(
            lang_code=lang, text=text, start_ms=start_ms, end_ms=end_ms, cps_cap=cps_cap
        )


# --- helper: normalize spaces -------------------
_WS_RE = re.compile(r"\s+")


def _normalize_spaces(s: str) -> str:
    return _WS_RE.sub(" ", s).strip()


# Reflow / ES-specific wrapping removed.


def _duration_seconds(start_ms: int, end_ms: int) -> float:
    return max(0.001, (end_ms - start_ms) / 1000.0)


def format_subtitle_text(
    *, lang_code: str, text: str, start_ms: int, end_ms: int, cps_cap: int
) -> str:
    """Normalize spaces; warn if CPS exceeds cap; never reflow or trim."""
    s = _normalize_spaces(text or "")
    if not s:
        return s
    dur = _duration_seconds(start_ms, end_ms)
    cps = len(s.replace("\n", "")) / dur
    if cps > max(1, int(cps_cap)):
        logging.getLogger(__name__).warning(
            "CPS over cap (lang=%s): cps=%.2f > cap=%d (chars=%d, dur=%.3fs)",
            lang_code,
            cps,
            cps_cap,
            len(s.replace("\n", "")),
            dur,
        )
    return s
