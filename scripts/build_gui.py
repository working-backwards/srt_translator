#!/usr/bin/env python3
"""
Quick GUI build script for SRT Translator.

WHAT IT DOES:
  • Builds the GUI executable using PyInstaller and the .spec file
  • Creates a single-file executable in dist/ directory
  • Fast, lightweight build for development and testing

WHEN TO USE THIS:
  • Quick local builds during development
  • Testing changes to the GUI before packaging
  • When you just need the executable, not a full release package

WHEN TO USE build_release.py INSTEAD:
  • Creating release packages with documentation
  • Building DMG files for macOS distribution
  • Creating ZIP packages for Windows distribution
  • When you need versioned, packaged artifacts

USAGE:
  python scripts/build_gui.py

OUTPUT:
  • Windows: dist/SRT-Translator.exe
  • macOS: dist/SRT Translator.app
"""

import logging
import os
import platform
import subprocess
import sys

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def main():
    """Build the SRT Translator GUI executable"""
    logger = logging.getLogger(__name__)
    logger.info("🚀 Building SRT Translator GUI Executable")
    logger.info("Platform: %s %s", platform.system(), platform.machine())

    # Check if PyInstaller is installed
    try:
        import PyInstaller

        logger.info("✅ PyInstaller %s found", PyInstaller.__version__)
    except ImportError:
        logger.error("❌ PyInstaller not found. Please install it:")
        logger.error("pip install pyinstaller")
        sys.exit(1)

    # Build using the existing spec file
    spec_file = "build_specs/srt_translator_gui.spec"
    if not os.path.exists(spec_file):
        logger.error("❌ Spec file not found: %s", spec_file)
        sys.exit(1)

    logger.info("🔨 Building GUI executable...")
    try:
        # Run PyInstaller with the spec file (spec file defines onefile vs onedir)
        subprocess.run(
            [sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm", spec_file],
            check=True,
            capture_output=True,
            text=True,
        )

        logger.info("✅ Successfully built GUI executable!")
        if platform.system() == "Windows":
            logger.info("📁 Executable created in: dist/ (SRT-Translator.exe)")
        else:
            logger.info("📁 App bundle created in: dist/SRT Translator/")

    except subprocess.CalledProcessError as e:
        logger.error("❌ Build failed: %s", e)
        logger.error("Error output: %s", e.stderr)
        sys.exit(1)
    except (OSError, subprocess.SubprocessError) as e:
        logger.error("❌ Build failed: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
