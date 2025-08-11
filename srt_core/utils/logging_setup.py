#!/usr/bin/env python3
"""
Logging setup for the SRT Translator.
"""

import logging
import os

from srt_core.config.settings import LOG_MODE


def setup_logging(log_file_override: str) -> str:
    """Configure logging and return active log file path.

    Behavior:
    - Removes any existing FileHandlers to avoid duplicate log lines across runs.
    - Uses the provided log_file_override path (required for batch-specific logging).
    - Ensures a single console StreamHandler exists.
    - Sets logging level to DEBUG if DEBUG_MODE environment variable is set to "true".
    """
    # Ensure directory exists
    os.makedirs(os.path.dirname(log_file_override), exist_ok=True)

    root_logger = logging.getLogger()

    # Remove and close prior file handlers to prevent duplication
    for handler in list(root_logger.handlers):
        if isinstance(handler, logging.FileHandler):
            root_logger.removeHandler(handler)
            try:
                handler.close()
            except Exception:
                pass

    # Use the provided log file path
    log_file = log_file_override

    class HTTPFilter(logging.Filter):
        def filter(self, record):
            if LOG_MODE == "Standard":
                msg = str(record.msg).lower()
                http_keywords = [
                    "http",
                    "https",
                    "request",
                    "response",
                    "api.openai.com",
                ]
                return not any(keyword in msg for keyword in http_keywords)
            return True

    log_format = "%(asctime)s - %(levelname)s - %(message)s"
    formatter = logging.Formatter(log_format)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.addFilter(HTTPFilter())

    # Add a console handler if one isn't already present
    has_stream = any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers)
    if not has_stream:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.addFilter(HTTPFilter())
        root_logger.addHandler(console_handler)

    # Set logging level based on DEBUG_MODE environment variable
    if os.getenv("DEBUG_MODE", "false").lower() == "true":
        root_logger.setLevel(logging.DEBUG)
        print("🔍 Debug logging enabled - detailed information will be shown")
    else:
        root_logger.setLevel(logging.INFO)

    root_logger.addHandler(file_handler)

    # Suppress verbose HTTP logs from dependencies
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)

    return log_file


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
