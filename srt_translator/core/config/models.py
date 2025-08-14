#!/usr/bin/env python3
"""
Typed configuration models for SRT Translator.
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Literal, Mapping


class LogMode(str, Enum):
    Standard = "Standard"
    Verbose = "Verbose"


@dataclass(frozen=True)
class TranslationConfig:
    target_languages: Dict[str, str]  # e.g., {"Spanish": "es", ...}
    dnt_terms: List[str]
    termbase: Dict[str, Dict[str, str]]  # target_lang_code -> {canonical_term -> translation}
    output_directory: Path
    api_key: str
    model_name: str
    batch_size: int
    aggressiveness: float  # Aggressiveness of automatic placeholder fixes
    log_mode: LogMode
    mode: Literal["CLI", "GUI"]

    @classmethod
    def from_raw(
        cls, raw: Mapping[str, Any], *, mode: Literal["CLI", "GUI"]
    ) -> "TranslationConfig":
        """Build TranslationConfig from raw configuration data with validation."""
        from .utils import (
            normalize_target_languages,
            parse_json_or_csv,
            validate_float_range,
            validate_positive_int,
        )
        from .validation import ConfigValidationError

        errors: List[str] = []
        warnings: List[str] = []

        # Validate required fields
        required_fields = ["api_key", "output_directory"]
        for field in required_fields:
            if not raw.get(field):
                errors.append(f"{field} is required")

        if errors:
            raise ConfigValidationError(errors, warnings)

        # Parse and validate target_languages
        try:
            langs_raw = raw.get("target_languages")
            if isinstance(langs_raw, str):
                langs_map = normalize_target_languages(
                    parse_json_or_csv(langs_raw, expect_mapping=True, field_name="target_languages")
                )
            else:
                langs_map = normalize_target_languages(langs_raw)
        except ValueError as e:
            errors.append(str(e))
            langs_map = {}

        # Parse and validate dnt_terms
        try:
            dnt_raw = raw.get("dnt_terms")
            if isinstance(dnt_raw, str):
                dnt_list = parse_json_or_csv(dnt_raw, expect_mapping=False, field_name="dnt_terms")
            else:
                dnt_list = dnt_raw or []
        except ValueError as e:
            errors.append(str(e))
            dnt_list = []

        # Handle termbase - expect actual data from client
        termbase = raw.get("termbase", {})
        if not isinstance(termbase, dict):
            warnings.append("termbase must be a dictionary")
            termbase = {}

        # Validate and convert other fields
        try:
            batch_size = validate_positive_int(
                raw.get("batch_size", 5), "batch_size", upper_bound=1000
            )
        except ValueError as e:
            errors.append(str(e))
            batch_size = 5

        try:
            aggressiveness = validate_float_range(raw.get("aggressiveness", 0.75), "aggressiveness")
        except ValueError as e:
            errors.append(str(e))
            aggressiveness = 0.75

        try:
            log_mode = LogMode(raw.get("log_mode", "Standard"))
        except ValueError:
            errors.append(
                f"log_mode must be one of {[m.value for m in LogMode]}, got '{raw.get('log_mode')}'"
            )
            log_mode = LogMode.Standard

        # Validate output directory path
        try:
            output_dir = Path(raw["output_directory"])
        except Exception as e:
            errors.append(f"Invalid output_directory path: {e}")
            output_dir = Path("translated_srt_files")

        # Check if parent directory exists (warning only)
        if not output_dir.parent.exists():
            warnings.append(f"Parent directory does not exist: {output_dir.parent}")

        if errors:
            raise ConfigValidationError(errors, warnings)

        return cls(
            target_languages=langs_map,
            dnt_terms=list(dnt_list),
            termbase=termbase,
            output_directory=output_dir,
            api_key=raw["api_key"],
            model_name=raw.get("openai_model", "gpt-4o-mini"),
            batch_size=batch_size,
            aggressiveness=aggressiveness,
            log_mode=log_mode,
            mode=mode,
        )
