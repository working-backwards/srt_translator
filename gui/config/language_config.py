"""
Unified Language Configuration
Handles loading and accessing language configuration from JSON file
"""

import json
import logging
import os
from typing import Dict, List, Optional


class LanguageConfig:
    """Unified language configuration manager"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "config", "languages.json"
        )
        self.config = self.load_config()

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
                "ru",
                "nl",
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
                "ru": {"name": "Russian", "popular": True},
                "nl": {"name": "Dutch", "popular": True},
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


# Global instance for easy access
language_config = LanguageConfig()
