#!/usr/bin/env python3
"""
Typed configuration models for SRT Translator.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import Any, Literal, TypedDict

from srt_translator.core.constants import (
    DEFAULT_TONE,
    DEFAULT_TRANSLATION_MODEL,
    DEFAULT_ERROR_POLICY, DEFAULT_TEMPERATURE
)



class LogMode(StrEnum):
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
    """
    Immutable configuration for translation runs.

    Architecture note: This config is frozen to prevent accidental mutation.
    DNT terms and termbase use immutable containers (Tuple, MappingProxyType)
    to enforce read-only semantics throughout the core engine.
    """

    # Required fields (no defaults) - must come first in dataclass
    target_languages: dict[str, str]  # e.g., {"Spanish": "es", ...}
    output_directory: Path
    api_key: str
    log_mode: LogMode
    mode: Literal["CLI", "GUI"]

    # Optional fields with defaults - must come after required fields
    translation_model_name: str = DEFAULT_TRANSLATION_MODEL
    temperature: float = DEFAULT_TEMPERATURE   # Aggressiveness of automatic placeholder fixes
    # Immutable sequence of DNT (Do Not Translate) terms.
    # Empty tuple if none provided - never None to avoid Optional handling in core.
    dnt_terms: tuple[str, ...] = ()

    # Immutable nested mapping: target_lang_code -> (source_term -> translation).
    # Empty MappingProxy if none provided - never None to avoid Optional handling in core.
    termbase: Mapping[str, Mapping[str, str]] = field(default_factory=lambda: MappingProxyType({}))

    error_policy: Literal["STRICT", "BOUNDED", "DEV"] = DEFAULT_ERROR_POLICY

    # File handling
    files: Iterable[Path] | None = None

    # Optional batch-level source language detection payload
    source_language: dict[str, object] | None = None

    # Language policies injected by GUI/CLI loaders
    language_policies: dict[str, dict[str, Any]] | None = None

    # Translation tone/register: casual, neutral, or formal
    tone: str = DEFAULT_TONE

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

        # Validate termbase (normalize to dict of dicts)
        termbase = raw.get("termbase", {}) or {}
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
        translation_model_name = raw.get("translation_model_name") or raw.get("openai_model") or raw.get("model_name") or DEFAULT_TRANSLATION_MODEL

        # Validate aggressiveness
        raw_agg = raw.get("Temperature")
        try:
            temperature = float(raw_agg) if raw_agg is not None else DEFAULT_TEMPERATURE
            if not 0.0 <= temperature <= 1.0:
                errors.append("temperature must be between 0.0 and 1.0")
                temperature =DEFAULT_TEMPERATURE
        except (ValueError, TypeError):
            errors.append("temperature must be a float")
            temperature = DEFAULT_TEMPERATURE

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
            error_policy = DEFAULT_ERROR_POLICY

        # Validate tone (case-insensitive, normalize to lowercase)
        tone_raw = raw.get("tone", "neutral")
        if tone_raw is None:
            tone =DEFAULT_TONE
        else:
            tone = str(tone_raw).lower().strip()
            if tone not in ("casual", "neutral", "formal"):
                errors.append(f"Invalid tone: '{tone_raw}'. Must be one of: casual, neutral, formal")
                tone = "neutral"

        if errors:
            raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")

        # Convert to immutable containers before constructing the frozen config.
        # This enforces read-only semantics throughout the core engine and prevents
        # accidental mutation of configuration state.

        # Convert DNT list to immutable tuple
        dnt_tuple: tuple[str, ...] = tuple(dnt_list)

        # Convert termbase to nested immutable mappings (MappingProxyType).
        # Outer mapping: language_code -> inner_mapping
        # Inner mapping: source_term -> target_translation
        safe_tb_outer: dict[str, Mapping[str, str]] = {}
        for lang, entries in (termbase or {}).items():
            if isinstance(entries, dict):
                # Copy inner dict to avoid aliasing to caller's mutable data
                safe_tb_outer[lang] = MappingProxyType(dict(entries))
            else:
                # Normalize invalid entries to empty mapping
                safe_tb_outer[lang] = MappingProxyType({})

        termbase_proxy = MappingProxyType(safe_tb_outer)

        return cls(
            target_languages=target_languages,
            dnt_terms=dnt_tuple,
            termbase=termbase_proxy,
            output_directory=output_dir,
            api_key=api_key,
            translation_model_name=translation_model_name,
            temperature=temperature,
            log_mode=log_mode,
            mode=mode,
            error_policy=error_policy,
            files=raw.get("files"),
            source_language=raw.get("source_language"),
            language_policies=raw.get("language_policies"),
            tone=tone,
        )
