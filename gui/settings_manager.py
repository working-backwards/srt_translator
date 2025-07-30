"""
Settings Manager for SRT Translator GUI
Handles persistent storage of user preferences and settings
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from PySide6.QtCore import QSettings


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
    def save_ai_config(self, excluded_terms: List[str], business_glossary: Dict[str, Dict[str, str]]) -> None:
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