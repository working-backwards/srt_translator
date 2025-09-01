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
