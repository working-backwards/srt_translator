"""
Settings Manager for SRT Translator GUI
Handles persistent storage of user preferences and settings
"""

import json
import logging
import os
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

from PySide6.QtCore import QSettings

from srt_core.config.language_config import language_config


@dataclass
class ConfigState:
    """Immutable configuration state with validation"""

    target_languages: Dict[str, str]  # language_name -> language_code
    dnt_terms: List[str]
    termbase: Dict[str, Dict[str, str]]  # language_code -> {term -> translation}
    output_directory: Optional[str] = None
    api_key: Optional[str] = None

    def __post_init__(self):
        """Validate state after initialization"""
        if not isinstance(self.target_languages, dict):
            raise ValueError("target_languages must be a dictionary")
        if not isinstance(self.dnt_terms, list):
            raise ValueError("dnt_terms must be a list")
        if not isinstance(self.termbase, dict):
            raise ValueError("termbase must be a dictionary")

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ConfigState":
        """Create from dictionary with validation"""
        return cls(**data)

    def copy(self) -> "ConfigState":
        """Create a deep copy of the state"""
        return ConfigState(
            target_languages=self.target_languages.copy(),
            dnt_terms=self.dnt_terms.copy(),
            termbase={k: v.copy() for k, v in self.termbase.items()},
            output_directory=self.output_directory,
            api_key=self.api_key,
        )


