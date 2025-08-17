"""
Language configuration management for CPS caps, families, and sentence endings.
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple, Any


class LanguageConfig:
    """Manages language-specific configuration including CPS caps and sentence endings."""
    
    def __init__(self, languages_path: str | Path = "languages.json"):
        self.languages_path = Path(languages_path)
        self._languages_meta = self._load_languages_meta()
    
    def _load_languages_meta(self) -> Dict[str, Any]:
        """Load languages metadata from JSON file."""
        try:
            if self.languages_path.exists():
                return json.loads(self.languages_path.read_text(encoding="utf-8"))
        except Exception as e:
            # Log warning but don't fail - use defaults
            print(f"[WARN] languages.json load failed: {e}")
        return {"languages": {}}
    
    def _family_of(self, lang_code: str) -> str:
        """Determine language family based on language code."""
        lang = (lang_code or "").lower()
        
        # CJK languages
        if lang in {"zh-hans", "zh-hant", "ja", "ko"}:
            return "cjk"
        
        # RTL languages
        if lang in {"ar", "he", "fa", "ur"}:
            return "rtl"
        
        # No-space languages
        if lang in {"th", "km", "lo"}:
            return "no_space"
        
        # Indic languages
        if lang in {"hi", "bn", "ta", "te", "ml", "mr", "gu", "pa", "kn", "or", "as", "si"}:
            return "indic"
        
        # Cyrillic languages
        if lang in {"ru", "uk", "bg", "be", "kk", "ky", "mk", "mn", "sr", "tt"}:
            return "cyrillic"
        
        # Greek
        if lang in {"el"}:
            return "greek"
        
        # Armenian
        if lang in {"hy"}:
            return "armenian"
        
        # Georgian
        if lang in {"ka"}:
            return "georgian"
        
        # Default to Latin
        return "latin"
    
    def get_cps_caps(self, lang_code: str) -> Tuple[int, int]:
        """Get soft and hard CPS caps for a language."""
        DEFAULT = (15, 20)
        FAMILY_DEFAULTS = {
            "cjk": (12, 15),
            "rtl": (14, 18),
            "no_space": (12, 16),
            "indic": (14, 18),
            "latin": (15, 20),
            "cyrillic": (15, 20),
            "greek": (15, 20),
            "armenian": (15, 20),
            "georgian": (15, 20)
        }
        
        meta = self._languages_meta.get("languages", {})
        lang_data = meta.get(lang_code) or meta.get((lang_code or "").split("-")[0]) or {}
        
        # Check for explicit caps
        soft = lang_data.get("cps_soft")
        hard = lang_data.get("cps_hard")
        if isinstance(soft, (int, float)) and isinstance(hard, (int, float)):
            return int(soft), int(hard)
        
        # Fall back to family defaults
        family = lang_data.get("family") or self._family_of(lang_code)
        return FAMILY_DEFAULTS.get(family, DEFAULT)
    
    def get_sentence_endings(self, lang_code: str) -> List[str]:
        """Get sentence ending characters for a language."""
        meta = self._languages_meta.get("languages", {})
        lang_data = meta.get(lang_code) or meta.get((lang_code or "").split("-")[0]) or {}
        
        # Check for explicit sentence endings
        endings = lang_data.get("sentence_endings")
        if isinstance(endings, list) and endings:
            return endings
        
        # Conservative default
        return ["。", "！", "？", "…", ".", "!", "?", "؟", "।"]
    
    def get_max_utterance_s(self, lang_code: str) -> float:
        """Get maximum utterance duration in seconds for a language."""
        meta = self._languages_meta.get("languages", {})
        lang_data = meta.get(lang_code) or meta.get((lang_code or "").split("-")[0]) or {}
        
        # Check for explicit max duration
        max_duration = lang_data.get("max_utterance_s")
        if isinstance(max_duration, (int, float)) and max_duration > 0:
            return float(max_duration)
        
        # Fall back to family defaults
        family = lang_data.get("family") or self._family_of(lang_code)
        family_defaults = {
            "cjk": 12.0,
            "no_space": 12.0,
            "indic": 14.0
        }
        return family_defaults.get(family, 15.0)
