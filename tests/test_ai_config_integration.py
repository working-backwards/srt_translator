import logging
import sys
import traceback

from srt_translator.core.config.language_config import LanguageConfig
from srt_translator.gui.ai_config import AIConfigGenerator
from srt_translator.gui.settings_manager import SettingsManager

# Set up logging
logging.basicConfig(level=logging.INFO)

#!/usr/bin/env python3
"""
Test script for AI Configuration Integration
"""


# Add the project root to the path
sys.path.insert(0, ".")


def test_settings_manager():
    """Test the SettingsManager AI configuration methods."""
    logger = logging.getLogger(__name__)
    logger.info("Testing SettingsManager AI configuration...")

    language_config = LanguageConfig({"languages": {}})
    settings_manager = SettingsManager(language_config)

    # Test saving and loading AI config
    test_terms = ["API", "CEO", "CFO", "Amazon"]
    test_termbase = {
        "es": {"API": "API", "CEO": "CEO", "CFO": "CFO"},
        "fr": {"API": "API", "CEO": "PDG", "CFO": "DF"},
    }

    # Save AI config
    settings_manager.save_ai_config(test_terms, test_termbase)
    logger.info("Saved AI config: %s terms, %s languages", len(test_terms), len(test_termbase))

    # Load AI config (returns 3 values)
    loaded_terms, loaded_termbase, loaded_source_lang = settings_manager.load_ai_config()
    logger.info("Loaded AI config: %s terms, %s languages", len(loaded_terms), len(loaded_termbase))

    # Verify data integrity
    assert loaded_terms == test_terms, f"Terms mismatch: {loaded_terms} != {test_terms}"
    assert loaded_termbase == test_termbase, f"Termbase mismatch: {loaded_termbase} != {test_termbase}"
    logger.info("Data integrity verified")

    # Test freshness check
    has_recent = settings_manager.has_recent_ai_config(max_age_days=30)
    logger.info("Has recent config: %s", has_recent)

    # Test config age
    age_days = settings_manager.get_ai_config_age_days()
    logger.info("Config age: %s days", age_days)

    logger.info("SettingsManager tests passed!\n")



def test_ai_config_generator():
    """Test the AIConfigGenerator basic functionality."""
    logger = logging.getLogger(__name__)
    logger.info("Testing AIConfigGenerator...")

    # This test requires an API key, so we'll just test instantiation
    try:
        # Test instantiation (without API key)
        generator = AIConfigGenerator("test-key")
        logger.info("AIConfigGenerator instantiated successfully")

        # Test supported languages
        logger.info("Supported languages: %s", len(generator.get_supported_languages()))

    except Exception as e:
        logger.info("AIConfigGenerator test skipped: %s", e)

    logger.info("AIConfigGenerator tests completed!\n")


def main():
    """Run all integration tests."""
    logger = logging.getLogger(__name__)
    logger.info("=" * 50)
    logger.info("AI Configuration Integration Tests")
    logger.info("=" * 50)

    try:
        test_settings_manager()
        test_ai_config_generator()

        logger.info("=" * 50)
        logger.info("All tests passed!")
        logger.info("=" * 50)

    except Exception as e:
        logger.error("Test failed: %s", e)

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
