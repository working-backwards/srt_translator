#!/usr/bin/env python3
"""
Test runner for SRT Translator
"""

import sys
import subprocess
import os


def run_tests():
    """Run all tests using pytest"""
    print("Running SRT Translator tests...")
    print("=" * 50)

    # Run tests with pytest
    cmd = [sys.executable, "-m", "pytest", "tests/", "-v"]

    try:
        result = subprocess.run(cmd, capture_output=False, text=True)
        return result.returncode
    except FileNotFoundError:
        print("Error: pytest not found. Please install pytest:")
        print("pip install pytest")
        return 1


def run_gui_tests():
    """Run GUI tests specifically"""
    print("Running GUI tests...")
    print("=" * 30)

    cmd = [sys.executable, "-m", "pytest", "tests/gui/", "-v"]

    try:
        result = subprocess.run(cmd, capture_output=False, text=True)
        return result.returncode
    except FileNotFoundError:
        print("Error: pytest not found. Please install pytest:")
        print("pip install pytest")
        return 1


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "gui":
        sys.exit(run_gui_tests())
    else:
        sys.exit(run_tests())
