"""
Core data structures for the utterance-based reflow translation system.
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


@dataclass
class Subtitle:
    """Light wrapper for subtitle data used internally."""
    index: int
    start_ms: int
    end_ms: int
    text: str


@dataclass
class Utterance:
    """Internal concept: a contiguous run of subtitles that forms one sentence/thought."""
    sub_start: int           # position in the subtitles list (0-based)
    sub_end: int             # inclusive
    text_src: str            # concatenated source text for this span
    subtitles: List[Subtitle]
    lang_code: str


class ErrorPolicy(Enum):
    """Error handling policy for reflow failures."""
    STRICT = "STRICT"        # Default for publish: fail run on any utterance failure
    BOUNDED = "BOUNDED"      # Allow K exceptions or P% of file (whichever smaller)
    DEV = "DEV"              # Allow pass-through for any failing utterance


@dataclass
class TranslationConfig:
    """Configuration for translation behavior."""
    error_policy: ErrorPolicy = ErrorPolicy.STRICT
    max_concurrency: int = 1
    bounded_max_exceptions: int = 2
    bounded_max_percent: float = 0.5
