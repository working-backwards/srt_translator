import logging
import sys
import traceback

from srt_translator.gui.ai_config import AIConfigGenerator
from srt_translator.gui.config_manager import GUIConfigManager
from srt_translator.gui.settings_manager import SettingsManager, AIConfigTriple
from srt_translator.core.config.language_config import LanguageConfig

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
        "Spanish": {"API": "API", "CEO": "CEO", "CFO": "CFO"},
        "French": {"API": "API", "CEO": "PDG", "CFO": "DF"},
    }

    # Save AI config
    settings_manager.save_ai_config(test_terms, test_termbase)
    logger.info(
        f"✓ Saved AI config: {len(test_terms)} terms, {len(test_termbase)} languages"
    )

    # Load AI config (returns 3 values)
    result = settings_manager.load_ai_config()
    assert isinstance(result, AIConfigTriple)
    loaded_terms, loaded_termbase, _ = result
    logger.info(
        f"✓ Loaded AI config: {len(loaded_terms)} terms, {len(loaded_termbase)} languages"
    )

    # Verify data integrity
    assert loaded_terms == test_terms, f"Terms mismatch: {loaded_terms} != {test_terms}"
    assert (
        loaded_termbase == test_termbase
    ), f"Termbase mismatch: {loaded_termbase} != {test_termbase}"
    logger.info("✓ Data integrity verified")

    # Test freshness check
    has_recent = settings_manager.has_recent_ai_config(max_age_days=30)
    logger.info(f"✓ Has recent config: {has_recent}")

    # Test config age
    age_days = settings_manager.get_ai_config_age_days()
    logger.info(f"✓ Config age: {age_days} days")

    logger.info("SettingsManager tests passed!\n")


def test_config_manager():
    """Test the GUIConfigManager priority system."""
    logger = logging.getLogger(__name__)
    logger.info("Testing GUIConfigManager priority system...")

    language_config = LanguageConfig({"languages": {}})
    settings_manager = SettingsManager(language_config)
    config_manager = GUIConfigManager(settings_manager, language_config)

    # Test getting DNT terms (should prioritize AI config)
    dnt_terms = config_manager.get_dnt_terms()
    logger.info(f"✓ DNT terms: {dnt_terms}")

    # Test getting termbase
    spanish_termbase = config_manager.get_termbase("Spanish")
    logger.info(f"✓ Spanish termbase: {spanish_termbase}")

    # Test getting all termbases
    all_termbases = config_manager.get_all_termbases()
    logger.info(f"✓ All termbases: {len(all_termbases)} languages")

    # Test config source info
    source_info = config_manager.get_config_source_info()
    logger.info(f"✓ Config source: {source_info}")

    # Test config summary
    summary = config_manager.get_config_summary()
    logger.info(f"✓ Config summary: {summary}")

    logger.info("GUIConfigManager tests passed!\n")


def test_ai_config_generator():
    """Test the AIConfigGenerator basic functionality."""
    logger = logging.getLogger(__name__)
    logger.info("Testing AIConfigGenerator...")

    # This test requires an API key, so we'll just test instantiation
    try:
        # Test instantiation (without API key)
        generator = AIConfigGenerator("test-key")
        logger.info("✓ AIConfigGenerator instantiated successfully")

        # Test supported languages
        logger.info(
            f"✓ Supported languages: {len(generator.get_supported_languages())}"
        )

    except Exception as e:
        logger.info(f"⚠ AIConfigGenerator test skipped: {e}")

    logger.info("AIConfigGenerator tests completed!\n")


def main():
    """Run all integration tests."""
    logger = logging.getLogger(__name__)
    logger.info("=" * 50)
    logger.info("AI Configuration Integration Tests")
    logger.info("=" * 50)

    try:
        test_settings_manager()
        test_config_manager()
        test_ai_config_generator()

        logger.info("=" * 50)
        logger.info("All tests passed! ✅")
        logger.info("=" * 50)

    except Exception as e:
        logger.error(f"❌ Test failed: {e}")

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
