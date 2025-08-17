#!/usr/bin/env python3
"""
Run summary utilities for SRT Translator.
Provides standardized formatting for DNT terms, termbase, and manifest outputs.
"""

import hashlib
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def normalize_language_code(lang_code: str) -> str:
    """
    Normalize language codes to IETF format.
    
    Args:
        lang_code: Language code (e.g., 'zh', 'pt-BR', 'es')
        
    Returns:
        Normalized IETF language code
    """
    # Common normalizations
    normalizations = {
        'zh': 'zh-Hans',  # Default to Simplified Chinese
        'pt': 'pt-BR',    # Default to Brazilian Portuguese
        'en': 'en-US',    # Default to US English
    }
    
    normalized = normalizations.get(lang_code.lower(), lang_code)
    logger.debug(f"Normalized language code: {lang_code} -> {normalized}")
    return normalized


def hash_content(content: Any) -> str:
    """
    Generate SHA256 hash of content for reproducibility.
    
    Args:
        content: Content to hash (will be converted to sorted JSON)
        
    Returns:
        SHA256 hash string
    """
    try:
        # Convert to sorted JSON for consistent hashing
        if isinstance(content, dict):
            # Sort dictionary keys for consistent hashing
            sorted_content = json.dumps(content, sort_keys=True, ensure_ascii=False)
        else:
            sorted_content = json.dumps(content, ensure_ascii=False)
        
        hash_obj = hashlib.sha256(sorted_content.encode('utf-8'))
        return hash_obj.hexdigest()
    except Exception as e:
        logger.warning(f"Failed to hash content: {e}")
        return "hash_failed"


