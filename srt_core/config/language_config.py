"""
Unified Language Configuration for CLI
Handles loading and accessing language configuration from JSON file
"""

import json
import logging
import os
import sys
from typing import Dict, List, Optional


class LanguageConfig:
    """Unified language configuration manager for CLI"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # Resolve path to languages.json with robust handling for PyInstaller builds
        self.config_path = self._resolve_languages_path()
        self.config = self.load_config()

    def _resolve_languages_path(self) -> str:
        """Resolve the languages.json path for both source and packaged builds.

        Order:
        1) PyInstaller one-file/one-dir runtime under sys._MEIPASS: config/languages.json
        2) Source tree relative to this file: ../../config/languages.json
        """
        # 1) PyInstaller
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidate = os.path.join(meipass, "config", "languages.json")
            if os.path.exists(candidate):
                return candidate

        # 2) Source tree relative path
        candidate = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "..", "config", "languages.json")
        )
        return candidate

    def load_config(self) -> Dict:
        """Load language configuration from JSON file"""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                self.logger.info(
                    f"Loaded language config with {len(config.get('languages', {}))} languages"
                )
                return config
        except FileNotFoundError:
            self.logger.error(f"Language config file not found: {self.config_path}")
            return self.get_fallback_config()
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in language config: {e}")
            return self.get_fallback_config()
        except Exception as e:
            self.logger.error(f"Error loading language config: {e}")
            return self.get_fallback_config()

    def get_fallback_config(self) -> Dict:
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

    def get_all_languages(self) -> Dict[str, Dict]:
        """Get all available languages"""
        return self.config.get("languages", {})

    def get_popular_languages(self) -> List[str]:
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

    def get_language_codes(self) -> List[str]:
        """Get list of all language codes"""
        return list(self.get_all_languages().keys())

    def get_language_names(self) -> Dict[str, str]:
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

    def get_target_languages_dict(self) -> Dict[str, str]:
        """Get target languages in the format expected by CLI (name: code)"""
        languages = self.get_all_languages()
        return {lang.get("name", code): code for code, lang in languages.items()}

    def get_language_rules(self, lang_code: str) -> Dict[str, List[str]]:
        """Get language-specific sentence boundary rules"""
        DEFAULT_SENTENCE_ENDINGS = [".", "!", "?", "...", ":", ";"]
        DEFAULT_BREAK_MARKERS = []
        
        languages = self.get_all_languages()
        lang_info = languages.get(lang_code, {})
        
        return {
            "sentence_endings": lang_info.get("sentence_endings", DEFAULT_SENTENCE_ENDINGS),
            "break_markers": lang_info.get("break_markers", DEFAULT_BREAK_MARKERS)
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
