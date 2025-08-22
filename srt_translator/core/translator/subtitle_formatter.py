"""
Subtitle formatter for applying per-subtitle formatting rules.

This module handles formatting individual subtitles according to language-specific
rules including CPS caps, wrapping, and orphan prevention.
"""

import logging
import math
import re
from typing import List, Tuple
from srt_translator.core.config.language_config import LanguageConfig


class SubtitleFormatter:
    """
    Applies per-subtitle formatting rules including CPS caps, wrapping, and orphan prevention.

    """

    def __init__(self, language_config: LanguageConfig):
        self.language_config = language_config
        self.logger = logging.getLogger(__name__)

    def apply_per_subtitle_formatting(
        self, text: str, start_ms: int, end_ms: int, lang: str
    ) -> str:
        """
        Apply per-subtitle formatting rules to translated text.

        This includes:
        - CPS soft/hard caps with overshoot policy
        - Smart word-boundary trimming with ellipsis
        - Max 2-line wrapping with orphan prevention
        - Tiny-window exceptions for very short subtitles

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

        # Get CPS limits for this language
        cps_caps = self.language_config.get_cps_caps(lang)
        cps_soft = cps_caps["cps_soft"]
        cps_hard = cps_caps["cps_hard"]

        # Use the new smart formatter
        return format_subtitle_text(
            lang_code=lang,
            text=text,
            start_ms=start_ms,
            end_ms=end_ms,
            cps_soft=cps_soft,
            cps_hard=cps_hard,
            overshoot_pct=0.10,  # 10% default overshoot
            tiny_threshold_s=1.0,  # 1 second threshold for tiny windows
            tiny_extra_pct=0.20,  # +20% extra for tiny windows
            max_lines=2,  # Maximum 2 lines per subtitle
        )


# --- helper: safe word-boundary trim with optional ellipsis -------------------
_WS_RE = re.compile(r"\s+")
_WORD_RE = re.compile(r"\w+|\S")


def _normalize_spaces(s: str) -> str:
    return _WS_RE.sub(" ", s).strip()


def _safe_trim_to_chars(s: str, max_chars: int, add_ellipsis: bool = True) -> str:
    """
    Trim string to <= max_chars on a word boundary. If we had to trim,
    optionally append an ellipsis '…'. Never return an empty string unless max_chars == 0.
    """
    if len(s) <= max_chars:
        return s
    if max_chars <= 0:
        return "" if not add_ellipsis else "…"

    # walk tokens until the next token would exceed the budget
    out = []
    used = 0
    for m in _WORD_RE.finditer(s):
        tok = m.group(0)
        step = (1 if used == 0 else 1) + len(tok)  # include space if not first
        if used + step > max_chars:
            break
        if used == 0:
            out.append(tok)
            used += len(tok)
        else:
            out.append(" ")
            out.append(tok)
            used += 1 + len(tok)
    joined = "".join(out).strip()
    if not joined:
        # couldn't keep any token; hard cut safely
        joined = s[:max_chars].rstrip()
    if add_ellipsis and len(joined) < len(s):
        # avoid double punctuation before ellipsis
        joined = joined.rstrip(" .,:;—-") + "…"
    return joined


# --- helper: two-line wrap with light orphan control -------------------------
_AVOID_LINE_START = {
    "es": {
        "y",
        "e",
        "o",
        "u",
        "a",
        "de",
        "del",
        "la",
        "el",
        "lo",
        "las",
        "los",
        "al",
        "que",
    },
}


def _wrap_two_lines(text: str, lang_code: str) -> str:
    """
    Greedy wrap into at most 2 lines. Balance lines if one is much longer.
    Avoid starting line 2 with very short function words (Spanish list).
    Assumes 'text' is already length-limited for CPS.
    """
    s = _normalize_spaces(text)
    if not s:
        return s
    words = s.split(" ")

    # More aggressive wrapping: wrap if text is long enough OR has enough words
    if len(words) <= 2 or len(s) < 40:  # Wrap if 3+ words OR 40+ characters
        return s

    # first pass: split near half
    total = sum(len(w) for w in words) + (len(words) - 1)
    target_first = math.ceil(total / 2)
    first, second = [], []
    used = 0
    for i, w in enumerate(words):
        step = (0 if i == 0 else 1) + len(w)
        if used + step <= target_first:
            first.append(w)
            used += step
        else:
            second = words[i:]
            break
    if not second:
        return " ".join(first)

    # orphan fix: avoid starting line 2 with very short function words
    avoid = _AVOID_LINE_START.get(lang_code.lower(), set())
    if (
        second
        and len(second[0]) <= 2
        and second[0].lower() in avoid
        and len(first) >= 2
    ):
        # move one token from end of first to start of second
        second.insert(0, first.pop())

    line1 = " ".join(first).strip()
    line2 = " ".join(second).strip()
    if not line1 or not line2:
        return s
    return f"{line1}\n{line2}"


# --- helper: compute allowed char budget for this window ---------------------
def _allowed_chars(
    duration_s: float,
    cps_soft: int,
    cps_hard: int,
    overshoot_pct: float,
    tiny_extra_pct: float,
    tiny_threshold_s: float,
) -> Tuple[int, int]:
    """
    Returns (soft_cap_chars, hard_cap_with_overshoot_chars) for this cue window.
    If duration < tiny_threshold_s, adds tiny_extra_pct to the overshoot budget.
    """
    soft_cap = int(math.floor(cps_soft * duration_s))
    hard_cap = int(math.floor(cps_hard * duration_s))
    extra = tiny_extra_pct if duration_s < tiny_threshold_s else 0.0
    hard_with_over = int(math.floor(hard_cap * (1.0 + overshoot_pct + extra)))
    return max(0, soft_cap), max(0, hard_with_over)


def format_subtitle_text(
    lang_code: str,
    text: str,
    start_ms: int,
    end_ms: int,
    cps_soft: int,
    cps_hard: int,
    overshoot_pct: float,
    tiny_threshold_s: float = 1.0,
    tiny_extra_pct: float = 0.20,
    max_lines: int = 2,
) -> str:
    """
    Format a single subtitle's text for the given time window.
    - Enforces CPS with a small overshoot allowance; adds extra allowance for very short windows.
    - Trims on word boundaries (adds ellipsis '…' if trimming occurred).
    - Reflows to at most 2 lines with light orphan control.

    Rule of thumb (documented):
      * Prefer not to trim; if we must, never cut mid-word.
      * Tiny windows (<1.0s) may exceed hard CPS by up to +20% to preserve short names/phrases.
      * Keep ≤2 lines for readability.
    """
    duration_s = max(0.001, (end_ms - start_ms) / 1000.0)
    s = text.strip()
    if not s:
        return s

    soft_cap, over_cap = _allowed_chars(
        duration_s, cps_soft, cps_hard, overshoot_pct, tiny_extra_pct, tiny_threshold_s
    )

    # Apply line wrapping first (before trimming)
    if max_lines >= 2:
        s_wrapped = _wrap_two_lines(s, lang_code)
        # Guard: if the wrap produced >2 lines (e.g., preexisting newlines), collapse then rewrap
        if s_wrapped.count("\n") > 1:
            s_wrapped = _wrap_two_lines(s.replace("\n", " "), lang_code)
        s = s_wrapped

    # Now apply CPS trimming if needed
    if len(s) > over_cap:
        logger = logging.getLogger(__name__)
        logger.info(
            f"Subtitle trim (lang={lang_code}): len={len(s)} > overshoot_cap={over_cap} "
            f"(soft_cap={soft_cap}, hard_cap={int(cps_hard*duration_s)}, overshoot={overshoot_pct*100:.1f}%, "
            f"tiny_extra={'yes' if duration_s < tiny_threshold_s else 'no'})"
        )
        s = _safe_trim_to_chars(_normalize_spaces(s), over_cap, add_ellipsis=True)

        # Re-apply wrapping after trimming to ensure we still have max 2 lines
        if (
            max_lines >= 2 and s.count("\n") == 0 and len(s) > 20
        ):  # Only re-wrap if it's long enough
            s_wrapped = _wrap_two_lines(s, lang_code)
            if s_wrapped.count("\n") == 1:  # Only use if it actually created 2 lines
                s = s_wrapped
    else:
        s = _normalize_spaces(s)

    return s
