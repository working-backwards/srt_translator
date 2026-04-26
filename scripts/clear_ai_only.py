#!/usr/bin/env python3
"""Clear only the AI-generated config (ai_* QSettings keys).

Unlike scripts/clear_ai_config.py, this preserves api_key, target_languages,
tone, last_input_directory, and other non-AI settings. Useful when you want
to re-import a termbase / DNT file without merging with stale ai_* data.

Removes: ai_dnt_terms, ai_termbase, ai_source_language, ai_config_timestamp,
ai_config_file_hash.

Run from the project root:
    python scripts/clear_ai_only.py
"""

import logging
import os
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def main() -> int:
    from srt_translator.core.config.language_config import LanguageConfig
    from srt_translator.gui.settings_manager import SettingsManager

    settings_manager = SettingsManager(LanguageConfig({"languages": {}}))
    settings_manager.migrate_from_native_if_needed()

    dnt_terms, termbase, _ = settings_manager.load_ai_config()
    logger.info(
        "Before clear: %d DNT terms, %d languages in termbase",
        len(dnt_terms),
        len(termbase),
    )

    settings_manager.clear_ai_config()

    dnt_terms, termbase, _ = settings_manager.load_ai_config()
    logger.info(
        "After clear:  %d DNT terms, %d languages in termbase",
        len(dnt_terms),
        len(termbase),
    )
    logger.info("Cleared AI config from %s", settings_manager.settings.fileName())
    return 0


if __name__ == "__main__":
    sys.exit(main())
