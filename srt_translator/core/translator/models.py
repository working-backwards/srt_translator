"""
Core data structures for subtitle translation processing.

IMPORTANT: Naming Convention to Avoid Library Conflicts
======================================================

This module defines internal data structures that are distinct from the srt library's
classes. We use explicit naming to prevent import conflicts:

- InternalSubtitle: Our custom class for internal processing
- srt.Subtitle: The library class for SRT file I/O

Usage Pattern:
1. Parse SRT files using srt.Subtitle (library class)
2. Convert to InternalSubtitle for our processing logic
3. Convert back to srt.Subtitle for output writing

This separation ensures we never accidentally use the wrong class and maintains
clear boundaries between external library functionality and our internal logic.
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


@dataclass
class InternalSubtitle:
    """
    Internal subtitle representation for translation processing.
    
    This class is distinct from srt.Subtitle to avoid naming conflicts.
    We use this for all internal data manipulation and translation processing.
    When writing output, we convert back to srt.Subtitle.
    
    Attributes:
        index: Subtitle index (1-based, matching SRT format)
        start_ms: Start time in milliseconds
        end_ms: End time in milliseconds  
        text: Subtitle text content
    """
    index: int
    start_ms: int
    end_ms: int
    text: str


class ErrorPolicy(Enum):
    """
    Error handling policy for translation failures.
    
    Controls how the system behaves when translation processing encounters errors:
    
    - STRICT: Fail the entire translation on any error (production default)
    - BOUNDED: Allow limited exceptions before failing (development/testing)
    - DEV: Allow pass-through for any failing subtitle (debugging only)
    """
    STRICT = "STRICT"        # Default for publish: fail run on any error
    BOUNDED = "BOUNDED"      # Allow K exceptions or P% of file (whichever smaller)
    DEV = "DEV"              # Allow pass-through for any failing subtitle


@dataclass
class TranslationConfig:
    """
    Configuration for translation behavior.
    
    This contains all the parameters needed for the subtitle-based translation
    system, including error handling policies and performance settings.
    
    Attributes:
        error_policy: How to handle translation processing failures
        max_concurrency: Maximum parallel translation threads
        bounded_max_exceptions: Max exceptions allowed in BOUNDED mode
        bounded_max_percent: Max percentage of file that can fail in BOUNDED mode
    """
    error_policy: ErrorPolicy = ErrorPolicy.STRICT
    max_concurrency: int = 1
    bounded_max_exceptions: int = 2
    bounded_max_percent: float = 0.5
