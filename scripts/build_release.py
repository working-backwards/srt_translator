#!/usr/bin/env python3
"""
Release build script for SRT Translator.
Creates executables and prepares release packages for distribution.
"""

import os
import sys
import platform
import subprocess
import shutil
import zipfile
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pyinstaller_build import main as build_executables


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
        "config/languages.json",
        ".env.example",
    ]

    for file_path in essential_files:
        if os.path.exists(file_path):
            dest_path = os.path.join(package_path, os.path.basename(file_path))
            shutil.copy2(file_path, dest_path)
            print(f"✅ Copied {file_path}")

    # Create quick start guide
    quick_start = f"""# SRT Translator - Quick Start Guide

## For Content Creators (Simple Installation)

1. **Extract** this package to a folder on your computer
2. **Configure API Key**: 
   - Copy `.env.example` to `.env`
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
   python run_gui.py    # GUI version
   python run_cli.py    # CLI version
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
        for root, dirs, files in os.walk(package_path):
            for file in files:
                file_path = os.path.join(root, file)
                arc_name = os.path.relpath(file_path, package_path)
                zipf.write(file_path, arc_name)

    print(f"✅ Created release package: {zip_path}")
    return zip_path


def main():
    """Main release build function."""
    print("🚀 Building SRT Translator Release")
    print(f"Platform: {platform.system()} {platform.machine()}")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Check if executables already exist
    gui_exe_path = "dist/SRT-Translator-GUI.exe"
    if os.path.exists(gui_exe_path):
        print(f"\n✅ Executable already exists: {gui_exe_path}")
        print("📦 Skipping build step...")
    else:
        # Build executables
        print("\n📦 Building executables...")
        try:
            build_executables()
        except Exception as e:
            print(f"❌ Failed to build executables: {e}")
            sys.exit(1)

    # Create release package
    print("\n📋 Creating release package...")
    try:
        release_path = create_release_package()
        print(f"\n🎉 Release build completed successfully!")
        print(f"📦 Release package: {release_path}")
        print(f"📁 Executables: dist/")
        print(f"📋 Documentation: release/")
    except Exception as e:
        print(f"❌ Failed to create release package: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
