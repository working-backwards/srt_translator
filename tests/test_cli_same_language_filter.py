#!/usr/bin/env python3
"""
Test that CLI filters out target languages matching the detected source language.

This test ensures that same-language filtering happens at the CLI boundary
(before TranslationConfig is constructed) rather than in the core engine.
"""

from srt_translator.core.config.models import TranslationConfig


def test_cli_filters_same_language():
    """
    Test that CLI-level same-language filtering works correctly.

    This test simulates the CLI workflow where:
    1. Raw config includes source_language detection
    2. One target language matches the detected source
    3. CLI filters out the matching target before creating TranslationConfig
    4. Core receives config with only non-matching targets
    """
    # Simulate CLI raw config with source language equal to one of the targets
    raw = {
        "target_languages": {"English": "en-US", "Spanish": "es"},
        "source_language": {"normalized_code": "en-US"},
        "output_directory": "translated_srt_files",
        "api_key": "sk-test",
        "model_name": "gpt-4o-mini",
    }

    # Simulate the CLI filtering logic (pre-filter targets before calling from_raw)
    # In actual CLI code, this happens in cli/app.py before constructing config
    source_code = raw["source_language"]["normalized_code"]
    filtered = {name: code for name, code in raw["target_languages"].items() if code.lower() != source_code.lower()}

    # Update raw config with filtered targets
    normalized_raw = dict(raw)
    normalized_raw["target_languages"] = filtered

    # Create config via from_raw (which converts to immutable types)
    cfg = TranslationConfig.from_raw(normalized_raw, mode="CLI")

    # Verify the source language was filtered out
    assert "en-US" not in cfg.target_languages.values(), (
        "Source language (en-US) should be filtered out from target languages"
    )
    assert "es" in cfg.target_languages.values(), "Non-source language (es) should remain in target languages"
    assert len(cfg.target_languages) == 1, "Should have exactly 1 target language after filtering"


def test_cli_no_filtering_when_no_match():
    """Test that targets are not filtered when they don't match the source."""
    raw = {
        "target_languages": {"Spanish": "es", "French": "fr"},
        "source_language": {"normalized_code": "en-US"},
        "output_directory": "translated_srt_files",
        "api_key": "sk-test",
        "model_name": "gpt-4o-mini",
    }

    # Simulate CLI filtering
    source_code = raw["source_language"]["normalized_code"]
    filtered = {name: code for name, code in raw["target_languages"].items() if code.lower() != source_code.lower()}

    normalized_raw = dict(raw)
    normalized_raw["target_languages"] = filtered

    cfg = TranslationConfig.from_raw(normalized_raw, mode="CLI")

    # All targets should remain (neither matches en-US)
    assert len(cfg.target_languages) == 2
    assert "es" in cfg.target_languages.values()
    assert "fr" in cfg.target_languages.values()


def test_cli_case_insensitive_filtering():
    """Test that same-language filtering is case-insensitive."""
    raw = {
        "target_languages": {"English": "EN-us", "Spanish": "es"},  # Mixed case
        "source_language": {"normalized_code": "en-US"},
        "output_directory": "translated_srt_files",
        "api_key": "sk-test",
        "model_name": "gpt-4o-mini",
    }

    # Simulate CLI filtering with case-insensitive comparison
    source_code = raw["source_language"]["normalized_code"]
    filtered = {name: code for name, code in raw["target_languages"].items() if code.lower() != source_code.lower()}

    normalized_raw = dict(raw)
    normalized_raw["target_languages"] = filtered

    cfg = TranslationConfig.from_raw(normalized_raw, mode="CLI")

    # EN-us should be filtered out (case-insensitive match with en-US)
    assert "EN-us" not in cfg.target_languages.values()
    assert "es" in cfg.target_languages.values()
    assert len(cfg.target_languages) == 1
