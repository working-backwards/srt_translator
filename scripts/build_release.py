#!/usr/bin/env python3
"""
Build release package for SRT Translator.
Creates executables and packages them for distribution.
"""

import logging
import os
import platform
import shutil
import sys
import zipfile
from datetime import datetime

# Set up logging - ALWAYS include this
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Add project root to path before imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from build_gui import main as build_executables  # noqa: E402

# Get logger for this module
logger = logging.getLogger(__name__)


def create_release_package():
    """Create a release package with executables and documentation."""
    release_dir = "release"
    package_name = f"SRT-Translator-v1.0.0-{platform.system().lower()}"
    package_path = os.path.join(release_dir, package_name)

    # Clean and create release directory
    if os.path.exists(release_dir):
        shutil.rmtree(release_dir)
    os.makedirs(release_dir)

    # Copy executables from dist
    dist_dir = "dist"
    if os.path.exists(dist_dir):
        shutil.copytree(dist_dir, package_path)

    # Copy essential files
    essential_files = [
        "README.md",
        "LICENSE",
        "examples/env_example",
    ]

    for file_path in essential_files:
        if os.path.exists(file_path):
            dest_path = os.path.join(package_path, os.path.basename(file_path))
            shutil.copy2(file_path, dest_path)
            logger.info(f"✅ Copied {file_path}")

    # Create quick start guide
    quick_start = f"""# SRT Translator - Quick Start Guide

## For Content Creators (Simple Installation)

1. **Extract** this package to a folder on your computer
2. **Configure API Key**:
   - Copy `examples/env_example` to `.env`
   - Edit `.env` and add your OpenAI API key
3. **Run the Application**: Double-click `SRT-Translator.exe`
4. **Add Your Files**: Place `.srt` files in the `original_captions` folder
5. **Translate**: Use the interface to translate your subtitles

## For Advanced Users

If you prefer to work with the source code:

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-repo/srt_translator.git
   cd srt_translator
   ```

2. **Install dependencies**:
   ```bash
   pip install -e .
   ```

3. **Run the application**:
   ```bash
   srtx              # GUI version
   srt-cli           # CLI version
   ```

## System Requirements

- **Operating System**: Windows 10+, macOS 10.14+, or Linux
- **Internet Connection**: Required for translation
- **OpenAI API Key**: Required (get one at https://platform.openai.com/)

## Features

- ✅ Translate to 78+ languages
- ✅ Preserve specific terms (DNT)
- ✅ Batch processing
- ✅ GUI interface
- ✅ Automatic error fixing
- ✅ Detailed logging

## Support

For issues and questions:
- GitHub Issues: https://github.com/your-repo/srt_translator/issues
- Documentation: See README.md for detailed instructions

## Version Information

- Version: 1.0.0
- Build Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- Platform: {platform.system()} {platform.machine()}
"""

    with open(os.path.join(package_path, "QUICK_START.md"), "w") as f:
        f.write(quick_start)

    # Create ZIP archive
    zip_path = f"{package_path}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _dirs, files in os.walk(package_path):
            for file in files:
                file_path = os.path.join(root, file)
                arc_name = os.path.relpath(file_path, package_path)
                zipf.write(file_path, arc_name)

    logger.info(f"✅ Created release package: {zip_path}")
    return zip_path


def main():
    """Main release build function."""
    logger.info("🚀 Building SRT Translator Release")
    logger.info(f"Platform: {platform.system()} {platform.machine()}")
    logger.info(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Check if executables already exist
    if platform.system() == "Windows":
        gui_exe_path = "dist/SRT-Translator.exe"
        app_bundle_path = None
    else:
        gui_exe_path = None
        app_bundle_path = "dist/SRT Translator/SRT Translator.app"

    if (gui_exe_path and os.path.exists(gui_exe_path)) or (
        app_bundle_path and os.path.exists(app_bundle_path)
    ):
        logger.info("\n✅ Executable already exists")
        logger.info("📦 Skipping build step...")
    else:
        # Build executables
        logger.info("\n📦 Building executables...")
        try:
            build_executables()
        except Exception as e:
            logger.error(f"❌ Failed to build executables: {e}")
            sys.exit(1)

    # Create release package
    logger.info("\n📋 Creating release package...")
    try:
        release_path = create_release_package()
        logger.info("\n🎉 Release build completed successfully!")
        logger.info(f"📦 Release package: {release_path}")
        logger.info("📁 Executables: dist/")
        logger.info("📋 Documentation: release/")
    except Exception as e:
        logger.error(f"❌ Failed to create release package: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
