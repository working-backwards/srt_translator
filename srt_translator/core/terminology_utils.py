#!/usr/bin/env python3
"""
Terminology utilities for SRT Translator.
Handles DNT filtering, hard-preserve detection, and effective DNT building.
"""

import re
from typing import Dict, List, Tuple


def is_numeric_like(text: str) -> bool:
    """Check if text contains number-like patterns that should be filtered out"""
    if not text or not text.strip():
        return False

    # Remove common numeric separators
    cleaned = re.sub(r"[,\s]", "", text)

    # Check if it's just digits and decimal points
    if re.match(r"^\d*\.?\d+$", cleaned):
        return True

    # Patterns that suggest numeric content
    number_patterns = [
        r"\d+\s*(?:milliseconds?|ms|seconds?|s|minutes?|min|hours?|hrs?)",
        r"\d+\.\d+",  # Decimal numbers
        r"\d{4}",  # Years
        r"\d{1,2}:\d{2}",  # Time formats
        r"\d+%",  # Percentages
        r"\$\d+",  # Currency
    ]

    normalized_text = text.lower().strip()
    return any(re.search(pattern, normalized_text) for pattern in number_patterns)


def is_hard_preserve(text: str) -> bool:
    """Check if a term should be hard-preserved (always kept in DNT)"""
    if not text or not text.strip():
        return False

    # Acronyms and alphanumeric tech tokens
    if re.match(r"^[A-Z0-9]{2,}$", text.strip()):
        return True

    # Product names, software, brands (common patterns)
    tech_patterns = [
        r"^[A-Z][a-z]+(?:[A-Z][a-z]+)*$",  # CamelCase
        r"^[A-Z][a-z]+\s+[A-Z][a-z]+$",  # Title Case
        r"^[a-z]+(?:[A-Z][a-z]+)*$",  # camelCase
    ]

    if any(re.match(pattern, text.strip()) for pattern in tech_patterns):
        return True

    return False


def partition_hard_preserve(terms: List[str]) -> Tuple[List[str], List[str]]:
    """Partition terms into hard-preserve and soft-preserve categories"""
    hard_preserve = []
    soft_preserve = []

    for term in terms:
        if is_hard_preserve(term):
            hard_preserve.append(term)
        else:
            soft_preserve.append(term)

    return hard_preserve, soft_preserve


def build_effective_dnt(dnt_terms: List[str], termbase: Dict[str, str]) -> List[str]:
    """
    Build effective DNT list with Termbase → DNT precedence.

    Hard-preserve terms (acronyms, codes) always stay in DNT.
    Soft-preserve terms are removed if they appear in termbase.
    """
    if not dnt_terms:
        return []

    # Partition DNT terms
    hard_preserve, soft_preserve = partition_hard_preserve(dnt_terms)

    # Filter soft-preserve terms based on termbase
    effective_soft = [term for term in soft_preserve if term not in termbase]

    # Combine hard-preserve (always kept) with filtered soft-preserve
    effective_dnt = hard_preserve + effective_soft

    return sorted(effective_dnt, key=str.lower)


def filter_dnt_terms_with_metadata(dnt_terms: List[str]) -> Tuple[List[str], List[str]]:
    """
    Filter DNT terms and return both filtered terms and metadata about what was filtered out.

    Args:
        dnt_terms: List of DNT terms to filter

    Returns:
        Tuple of (filtered_terms, filtered_out_terms)
    """
    if not dnt_terms:
        return [], []

    filtered_terms = []
    filtered_out = []

    for term in dnt_terms:
        if not term or not term.strip():
            continue

        # Skip numeric and number-like terms
        if is_numeric_like(term):
            filtered_out.append(f"{term} (filtered: numeric/number-like)")
            continue

        filtered_terms.append(term)

    return filtered_terms, filtered_out
