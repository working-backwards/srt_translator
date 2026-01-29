#!/usr/bin/env python3
"""
Settings Manager for the SRT Translator GUI.
Handles persistent storage of user preferences and configuration.
"""

import hashlib
import logging
import os
from datetime import datetime
from typing import Any

from PySide6.QtCore import QSettings

from srt_translator.core.config.language_config import LanguageConfig


class SettingsManager:
    """Manages persistent settings for the SRT Translator GUI (AI Config is SSOT)"""

    def __init__(self, language_config: LanguageConfig):
        self.settings = QSettings("SRTTranslator", "SRTTranslator")
        self.logger = logging.getLogger(__name__)
        self.language_config = language_config

    # NOTE: All former 'current_state' APIs have been removed.
    # AI Config stored in QSettings is the single source of truth.

    def load_last_input_directory(self) -> str:
        """Load last used input directory"""
        return self.settings.value("last_input_directory", "")

    def save_last_output_directory(self, directory: str) -> None:
        """Save last used output directory"""
        self.settings.setValue("last_output_directory", directory)

    def load_last_output_directory(self) -> str:
        """Load last used output directory"""
        return self.settings.value("last_output_directory", "")

    def save_selected_files(self, file_paths: list[str]) -> None:
        """Save list of selected files"""
        self.settings.setValue("selected_files", file_paths)

    def load_selected_files(self) -> list[str]:
        """Load list of selected files"""
        return self.settings.value("selected_files", [])

    def save_ai_config(
        self,
        dnt_terms: list[str],
        termbase: dict[str, dict[str, str]],
        source_language: dict[str, object] | None = None,
    ) -> None:
        """Save AI-generated configuration"""
        # Save AI configuration
        self.settings.setValue("ai_dnt_terms", dnt_terms)
        self.settings.setValue("ai_termbase", termbase)
        self.settings.setValue("ai_source_language", source_language or {})
        self.settings.setValue("ai_config_timestamp", datetime.now().isoformat())

        # Calculate and store file hash for change detection
        file_hash = self._calculate_file_hash()
        self.settings.setValue("ai_config_file_hash", file_hash)

    def load_ai_config(self) -> tuple[list[str], dict[str, dict[str, str]], dict[str, Any]]:
        """Load AI-generated configuration as a stable 3-tuple.
        Returns:
            tuple(dnt_terms, termbase, source_language)
        """

        dnt_terms = self.settings.value("ai_dnt_terms", [])
        termbase = self.settings.value("ai_termbase", {})
        source_language = self.settings.value("ai_source_language", {})

        # Defensive normalization: QSettings may hand back unexpected types
        if not isinstance(dnt_terms, list):
            dnt_terms = []
        if not isinstance(termbase, dict):
            termbase = {}
        if not isinstance(source_language, dict):
            source_language = {}

        return dnt_terms, termbase, source_language

    def has_recent_ai_config(self, max_age_days: int = 30) -> bool:
        """Check if AI configuration is recent"""
        timestamp_str = self.settings.value("ai_config_timestamp", "")
        if not timestamp_str:
            return False

        try:
            timestamp = datetime.fromisoformat(timestamp_str)
            age = datetime.now() - timestamp
            return age.days <= max_age_days
        except (ValueError, TypeError):
            return False

    def has_ai_config(self) -> bool:
        """Check if AI configuration exists"""
        dnt_terms, termbase, _ = self.load_ai_config()
        return bool(dnt_terms or termbase)

    def clear_ai_config(self) -> None:
        """Clear AI configuration"""
        self.settings.remove("ai_dnt_terms")
        self.settings.remove("ai_termbase")
        self.settings.remove("ai_source_language")
        self.settings.remove("ai_config_timestamp")
        self.settings.remove("ai_config_file_hash")

    def get_ai_config_age_days(self) -> int | None:
        """Get age of AI configuration in days"""
        timestamp_str = self.settings.value("ai_config_timestamp", "")
        if not timestamp_str:
            return None

        try:
            timestamp = datetime.fromisoformat(timestamp_str)
            age = datetime.now() - timestamp
            return age.days
        except (ValueError, TypeError):
            return None

    def save_api_key(self, api_key: str) -> None:
        """Save API key to settings"""
        self.settings.setValue("api_key", api_key)

    def load_api_key(self) -> str:
        """Load API key from settings"""
        value = self.settings.value("api_key", "")
        return str(value) if value is not None else ""

    def save_target_languages(self, languages: dict[str, str]) -> None:
        """Save target languages dictionary"""
        self.settings.setValue("target_languages", languages)

    # --- UI compatibility shims (keep SSOT in QSettings) ---
    def update_target_languages(self, languages: dict[str, str]) -> None:
        self.save_target_languages(languages)

    def get_current_target_languages(self) -> dict[str, str]:
        return self.load_target_languages()

    def load_target_languages(self) -> dict[str, str]:
        """Load target languages dictionary"""
        value = self.settings.value("target_languages", {})
        if isinstance(value, dict):
            return value
        return {}

    def save_target_languages_from_codes(self, language_codes: list[str]) -> None:
        """Save target languages from list of language codes using unified config"""
        languages = {}
        for code in language_codes:
            if self.language_config.validate_language_code(code):
                name = self.language_config.get_language_name(code)
                languages[name] = code

        self.save_target_languages(languages)

    def load_target_language_codes(self) -> list[str]:
        """Load target languages as list of codes"""
        languages = self.load_target_languages()
        return list(languages.values())

    def get_popular_languages(self) -> list[str]:
        """Get popular languages from unified config"""
        return self.language_config.get_popular_languages()

    def get_adaptive_popular_languages(self) -> list[str]:
        """
        Get adaptive popular languages based on user preferences and usage.

        Returns:
            List of language codes for popular languages, combining:
            - User's frequently used languages
            - Default popular languages to fill remaining slots
        """
        popular_limit = self.language_config.get_popular_limit()
        user_preferences = self.load_user_popular_languages()
        default_popular = self.language_config.get_popular_languages()

        # If user has no preferences, use default popular languages
        if not user_preferences:
            return default_popular[:popular_limit]

        # If user has preferences but they're fewer than the limit,
        # fill the remaining slots with default popular languages
        if len(user_preferences) < popular_limit:
            # Get default languages that aren't already in user preferences
            remaining_defaults = [code for code in default_popular if code not in user_preferences]
            # Fill up to the limit
            additional_languages = remaining_defaults[: popular_limit - len(user_preferences)]
            return user_preferences + additional_languages
        # If user has enough preferences, use them (up to the limit)
        return user_preferences[:popular_limit]

    def save_user_popular_languages(self, language_codes: list[str]) -> None:
        """Save user's preferred popular languages (deduped, capped to limit)"""
        try:
            # Ensure uniqueness while preserving order
            seen = set()
            deduped = []
            for code in language_codes or []:
                if code not in seen:
                    seen.add(code)
                    deduped.append(code)
            # Cap to configured limit
            limit = self.language_config.get_popular_limit()
            capped = deduped[:limit]
            self.settings.setValue("user_popular_languages", capped)
        except Exception as e:
            self.logger.warning("Failed to save user popular languages: %s", e)

    def load_user_popular_languages(self) -> list[str]:
        """Load user's preferred popular languages"""
        value = self.settings.value("user_popular_languages", [])
        if isinstance(value, list):
            return value
        return []

    def reset_adaptive_popular_languages(self) -> None:
        """Reset adaptive popular languages to default values"""
        self.settings.remove("user_popular_languages")

    def track_language_usage(self, language_code: str) -> None:
        """Track language usage for adaptive popular languages"""
        usage_data = self.load_language_usage_data()

        # Update usage count and last used timestamp
        if language_code not in usage_data:
            usage_data[language_code] = {"count": 0, "last_used": None}

        usage_data[language_code]["count"] += 1
        usage_data[language_code]["last_used"] = datetime.now().isoformat()

        self.save_language_usage_data(usage_data)
        self._update_adaptive_popular_languages(usage_data)

    def load_language_usage_data(self) -> dict[str, dict]:
        """Load language usage tracking data"""
        return self.settings.value("language_usage_data", {})

    def save_language_usage_data(self, usage_data: dict[str, dict]) -> None:
        """Save language usage tracking data"""
        self.settings.setValue("language_usage_data", usage_data)

    def _update_adaptive_popular_languages(self, usage_data: dict[str, dict]) -> None:
        """Update adaptive popular languages based on usage data"""
        # Sort languages by usage count (descending) and then by last used
        # (descending)
        sorted_languages = sorted(
            usage_data.items(),
            key=lambda x: (x[1]["count"], x[1]["last_used"] or ""),
            reverse=True,
        )

        # Get top used languages
        popular_limit = self.language_config.get_popular_limit()
        top_languages = [lang_code for lang_code, _ in sorted_languages[:popular_limit]]

        # Save as user's preferred popular languages (will dedupe/cap)
        self.save_user_popular_languages(top_languages)

    def get_all_languages(self) -> dict[str, str]:
        """Get all available languages from unified config"""
        return self.language_config.get_all_languages()

    def save_last_input_directory(self, directory: str) -> None:
        """Save last used input directory"""
        self.settings.setValue("last_input_directory", directory)

    def _calculate_file_hash(self) -> str:
        """Calculate hash of selected files for change detection"""
        try:
            selected_files = self.load_selected_files()
            if not selected_files:
                return ""

            # Create hash from file paths and modification times
            hash_input = ""
            for file_path in selected_files:
                if os.path.exists(file_path):
                    stat = os.stat(file_path)
                    hash_input += f"{file_path}:{stat.st_mtime}:{stat.st_size}\n"

            return hashlib.md5(hash_input.encode(), usedforsecurity=False).hexdigest()
        except Exception as e:
            self.logger.error("Error calculating file hash: %s", e)
            return ""

    def has_files_changed(self) -> bool:
        """Check if selected files have changed since AI config was generated"""
        stored_hash = self.settings.value("ai_config_file_hash", "")
        if not stored_hash:
            return True  # No stored hash means files have "changed"

        current_hash = self._calculate_file_hash()
        return stored_hash != current_hash

    def save_user_termbase(self, termbase: dict[str, dict[str, str]]) -> None:
        """Save user-provided termbase that will be merged with AI-generated termbase"""
        self.settings.setValue("user_termbase", termbase)
        self.logger.info("Saved user-provided termbase: %s languages", len(termbase))

    def load_user_termbase(self) -> dict[str, dict[str, str]]:
        """Load user-provided termbase"""
        value = self.settings.value("user_termbase", {})
        if isinstance(value, dict):
            return value
        return {}

    def save_user_dnt_terms(self, dnt_terms: list[str]) -> None:
        """Save user-provided DNT terms that will be merged with AI-generated DNT terms"""
        self.settings.setValue("user_dnt_terms", dnt_terms)
        self.logger.info("Saved user-provided DNT terms: %s terms", len(dnt_terms))

    def load_user_dnt_terms(self) -> list[str]:
        """Load user-provided DNT terms"""
        value = self.settings.value("user_dnt_terms", [])
        if isinstance(value, list):
            return value
        return []

    def save_tone(self, tone: str) -> None:
        """Save translation tone setting (casual, neutral, or formal)"""
        # Normalize to lowercase and validate
        tone_lower = (tone or "neutral").lower().strip()
        if tone_lower not in ("casual", "neutral", "formal"):
            tone_lower = "neutral"
        self.settings.setValue("tone", tone_lower)

    def load_tone(self) -> str:
        """Load translation tone setting (defaults to 'neutral')"""
        value = self.settings.value("tone", "neutral")
        tone = str(value).lower().strip() if value else "neutral"
        # Validate and return
        if tone in ("casual", "neutral", "formal"):
            return tone
        return "neutral"