class SettingsManager:
    """Manages persistent settings for the SRT Translator GUI"""

    def __init__(self):
        self.settings = QSettings("SRTTranslator", "SRTTranslator")
        self._state = ConfigState(target_languages={}, dnt_terms=[], termbase={})
        self._lock = threading.Lock()
        self.logger = logging.getLogger(__name__)

    # === CENTRALIZED STATE MANAGEMENT ===

    def get_current_state(self) -> ConfigState:
        """Get current state (thread-safe)"""
        with self._lock:
            # If current state is empty, try to load AI configuration
            if not self._state.dnt_terms and not self._state.termbase:
                try:
                    ai_dnt_terms, ai_termbase = self.load_ai_config()
                    if ai_dnt_terms or ai_termbase:
                        self.logger.info("Loading AI configuration into current state")
                        new_state = self._state.copy()
                        new_state.dnt_terms = ai_dnt_terms.copy()
                        new_state.termbase = {
                            k: v.copy() for k, v in ai_termbase.items()
                        }
                        self._state = new_state
                except Exception as e:
                    self.logger.warning(f"Failed to load AI configuration: {e}")

            return self._state.copy()

    def update_state(self, new_state: ConfigState):
        """Update state (thread-safe)"""
        with self._lock:
            self._state = new_state
        self._persist_state(new_state)

    def get_current_target_languages(self) -> Dict[str, str]:
        """Get current language selection from UI state (thread-safe)"""
        with self._lock:
            return self._state.target_languages.copy()

    def update_target_languages(self, languages: Dict[str, str]):
        """Update both UI state and persistent storage (thread-safe)"""
        with self._lock:
            new_state = self._state.copy()
            new_state.target_languages = languages.copy()
            self._state = new_state
        self._persist_state(self._state)
        # Also update legacy storage for backward compatibility
        self.save_target_languages(languages)

    def get_current_dnt_terms(self) -> List[str]:
        """Get current DNT terms (thread-safe)"""
        with self._lock:
            return self._state.dnt_terms.copy()

    def update_dnt_terms(self, dnt_terms: List[str]):
        """Update DNT terms (thread-safe)"""
        with self._lock:
            new_state = self._state.copy()
            new_state.dnt_terms = dnt_terms.copy()
            self._state = new_state
        self._persist_state(self._state)

    def get_current_termbase(self) -> Dict[str, Dict[str, str]]:
        """Get current termbase (thread-safe)"""
        with self._lock:
            return {k: v.copy() for k, v in self._state.termbase.items()}

    def update_termbase(self, termbase: Dict[str, Dict[str, str]]):
        """Update termbase (thread-safe)"""
        with self._lock:
            new_state = self._state.copy()
            new_state.termbase = {k: v.copy() for k, v in termbase.items()}
            self._state = new_state
        self._persist_state(self._state)

    def _persist_state(self, state: ConfigState):
        """Persist state to storage"""
        try:
            state_dict = state.to_dict()
            # Remove sensitive data before persistence
            if "api_key" in state_dict:
                del state_dict["api_key"]
            # Save to QSettings
            self.settings.setValue("current_state", state_dict)
        except Exception as e:
            self.logger.error(f"Failed to persist state: {e}")

    def _load_state_from_storage(self) -> ConfigState:
        """Load state from storage"""
        try:
            data = self.settings.value("current_state", {})
            if data:
                return ConfigState.from_dict(data)
        except Exception as e:
            self.logger.warning(f"Failed to load state, using defaults: {e}")
        return ConfigState(target_languages={}, dnt_terms=[], termbase={})

    # === LEGACY METHODS (for backward compatibility) ===

    def save_api_key(self, api_key: str) -> None:
        """Save API key to settings"""
        self.settings.setValue("api_key", api_key)
        # Also update current state
        with self._lock:
            new_state = self._state.copy()
            new_state.api_key = api_key
            self._state = new_state

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

    def load_language_usage_data(self) -> Dict[str, Dict]:
        """Load language usage tracking data"""
        return self.settings.value("language_usage_data", {})

    def save_language_usage_data(self, usage_data: Dict[str, Dict]) -> None:
        """Save language usage tracking data"""
        self.settings.setValue("language_usage_data", usage_data)

    def _update_adaptive_popular_languages(self, usage_data: Dict[str, Dict]) -> None:
        """Update adaptive popular languages based on usage data"""
        # Sort languages by usage count (descending) and then by last used (descending)
        sorted_languages = sorted(
            usage_data.items(),
            key=lambda x: (x[1]["count"], x[1]["last_used"] or ""),
            reverse=True,
        )

        # Get top used languages
        popular_limit = language_config.get_popular_limit()
        top_languages = [lang_code for lang_code, _ in sorted_languages[:popular_limit]]

        # Save as user's preferred popular languages
        self.save_user_popular_languages(top_languages)

    def get_all_languages(self) -> Dict[str, str]:
        """Get all available languages from unified config"""
        return language_config.get_all_languages()

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
        """Save list of selected files"""
        self.settings.setValue("selected_files", file_paths)

    def load_selected_files(self) -> List[str]:
        """Load list of selected files"""
        return self.settings.value("selected_files", [])

    def save_window_geometry(self, geometry: bytes) -> None:
        """Save window geometry"""
        self.settings.setValue("window_geometry", geometry)

    def load_window_geometry(self) -> Optional[bytes]:
        """Load window geometry"""
        return self.settings.value("window_geometry", None)

    def clear_all_settings(self) -> None:
        """Clear all settings"""
        self.settings.clear()
        # Reset current state
        with self._lock:
            self._state = ConfigState(target_languages={}, dnt_terms=[], termbase={})

    def save_ai_config(
        self, dnt_terms: List[str], termbase: Dict[str, Dict[str, str]]
    ) -> None:
        """Save AI-generated configuration"""
        # Save to legacy storage
        self.settings.setValue("ai_dnt_terms", dnt_terms)
        self.settings.setValue("ai_termbase", termbase)
        self.settings.setValue("ai_config_timestamp", datetime.now().isoformat())

        # Also update current state
        with self._lock:
            new_state = self._state.copy()
            new_state.dnt_terms = dnt_terms.copy()
            new_state.termbase = {k: v.copy() for k, v in termbase.items()}
            self._state = new_state

        # Calculate and store file hash for change detection
        file_hash = self._calculate_file_hash()
        self.settings.setValue("ai_config_file_hash", file_hash)

    def load_ai_config(
        self,
    ) -> Tuple[List[str], Dict[str, Dict[str, str]]]:
        """Load AI-generated configuration"""
        dnt_terms = self.settings.value("ai_dnt_terms", [])
        termbase = self.settings.value("ai_termbase", {})
        return dnt_terms, termbase

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
        dnt_terms, termbase = self.load_ai_config()
        return bool(dnt_terms or termbase)

    def clear_ai_config(self) -> None:
        """Clear AI configuration"""
        self.settings.remove("ai_dnt_terms")
        self.settings.remove("ai_termbase")
        self.settings.remove("ai_config_timestamp")
        self.settings.remove("ai_config_file_hash")

        # Also clear from current state
        with self._lock:
            new_state = self._state.copy()
            new_state.dnt_terms = []
            new_state.termbase = {}
            self._state = new_state

    def get_ai_config_age_days(self) -> Optional[int]:
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

    def _calculate_file_hash(self) -> str:
        """Calculate hash of selected files for change detection"""
        try:
            import hashlib

            selected_files = self.load_selected_files()
            if not selected_files:
                return ""

            # Create hash from file paths and modification times
            hash_input = ""
            for file_path in selected_files:
                if os.path.exists(file_path):
                    stat = os.stat(file_path)
                    hash_input += f"{file_path}:{stat.st_mtime}:{stat.st_size}\n"

            return hashlib.md5(hash_input.encode()).hexdigest()
        except Exception as e:
            self.logger.error(f"Error calculating file hash: {e}")
            return ""

    def has_files_changed(self) -> bool:
        """Check if selected files have changed since AI config was generated"""
        stored_hash = self.settings.value("ai_config_file_hash", "")
        if not stored_hash:
            return True  # No stored hash means files have "changed"

        current_hash = self._calculate_file_hash()
        return stored_hash != current_hash
