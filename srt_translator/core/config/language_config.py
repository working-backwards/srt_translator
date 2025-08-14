#!/usr/bin/env python3
"""
Language configuration for the SRT Translator.
"""

import logging
from typing import Any, Dict, Optional, cast

from .languages_data import LANGUAGES_JSON


class LanguageConfig:
    """Unified language configuration manager for CLI"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._config: Optional[Dict[str, Any]] = None

    def load_config(self) -> dict:
        """Load language configuration from JSON file using resource loader"""
        if self._config is not None:
            return self._config

        try:
            # Use the resource loader which handles both package resources and repo paths
            config = LANGUAGES_JSON
            languages = config.get("languages", {})
            if isinstance(languages, dict):
                self.logger.info(
                    f"Loaded language config with {len(languages)} languages"
                )
            else:
                self.logger.info(
                    "Loaded language config with unknown number of languages"
                )
            self._config = config
            return config
        except Exception as e:
            self.logger.error(f"Error loading language config: {e}")
            fallback = self.get_fallback_config()
            self._config = fallback
            return fallback

    @property
    def config(self) -> dict:
        """Get configuration, loading if necessary"""
        return self.load_config()

    def get_fallback_config(self) -> dict:
        """Get fallback configuration if JSON file is unavailable"""
        self.logger.warning("Using fallback language configuration")
        return {
            "version": "1.0",
            "default_popular_limit": 12,
            "default_popular_languages": [
                "es",
                "fr",
                "de",
                "it",
                "pt-BR",
                "zh-Hans",
                "ja",
                "ko",
                "ar",
                "hi",
                "id",
                "vi",
            ],
            "languages": {
                "es": {"name": "Spanish", "popular": True},
                "fr": {"name": "French", "popular": True},
                "de": {"name": "German", "popular": True},
                "it": {"name": "Italian", "popular": True},
                "pt-BR": {"name": "Portuguese (Brazil)", "popular": True},
                "zh-Hans": {"name": "Chinese (Simplified)", "popular": True},
                "ja": {"name": "Japanese", "popular": True},
                "ko": {"name": "Korean", "popular": True},
                "ar": {"name": "Arabic", "popular": True},
                "hi": {"name": "Hindi", "popular": True},
                "id": {"name": "Indonesian", "popular": True},
                "vi": {"name": "Vietnamese", "popular": True},
            },
        }

    def get_all_languages(self) -> dict[str, dict[str, Any]]:
        """Get all available languages"""
        languages = cast(dict[str, dict[str, Any]], self.config.get("languages", {}))
        return languages

    def get_popular_languages(self) -> list[str]:
        """Get current popular languages (defaults for now, user preferences in future)"""
        return cast(list[str], self.config.get("default_popular_languages", []))

    def get_language_name(self, code: str) -> str:
        """Get display name for language code"""
        languages = self.get_all_languages()
        lang_info = languages.get(code, {})
        name = lang_info.get("name")
        return name if name is not None else code

    def is_popular(self, code: str) -> bool:
        """Check if language is marked as popular"""
        languages = self.get_all_languages()
        lang_info = languages.get(code, {})
        popular = lang_info.get("popular")
        return bool(popular) if popular is not None else False

    def get_language_codes(self) -> list[str]:
        """Get list of all language codes"""
        return list(self.get_all_languages().keys())

    def get_language_names(self) -> dict[str, str]:
        """Get mapping of language codes to display names"""
        languages = self.get_all_languages()
        result = {}
        for code, lang in languages.items():
            name = lang.get("name")
            result[code] = name if name is not None else code
        return result

    def validate_language_code(self, code: str) -> bool:
        """Check if a language code is valid"""
        return code in self.get_all_languages()

    def get_config_version(self) -> str:
        """Get the configuration version"""
        version = self.config.get("version")
        return version if version is not None else "1.0"

    def get_popular_limit(self) -> int:
        """Get the default popular languages limit"""
        limit = self.config.get("default_popular_limit")
        return limit if limit is not None else 12

    def get_target_languages_dict(self) -> dict[str, str]:
        """Get target languages in the format expected by CLI (name: code)"""
        languages = self.get_all_languages()
        result = {}
        for code, lang in languages.items():
            name = lang.get("name")
            if name is not None:
                result[name] = code
            else:
                result[code] = code
        return result

    def get_language_rules(self, lang_code: str) -> dict[str, list[str]]:
        """Get language-specific sentence boundary rules"""
        DEFAULT_SENTENCE_ENDINGS: list[str] = [".", "!", "?", "...", ":", ";"]
        DEFAULT_BREAK_MARKERS: list[str] = []

        languages = self.get_all_languages()
        lang_info = languages.get(lang_code, {})

        sentence_endings = lang_info.get("sentence_endings")
        if not isinstance(sentence_endings, list):
            sentence_endings = DEFAULT_SENTENCE_ENDINGS

        break_markers = lang_info.get("break_markers")
        if not isinstance(break_markers, list):
            break_markers = DEFAULT_BREAK_MARKERS

        return {
            "sentence_endings": sentence_endings,
            "break_markers": break_markers,
        }

    def normalize_to_code(self, name_or_code: str) -> Optional[str]:
        """Convert language name or code to normalized language code"""
        if not name_or_code:
            return None

        # First check if it's already a valid language code
        if self.validate_language_code(name_or_code):
            return name_or_code

        # If not, try to find it by name
        languages = self.get_all_languages()
        for code, lang_info in languages.items():
            # code is now str, not Any
            name = lang_info.get("name")
            if name and name.lower() == name_or_code.lower():
                return code

        # If still not found, try partial matches
        for code, lang_info in languages.items():
            lang_name = lang_info.get("name")
            if lang_name:
                if (
                    name_or_code.lower() in lang_name.lower()
                    or lang_name.lower() in name_or_code.lower()
                ):
                    return code

        # If no match found, return None
        return None


# Create instance only when needed, not at import time
def get_language_config() -> LanguageConfig:
    """Get language configuration instance (lazy initialization)"""
    return LanguageConfig()
