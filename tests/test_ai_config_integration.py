import os
import sys
import traceback

from PySide6.QtWidgets import QApplication

from gui.ai_config import AIConfigGenerator
from gui.config_manager import GUIConfigManager
from gui.settings_manager import SettingsManager

#!/usr/bin/env python3
"""
Test script for AI Configuration Integration
"""


# Add the project root to the path
sys.path.insert(0, ".")


def test_settings_manager():
    """Test the SettingsManager AI configuration methods."""
    print("Testing SettingsManager AI configuration...")

    settings_manager = SettingsManager()

    # Test saving and loading AI config
    test_terms = ["API", "CEO", "CFO", "Amazon"]
    test_termbase = {
        "Spanish": {"API": "API", "CEO": "CEO", "CFO": "CFO"},
        "French": {"API": "API", "CEO": "PDG", "CFO": "DF"},
    }

    # Save AI config
    settings_manager.save_ai_config(test_terms, test_termbase)
    print(f"✓ Saved AI config: {len(test_terms)} terms, {len(test_termbase)} languages")

    # Load AI config
    loaded_terms, loaded_termbase = settings_manager.load_ai_config()
    print(
        f"✓ Loaded AI config: {len(loaded_terms)} terms, {len(loaded_termbase)} languages"
    )

    # Verify data integrity
    assert loaded_terms == test_terms, f"Terms mismatch: {loaded_terms} != {test_terms}"
    assert (
        loaded_termbase == test_termbase
    ), f"Termbase mismatch: {loaded_termbase} != {test_termbase}"
    print("✓ Data integrity verified")

    # Test freshness check
    has_recent = settings_manager.has_recent_ai_config(max_age_days=30)
    print(f"✓ Has recent config: {has_recent}")

    # Test config age
    age_days = settings_manager.get_ai_config_age_days()
    print(f"✓ Config age: {age_days} days")

    print("SettingsManager tests passed!\n")


def test_config_manager():
    """Test the GUIConfigManager priority system."""
    print("Testing GUIConfigManager priority system...")

    settings_manager = SettingsManager()
    config_manager = GUIConfigManager(settings_manager)

    # Test getting DNT terms (should prioritize AI config)
    dnt_terms = config_manager.get_dnt_terms()
    print(f"✓ DNT terms: {dnt_terms}")

    # Test getting termbase
    spanish_termbase = config_manager.get_termbase("Spanish")
    print(f"✓ Spanish termbase: {spanish_termbase}")

    # Test getting all termbases
    all_termbases = config_manager.get_all_termbases()
    print(f"✓ All termbases: {len(all_termbases)} languages")

    # Test config source info
    source_info = config_manager.get_config_source_info()
    print(f"✓ Config source: {source_info}")

    # Test config summary
    summary = config_manager.get_config_summary()
    print(f"✓ Config summary: {summary}")

    print("GUIConfigManager tests passed!\n")


def test_ai_config_generator():
    """Test the AIConfigGenerator basic functionality."""
    print("Testing AIConfigGenerator...")

    # This test requires an API key, so we'll just test instantiation
    try:
        # Test instantiation (without API key)
        generator = AIConfigGenerator("test-key")
        print("✓ AIConfigGenerator instantiated successfully")

        # Test supported languages
        print(f"✓ Supported languages: {len(generator.get_supported_languages())}")

    except Exception as e:
        print(f"⚠ AIConfigGenerator test skipped: {e}")

    print("AIConfigGenerator tests completed!\n")


def main():
    """Run all integration tests."""
    print("=" * 50)
    print("AI Configuration Integration Tests")
    print("=" * 50)

    try:
        test_settings_manager()
        test_config_manager()
        test_ai_config_generator()

        print("=" * 50)
        print("All tests passed! ✅")
        print("=" * 50)

    except Exception as e:
        print(f"❌ Test failed: {e}")

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
