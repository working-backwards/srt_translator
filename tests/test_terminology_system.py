#!/usr/bin/env python3
"""
Tests for the new terminology system.
"""

import pytest

from srt_translator.core.config.language_config import LanguageConfig
from srt_translator.core.terminology_utils import (
    build_effective_dnt,
    is_hard_preserve,
    is_numeric_like,
    partition_hard_preserve,
)


class TestTerminologyUtils:
    """Test terminology utility functions."""

    def test_is_numeric_like(self):
        """Test numeric-like term detection."""
        # Should be filtered out
        assert is_numeric_like("300")
        assert is_numeric_like("6.7")
        assert is_numeric_like("300ms")
        assert is_numeric_like("$99.99")
        assert is_numeric_like("2024")

        # Should not be filtered
        assert not is_numeric_like("API")
        assert not is_numeric_like("machine learning")
        assert not is_numeric_like("Adobe Premiere")

    def test_is_hard_preserve(self):
        """Test hard-preserve term detection."""
        # Should be hard-preserved
        assert is_hard_preserve("API")
        assert is_hard_preserve("GPU")
        assert is_hard_preserve("NASA")
        assert is_hard_preserve("MachineLearning")
        assert is_hard_preserve("Adobe Premiere")

        # Should not be hard-preserved
        assert not is_hard_preserve("machine learning")
        assert not is_hard_preserve("artificial intelligence")
        assert not is_hard_preserve("deep learning")

    def test_partition_hard_preserve(self):
        """Test partitioning of terms into hard/soft preserve."""
        terms = ["API", "machine learning", "GPU", "artificial intelligence"]
        hard, soft = partition_hard_preserve(terms)
        
        assert set(hard) == {"API", "GPU"}
        assert set(soft) == {"machine learning", "artificial intelligence"}

    def test_build_effective_dnt(self):
        """Test effective DNT building with precedence."""
        dnt_terms = ["API", "machine learning", "GPU", "artificial intelligence"]
        termbase = {"machine learning": "机器学习"}
        
        effective = build_effective_dnt(dnt_terms, termbase)
        
        # Hard-preserve terms should always be included
        assert "API" in effective
        assert "GPU" in effective
        
        # Soft-preserve terms should be excluded if in termbase
        assert "machine learning" not in effective  # Overridden by termbase
        assert "artificial intelligence" in effective  # Not in termbase


class TestLanguageConfigScriptValidation:
    """Test language configuration script validation."""

    def test_get_script_spec(self):
        """Test script specification retrieval."""
        test_data = {
            "version": "1.1",
            "languages": {
                "zh-Hans": {"name": "Chinese (Simplified)", "family": "cjk", "script": "cjk", "script_blocks": ["CJK"]},
                "ja": {"name": "Japanese", "family": "cjk", "script": "japanese", "script_blocks": ["Hiragana", "Katakana", "CJK"]},
                "en": {"name": "English", "family": "latin"}
            }
        }
        config = LanguageConfig(test_data)
        
        # Test Chinese with explicit script_blocks
        zh_spec = config.get_script_spec("zh-Hans")
        assert "script" in zh_spec
        assert "script_blocks" in zh_spec
        assert zh_spec["script"] == "cjk"
        assert "CJK" in zh_spec["script_blocks"]
        
        # Test Japanese with multiple script_blocks
        ja_spec = config.get_script_spec("ja")
        assert "script" in ja_spec
        assert "script_blocks" in ja_spec
        assert ja_spec["script"] == "japanese"
        assert "Hiragana" in ja_spec["script_blocks"]
        assert "Katakana" in ja_spec["script_blocks"]
        assert "CJK" in ja_spec["script_blocks"]
        
        # Test Latin language (no script restrictions)
        en_spec = config.get_script_spec("en")
        assert en_spec == {}  # Latin has no script restrictions

    def test_text_matches_script(self):
        """Test script validation."""
        test_data = {
            "version": "1.1",
            "languages": {
                "zh-Hans": {"name": "Chinese (Simplified)", "family": "cjk", "script": "cjk", "script_blocks": ["CJK"]},
                "ja": {"name": "Japanese", "family": "cjk", "script": "japanese", "script_blocks": ["Hiragana", "Katakana", "CJK"]},
                "en": {"name": "English", "family": "latin"}
            }
        }
        config = LanguageConfig(test_data)
        
        # Test Chinese script validation
        zh_spec = config.get_script_spec("zh-Hans")
        assert config.text_matches_script("机器学习", zh_spec)
        assert not config.text_matches_script("machine learning", zh_spec)

        # Test Japanese script validation
        ja_spec = config.get_script_spec("ja")
        assert config.text_matches_script("機械学習", ja_spec)  # CJK
        assert config.text_matches_script("きかいがくしゅう", ja_spec)  # Hiragana 
        assert config.text_matches_script("マシンラーニング", ja_spec)  # Katakana 
        assert not config.text_matches_script("machine learning", ja_spec)

        # Test Latin language (no restrictions)
        en_spec = config.get_script_spec("en")
        assert config.text_matches_script("machine learning", en_spec)
        assert config.text_matches_script("123", en_spec)
        assert config.text_matches_script("", en_spec)


if __name__ == "__main__":
    pytest.main([__file__])
