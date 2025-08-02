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
    2. Manual .env/business_glossary.json (fallback)
    3. Built-in defaults (last resort)
    """

    def __init__(self, settings_manager: SettingsManager):
        """Initialize the GUI config manager"""
        self.settings_manager = settings_manager
        self.logger = logging.getLogger(__name__)

        # Built-in defaults
        self.DEFAULT_EXCLUDED_TERMS = [
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

        self.DEFAULT_BUSINESS_GLOSSARY = {
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

    def get_excluded_terms(self) -> List[str]:
        """
        Get excluded terms using three-tier fallback system

        Returns:
            List of terms to exclude from translation
        """
        # Priority 1: GUI AI-generated config
        ai_excluded_terms, _ = self.settings_manager.load_ai_config()
        if ai_excluded_terms:
            self.logger.info("Using AI-generated excluded terms")
            return ai_excluded_terms

        # Priority 2: Manual .env file fallback
        env_excluded_terms = self._load_excluded_terms_from_env()
        if env_excluded_terms:
            self.logger.info("Using excluded terms from .env file")
            return env_excluded_terms

        # Priority 3: Built-in defaults
        self.logger.info("Using default excluded terms")
        return self.DEFAULT_EXCLUDED_TERMS.copy()

    def get_business_glossary(self, target_language: str) -> Dict[str, str]:
        """
        Get business glossary for a specific language using three-tier fallback

        Args:
            target_language: Target language for translation

        Returns:
            Dictionary of English terms to translated terms
        """
        # Priority 1: GUI AI-generated config
        _, ai_business_glossary = self.settings_manager.load_ai_config()
        if (
            target_language in ai_business_glossary
            and ai_business_glossary[target_language]
        ):
            self.logger.info(
                f"Using AI-generated business glossary for {target_language}"
            )
            return ai_business_glossary[target_language]

        # Priority 2: Manual business_glossary.json fallback
        manual_glossary = self._load_business_glossary_from_file()
        if target_language in manual_glossary and manual_glossary[target_language]:
            self.logger.info(f"Using business glossary from file for {target_language}")
            return manual_glossary[target_language]

        # Priority 3: Built-in defaults
        if target_language in self.DEFAULT_BUSINESS_GLOSSARY:
            self.logger.info(f"Using default business glossary for {target_language}")
            return self.DEFAULT_BUSINESS_GLOSSARY[target_language].copy()

        # No glossary available for this language
        self.logger.warning(f"No business glossary available for {target_language}")
        return {}

    def get_all_business_glossaries(self) -> Dict[str, Dict[str, str]]:
        """
        Get business glossaries for all languages using three-tier fallback

        Returns:
            Dictionary with language keys and term-translation pairs
        """
        # Priority 1: GUI AI-generated config
        _, ai_business_glossary = self.settings_manager.load_ai_config()
        if ai_business_glossary:
            self.logger.info("Using AI-generated business glossaries")
            return ai_business_glossary

        # Priority 2: Manual business_glossary.json fallback
        manual_glossary = self._load_business_glossary_from_file()
        if manual_glossary:
            self.logger.info("Using business glossaries from file")
            return manual_glossary

        # Priority 3: Built-in defaults
        self.logger.info("Using default business glossaries")
        return self.DEFAULT_BUSINESS_GLOSSARY.copy()

    def get_config_source_info(self) -> Dict[str, str]:
        """
        Get information about which configuration source is being used

        Returns:
            Dictionary with source information for excluded terms and business glossary
        """
        info = {}

        # Check excluded terms source
        ai_excluded_terms, _ = self.settings_manager.load_ai_config()
        if ai_excluded_terms:
            info["excluded_terms_source"] = "AI Generated"
        elif self._load_excluded_terms_from_env():
            info["excluded_terms_source"] = "Manual (.env)"
        else:
            info["excluded_terms_source"] = "Default"

        # Check business glossary source
        _, ai_business_glossary = self.settings_manager.load_ai_config()
        if ai_business_glossary:
            info["business_glossary_source"] = "AI Generated"
        elif self._load_business_glossary_from_file():
            info["business_glossary_source"] = "Manual (business_glossary.json)"
        else:
            info["business_glossary_source"] = "Default"

        return info

    def _load_excluded_terms_from_env(self) -> List[str]:
        """Load excluded terms from .env file"""
        try:
            env_file = ".env"
            if not os.path.exists(env_file):
                return []

            excluded_terms = []
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("EXCLUDED_TERMS="):
                        # Parse comma-separated terms
                        terms_str = line.split("=", 1)[1].strip()
                        if terms_str.startswith('"') and terms_str.endswith('"'):
                            terms_str = terms_str[1:-1]
                        excluded_terms = [
                            term.strip()
                            for term in terms_str.split(",")
                            if term.strip()
                        ]
                        break

            return excluded_terms

        except Exception as e:
            self.logger.error(f"Error loading excluded terms from .env: {e}")
            return []

    def _load_business_glossary_from_file(self) -> Dict[str, Dict[str, str]]:
        """Load business glossary from business_glossary.json file"""
        try:
            glossary_file = "business_glossary.json"
            if not os.path.exists(glossary_file):
                return {}

            with open(glossary_file, "r", encoding="utf-8") as f:
                business_glossary = json.load(f)

            # Validate structure
            if not isinstance(business_glossary, dict):
                self.logger.warning("business_glossary.json is not a valid dictionary")
                return {}

            return business_glossary

        except Exception as e:
            self.logger.error(f"Error loading business glossary from file: {e}")
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

        # Validate excluded terms
        excluded_terms, _ = self.settings_manager.load_ai_config()
        if not excluded_terms:
            issues.append("No excluded terms in AI configuration")

        # Validate business glossary
        _, business_glossary = self.settings_manager.load_ai_config()
        if not business_glossary:
            issues.append("No business glossary in AI configuration")

        return len(issues) == 0, issues

    def get_config_summary(self) -> Dict[str, any]:
        """
        Get a summary of the current configuration status

        Returns:
            Dictionary with configuration summary information
        """
        excluded_terms = self.get_excluded_terms()
        business_glossaries = self.get_all_business_glossaries()
        source_info = self.get_config_source_info()
        is_valid, issues = self.validate_ai_config()

        return {
            "excluded_terms_count": len(excluded_terms),
            "business_glossary_languages": list(business_glossaries.keys()),
            "total_glossary_terms": sum(
                len(glossary) for glossary in business_glossaries.values()
            ),
            "source_info": source_info,
            "ai_config_valid": is_valid,
            "ai_config_issues": issues,
            "has_ai_config": self.settings_manager.has_ai_config(),
            "ai_config_age_days": self.settings_manager.get_ai_config_age_days(),
            "files_changed": self.settings_manager.has_files_changed(),
        }
