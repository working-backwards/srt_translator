import logging
import os
import sys

from srt_translator.core.config.language_config import LanguageConfig
from srt_translator.gui.ai_config import AIConfigGenerator
from srt_translator.gui.config_manager import GUIConfigManager
from srt_translator.gui.settings_manager import AIConfigTriple, SettingsManager

#!/usr/bin/env python3
"""
Test script for AI Configuration System
"""


# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(level=logging.INFO)


def test_ai_config_system():
    """Test the AI configuration system"""
    logger = logging.getLogger(__name__)
    logger.info("Testing AI Configuration System...")

    # Test 1: Settings Manager
    logger.info("1. Testing Settings Manager...")
    language_config = LanguageConfig({"languages": {}})
    settings_manager = SettingsManager(language_config)

    # Test saving and loading AI config
    test_dnt_terms = ["API", "CEO", "CFO", "Amazon"]
    test_termbase = {
        "Spanish": {
            "operating plan": "plan operativo",
            "business review": "revisión de negocio",
        },
        "French": {
            "operating plan": "plan opérationnel",
            "business review": "revue d'affaires",
        },
    }

    settings_manager.save_ai_config(test_dnt_terms, test_termbase)
    result = settings_manager.load_ai_config()
    assert isinstance(result, AIConfigTriple)
    loaded_terms, loaded_termbase, loaded_source_lang = result

    logger.info(f"Saved DNT terms: {test_dnt_terms}")
    logger.info(f"Loaded DNT terms: {loaded_terms}")
    logger.info(f"Terms match: {test_dnt_terms == loaded_terms}")

    logger.info(f"Saved termbase languages: {list(test_termbase.keys())}")
    logger.info(f"Loaded termbase languages: {list(loaded_termbase.keys())}")
    logger.info(f"Termbase match: {test_termbase == loaded_termbase}")

    # Test 2: Config Manager
    logger.info("2. Testing Config Manager...")
    config_manager = GUIConfigManager(settings_manager, language_config)

    # Test getting DNT terms (should return AI-generated ones)
    dnt_terms = config_manager.get_dnt_terms()
    logger.info(f"Config manager DNT terms: {dnt_terms}")

    # Test getting termbase
    spanish_termbase = config_manager.get_termbase("Spanish")
    logger.info(f"Spanish termbase: {spanish_termbase}")

    # Test config summary
    summary = config_manager.get_config_summary()
    logger.info(f"Config summary: {summary}")

    # Test 3: AI Config Generator (without API key)
    logger.info("3. Testing AI Config Generator structure...")
    try:
        # This should fail without a valid API key, but we can test the structure
        ai_generator = AIConfigGenerator("test-key")
        logger.info("AI Config Generator created successfully")
        logger.info(f"Max content length: {ai_generator.MAX_CONTENT_LENGTH}")
        logger.info(
            f"Supported languages: {len(ai_generator.get_supported_languages())}"
        )
    except Exception as e:
        logger.info(f"AI Config Generator test (expected error): {e}")

    logger.info("AI Configuration System test completed!")


if __name__ == "__main__":
    test_ai_config_system()
