#!/usr/bin/env python3
"""
Tests for the Tone feature.

Tests cover:
- TranslationConfig tone validation (from_raw)
- LanguageConfig.get_tone_hint() method
- Prompt insertion (covered in test_prompts_snapshot.py)
"""

import pytest

from srt_translator.core.config.language_config import LanguageConfig
from srt_translator.core.config.models import TranslationConfig

# =============================================================================
# TranslationConfig tone validation tests
# =============================================================================


class TestTranslationConfigTone:
    """Tests for TranslationConfig tone field validation."""

    @pytest.fixture
    def base_raw_config(self):
        """Base raw config with required fields."""
        return {
            "api_key": "sk-test",
            "target_languages": {"Spanish": "es"},
            "output_directory": "output",
            "aggressiveness": 0.75,
            "log_mode": "Standard",
        }

    def test_tone_defaults_to_neutral(self, base_raw_config):
        """Test that tone defaults to 'neutral' when not provided."""
        config = TranslationConfig.from_raw(base_raw_config)
        assert config.tone == "neutral"

    def test_tone_accepts_casual(self, base_raw_config):
        """Test that tone accepts 'casual' value."""
        base_raw_config["tone"] = "casual"
        config = TranslationConfig.from_raw(base_raw_config)
        assert config.tone == "casual"

    def test_tone_accepts_neutral(self, base_raw_config):
        """Test that tone accepts 'neutral' value."""
        base_raw_config["tone"] = "neutral"
        config = TranslationConfig.from_raw(base_raw_config)
        assert config.tone == "neutral"

    def test_tone_accepts_formal(self, base_raw_config):
        """Test that tone accepts 'formal' value."""
        base_raw_config["tone"] = "formal"
        config = TranslationConfig.from_raw(base_raw_config)
        assert config.tone == "formal"

    def test_tone_normalizes_to_lowercase(self, base_raw_config):
        """Test that tone is normalized to lowercase."""
        base_raw_config["tone"] = "FORMAL"
        config = TranslationConfig.from_raw(base_raw_config)
        assert config.tone == "formal"

        base_raw_config["tone"] = "Casual"
        config = TranslationConfig.from_raw(base_raw_config)
        assert config.tone == "casual"

        base_raw_config["tone"] = "NEUTRAL"
        config = TranslationConfig.from_raw(base_raw_config)
        assert config.tone == "neutral"

    def test_tone_handles_whitespace(self, base_raw_config):
        """Test that tone handles leading/trailing whitespace."""
        base_raw_config["tone"] = "  formal  "
        config = TranslationConfig.from_raw(base_raw_config)
        assert config.tone == "formal"

    def test_tone_invalid_value_raises_error(self, base_raw_config):
        """Test that invalid tone value raises validation error."""
        base_raw_config["tone"] = "informal"  # Not a valid option
        with pytest.raises(ValueError) as exc_info:
            TranslationConfig.from_raw(base_raw_config)
        assert "Invalid tone" in str(exc_info.value)
        assert "informal" in str(exc_info.value)

    def test_tone_none_defaults_to_neutral(self, base_raw_config):
        """Test that None tone defaults to 'neutral'."""
        base_raw_config["tone"] = None
        config = TranslationConfig.from_raw(base_raw_config)
        assert config.tone == "neutral"


# =============================================================================
# LanguageConfig.get_tone_hint() tests
# =============================================================================


