"""
Pure utility functions for configuration parsing and normalization.
"""

import json
from typing import Dict, Optional, Sequence, Union


def parse_json_or_csv(val: Optional[str], *, expect_mapping: bool, field_name: str = "value"):
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
            raise ValueError(f"Invalid JSON in {field_name}: {e}") from e

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
