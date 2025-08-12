#!/usr/bin/env python3
"""
Linting and formatting script for the SRT Translator project.
Runs all code quality tools in the correct order.
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
            logger.error(f"STDOUT: {e.stdout}")
        if e.stderr:
            logger.error(f"STDERR: {e.stderr}")
        return False


def main():
    """Run all linting and formatting tools."""
    project_root = Path(__file__).parent.parent
    python_files = list(project_root.rglob("*.py"))

    # Filter out virtual environment and cache directories
    python_files = [
        f
        for f in python_files
        if not any(
            part.startswith(".") or part in ["venv", "__pycache__", ".pytest_cache"]
            for part in f.parts
        )
    ]

    logger.info(f"Found {len(python_files)} Python files to process")

    success = True

    # 1. Format code with Black
    success &= run_command(
        ["black", "--check", "srt_core", "gui", "tests", "scripts"],
        "Black code formatting check",
    )

    # 2. Sort imports with isort
    success &= run_command(
        ["isort", "--check-only", "--diff", "srt_core", "gui", "tests", "scripts"],
        "isort import sorting check",
    )

    # 3. Run flake8
    success &= run_command(
        ["flake8", "--max-line-length=88", "srt_core", "gui", "tests", "scripts"],
        "flake8 style checking",
    )

    # 4. Run pylint
    success &= run_command(
        ["pylint", "srt_core", "gui", "tests"], "pylint code analysis"
    )

    # 5. Run mypy (optional - can be skipped if too strict)
    try:
        success &= run_command(["mypy", "srt_core", "gui"], "mypy type checking")
    except FileNotFoundError:
        logger.warning("\n⚠️  mypy not found. Install with: pip install mypy")

    logger.info("=" * 60)
    if success:
        logger.info("🎉 All checks passed!")
        sys.exit(0)
    else:
        logger.error("❌ Some checks failed. Please fix the issues above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
