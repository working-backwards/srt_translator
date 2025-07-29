"""
Settings Manager for SRT Translator GUI
Handles persistent storage of user preferences and settings
"""

import os
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