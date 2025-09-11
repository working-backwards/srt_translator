#!/usr/bin/env python3
"""
Logging configuration for entry points only.
"""

import logging
import os
from typing import Protocol


class LoggerLike(Protocol):
    """Protocol for logger-like objects to help with type checking."""

    def debug(self, msg: str, *args, **kwargs) -> None: ...
    def info(self, msg: str, *args, **kwargs) -> None: ...
    def warning(self, msg: str, *args, **kwargs) -> None: ...
    def error(self, msg: str, *args, **kwargs) -> None: ...
    def critical(self, msg: str, *args, **kwargs) -> None: ...


def setup_logging(log_file_override: str) -> str:
    """Configure logging for batch operations (legacy support)"""
    # Ensure directory exists
    os.makedirs(os.path.dirname(log_file_override), exist_ok=True)

    # Create a dedicated logger for translation operations
    # This avoids conflicts with existing root logger configurations
    translation_logger = logging.getLogger("srt_translator")
    # Don't override the logging level - respect what was already set
    # translation_logger.setLevel(logging.INFO)  # Commented out to respect GUI logging level

    # Remove any existing handlers to avoid duplicates
    for handler in translation_logger.handlers[:]:
        translation_logger.removeHandler(handler)

    # Create a file handler for the batch log
    file_handler = logging.FileHandler(log_file_override, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

    # Add the file handler to the translation logger
    translation_logger.addHandler(file_handler)

    # Ensure the translation logger propagates to root for console output
    translation_logger.propagate = True

    return log_file_override
