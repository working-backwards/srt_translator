#!/usr/bin/env python3
"""Configuration manager for the SRT Translator GUI (no fallbacks)."""

import logging
from typing import Any, Dict, List, Tuple

from srt_translator.core.config.language_config import LanguageConfig
from srt_translator.gui.settings_manager import SettingsManager


class GUIConfigManager:
    """Retrieves optional config purely from the GUI AI-generated config.
    No environment, no local files, no built-in defaults.
    """

    def __init__(self, settings_manager: SettingsManager, language_config: LanguageConfig):
        """Initialize the GUI config manager"""
        self.settings_manager = settings_manager
        self.language_config = language_config
        self.logger = logging.getLogger(__name__)

    def get_dnt_terms(self) -> List[str]:
        """Return DNT terms from AI config if present, else []."""
        result = self.settings_manager.load_ai_config()
        ai_dnt_terms = getattr(result, "dnt_terms", None) or []
        if ai_dnt_terms:
            self.logger.info("Using AI-generated DNT terms")
        else:
            self.logger.debug("No DNT terms provided")
        return ai_dnt_terms

    def get_termbase(self, target_language: str) -> Dict[str, str]:
        """Return the AI-config termbase for target_language (by name or code), else {}."""
        result = self.settings_manager.load_ai_config()
        ai_termbase: Dict[str, Dict[str, str]] = getattr(result, "termbase", {}) or {}
        if not ai_termbase:
            self.logger.debug("No termbases provided")
            return {}
        # direct key (language name or code)
        if target_language in ai_termbase and ai_termbase[target_language]:
            self.logger.info("Using AI-generated termbase for %s", target_language)
            return ai_termbase[target_language]
        # try mapping from name -> code
        try:
            for code, lang_info in self.language_config.get_all_languages().items():
                if lang_info.get("name") == target_language and code in ai_termbase:
                    self.logger.info(
                        "Using AI-generated termbase for %s (code: %s)", target_language, code
                    )
                    return ai_termbase[code]
        except Exception as e:
            self.logger.debug("Language mapping lookup failed: %s", e)
        self.logger.debug("No termbase found for %s", target_language)
        return {}

    def get_all_termbases(self) -> Dict[str, Dict[str, str]]:
        """Return all AI-config termbases, else {}."""
        result = self.settings_manager.load_ai_config()
        ai_termbase = getattr(result, "termbase", {}) or {}
        if ai_termbase:
            self.logger.info("Using AI-generated termbases")
        else:
            self.logger.debug("No termbases provided")
        return ai_termbase

    def get_config_source_info(self) -> Dict[str, str]:
        """Report whether AI-generated config is present."""
        info: Dict[str, str] = {}
        result = self.settings_manager.load_ai_config()
        if getattr(result, "dnt_terms", None):
            info["dnt_terms_source"] = "AI Generated"
        if getattr(result, "termbase", None):
            info["termbase_source"] = "AI Generated"
        return info

    def validate_ai_config(self) -> Tuple[bool, List[str]]:
        """Validate AI config recency and file-coherency only; DNT/termbase are optional."""
        issues: List[str] = []
        if not self.settings_manager.has_ai_config():
            # It's valid to proceed without AI config for DNT/termbase—report, but don't fail hard.
            return True, ["No AI configuration found"]
        if not self.settings_manager.has_recent_ai_config():
            age_days = self.settings_manager.get_ai_config_age_days()
            issues.append(f"AI configuration is {age_days} days old (older than 30 days)")
        if self.settings_manager.has_files_changed():
            issues.append("Selected files have changed since AI configuration was generated")
        return True, issues

    def get_config_summary(self) -> Dict[str, Any]:
        """Summarize current optional configuration without implying defaults."""
        dnt_terms = self.get_dnt_terms()
        termbases = self.get_all_termbases()
        source_info = self.get_config_source_info()
        _, issues = self.validate_ai_config()
        return {
            "dnt_terms_count": len(dnt_terms),
            "termbase_languages": list(termbases.keys()),
            "total_termbase_terms": sum(len(tb) for tb in termbases.values()),
            "source_info": source_info,
            "ai_config_issues": issues,
            "has_ai_config": self.settings_manager.has_ai_config(),
            "ai_config_age_days": self.settings_manager.get_ai_config_age_days(),
            "files_changed": self.settings_manager.has_files_changed(),
        }
