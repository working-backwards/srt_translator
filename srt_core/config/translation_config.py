"""Configuration abstraction layer for translation system"""

import json
import logging
import os
from dataclasses import dataclass
from typing import Dict, List, Optional

from srt_core.config.language_config import language_config


@dataclass
class TranslationConfig:
    """Immutable translation configuration with validation"""

    target_languages: Dict[str, str]  # language_name or code → code
    dnt_terms: List[str]
    termbase: Dict[str, Dict[str, str]]
    output_directory: str = "translated_srt_files"
    api_key: Optional[str] = None
    logger: Optional[logging.Logger] = None

    def __post_init__(self):
        """Validate configuration integrity and normalize language codes"""
        if self.logger is None:
            self.logger = logging.getLogger(__name__)

        # Normalize all target_languages to language codes once
        normalized = {}
        for name_or_code, code in self.target_languages.items():
            norm_code = language_config.normalize_to_code(name_or_code)
            if norm_code:
                normalized[name_or_code] = norm_code
            else:
                self.logger.warning(f"Unrecognized language identifier: {name_or_code}")
        self.target_languages = normalized

        if not self.target_languages:
            raise ValueError("At least one valid target language required")

        # Validate other fields
        if not isinstance(self.dnt_terms, list):
            raise ValueError("dnt_terms must be a list")
        if not isinstance(self.termbase, dict):
            raise ValueError("termbase must be a dictionary")

        # Log configuration summary
        self.logger.info(f"TranslationConfig created: {self.to_log_string()}")

    def to_log_string(self):
        """Return a concise string representation for logging"""
        return f"Languages: {list(self.target_languages.values())}, DNT: {len(self.dnt_terms)}, Termbase: {list(self.termbase.keys())}"

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            "target_languages": self.target_languages,
            "dnt_terms": self.dnt_terms,
            "termbase": self.termbase,
            "output_directory": self.output_directory,
            "api_key": self.api_key,
        }

    @classmethod
    def from_dict(
        cls, data: dict, logger: Optional[logging.Logger] = None
    ) -> "TranslationConfig":
        """Create from dictionary with validation"""
        return cls(
            target_languages=data.get("target_languages", {}),
            dnt_terms=data.get("dnt_terms", []),
            termbase=data.get("termbase", {}),
            output_directory=data.get("output_directory", "translated_srt_files"),
            api_key=data.get("api_key"),
            logger=logger,
        )


def build_config_from_gui(settings_manager) -> TranslationConfig:
    """Build configuration from GUI settings manager"""
    # Defensive check to prevent CLI/GUI code path mixing
    assert (
        os.getenv("GUI_MODE") != "false"
    ), "build_config_from_gui() should never run in CLI mode"

    # Get current state from settings manager (thread-safe)
    config_state = settings_manager.get_current_state()

    return TranslationConfig(
        target_languages=config_state.target_languages,
        dnt_terms=config_state.dnt_terms,
        termbase=config_state.termbase,
        api_key=settings_manager.load_api_key(),
        output_directory=settings_manager.load_last_output_directory()
        or "translated_srt_files",
    )


def build_config_from_cli(env_file_path: Optional[str] = None) -> TranslationConfig:
    """Build configuration from CLI environment variables"""
    # Load from environment variables
    target_languages_str = os.getenv("TARGET_LANGUAGES", "{}")
    dnt_terms_str = os.getenv("DNT_TERMS", "[]")
    termbase_str = os.getenv("TERMBASE", "{}")

    try:
        target_languages = json.loads(target_languages_str)
        dnt_terms = json.loads(dnt_terms_str)
        termbase = json.loads(termbase_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid environment variable format: {e}")

    return TranslationConfig(
        target_languages=target_languages,
        dnt_terms=dnt_terms,
        termbase=termbase,
        output_directory=os.getenv("OUTPUT_DIRECTORY", "translated_srt_files"),
        api_key=os.getenv("OPENAI_API_KEY"),
    )


def build_config_from_parameters(
    target_languages: Dict[str, str],
    dnt_terms: Optional[List[str]] = None,
    termbase: Optional[Dict[str, Dict[str, str]]] = None,
    output_directory: Optional[str] = None,
    api_key: Optional[str] = None,
    logger: Optional[logging.Logger] = None,
) -> TranslationConfig:
    """Build configuration from explicit parameters"""
    return TranslationConfig(
        target_languages=target_languages,
        dnt_terms=dnt_terms or [],
        termbase=termbase or {},
        output_directory=output_directory or "translated_srt_files",
        api_key=api_key,
        logger=logger,
    )
