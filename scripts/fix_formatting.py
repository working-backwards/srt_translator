#!/usr/bin/env python3
"""
Auto-fix formatting script for the SRT Translator project.
Automatically fixes code formatting issues.
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n{'=' * 60}")
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
    """Run all auto-fixing tools."""
    project_root = Path(__file__).parent.parent

    print("🔧 Auto-fixing code formatting issues...")

    success = True

    # 1. Format code with Black
    success &= run_command(
        ["black", "srt_core", "gui", "tests", "scripts"], "Black code formatting"
    )

    # 2. Sort imports with isort
    success &= run_command(
        ["isort", "srt_core", "gui", "tests", "scripts"], "isort import sorting"
    )

    print(f"\n{'=' * 60}")
    if success:
        print("🎉 All formatting issues have been fixed!")
        print("\nNext steps:")
        print("1. Review the changes with: git diff")
        print("2. Run linting check: python scripts/lint.py")
        sys.exit(0)
    else:
        print("❌ Some fixes failed. Please check the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
