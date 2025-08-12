#!/usr/bin/env python3
"""
Test runner for SRT Translator
"""

import logging
import os
import subprocess
import sys

# Set up logging - ALWAYS include this
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Get logger for this module
logger = logging.getLogger(__name__)


def run_tests():
    """Run all tests using pytest"""
    logger.info("Running SRT Translator tests...")
    logger.info("=" * 50)

    # Run tests with pytest
    cmd = [sys.executable, "-m", "pytest", "tests/", "-v"]

    try:
        result = subprocess.run(cmd, capture_output=False, text=True)
        return result.returncode
    except FileNotFoundError:
        logger.error("Error: pytest not found. Please install pytest:")
        logger.error("pip install pytest")
        return 1


def run_gui_tests():
    """Run GUI tests specifically"""
    logger.info("Running GUI tests...")
    logger.info("=" * 30)

    cmd = [sys.executable, "-m", "pytest", "tests/gui/", "-v"]

    try:
        result = subprocess.run(cmd, capture_output=False, text=True)
        return result.returncode
    except FileNotFoundError:
        logger.error("Error: pytest not found. Please install pytest:")
        logger.error("pip install pytest")
        return 1


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "gui":
        sys.exit(run_gui_tests())
    else:
        sys.exit(run_tests())
