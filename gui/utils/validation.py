"""
Validation Utilities
Input validation functions for the GUI
"""

import logging
from typing import Dict, List

from PySide6.QtWidgets import QMessageBox


def validate_translation_inputs(
    api_key: str, selected_files: List[str], target_languages: Dict[str, str]
) -> tuple[bool, str]:
    """
    Validate translation inputs

    Returns:
        tuple: (is_valid, error_message)
    """
    logging.info(f"API key loaded: {'Yes' if api_key else 'No'}")

    if not api_key:
        return False, "Please enter your OpenAI API key."

    logging.info(f"Selected files: {len(selected_files)}")
    if not selected_files:
        return False, "Please select at least one SRT file to translate."

    logging.info(f"Target languages: {target_languages}")
    if not target_languages:
        return False, "Please select at least one target language."

    return True, ""


def show_validation_error(parent, title: str, message: str):
    """Show validation error message"""
    QMessageBox.warning(parent, title, message)


def show_translation_results(parent, results: dict):
    """Show translation completion results"""
    success_count = results.get("completed", 0)
    error_count = results.get("failed", 0)
    total_files = results.get("total_files", 0)

    logging.info(
        f"Success count: {success_count}, Error count: {error_count}, Total files: {total_files}"
    )

    if error_count == 0:
        QMessageBox.information(
            parent,
            "Translation Complete",
            f"Successfully translated {success_count} files!\n\n"
            f"Output files are available in the 'translated_srt_files' directory.",
        )
    else:
        QMessageBox.warning(
            parent,
            "Translation Complete with Errors",
            f"Translated {success_count} files successfully.\n"
            f"Encountered {error_count} errors.\n\n"
            f"Check the log output above for details.",
        )


def show_translation_error(parent, error_message: str):
    """Show translation error message"""
    QMessageBox.critical(
        parent,
        "Translation Error",
        f"An error occurred during translation:\n\n{error_message}",
    )
