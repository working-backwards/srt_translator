"""Configuration abstraction layer for translation system"""

import json
import logging
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

from srt_core.config.language_config import language_config


def _mask_tail(value: str, visible: int = 4) -> str:
    if not value:
        return ""
    tail = value[-visible:]
    return f"…{tail}"  # only last 4 shown


@dataclass
class TranslationConfig:
    """Immutable translation configuration with validation"""

    target_languages: Dict[str, str]  # language_name or code → code
    dnt_terms: List[str]
    termbase: Dict[str, Dict[str, str]]
    output_directory: str = "translated_srt_files"
    api_key: Optional[str] = None
    model_name: str = "gpt-4o-mini"
    batch_size: int = 5
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
        if self.batch_size <= 0:
            raise ValueError("batch_size must be greater than 0")

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
            "model_name": self.model_name,
            "batch_size": self.batch_size,
        }

    def to_safe_log_dict(self) -> Dict[str, Any]:
        """Redacted snapshot for DEBUG logs only (never INFO)."""
        return {
            "output_directory": self.output_directory,
            "target_languages": list(self.target_languages.values()),
            "target_lang_count": len(self.target_languages),
            "dnt_terms_count": len(self.dnt_terms),
            "dnt_terms_sample": self.dnt_terms[:5],  # short sample, optional
            "termbase": self.termbase,  # Show actual termbase content
            "api_key_tail": _mask_tail(self.api_key or ""),  # only last 4 chars
            "model_name": getattr(self, "model_name", "gpt-4o-mini"),
            "batch_size": getattr(self, "batch_size", 5),
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
            model_name=data.get("model_name", "gpt-4o-mini"),
            batch_size=int(data.get("batch_size", 5)),
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

    # Debug logging to see what we got from the settings manager
    import logging

    logger = logging.getLogger(__name__)
    logger.info(
        f"build_config_from_gui - config_state.dnt_terms count: {len(config_state.dnt_terms) if config_state.dnt_terms else 0}"
    )
    logger.info(
        f"build_config_from_gui - config_state.termbase keys: {list(config_state.termbase.keys()) if config_state.termbase else 'None'}"
    )

    # Until SettingsManager exposes model/batch explicitly, fall back to env/defaults
    model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    try:
        batch_size = int(os.getenv("BATCH_SIZE", 5))
    except ValueError:
        batch_size = 5

    return TranslationConfig(
        target_languages=config_state.target_languages,
        dnt_terms=config_state.dnt_terms,
        termbase=config_state.termbase,
        api_key=settings_manager.load_api_key(),
        output_directory=settings_manager.load_last_output_directory()
        or "translated_srt_files",
        model_name=model_name,
        batch_size=batch_size,
    )


def build_config_from_cli(env_file_path: Optional[str] = None) -> TranslationConfig:
    """Build configuration from CLI environment variables"""
    # Load from environment variables
    target_languages_str = os.getenv("TARGET_LANGUAGES", "{}")
    dnt_terms_str = os.getenv("DNT_TERMS", "[]")

    # Load termbase from physical file in root directory (not from environment variable)
    from .settings import TERMBASE

    termbase = TERMBASE

    try:
        target_languages = json.loads(target_languages_str)
        dnt_terms = json.loads(dnt_terms_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid environment variable format: {e}")

    try:
        batch_size = int(os.getenv("BATCH_SIZE", 5))
    except ValueError:
        batch_size = 5

    return TranslationConfig(
        target_languages=target_languages,
        dnt_terms=dnt_terms,
        termbase=termbase,
        output_directory=os.getenv("OUTPUT_DIRECTORY", "translated_srt_files"),
        api_key=os.getenv("OPENAI_API_KEY"),
        model_name=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        batch_size=batch_size,
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
        model_name=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        batch_size=int(os.getenv("BATCH_SIZE", 5)),
        logger=logger,
    )
