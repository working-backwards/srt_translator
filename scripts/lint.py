#!/usr/bin/env python3
"""
Linting and formatting script for the SRT Translator project.
Runs all code quality tools in the correct order.
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print("=" * 60)

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ SUCCESS")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print("❌ FAILED")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
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

    print(f"Found {len(python_files)} Python files to process")

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
        ["flake8", "srt_core", "gui", "tests", "scripts"], "flake8 style checking"
    )

    # 4. Run pylint
    success &= run_command(
        ["pylint", "srt_core", "gui", "tests"], "pylint code analysis"
    )

    # 5. Run mypy (optional - can be skipped if too strict)
    try:
        success &= run_command(["mypy", "srt_core", "gui"], "mypy type checking")
    except FileNotFoundError:
        print("\n⚠️  mypy not found. Install with: pip install mypy")

    print(f"\n{'='*60}")
    if success:
        print("🎉 All checks passed!")
        sys.exit(0)
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
