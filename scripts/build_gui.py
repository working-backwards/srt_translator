#!/usr/bin/env python3
"""
Simple build wrapper for SRT Translator.
Builds the GUI executable using PyInstaller.
"""

import logging
import os
import platform
import subprocess
import sys

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


def main():
    """Build the SRT Translator GUI executable"""
    logger = logging.getLogger(__name__)
    logger.info("🚀 Building SRT Translator GUI Executable")
    logger.info(f"Platform: {platform.system()} {platform.machine()}")

    # Check if PyInstaller is installed
    try:
        import PyInstaller

        logger.info(f"✅ PyInstaller {PyInstaller.__version__} found")
    except ImportError:
        logger.error("❌ PyInstaller not found. Please install it:")
        logger.error("pip install pyinstaller")
        sys.exit(1)

    # Build using the existing spec file
    spec_file = "build_specs/srt_translator_gui.spec"
    if not os.path.exists(spec_file):
        logger.error(f"❌ Spec file not found: {spec_file}")
        sys.exit(1)

    logger.info("🔨 Building GUI executable...")
    try:
        # Run PyInstaller
        result = subprocess.run(
            [sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm", spec_file],
            check=True,
            capture_output=True,
            text=True,
        )

        logger.info("✅ Successfully built GUI executable!")
        logger.info("📁 Executable created in: dist/windows/")

    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Build failed: {e}")
        logger.error(f"Error output: {e.stderr}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Build failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