class TestLanguageConfigToneHint:
    """Tests for LanguageConfig.get_tone_hint() method."""

    @pytest.fixture
    def language_config_with_hints(self):
        """Create a LanguageConfig with tone_hint entries."""
        data = {
            "languages": {
                "fr": {
                    "name": "French",
                    "tone_hint": {
                        "casual": "Use informal phrasing (tu).",
                        "neutral": "Use professional wording; prefer 'vous'.",
                        "formal": "Use formal/deferential phrasing.",
                    },
                },
                "zh-Hans": {
                    "name": "Chinese (Simplified)",
                    "tone_hint": {
                        "casual": "Use '你' for addressing the viewer.",
                        "neutral": "Prefer '你' for business training.",
                        "formal": "Prefer '您' for formal contexts.",
                    },
                },
                "de": {
                    "name": "German",
                    # No tone_hint - testing missing field
                },
                "ja": {
                    "name": "Japanese",
                    "tone_hint": {
                        # Only has casual and formal, missing neutral
                        "casual": "Use plain verb forms.",
                        "formal": "Use keigo.",
                    },
                },
            }
        }
        return LanguageConfig(data)

    @pytest.fixture
    def empty_language_config(self):
        """Create an empty LanguageConfig."""
        return LanguageConfig({"languages": {}})

    def test_get_tone_hint_returns_correct_hint(self, language_config_with_hints):
        """Test that get_tone_hint returns correct hint for lang and tone."""
        hint = language_config_with_hints.get_tone_hint("fr", "neutral")
        assert hint == "Use professional wording; prefer 'vous'."

        hint = language_config_with_hints.get_tone_hint("zh-Hans", "formal")
        assert hint == "Prefer '您' for formal contexts."

    def test_get_tone_hint_case_insensitive_lang(self, language_config_with_hints):
        """Test that lang_code lookup is case-insensitive."""
        hint = language_config_with_hints.get_tone_hint("FR", "neutral")
        assert hint == "Use professional wording; prefer 'vous'."

        hint = language_config_with_hints.get_tone_hint("ZH-HANS", "casual")
        assert hint == "Use '你' for addressing the viewer."

    def test_get_tone_hint_case_insensitive_tone(self, language_config_with_hints):
        """Test that tone lookup is case-insensitive."""
        hint = language_config_with_hints.get_tone_hint("fr", "NEUTRAL")
        assert hint == "Use professional wording; prefer 'vous'."

        hint = language_config_with_hints.get_tone_hint("fr", "Formal")
        assert hint == "Use formal/deferential phrasing."

    def test_get_tone_hint_unknown_lang_returns_none(self, language_config_with_hints):
        """Test that unknown lang_code returns None."""
        hint = language_config_with_hints.get_tone_hint("xx", "neutral")
        assert hint is None

    def test_get_tone_hint_no_tone_hint_field_returns_none(self, language_config_with_hints):
        """Test that lang without tone_hint field returns None."""
        hint = language_config_with_hints.get_tone_hint("de", "neutral")
        assert hint is None

    def test_get_tone_hint_missing_tone_key_returns_none(self, language_config_with_hints):
        """Test that missing tone key in tone_hint returns None."""
        # Japanese has casual and formal but not neutral
        hint = language_config_with_hints.get_tone_hint("ja", "neutral")
        assert hint is None

        # But casual and formal should work
        hint = language_config_with_hints.get_tone_hint("ja", "casual")
        assert hint == "Use plain verb forms."

    def test_get_tone_hint_empty_lang_returns_none(self, language_config_with_hints):
        """Test that empty lang_code returns None."""
        hint = language_config_with_hints.get_tone_hint("", "neutral")
        assert hint is None

    def test_get_tone_hint_empty_tone_returns_none(self, language_config_with_hints):
        """Test that empty tone returns None."""
        hint = language_config_with_hints.get_tone_hint("fr", "")
        assert hint is None

    def test_get_tone_hint_none_inputs_returns_none(self, language_config_with_hints):
        """Test that None inputs return None."""
        hint = language_config_with_hints.get_tone_hint(None, "neutral")
        assert hint is None

        hint = language_config_with_hints.get_tone_hint("fr", None)
        assert hint is None

    def test_get_tone_hint_empty_config_returns_none(self, empty_language_config):
        """Test that empty config returns None for any query."""
        hint = empty_language_config.get_tone_hint("fr", "neutral")
        assert hint is None
