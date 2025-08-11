#!/usr/bin/env python3
"""
Language configuration for the SRT Translator.
"""

import logging
from typing import Optional

from .languages_data import LANGUAGES_JSON


class LanguageConfig:
    """Unified language configuration manager for CLI"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config = self.load_config()

    def load_config(self) -> dict:
        """Load language configuration from JSON file using resource loader"""
        try:
            # Use the resource loader which handles both package resources and repo paths
            config = LANGUAGES_JSON
            self.logger.info(
                f"Loaded language config with {len(config.get('languages', {}))} languages"
            )
            return config
        except Exception as e:
            self.logger.error(f"Error loading language config: {e}")
            return self.get_fallback_config()

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

    def get_all_languages(self) -> dict:
        """Get all available languages"""
        return self.config.get("languages", {})

    def get_popular_languages(self) -> list:
        """Get current popular languages (defaults for now, user preferences in future)"""
        return self.config.get("default_popular_languages", [])

    def get_language_name(self, code: str) -> str:
        """Get display name for language code"""
        languages = self.get_all_languages()
        return languages.get(code, {}).get("name", code)

    def is_popular(self, code: str) -> bool:
        """Check if language is marked as popular"""
        languages = self.get_all_languages()
        return languages.get(code, {}).get("popular", False)

    def get_language_codes(self) -> list:
        """Get list of all language codes"""
        return list(self.get_all_languages().keys())

    def get_language_names(self) -> dict:
        """Get mapping of language codes to display names"""
        languages = self.get_all_languages()
        return {code: lang.get("name", code) for code, lang in languages.items()}

    def validate_language_code(self, code: str) -> bool:
        """Check if a language code is valid"""
        return code in self.get_all_languages()

    def get_config_version(self) -> str:
        """Get the configuration version"""
        return self.config.get("version", "1.0")

    def get_popular_limit(self) -> int:
        """Get the default popular languages limit"""
        return self.config.get("default_popular_limit", 12)

    def get_target_languages_dict(self) -> dict:
        """Get target languages in the format expected by CLI (name: code)"""
        languages = self.get_all_languages()
        return {lang.get("name", code): code for code, lang in languages.items()}

    def get_language_rules(self, lang_code: str) -> dict:
        """Get language-specific sentence boundary rules"""
        DEFAULT_SENTENCE_ENDINGS = [".", "!", "?", "...", ":", ";"]
        DEFAULT_BREAK_MARKERS = []

        languages = self.get_all_languages()
        lang_info = languages.get(lang_code, {})

        return {
            "sentence_endings": lang_info.get(
                "sentence_endings", DEFAULT_SENTENCE_ENDINGS
            ),
            "break_markers": lang_info.get("break_markers", DEFAULT_BREAK_MARKERS),
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
            if lang_info.get("name", "").lower() == name_or_code.lower():
                return code

        # If still not found, try partial matches
        for code, lang_info in languages.items():
            lang_name = lang_info.get("name", "").lower()
            if name_or_code.lower() in lang_name or lang_name in name_or_code.lower():
                return code

        # If no match found, return None
        return None


# Global instance for easy access
language_config = LanguageConfig()
