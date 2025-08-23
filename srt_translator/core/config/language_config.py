#!/usr/bin/env python3
"""
Language configuration for the SRT Translator.
"""

import logging
import unicodedata
from typing import Any, Dict, List


class LanguageConfig:
    """Immutable view over a preloaded languages mapping.
    Core code MUST receive this via DI; it never reads files itself."""

    def __init__(self, data: Dict[str, Any]):
        if not isinstance(data, dict) or "languages" not in data:
            raise ValueError(
                "LanguageConfig requires a preloaded mapping with a 'languages' key."
            )
        if not data["languages"]:
            raise ValueError("LanguageConfig requires non-empty languages mapping.")
        self._config: Dict[str, Any] = data
        self.logger = logging.getLogger(__name__)

    def get_all_languages(self) -> Dict[str, Any]:
        """Get all available languages"""
        return self._config.get("languages", {})

    def get_popular_languages(self) -> list[str]:
        """Get current popular languages"""
        return self._config.get("default_popular_languages", [])

    def get_language_name(self, code: str) -> str:
        """Get display name for language code"""
        languages = self.get_all_languages()
        lang_info = languages.get(code, {})
        name = lang_info.get("name")
        return name if name is not None else code

    def is_popular(self, code: str) -> bool:
        """Check if language is marked as popular"""
        languages = self.get_all_languages()
        lang_info = languages.get(code, {})
        popular = lang_info.get("popular")
        return bool(popular) if popular is not None else False

    def get_language_codes(self) -> list[str]:
        """Get list of all language codes"""
        return list(self.get_all_languages().keys())

    def get_language_names(self) -> dict[str, str]:
        """Get mapping of language codes to display names"""
        languages = self.get_all_languages()
        result = {}
        for code, lang in languages.items():
            name = lang.get("name")
            result[code] = name if name is not None else code
        return result

    def validate_language_code(self, code: str) -> bool:
        """Check if a language code is valid"""
        return code in self.get_all_languages()

    def get_config_version(self) -> str:
        """Get the configuration version"""
        return self._config.get("version", "1.0")

    def get_popular_limit(self) -> int:
        """Get the default popular languages limit"""
        return self._config.get("default_popular_limit", 12)

    def get_target_languages_dict(self) -> dict[str, str]:
        """Get target languages in the format expected by CLI (name: code)"""
        languages = self.get_all_languages()
        result = {}
        for code, lang in languages.items():
            name = lang.get("name")
            if name is not None:
                result[name] = code
            else:
                result[code] = code
        return result

    def get_language_rules(self, code: str) -> Dict[str, Any]:
        """Get language-specific rules for sentence endings and break markers"""
        languages = self.get_all_languages()
        lang_info = languages.get(code, {})
        return {
            "sentence_endings": lang_info.get("sentence_endings", []),
            "break_markers": lang_info.get("break_markers", []),
        }

    def get_cps_cap(self, code: str) -> int:
        """Return the single CPS cap for a language (required)."""
        meta = self.get_all_languages().get(code, {}) or {}
        cap = meta.get("cps_cap")
        if cap is None:
            # Default fallback for robustness
            return 20
        return int(cap)

    @classmethod
    def normalize_language_code(cls, code: str) -> str:
        """Normalize language code to standard form."""
        if not code:
            return code

        # Normalize case
        normalized = code.strip().lower()

        # Handle common language code variations
        if normalized == "zh":
            return "zh-Hans"  # Default to Simplified Chinese
        elif normalized == "pt":
            return "pt-BR"  # Default to Brazilian Portuguese
        elif normalized == "en":
            return "en-US"  # Default to US English
        elif normalized in ["zh-hans", "zh-cn"]:
            return "zh-Hans"
        elif normalized in ["zh-hant", "zh-tw", "zh-hk"]:
            return "zh-Hant"
        elif normalized in ["pt-br", "pt-brazil"]:
            return "pt-BR"
        elif normalized in ["pt-pt", "pt-portugal"]:
            return "pt-PT"
        elif normalized in ["en-us", "en-america"]:
            return "en-US"
        elif normalized in ["en-gb", "en-uk", "en-britain"]:
            return "en-GB"

        # Return as-is for other codes
        return code

    def get_family_defaults(self, family: str) -> dict:
        """Get family-level defaults for language configuration"""
        return (self._config.get("family_defaults") or {}).get(family, {})

    # Orphan/protected lists are removed (no reflow/wrapping policy).

    def family(self, code: str) -> str:
        """Get the language family for a given language code"""
        languages = self.get_all_languages()
        lang_info = languages.get(code, {})
        return lang_info.get("family", "")

    def get_sentence_endings(self, code: str) -> List[str]:
        """Get sentence ending punctuation for a language"""
        languages = self.get_all_languages()
        lang_info = languages.get(code, {})
        return lang_info.get("sentence_endings", [".", "!", "?"])

    # ---------- Script helpers (unchanged design; now fed by JSON) ----------
    _UNICODE_BLOCKS = {
        "CJK": [("\u4E00", "\u9FFF")],
        "Hiragana": [("\u3040", "\u309F")],
        "Katakana": [("\u30A0", "\u30FF")],
        "Hangul": [("\uAC00", "\uD7A3")],
        "Arabic": [("\u0600", "\u06FF")],
        "Hebrew": [("\u0590", "\u05FF")],
        "Cyrillic": [("\u0400", "\u04FF")],
        "Greek": [("\u0370", "\u03FF")],
        "Devanagari": [("\u0900", "\u097F")],
        "Bengali": [("\u0980", "\u09FF")],
        "Gurmukhi": [("\u0A00", "\u0A7F")],
        "Gujarati": [("\u0A80", "\u0AFF")],
        "Oriya": [("\u0B00", "\u0B7F")],
        "Tamil": [("\u0B80", "\u0BFF")],
        "Telugu": [("\u0C00", "\u0C7F")],
        "Kannada": [("\u0C80", "\u0CFF")],
        "Malayalam": [("\u0D00", "\u0D7F")],
        "Sinhala": [("\u0D80", "\u0DFF")],
        "Thai": [("\u0E00", "\u0E7F")],
        "Lao": [("\u0E80", "\u0EFF")],
        "Khmer": [("\u1780", "\u17FF")],
        "Georgian": [("\u10A0", "\u10FF")],
    }

    def get_script_spec(self, code: str) -> dict:
        """Get script specification for a language"""
        languages = self.get_all_languages()
        meta = languages.get(code, {})
        spec = {}

        if "script_blocks" in meta:
            spec["script_blocks"] = meta["script_blocks"]
        if "script" in meta:
            spec["script"] = meta["script"]

        if not spec:
            # Fall back to family-based defaults
            fam = (meta.get("family") or "").lower()
            blocks = self._FAMILY_TO_DEFAULT_BLOCK.get(fam, [])
            if blocks:
                spec["script_blocks"] = blocks

        return spec

    def text_matches_script(self, text: str, spec: dict) -> bool:
        """Check if text contains characters that match the required script"""
        if not spec:
            return True

        blocks = spec.get("script_blocks")
        if not blocks:
            # Map script names to blocks
            mapping = {
                "cjk": ["CJK"],
                "japanese": ["Hiragana", "Katakana", "CJK"],
                "hangul": ["Hangul"],
                "arabic": ["Arabic"],
                "hebrew": ["Hebrew"],
                "cyrillic": ["Cyrillic"],
                "greek": ["Greek"],
                "devanagari": ["Devanagari"],
                "bengali": ["Bengali"],
                "gurmukhi": ["Gurmukhi"],
                "gujarati": ["Gujarati"],
                "odia": ["Oriya"],
                "tamil": ["Tamil"],
                "telugu": ["Telugu"],
                "kannada": ["Kannada"],
                "malayalam": ["Malayalam"],
                "sinhala": ["Sinhala"],
                "thai": ["Thai"],
                "lao": ["Lao"],
                "khmer": ["Khmer"],
                "georgian": ["Georgian"],
                "latin": [],
            }
            blocks = mapping.get((spec.get("script") or "").lower(), [])

        if not blocks:
            return True  # Latin or unknown: don't enforce

        # Check if text contains at least one character in any required block
        for ch in text or "":
            for b in blocks:
                for lo, hi in self._UNICODE_BLOCKS.get(b, []):
                    if lo <= ch <= hi:
                        return True

        return False

    _FAMILY_TO_DEFAULT_BLOCK = {
        "cjk": ["CJK"],
        "rtl": ["Arabic"],
        "cyrillic": ["Cyrillic"],
        "greek": ["Greek"],
        "armenian": [],
        "georgian": ["Georgian"],
        "indic": [],
        "latin": [],
        "no_space": [],
    }

    def get_family_defaults(self, family: str) -> dict:
        cfg = self._config
        return (cfg.get("family_defaults") or {}).get(family, {})

    def family(self, code: str) -> str:
        return (self.get_all_languages().get(code, {}) or {}).get("family", "")

    def no_orphan_end(self, code: str) -> list[str]:
        lang = self.get_all_languages().get(code, {})
        fam = self.get_family_defaults(lang.get("family", ""))
        return lang.get("no_orphan_end") or fam.get("no_orphan_end") or []

    def no_orphan_chars_end(self, code: str) -> list[str]:
        lang = self.get_all_languages().get(code, {})
        fam = self.get_family_defaults(lang.get("family", ""))
        return lang.get("no_orphan_chars_end") or fam.get("no_orphan_chars_end") or []

    def protected_bigrams(self, code: str) -> list[str]:
        lang = self.get_all_languages().get(code, {})
        fam = self.get_family_defaults(lang.get("family", ""))
        return lang.get("protected_bigrams") or fam.get("protected_bigrams") or []

    # Reflow policy removed.
