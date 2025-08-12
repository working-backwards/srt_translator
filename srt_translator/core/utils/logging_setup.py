#!/usr/bin/env python3
"""
Logging configuration for entry points only.
"""

import logging
import os

from srt_translator.core.config.models import LogMode


def configure_logging(log_mode: LogMode) -> None:
    """Configure logging based on the specified mode."""
    level = logging.DEBUG if log_mode == LogMode.Verbose else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
        ],
    )


def setup_logging(log_file_override: str) -> str:
    """Configure logging for batch operations (legacy support)"""
    # Ensure directory exists
    os.makedirs(os.path.dirname(log_file_override), exist_ok=True)

    # Create a dedicated logger for translation operations
    # This avoids conflicts with existing root logger configurations
    translation_logger = logging.getLogger("srt_translator")
    translation_logger.setLevel(logging.INFO)

    # Remove any existing handlers to avoid duplicates
    for handler in translation_logger.handlers[:]:
        translation_logger.removeHandler(handler)

    # Create a file handler for the batch log
    file_handler = logging.FileHandler(log_file_override, encoding="utf-8")
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )

    # Add the file handler to the translation logger
    translation_logger.addHandler(file_handler)

    # Ensure the translation logger propagates to root for console output
    translation_logger.propagate = True

    return log_file_override


def log_placeholder_issue(issue_type, issue_details):
    """Log placeholder issues with a reason description and subtitle number"""
    fixable_status = (
        "Computer-fixable"
        if issue_details.get("fixable", False)
        else "Requires human review"
    )
    reason_description = issue_details.get(
        "reason_description", "No specific reason provided."
    )
    subtitle_number = issue_details.get("subtitle_number", "Unknown")

    logging.warning(
        f"""
==================================================
{issue_type.upper()}:
File: {issue_details["filename"]}
Subtitle Number: {subtitle_number}
Language: {issue_details["language"]}
Original Term: {issue_details["original_term"]}
Placeholder: {issue_details["placeholder"]}
Original Context: {issue_details.get("original_context", "N/A")}
Translated Context: {issue_details.get("translated_context", "N/A")}
Status: {fixable_status}
Reason: {reason_description}
==================================================
"""
    )
