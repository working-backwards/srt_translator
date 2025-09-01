#!/usr/bin/env python3
"""
Simple script to clear AI-generated configuration from the GUI settings.
Run this from the project root directory.
"""

import logging
import os
import sys

# Set up logging - ALWAYS include this
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Get logger for this module
logger = logging.getLogger(__name__)

# Add the project root to the path (scripts/ is one level down)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def main():
    try:
        from srt_translator.core.config.language_config import LanguageConfig
        from srt_translator.gui.settings_manager import SettingsManager

        logger.info("Clearing AI-generated configuration...")
        language_config = LanguageConfig({"languages": {}})
        settings_manager = SettingsManager(language_config)

        # Check what's currently stored
        result = settings_manager.load_ai_config()
        dnt_terms, termbase = result.dnt_terms, result.termbase
        logger.info(
            f"Current AI config: {len(dnt_terms)} DNT terms, {len(termbase)} languages in termbase"
        )

        # Clear the AI configuration
        settings_manager.clear_ai_config()

        # Verify it's cleared
        result = settings_manager.load_ai_config()
        dnt_terms, termbase = result.dnt_terms, result.termbase
        logger.info(
            f"After clearing: {len(dnt_terms)} DNT terms, {len(termbase)} languages in termbase"
        )

        logger.info("✅ AI configuration cleared successfully!")

    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        logger.error("Make sure you're running this from the project root directory")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
