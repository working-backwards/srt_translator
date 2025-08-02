"""
Settings Manager for SRT Translator GUI
Handles persistent storage of user preferences and settings
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import QSettings

from .config.language_config import language_config


class SettingsManager:
    """Manages persistent settings for the SRT Translator GUI"""

    def __init__(self):
        self.settings = QSettings("SRTTranslator", "SRTTranslator")

    def save_api_key(self, api_key: str) -> None:
        """Save API key to settings"""
        self.settings.setValue("api_key", api_key)

    def load_api_key(self) -> str:
        """Load API key from settings"""
        return self.settings.value("api_key", "")

    def save_target_languages(self, languages: Dict[str, str]) -> None:
        """Save target languages dictionary"""
        self.settings.setValue("target_languages", languages)

    def load_target_languages(self) -> Dict[str, str]:
        """Load target languages dictionary"""
        return self.settings.value("target_languages", {})

    def save_target_languages_from_codes(self, language_codes: List[str]) -> None:
        """Save target languages from list of language codes using unified config"""
        languages = {}
        for code in language_codes:
            if language_config.validate_language_code(code):
                name = language_config.get_language_name(code)
                languages[name] = code

        self.save_target_languages(languages)

    def load_target_language_codes(self) -> List[str]:
        """Load target languages as list of codes"""
        languages = self.load_target_languages()
        return list(languages.values())

    def get_popular_languages(self) -> List[str]:
        """Get popular languages from unified config"""
        return language_config.get_popular_languages()

    def get_adaptive_popular_languages(self) -> List[str]:
        """
        Get adaptive popular languages based on user preferences and usage

        Returns:
            List of language codes for popular languages, combining:
            - User's frequently used languages
            - Default popular languages to fill remaining slots
        """
        popular_limit = language_config.get_popular_limit()
        user_preferences = self.load_user_popular_languages()
        default_popular = language_config.get_popular_languages()

        # If user has no preferences, use default popular languages
        if not user_preferences:
            return default_popular[:popular_limit]

        # If user has preferences but they're fewer than the limit,
        # fill the remaining slots with default popular languages
        if len(user_preferences) < popular_limit:
            # Get default languages that aren't already in user preferences
            remaining_defaults = [
                code for code in default_popular if code not in user_preferences
            ]
            # Fill up to the limit
            additional_languages = remaining_defaults[
                : popular_limit - len(user_preferences)
            ]
            return user_preferences + additional_languages

        # If user has enough preferences, use them (up to the limit)
        return user_preferences[:popular_limit]

    def save_user_popular_languages(self, language_codes: List[str]) -> None:
        """Save user's preferred popular languages"""
        self.settings.setValue("user_popular_languages", language_codes)

    def load_user_popular_languages(self) -> List[str]:
        """Load user's preferred popular languages"""
        return self.settings.value("user_popular_languages", [])

    def reset_adaptive_popular_languages(self) -> None:
        """Reset adaptive popular languages to default values"""
        self.settings.remove("user_popular_languages")
        self.settings.remove("language_usage_data")
        logging.info("Reset adaptive popular languages to defaults")

    def track_language_usage(self, language_code: str) -> None:
        """
        Track when a user selects a language to improve adaptive popular languages

        Args:
            language_code: The language code that was selected
        """
        if not language_config.validate_language_code(language_code):
            return

        # Get current usage tracking
        usage_data = self.load_language_usage_data()

        # Update usage count and last used timestamp
        current_time = datetime.now().isoformat()
        if language_code in usage_data:
            usage_data[language_code]["count"] += 1
            usage_data[language_code]["last_used"] = current_time
        else:
            usage_data[language_code] = {"count": 1, "last_used": current_time}

        # Save updated usage data
        self.save_language_usage_data(usage_data)

        # Update popular languages if needed
        self._update_adaptive_popular_languages(usage_data)

    def load_language_usage_data(self) -> Dict[str, Dict]:
        """Load language usage tracking data"""
        return self.settings.value("language_usage_data", {})

    def save_language_usage_data(self, usage_data: Dict[str, Dict]) -> None:
        """Save language usage tracking data"""
        self.settings.setValue("language_usage_data", usage_data)

    def _update_adaptive_popular_languages(self, usage_data: Dict[str, Dict]) -> None:
        """
        Update adaptive popular languages based on usage data

        Args:
            usage_data: Dictionary of language usage statistics
        """
        popular_limit = language_config.get_popular_limit()
        current_popular = self.load_user_popular_languages()

        # Sort languages by usage count (descending) and then by last used (descending)
        sorted_languages = sorted(
            usage_data.items(),
            key=lambda x: (x[1]["count"], x[1]["last_used"]),
            reverse=True,
        )

        # Get top used languages
        top_used_codes = [code for code, _ in sorted_languages[:popular_limit]]

        # If the top used languages are different from current popular, update them
        if top_used_codes != current_popular:
            self.save_user_popular_languages(top_used_codes)
            logging.info(f"Updated adaptive popular languages: {top_used_codes}")

    def get_all_languages(self) -> Dict[str, str]:
        """Get all available languages from unified config"""
        return language_config.get_language_names()

    def save_last_input_directory(self, directory: str) -> None:
        """Save last used input directory"""
        self.settings.setValue("last_input_directory", directory)

    def load_last_input_directory(self) -> str:
        """Load last used input directory"""
        return self.settings.value("last_input_directory", "")

    def save_last_output_directory(self, directory: str) -> None:
        """Save last used output directory"""
        self.settings.setValue("last_output_directory", directory)

    def load_last_output_directory(self) -> str:
        """Load last used output directory"""
        return self.settings.value("last_output_directory", "")

    def save_selected_files(self, file_paths: List[str]) -> None:
        """Save list of selected file paths"""
        self.settings.setValue("selected_files", file_paths)

    def load_selected_files(self) -> List[str]:
        """Load list of selected file paths"""
        return self.settings.value("selected_files", [])

    def save_window_geometry(self, geometry: bytes) -> None:
        """Save window geometry"""
        self.settings.setValue("window_geometry", geometry)

    def load_window_geometry(self) -> Optional[bytes]:
        """Load window geometry"""
        return self.settings.value("window_geometry")

    def clear_all_settings(self) -> None:
        """Clear all saved settings"""
        self.settings.clear()

    # AI Configuration Methods
    def save_ai_config(
        self, excluded_terms: List[str], business_glossary: Dict[str, Dict[str, str]]
    ) -> None:
        """
        Save AI-generated configuration persistently

        Args:
            excluded_terms: List of terms to exclude from translation
            business_glossary: Dictionary with language keys and term-translation pairs
        """
        # Save excluded terms
        self.settings.setValue("ai_excluded_terms", excluded_terms)

        # Save business glossary as JSON string
        glossary_json = json.dumps(business_glossary, ensure_ascii=False)
        self.settings.setValue("ai_business_glossary", glossary_json)

        # Save timestamp
        timestamp = datetime.now().isoformat()
        self.settings.setValue("ai_config_timestamp", timestamp)

        # Save file hash to detect changes
        self.settings.setValue("ai_config_file_hash", self._calculate_file_hash())

    def load_ai_config(self) -> Tuple[List[str], Dict[str, Dict[str, str]]]:
        """
        Load last AI-generated configuration

        Returns:
            Tuple of (excluded_terms, business_glossary)
        """
        # Load excluded terms
        excluded_terms = self.settings.value("ai_excluded_terms", [])

        # Load business glossary
        glossary_json = self.settings.value("ai_business_glossary", "{}")
        try:
            business_glossary = json.loads(glossary_json)
        except (json.JSONDecodeError, TypeError):
            business_glossary = {}

        return excluded_terms, business_glossary

    def has_recent_ai_config(self, max_age_days: int = 30) -> bool:
        """
        Check if we have recent AI config to avoid re-generation

        Args:
            max_age_days: Maximum age in days for config to be considered recent

        Returns:
            True if recent config exists, False otherwise
        """
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
        """Check if any AI configuration exists"""
        excluded_terms, business_glossary = self.load_ai_config()
        return bool(excluded_terms or business_glossary)

    def clear_ai_config(self) -> None:
        """Clear all AI configuration data"""
        self.settings.remove("ai_excluded_terms")
        self.settings.remove("ai_business_glossary")
        self.settings.remove("ai_config_timestamp")
        self.settings.remove("ai_config_file_hash")

    def get_ai_config_age_days(self) -> Optional[int]:
        """
        Get the age of the AI configuration in days

        Returns:
            Age in days, or None if no config exists
        """
        timestamp_str = self.settings.value("ai_config_timestamp", "")
        if not timestamp_str:
            return None

        try:
            timestamp = datetime.fromisoformat(timestamp_str)
            age = datetime.now() - timestamp
            return age.days
        except (ValueError, TypeError):
            return None

    def _calculate_file_hash(self) -> str:
        """Calculate a simple hash of the current file selection for change detection"""
        # This is a simplified hash - in a real implementation, you might want
        # to hash the actual file contents or use file modification times
        selected_files = self.load_selected_files()
        if not selected_files:
            return ""

        # Simple hash based on file names and modification times
        hash_parts = []
        for file_path in selected_files:
            if os.path.exists(file_path):
                try:
                    mtime = os.path.getmtime(file_path)
                    hash_parts.append(f"{file_path}:{mtime}")
                except OSError:
                    hash_parts.append(file_path)

        return str(hash(tuple(hash_parts)))

    def has_files_changed(self) -> bool:
        """
        Check if the selected files have changed since last AI config generation

        Returns:
            True if files have changed, False otherwise
        """
        current_hash = self._calculate_file_hash()
        saved_hash = self.settings.value("ai_config_file_hash", "")
        return current_hash != saved_hash
