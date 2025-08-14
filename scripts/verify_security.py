#!/usr/bin/env python3
"""
Security verification script for SRT Translator executable.
Checks if sensitive files are accidentally included in the executable.
"""

import logging
import os
import sys
import zipfile

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def check_executable_security(executable_path):
    """
    Check if the executable contains sensitive files.

    Args:
        executable_path: Path to the executable to check

    Returns:
        Tuple of (is_safe, issues_found)
    """
    logger = logging.getLogger(__name__)
    if not os.path.exists(executable_path):
        logger.error(f"❌ Error: Executable not found at {executable_path}")
        return False, ["Executable not found"]

    logger.info(f"🔍 Checking executable: {executable_path}")
    logger.info(f"📏 File size: {os.path.getsize(executable_path) / (1024 * 1024):.1f} MB")

    # List of sensitive files/patterns to check for
    sensitive_patterns = [
        "termbase.json",
        "translation_logs",
        "original_captions",
        "translated_srt_files",
        "translation_prompt.txt",
        "OPENAI_API_KEY",
        "API_KEY",
    ]

    issues_found = []

    try:
        # Try to extract files (PyInstaller executables are essentially ZIP files)
        try:
            with zipfile.ZipFile(executable_path, "r") as zip_ref:
                file_list = zip_ref.namelist()

                logger.info(f"📁 Found {len(file_list)} files in executable")

                # Check for sensitive patterns
                for pattern in sensitive_patterns:
                    for file_path in file_list:
                        if pattern.lower() in file_path.lower():
                            issues_found.append(f"Sensitive file found: {file_path}")

                # Check for any environment files
                env_files = [f for f in file_list if ".env" in f.lower()]
                if env_files:
                    issues_found.append(f"Environment files found: {env_files}")

                # Check for any JSON files that might be termbase
                json_files = [f for f in file_list if f.endswith(".json")]
                if json_files:
                    logger.info(f"📄 JSON files found: {json_files}")

        except zipfile.BadZipFile:
            # Not a ZIP file, try to search for patterns in binary content
            logger.warning("⚠️  Executable is not a ZIP file, checking binary content...")

            with open(executable_path, "rb") as f:
                content = f.read()

            # Check for sensitive strings in binary content
            for pattern in sensitive_patterns:
                if pattern.encode() in content:
                    issues_found.append(f"Sensitive pattern found in binary: {pattern}")

    except Exception as e:
        issues_found.append(f"Error during security check: {e}")

    # Report results
    if issues_found:
        logger.error("\n❌ SECURITY ISSUES FOUND:")
        for issue in issues_found:
            logger.error(f"   • {issue}")
        return False, issues_found
    else:
        logger.info("\n✅ SECURITY CHECK PASSED")
        logger.info("   • No sensitive files found in executable")
        logger.info("   • No API keys detected")
        logger.info("   • No user data included")
        return True, []


def main():
    """Main function to run security verification."""
    logger = logging.getLogger(__name__)
    logger.info("🔒 SRT Translator Security Verification")
    logger.info("=" * 50)

    # Look for executable in common locations
    possible_paths = [
        "dist/SRT-Translator-GUI.exe",
        "dist/SRT-Translator.exe",
        "dist/SRT-Translator",
        "build_specs/dist/SRT-Translator-GUI.exe",
        "build_specs/dist/SRT-Translator.exe",
        "build_specs/dist/SRT-Translator",
    ]

    executable_path = None
    for path in possible_paths:
        if os.path.exists(path):
            executable_path = path
            break

    if not executable_path:
        logger.error("❌ No executable found. Please run the build script first.")
        logger.error("\nExpected locations:")
        for path in possible_paths:
            logger.error(f"   • {path}")
        return 1

    # Run security check
    is_safe, issues = check_executable_security(executable_path)

    logger.info("\n" + "=" * 50)
    if is_safe:
        logger.info("🎉 Your executable is safe to distribute!")
        logger.info("   • No sensitive data included")
        logger.info("   • Users can safely run without exposing your API keys")
        return 0
    else:
        logger.warning("⚠️  Security issues detected!")
        logger.warning("   • Do not distribute this executable")
        logger.warning("   • Rebuild with the updated security settings")
        return 1


if __name__ == "__main__":
    sys.exit(main())
