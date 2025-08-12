#!/usr/bin/env python3
"""
Auto-fix formatting script for the SRT Translator project.
Automatically fixes code formatting issues.
"""

import logging
import subprocess
import sys
from pathlib import Path

# Set up logging - ALWAYS include this
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Get logger for this module
logger = logging.getLogger(__name__)


def run_command(cmd, description):
    """Run a command and handle errors."""
    logger.info("=" * 60)
    logger.info(f"Running: {description}")
    logger.info(f"Command: {' '.join(cmd)}")
    logger.info("=" * 60)

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info("✅ SUCCESS")
        if result.stdout:
            logger.info(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        logger.error("❌ FAILED")
        if e.stdout:
            logger.error("STDOUT:", e.stdout)
        if e.stderr:
            logger.error("STDERR:", e.stderr)
        return False


def main():
    """Run all auto-fixing tools."""
    project_root = Path(__file__).parent.parent

    logger.info("🔧 Auto-fixing code formatting issues...")

    success = True

    # 1. Format code with Black
    success &= run_command(
        ["black", "srt_translator", "tests", "scripts"], "Black code formatting"
    )

    # 2. Sort imports with isort
    success &= run_command(
        ["isort", "srt_translator", "tests", "scripts"], "isort import sorting"
    )

    logger.info("=" * 60)
    if success:
        logger.info("🎉 All formatting issues have been fixed!")
        logger.info("Next steps:")
        logger.info("1. Review the changes with: git diff")
        logger.info("2. Run linting check: python scripts/lint.py")
        sys.exit(0)
    else:
        logger.error("❌ Some fixes failed. Please check the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
