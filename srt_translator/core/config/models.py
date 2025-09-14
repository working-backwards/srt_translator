#!/usr/bin/env python3
"""
Typed configuration models for SRT Translator.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Literal, TypedDict


class LogMode(str, Enum):
    """Logging mode for the translation system."""

    STANDARD = "Standard"
    VERBOSE = "Verbose"
    DEBUG = "Debug"


class SummaryDict(TypedDict):
    """Summary of translation results."""

    total_files: int
    unique_languages: int
    total_operations: int
    successes: int
    skipped: int
    errors: int
    error_details: list[str]
    batch_directory: str


@dataclass(frozen=True)
class TranslationConfig:
    # Core translation parameters
    target_languages: dict[str, str]  # e.g., {"Spanish": "es", ...}
    dnt_terms: list[str]
    termbase: dict[str, dict[str, str]]  # target_lang_code -> {canonical_term -> translation}
    output_directory: Path
    api_key: str
    model_name: str
    aggressiveness: float  # Aggressiveness of automatic placeholder fixes
    log_mode: LogMode
    mode: Literal["CLI", "GUI"]
    error_policy: Literal["STRICT", "BOUNDED", "DEV"] = (
        "BOUNDED"  # Error handling policy for translation system (BOUNDED for testing)
    )
    # File handling
    files: Iterable[Path] | None = None
    # NEW: optional batch-level source language detection payload
    source_language: dict[str, object] | None = None
    # NEW: language policies injected by GUI/CLI loaders
    language_policies: dict[str, dict[str, Any]] | None = None

    def run(self) -> SummaryDict:
        """Run the translation with this configuration and return summary."""
        from srt_translator.core.main import translate_srt_files

        if not self.files:
            raise ValueError("No files specified for translation")

        return translate_srt_files(
            file_paths=[str(f) for f in self.files],
            config=self,
        )

    @classmethod
    def from_raw(cls, raw: dict[str, Any], mode: Literal["CLI", "GUI"] = "GUI") -> "TranslationConfig":
        """Create a TranslationConfig from raw configuration data."""
        errors = []

        # Validate target languages
        target_languages = raw.get("target_languages", {})
        if not isinstance(target_languages, dict):
            errors.append("target_languages must be a dictionary")
            target_languages = {}

        # Validate DNT terms
        dnt_terms = raw.get("dnt_terms", [])
        if isinstance(dnt_terms, str):
            # Handle comma-separated string format
            dnt_list = [term.strip() for term in dnt_terms.split(",") if term.strip()]
        elif isinstance(dnt_terms, list):
            dnt_list = [str(term) for term in dnt_terms if term]
        else:
            dnt_list = []

        # Validate termbase
        termbase = raw.get("termbase", {})
        if not isinstance(termbase, dict):
            errors.append("termbase must be a dictionary")
            termbase = {}

        # Validate output directory path
        try:
            output_dir = Path(raw["output_directory"])
        except Exception as e:
            errors.append(f"Invalid output_directory path: {e}")
            output_dir = Path("translated_srt_files")

        # Validate API key
        api_key = raw.get("api_key")
        if not api_key:
            errors.append("api_key is required")
            api_key = ""

        # Validate model name (handle both openai_model and model_name)
        model_name = raw.get("openai_model") or raw.get("model_name", "gpt-4o-mini")

        # Validate aggressiveness
        try:
            aggressiveness = float(raw.get("aggressiveness", 0.75))
            if not 0.0 <= aggressiveness <= 1.0:
                errors.append("aggressiveness must be between 0.0 and 1.0")
                aggressiveness = 0.75
        except (ValueError, TypeError):
            errors.append("aggressiveness must be a float")
            aggressiveness = 0.75

        # Validate log mode
        try:
            log_mode = LogMode(raw.get("log_mode", "Standard"))
        except ValueError:
            errors.append(f"Invalid log_mode: {raw.get('log_mode')}")
            log_mode = LogMode.STANDARD

        # Validate error policy
        error_policy = raw.get("error_policy", "BOUNDED")
        if error_policy not in ("STRICT", "BOUNDED", "DEV"):
            errors.append(f"Invalid error_policy: {error_policy}")
            error_policy = "BOUNDED"

        if errors:
            raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")

        return cls(
            target_languages=target_languages,
            dnt_terms=list(dnt_list),
            termbase=termbase,
            output_directory=output_dir,
            api_key=api_key,
            model_name=model_name,
            aggressiveness=aggressiveness,
            log_mode=log_mode,
            mode=mode,
            error_policy=error_policy,
            files=raw.get("files"),
            source_language=raw.get("source_language"),
            language_policies=raw.get("language_policies"),
        )
