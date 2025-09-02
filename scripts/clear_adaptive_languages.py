#!/usr/bin/env python3
"""
Clear adaptive language settings from the GUI.

This script removes all adaptive language data including:
- User popular languages
- Language usage tracking data
- Adaptive popular languages

This does NOT affect:
- AI-generated DNT terms, termbase, or source language
- Target language selections
- Other GUI settings
"""

import logging
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from srt_translator.core.config.language_config import LanguageConfig  # noqa: E402
from srt_translator.gui.settings_manager import SettingsManager  # noqa: E402


def main():
    """Clear adaptive language settings."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    logger = logging.getLogger(__name__)

    try:
        logger.info("Clearing adaptive language settings...")

        # Initialize settings manager
        language_config = LanguageConfig({"languages": {}})
        settings_manager = SettingsManager(language_config)

        # Clear adaptive language data
        settings_manager.reset_adaptive_popular_languages()

        logger.info("✓ Adaptive language settings cleared successfully")
        logger.info("  - User popular languages reset")
        logger.info("  - Language usage tracking data cleared")
        logger.info("  - Adaptive popular languages reset")

    except Exception as e:
        logger.error("Failed to clear adaptive language settings: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
