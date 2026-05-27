from __future__ import annotations

import logging
from typing import Any

from srt_translator.core.config.models import TranslationConfig


class Translator:
    """Facade class for running translations from GUI/CLI."""

    def __init__(self, config: TranslationConfig):
        self.config = config

    def run(self) -> dict[str, Any]:
        """Run the translation and return results."""
        try:
            # Run the translation and get summary
            summary = self.config.run()

            # Return results in format expected by GUI
            return {
                "status": "success",
                "message": "Translation completed successfully",
                "completed": summary["successes"],
                "failed": summary["errors"],
                "total_files": summary["total_files"],
                "output_directory": str(self.config.output_directory),  # Include actual output directory
                "successful_languages": summary["successful_languages"],
                "failed_languages": summary["failed_languages"],
                "batch_directory": summary["batch_directory"],
                "cancelled": summary.get("cancelled", False),
            }
        except Exception as e:
            logging.error("Translation failed: %s", e)
            raise
