#!/usr/bin/env python3
"""
Simple build wrapper for SRT Translator.
Builds the GUI executable using PyInstaller.
"""

import os
import platform
import subprocess
import sys


def main():
    """Build the SRT Translator GUI executable"""
    print("🚀 Building SRT Translator GUI Executable")
    print(f"Platform: {platform.system()} {platform.machine()}")

    # Check if PyInstaller is installed
    try:
        import PyInstaller

        print(f"✅ PyInstaller {PyInstaller.__version__} found")
    except ImportError:
        print("❌ PyInstaller not found. Please install it:")
        print("pip install pyinstaller")
        sys.exit(1)

    # Build using the existing spec file
    spec_file = "build_specs/srt_translator_gui.spec"
    if not os.path.exists(spec_file):
        print(f"❌ Spec file not found: {spec_file}")
        sys.exit(1)

    print("🔨 Building GUI executable...")
    try:
        # Run PyInstaller
        result = subprocess.run(
            [sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm", spec_file],
            check=True,
            capture_output=True,
            text=True,
        )

        print("✅ Successfully built GUI executable!")
        print(f"📁 Executable created in: dist/windows/")

    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed: {e}")
        print(f"Error output: {e.stderr}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Build failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
