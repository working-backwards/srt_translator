"""
GUI Configuration Manager
Handles the three-tier fallback system for translation configurations
"""

import json
import logging
import os
from typing import Dict, List, Optional, Tuple

from .settings_manager import SettingsManager


class GUIConfigManager:
    """
    Manages configuration retrieval with three-tier fallback system:
    1. GUI AI-generated config (highest priority)
    2. Manual environment/termbase.json (fallback)
    3. Built-in defaults (last resort)
    """

    def __init__(self, settings_manager: SettingsManager):
        """Initialize the GUI config manager"""
        self.settings_manager = settings_manager
        self.logger = logging.getLogger(__name__)

        # Built-in defaults
        self.DEFAULT_DNT_TERMS = [
            "API",
            "CEO",
            "CFO",
            "CTO",
            "HR",
            "IT",
            "UI",
            "UX",
            "GDPR",
            "ROI",
        ]

        self.DEFAULT_TERMBASE = {
            "Spanish": {
                "operating plan": "plan operativo",
                "business review": "revisión de negocio",
                "input metrics": "métricas de entrada",
            },
            "French": {
                "operating plan": "plan opérationnel",
                "business review": "revue d'affaires",
                "input metrics": "indicateurs d'entrée",
            },
            "German": {
                "operating plan": "Betriebsplan",
                "business review": "Geschäftsüberprüfung",
                "input metrics": "Eingangskennzahlen",
            },
        }

    def get_dnt_terms(self) -> List[str]:
        """
        Get DNT terms using three-tier fallback system

        Returns:
            List of terms to exclude from translation
        """
        # Priority 1: GUI AI-generated config
        ai_dnt_terms, _ = self.settings_manager.load_ai_config()
        if ai_dnt_terms:
            self.logger.info("Using AI-generated DNT terms")
            return ai_dnt_terms

        # Priority 2: Manual environment variable fallback
        env_dnt_terms = self._load_dnt_terms_from_env()
        if env_dnt_terms:
            self.logger.info("Using DNT terms from environment variables")
            return env_dnt_terms

        # Priority 3: Built-in defaults
        self.logger.info("Using default DNT terms")
        return self.DEFAULT_DNT_TERMS.copy()

    def get_termbase(self, target_language: str) -> Dict[str, str]:
        """
        Get termbase for a specific language using three-tier fallback

        Args:
            target_language: Target language for translation (can be name or code)

        Returns:
            Dictionary of English terms to translated terms
        """
        # Priority 1: GUI AI-generated config
        _, ai_termbase = self.settings_manager.load_ai_config()
        
        # Try direct lookup first
        if target_language in ai_termbase and ai_termbase[target_language]:
            self.logger.info(f"Using AI-generated termbase for {target_language}")
            return ai_termbase[target_language]
        
        # Try language name to code mapping
        try:
            from srt_core.config.language_config import language_config
            all_languages = language_config.get_all_languages()
            
            for code, lang_info in all_languages.items():
                if lang_info.get('name') == target_language:
                    if code in ai_termbase:
                        self.logger.info(f"Using AI-generated termbase for {target_language} (code: {code})")
                        return ai_termbase[code]
        except Exception as e:
            self.logger.debug(f"Error checking language mapping: {e}")
            pass

        # Priority 2: Manual termbase.json fallback
        manual_termbase = self._load_termbase_from_file()
        if target_language in manual_termbase and manual_termbase[target_language]:
            self.logger.info(f"Using termbase from file for {target_language}")
            return manual_termbase[target_language]

        # Priority 3: Built-in defaults
        if target_language in self.DEFAULT_TERMBASE:
            self.logger.info(f"Using default termbase for {target_language}")
            return self.DEFAULT_TERMBASE[target_language].copy()

        # No termbase available for this language
        self.logger.warning(f"No termbase available for {target_language}")
        return {}

    def get_all_termbases(self) -> Dict[str, Dict[str, str]]:
        """
        Get termbases for all languages using three-tier fallback

        Returns:
            Dictionary with language keys and term-translation pairs
        """
        # Priority 1: GUI AI-generated config
        _, ai_termbase = self.settings_manager.load_ai_config()
        if ai_termbase:
            self.logger.info("Using AI-generated termbases")
            return ai_termbase

        # Priority 2: Manual termbase.json fallback
        manual_termbase = self._load_termbase_from_file()
        if manual_termbase:
            self.logger.info("Using termbases from file")
            return manual_termbase

        # Priority 3: Built-in defaults
        self.logger.info("Using default termbases")
        return self.DEFAULT_TERMBASE.copy()

    def get_config_source_info(self) -> Dict[str, str]:
        """
        Get information about which configuration source is being used

        Returns:
            Dictionary with source information for DNT terms and termbase
        """
        info = {}

        # Check DNT terms source
        ai_dnt_terms, _ = self.settings_manager.load_ai_config()
        if ai_dnt_terms:
            info["dnt_terms_source"] = "AI Generated"
        elif self._load_dnt_terms_from_env():
            info["dnt_terms_source"] = "Manual (environment)"
        else:
            info["dnt_terms_source"] = "Default"

        # Check termbase source
        _, ai_termbase = self.settings_manager.load_ai_config()
        if ai_termbase:
            info["termbase_source"] = "AI Generated"
        elif self._load_termbase_from_file():
            info["termbase_source"] = "Manual (termbase.json)"
        else:
            info["termbase_source"] = "Default"

        return info

    def _load_dnt_terms_from_env(self) -> List[str]:
        """Load DNT terms from environment variables"""
        try:
            # Check environment variable first
            dnt_terms_str = os.environ.get("DNT_TERMS", "")
            if dnt_terms_str:
                # Parse the string format: ["term1", "term2", "term3"]
                if dnt_terms_str.startswith('[') and dnt_terms_str.endswith(']'):
                    terms_content = dnt_terms_str[1:-1]
                    dnt_terms = [
                        term.strip().strip('"').strip("'")
                        for term in terms_content.split(",")
                        if term.strip()
                    ]
                    return dnt_terms
            
            return []

        except Exception as e:
            self.logger.error(f"Error loading DNT terms from environment: {e}")
            return []

    def _load_termbase_from_file(self) -> Dict[str, Dict[str, str]]:
        """Load termbase from termbase.json file"""
        try:
            termbase_file = "termbase.json"
            if not os.path.exists(termbase_file):
                return {}

            with open(termbase_file, "r", encoding="utf-8") as f:
                termbase = json.load(f)

            # Validate structure
            if not isinstance(termbase, dict):
                self.logger.warning("termbase.json is not a valid dictionary")
                return {}

            return termbase

        except Exception as e:
            self.logger.error(f"Error loading termbase from file: {e}")
            return {}

    def validate_ai_config(self) -> Tuple[bool, List[str]]:
        """
        Validate the current AI configuration

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []

        # Check if AI config exists
        if not self.settings_manager.has_ai_config():
            issues.append("No AI configuration found")
            return False, issues

        # Check if AI config is recent
        if not self.settings_manager.has_recent_ai_config():
            age_days = self.settings_manager.get_ai_config_age_days()
            issues.append(
                f"AI configuration is {age_days} days old (older than 30 days)"
            )

        # Check if files have changed
        if self.settings_manager.has_files_changed():
            issues.append(
                "Selected files have changed since AI configuration was generated"
            )

        # Validate DNT terms
        dnt_terms, _ = self.settings_manager.load_ai_config()
        if not dnt_terms:
            issues.append("No DNT terms in AI configuration")

        # Validate termbase
        _, termbase = self.settings_manager.load_ai_config()
        if not termbase:
            issues.append("No termbase in AI configuration")

        return len(issues) == 0, issues

    def get_config_summary(self) -> Dict[str, any]:
        """
        Get a summary of the current configuration status

        Returns:
            Dictionary with configuration summary information
        """
        dnt_terms = self.get_dnt_terms()
        termbases = self.get_all_termbases()
        source_info = self.get_config_source_info()
        is_valid, issues = self.validate_ai_config()

        return {
            "dnt_terms_count": len(dnt_terms),
            "termbase_languages": list(termbases.keys()),
            "total_termbase_terms": sum(
                len(termbase) for termbase in termbases.values()
            ),
            "source_info": source_info,
            "ai_config_valid": is_valid,
            "ai_config_issues": issues,
            "has_ai_config": self.settings_manager.has_ai_config(),
            "ai_config_age_days": self.settings_manager.get_ai_config_age_days(),
            "files_changed": self.settings_manager.has_files_changed(),
        }
