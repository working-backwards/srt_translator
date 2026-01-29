#!/usr/bin/env python3
"""
Utility functions for merging user-provided termbase and DNT terms with AI-generated ones.
"""

import json
import logging


def merge_dnt_terms(
    ai_generated: list[str], user_provided: list[str] | None = None
) -> list[str]:
    """
    Merge AI-generated DNT terms with user-provided DNT terms.
    
    Strategy:
    - User-provided terms take precedence (added first)
    - AI-generated terms are added if not already present (case-insensitive)
    - Returns sorted, deduplicated list
    
    Args:
        ai_generated: List of AI-generated DNT terms
        user_provided: Optional list of user-provided DNT terms
        
    Returns:
        Merged and deduplicated list of DNT terms
    """

    if not ai_generated:
        ai_generated = []

    if not user_provided:
        return sorted(set(ai_generated), key=str.lower)
    
    # Start with user-provided terms (they take precedence)
    merged = []
    seen_lower = set()
    
    # Add user-provided terms first
    for term in user_provided:
        if term and term.strip():
            term_clean = term.strip()
            term_lower = term_clean.lower()
            if term_lower not in seen_lower:
                merged.append(term_clean)
                seen_lower.add(term_lower)
    
    # Add AI-generated terms that aren't duplicates
    for term in ai_generated:
        if term and term.strip():
            term_clean = term.strip()
            term_lower = term_clean.lower()
            if term_lower not in seen_lower:
                merged.append(term_clean)
                seen_lower.add(term_lower)
    
    return sorted(merged, key=str.lower)


def merge_termbase(
    ai_generated: dict[str, dict[str, str]],
    user_provided: dict[str, dict[str, str]] | None = None,
) -> dict[str, dict[str, str]]:
    """
    Merge AI-generated termbase with user-provided termbase.
    
    Strategy:
    - For each language, user-provided entries take precedence
    - AI-generated entries are added if the source term doesn't exist in user termbase
    - User-provided translations override AI-generated ones for the same source term
    
    Args:
        ai_generated: AI-generated termbase {lang_code: {source_term: translation}}
        user_provided: Optional user-provided termbase {lang_code: {source_term: translation}}
        
    Returns:
        Merged termbase dictionary
    """

    if not ai_generated:
        ai_generated = {}

    if not user_provided:
        return ai_generated.copy()

    merged = {}
    
    # Get all unique language codes from both sources
    all_languages = set(ai_generated.keys()) | set(user_provided.keys())
    
    for lang_code in all_languages:
        user_tb = user_provided.get(lang_code, {})
        ai_tb = ai_generated.get(lang_code, {})
        
        # Start with user-provided entries (they take precedence)
        merged_tb = user_tb.copy()
        
        # Add AI-generated entries that don't conflict
        for source_term, translation in ai_tb.items():
            if source_term and translation:
                source_clean = source_term.strip()
                # User-provided takes precedence, so only add if not present
                if source_clean not in merged_tb:
                    merged_tb[source_clean] = translation.strip()
        
        if merged_tb:
            merged[lang_code] = merged_tb
    
    return merged

def load_termbase_from_file(file_path: str, logger: logging.Logger | None = None) -> dict[str, dict[str, str]]:
    """
        Load termbase from a JSON file.

        Expected format:
        {
          "lang_code": {
            "source_term": "translation",
            ...
          },
          ...
        }

        Args:
            file_path: Path to termbase JSON file
            logger: Optional logger for error reporting

        Returns:
            Termbase dictionary, or empty dict if loading fails
        """
    log = logger or logging.getLogger(__name__)

    try:
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            raise ValueError("Termbase must be a JSON object")

        validated = {}

        for lang_code, term_map in data.items():
            if not isinstance(lang_code, str):
                raise ValueError("Language code must be string")

            if not isinstance(term_map, dict):
                raise ValueError(f"Entries for '{lang_code}' must be an object")

            clean = {}
            for k, v in term_map.items():
                if not isinstance(k, str) or not isinstance(v, str):
                    raise ValueError(f"Invalid term entry in '{lang_code}'")

                clean[k.strip()] = v.strip()

            validated[lang_code] = clean

        if not validated:
            raise ValueError("Termbase is empty")

        log.info(
            "Loaded termbase from %s: %s languages, %s total entries",
            file_path,
            len(validated),
            sum(len(tb) for tb in validated.values()),
        )

        return validated

    except Exception:
        log.exception("Invalid termbase file: %s", file_path)
        raise


def load_dnt_terms_from_file(file_path: str, logger: logging.Logger | None = None) -> list[str]:
    """
     Load DNT terms from a JSON file or text file.

     Supports:
     - JSON array: ["term1", "term2", ...]

     Args:
         file_path: Path to DNT terms file
         logger: Optional logger for error reporting

     Returns:
         List of DNT terms, or empty list if loading fails
     """
    log = logger or logging.getLogger(__name__)
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read().strip()

        # If file looks like JSON, it MUST be valid JSON list
        if content.startswith("["):
            data = json.loads(content)

            if not isinstance(data, list):
                raise ValueError("DNT JSON must be a list")

            terms = [str(term).strip() for term in data if str(term).strip()]
        else:
            raise ValueError("No valid DNT terms found")

        log.info("Loaded %s DNT terms from %s", len(terms), file_path)
        return terms

    except Exception:
        log.exception("Invalid DNT file: %s", file_path)
        raise
