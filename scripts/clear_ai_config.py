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
        dnt_terms, termbase, _ = settings_manager.load_ai_config()
        logger.info(
            "Current AI config: %d DNT terms, %d languages in termbase",
            len(dnt_terms),
            len(termbase),
        )

        # Clear the AI configuration
        settings_manager.clear_ai_config()

        settings_manager.save_api_key("")
        logger.info("Cleared saved API key")

        settings_manager.save_selected_files([])
        logger.info("Cleared selected files")

        settings_manager.save_target_languages({})
        logger.info("Cleared saved target languages")

        settings_manager.save_last_output_directory("")
        logger.info("Output directory cleared")

        # Verify it's cleared
        dnt_terms, termbase, _ = settings_manager.load_ai_config()
        logger.info(
            "After clearing: %d DNT terms, %d languages in termbase",
            len(dnt_terms),
            len(termbase),
        )

        logger.info("✅ AI configuration cleared successfully!")

    except ImportError as e:
        logger.error("Import error: %s", e)
        logger.error("Make sure you're running this from the project root directory")
        sys.exit(1)
    except Exception as e:
        logger.error("Error: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
