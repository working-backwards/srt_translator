#!/usr/bin/env python3
"""
Language configuration for the SRT Translator.
"""

import logging
from typing import Any


class LanguageConfig:
    """Immutable view over a preloaded languages mapping.
    Core code MUST receive this via DI; it never reads files itself."""

    def __init__(self, data: dict[str, Any]):
        # Injected languages.json content (nested or flat). No file I/O here.
        self._raw = data or {}
        self._defaults = self._raw.get("policy_defaults", {})
        self._langs = self._raw.get("languages", self._raw)
        self.logger = logging.getLogger(__name__)

    def codes(self) -> list[str]:
        "Return language codes available in the injected policy."
        return list(self._langs.keys())

    def get_all_languages(self) -> dict[str, Any]:
        """Get all available languages"""
        return self._langs

    def get_popular_languages(self) -> list[str]:
        """Get current popular languages"""
        return self._raw.get("default_popular_languages", [])

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
        return self._raw.get("version", "1.0")

    def get_popular_limit(self) -> int:
        """Get the default popular languages limit"""
        return self._raw.get("default_popular_limit", 12)

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

    def get_language_rules(self, code: str) -> dict[str, Any]:
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

    def get_target_batch_size(self, code: str) -> int:
        """Get the target batch size for a language."""
        languages = self.get_all_languages()
        lang_info = languages.get(code, {})
        # Check language-specific override first
        if "target_batch_size" in lang_info:
            return int(lang_info["target_batch_size"])
        # Check policy defaults
        if "target_batch_size" in self._defaults:
            return int(self._defaults["target_batch_size"])
        # Log the error before raising
        self.logger.error("Missing target_batch_size for language %s and no policy default", code)
        raise ValueError(f"Missing target_batch_size for language {code} and no policy default")

    def get_max_batch_size(self, code: str) -> int:
        """Get the maximum batch size for a language."""
        languages = self.get_all_languages()
        lang_info = languages.get(code, {})
        # Check language-specific override first
        if "max_batch_size" in lang_info:
            return int(lang_info["max_batch_size"])
        # Check policy defaults
        if "max_batch_size" in self._defaults:
            return int(self._defaults["max_batch_size"])
        # Log the error before raising
        self.logger.error("Missing max_batch_size for language %s and no policy default", code)
        raise ValueError(f"Missing max_batch_size for language {code} and no policy default")

    def allows_placeholder_apostrophe(self, code: str) -> bool:
        """Check if a language allows apostrophes after DNT placeholders."""
        languages = self.get_all_languages()
        lang_info = languages.get(code, {})
        # Check language-specific override first, then fall back to policy defaults
        return bool(
            lang_info.get(
                "allow_placeholder_apostrophe",
                self._defaults.get("allow_placeholder_apostrophe", False),
            )
        )

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

    def get_sentence_endings(self, code: str) -> list[str]:
        """Get sentence ending punctuation for a language"""
        languages = self.get_all_languages()
        lang_info = languages.get(code, {})
        return lang_info.get("sentence_endings", [".", "!", "?"])

    # ---------- Script helpers (unchanged design; now fed by JSON) ----------
    _UNICODE_BLOCKS = {
        "CJK": [("\u4e00", "\u9fff")],
        "Hiragana": [("\u3040", "\u309f")],
        "Katakana": [("\u30a0", "\u30ff")],
        "Hangul": [("\uac00", "\ud7a3")],
        "Arabic": [("\u0600", "\u06ff")],
        "Hebrew": [("\u0590", "\u05ff")],
        "Cyrillic": [("\u0400", "\u04ff")],
        "Greek": [("\u0370", "\u03ff")],
        "Devanagari": [("\u0900", "\u097f")],
        "Bengali": [("\u0980", "\u09ff")],
        "Gurmukhi": [("\u0a00", "\u0a7f")],
        "Gujarati": [("\u0a80", "\u0aff")],
        "Oriya": [("\u0b00", "\u0b7f")],
        "Tamil": [("\u0b80", "\u0bff")],
        "Telugu": [("\u0c00", "\u0c7f")],
        "Kannada": [("\u0c80", "\u0cff")],
        "Malayalam": [("\u0d00", "\u0d7f")],
        "Sinhala": [("\u0d80", "\u0dff")],
        "Thai": [("\u0e00", "\u0e7f")],
        "Lao": [("\u0e80", "\u0eff")],
        "Khmer": [("\u1780", "\u17ff")],
        "Georgian": [("\u10a0", "\u10ff")],
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
