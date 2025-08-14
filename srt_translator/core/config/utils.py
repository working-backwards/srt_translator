"""
Pure utility functions for configuration parsing and normalization.
"""

import json
from pathlib import Path
from typing import Any, Dict, Sequence, Union


def parse_json_or_csv(val: str | None, *, expect_mapping: bool, field_name: str = "value"):
    """Parse JSON or CSV string into appropriate data structure."""
    if not val or not val.strip():
        return {} if expect_mapping else []

    s = val.strip()
    if s.startswith("{") or s.startswith("["):
        try:
            obj = json.loads(s)
            if expect_mapping and not isinstance(obj, dict):
                raise ValueError(f"Expected a JSON object in {field_name}")
            if not expect_mapping and not isinstance(obj, list):
                raise ValueError(f"Expected a JSON array in {field_name}")
            return obj
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {field_name}: {e}")

    # Parse as CSV
    parts = [p.strip() for p in s.split(",") if p.strip()]
    return {p: p for p in parts} if expect_mapping else parts


def normalize_target_languages(
    val: Union[Dict[str, str], Sequence[str], None],
) -> Dict[str, str]:
    """Normalize target languages to consistent dict format."""
    if val is None:
        return {}

    if isinstance(val, dict):
        # Already mapping -> mapping
        return {str(k): str(v) for k, v in val.items()}

    # Sequence like ["es","fr"] -> {"es":"es","fr":"fr"}
    if isinstance(val, (list, tuple)):
        return {str(code): str(code) for code in val}

    # Handle string input
    if isinstance(val, str):
        return parse_json_or_csv(val, expect_mapping=True, field_name="target_languages")

    raise ValueError(f"Invalid target_languages format: {type(val)}")


def load_termbase_from_file(path: Path) -> Dict[str, Dict[str, str]]:
    """Load termbase from file path, with smart format detection."""
    if not path.exists():
        return {}

    try:
        with path.open("r", encoding="utf-8") as f:
            data: Any = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        raise ValueError(f"Failed to load termbase from {path}: {e}")

    if not isinstance(data, dict):
        raise ValueError(f"Termbase must be a JSON object, got {type(data)}")

    if not data:
        return {}

    # Accept canonical (lang->term->trans) or term-first and normalize
    sample_key = next(iter(data))
    looks_like_lang = "-" in str(sample_key) or len(str(sample_key)) in (2, 3)

    if looks_like_lang:
        # Canonical format: {"es": {"term": "translation"}}
        return {
            str(lang): {str(term): str(tr) for term, tr in terms.items()}
            for lang, terms in data.items()
            if isinstance(terms, dict)
        }
    else:
        # Term-first format: {"Machine Learning": {"es": "...", "fr": "..."}}
        normalized: Dict[str, Dict[str, str]] = {}
        for term, per_lang in data.items():
            if isinstance(per_lang, dict):
                for lang, trans in per_lang.items():
                    normalized.setdefault(str(lang), {})[str(term)] = str(trans)
        return normalized


def validate_positive_int(value: Any, field_name: str, upper_bound: int = None) -> int:
    """Validate and convert to positive integer."""
    try:
        int_val = int(value)
    except (ValueError, TypeError):
        raise ValueError(f"{field_name} must be an integer, got '{value}'")

    if int_val <= 0:
        raise ValueError(f"{field_name} must be positive, got {int_val}")

    if upper_bound and int_val > upper_bound:
        raise ValueError(f"{field_name} must be ≤ {upper_bound}, got {int_val}")

    return int_val


def validate_float_range(
    value: Any, field_name: str, min_val: float = 0.0, max_val: float = 1.0
) -> float:
    """Validate and convert to float within specified range."""
    try:
        float_val = float(value)
    except (ValueError, TypeError):
        raise ValueError(f"{field_name} must be a number, got '{value}'")

    if float_val < min_val or float_val > max_val:
        raise ValueError(f"{field_name} must be between {min_val} and {max_val}, got {float_val}")

    return float_val