def create_dnt_summary(
    user_terms: List[str],
    filtered_terms: List[str],
    filtered_out: List[str],
    lang_code: str,
    filtering_rules: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create standardized DNT terms summary.
    
    Args:
        user_terms: Original DNT terms as provided by user
        filtered_terms: DNT terms actually used during translation
        filtered_out: Terms that were filtered out
        lang_code: Target language code
        filtering_rules: Rules applied during filtering
        
    Returns:
        Standardized DNT summary dictionary
    """
    normalized_lang = normalize_language_code(lang_code)
    
    return {
        "description": "DNT terms processing summary",
        "lang": normalized_lang,
        "timestamp": datetime.now().isoformat(),
        "user_provided": {
            "description": "Original DNT terms as provided by user",
            "terms": user_terms,
            "count": len(user_terms),
            "sha256": hash_content(user_terms)
        },
        "filtered_for_translation": {
            "description": "DNT terms actually used during translation (numeric items removed)",
            "terms": filtered_terms,
            "count": len(filtered_terms),
            "filtered_out": filtered_out,
            "filtering_reason": "Removed numeric and number-like terms for better localization",
            "filters": filtering_rules
        }
    }


def create_termbase_summary(
    user_termbase: Dict[str, Dict[str, str]],
    filtered_termbase: Dict[str, Dict[str, str]],
    collisions_removed: Dict[str, Any],
    lang_code: str,
    filtering_rules: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create standardized termbase summary.
    
    Args:
        user_termbase: Original termbase as provided by user
        filtered_termbase: Termbase actually used during translation
        collisions_removed: Details about removed collisions
        lang_code: Target language code
        filtering_rules: Rules applied during filtering
        
    Returns:
        Standardized termbase summary dictionary
    """
    normalized_lang = normalize_language_code(lang_code)
    
    # Count entries per language
    user_entries = {lang: len(terms) for lang, terms in user_termbase.items()}
    filtered_entries = {lang: len(terms) for lang, terms in filtered_termbase.items()}
    
    return {
        "description": "Termbase processing summary",
        "lang": normalized_lang,
        "timestamp": datetime.now().isoformat(),
        "user_provided": {
            "description": "Original termbase as provided by user",
            "languages": user_termbase,
            "entry_counts": user_entries,
            "total_entries": sum(user_entries.values()),
            "sha256": hash_content(user_termbase)
        },
        "filtered_for_translation": {
            "description": "Termbase actually used during translation (DNT collisions removed, relevant-only, capped)",
            "languages": filtered_termbase,
            "entry_counts": filtered_entries,
            "total_entries": sum(filtered_entries.values()),
            "collisions_removed": collisions_removed,
            "filtering_reason": "Removed termbase entries that conflict with DNT terms; kept only entries found in batch; capped to 30",
            "filters": filtering_rules
        }
    }


def create_manifest_summary(
    version: str,
    timestamp: str,
    mode: str,
    source_files: List[str],
    target_languages: List[str],
    summary: Dict[str, Any],
    processing_summary: Dict[str, Any],
    dnt_meta: Dict[str, Any],
    tb_meta: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create enriched manifest with processing details.
    
    Args:
        version: App version
        timestamp: Run timestamp
        mode: Run mode (GUI/CLI)
        source_files: Source SRT files
        target_languages: Target language codes
        summary: Translation summary
        processing_summary: Processing details
        dnt_meta: DNT terms metadata
        tb_meta: Termbase metadata
        
    Returns:
        Enriched manifest dictionary
    """
    # Normalize all language codes
    normalized_langs = [normalize_language_code(lang) for lang in target_languages]
    
    return {
        "version": version,
        "timestamp": timestamp,
        "mode": mode,
        "source_files": source_files,
        "target_languages": normalized_langs,
        "summary": summary,
        "processing_summary": processing_summary,
        "artifacts": {
            "dnt_terms": {
                "provided": dnt_meta["user_provided"]["count"],
                "used": dnt_meta["filtered_for_translation"]["count"],
                "filtered": len(dnt_meta["filtered_for_translation"]["filtered_out"]),
                "lang": dnt_meta["lang"]
            },
            "termbase": {
                "provided_entries": tb_meta["user_provided"]["total_entries"],
                "used_entries": tb_meta["filtered_for_translation"]["total_entries"],
                "collisions_resolved": len(tb_meta["filtered_for_translation"]["collisions_removed"]),
                "lang": tb_meta["lang"]
            },
            "quality_improvements": [
                "Numeric DNT terms automatically filtered",
                "DNT precedence enforced over termbase",
                "Relevant-only termbase injection"
            ],
            "filters": {
                "numeric_filter": True,
                "dnt_precedence": True,
                "relevant_only_tb": True,
                "tb_cap": 30
            }
        }
    }


def write_run_artifacts(
    artifacts_dir: str,
    lang_code: str,
    dnt_meta: Dict[str, Any],
    tb_meta: Dict[str, Any],
    manifest_data: Dict[str, Any]
) -> Tuple[str, str, str]:
    """
    Write all run artifacts to the artifacts directory structure.
    
    Args:
        artifacts_dir: Base artifacts directory
        lang_code: Target language code
        dnt_meta: DNT terms metadata
        tb_meta: Termbase metadata
        manifest_data: Manifest data
        
    Returns:
        Tuple of (dnt_summary_path, termbase_summary_path, manifest_path)
    """
    normalized_lang = normalize_language_code(lang_code)
    
    # Create per-language artifacts directory
    lang_artifacts_dir = os.path.join(artifacts_dir, normalized_lang)
    os.makedirs(lang_artifacts_dir, exist_ok=True)
    
    # Write DNT summary
    dnt_summary_path = os.path.join(lang_artifacts_dir, "dnt_summary.json")
    with open(dnt_summary_path, "w", encoding="utf-8") as f:
        json.dump(dnt_meta, f, ensure_ascii=False, indent=2)
    
    # Write termbase summary
    termbase_summary_path = os.path.join(lang_artifacts_dir, "termbase_summary.json")
    with open(termbase_summary_path, "w", encoding="utf-8") as f:
        json.dump(tb_meta, f, ensure_ascii=False, indent=2)
    
    # Write manifest
    manifest_path = os.path.join(lang_artifacts_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Artifacts written to: {lang_artifacts_dir}")
    return dnt_summary_path, termbase_summary_path, manifest_path


def get_filtering_rules() -> Dict[str, Any]:
    """
    Get standard filtering rules configuration.
    
    Returns:
        Dictionary of filtering rules and their values
    """
    return {
        "numeric_filter": True,
        "dnt_precedence": True,
        "relevant_only_tb": True,
        "tb_cap": 30,
        "tolerant_match": True
    }
