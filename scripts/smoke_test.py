#!/usr/bin/env python3
"""
Smoke test script for SRT Translator
Tests basic functionality: parse SRT, verify structure, write output
"""

import logging
import os
import shutil
import sys

# Set up logging - ALWAYS include this
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# Get logger for this module
logger = logging.getLogger(__name__)

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_srt_parsing():
    """Test SRT parsing functionality"""
    logger.info("🔍 Testing SRT parsing...")

    from srt_translator.core.translator.srt_parser import SRTParser

    # Create test SRT content
    srt_content = """1
00:00:01,000 --> 00:00:04,000
Hello world
This is a test subtitle

2
00:00:05,000 --> 00:00:08,000
Testing SRT parser
And writer functionality"""

    # Write test file
    with open("test.srt", "w", encoding="utf-8") as f:
        f.write(srt_content)

    # Parse the file
    subtitles = SRTParser.parse_file("test.srt")

    if len(subtitles) == 2:
        logger.info("✅ SRT parsing successful: found %s subtitles", len(subtitles))
        for i, sub in enumerate(subtitles, 1):
            logger.info('   %s. %s --> %s: "%s"', i, sub.start, sub.end, sub.content)
        return True
    else:
        logger.error("❌ SRT parsing failed: expected 2 subtitles, got %s", len(subtitles))
        return False


def test_srt_writing():
    """Test SRT writing functionality"""
    logger.info("💾 Testing SRT writing...")

    from srt_translator.core.translator.srt_parser import SRTParser

    # Parse the test file
    subtitles = SRTParser.parse_file("test.srt")

    # Write to output file
    SRTParser.write_file("output.srt", subtitles)

    # Verify output file exists and has content
    if os.path.exists("output.srt"):
        with open("output.srt", encoding="utf-8") as f:
            content = f.read()
        if "Hello world" in content and "Testing SRT parser" in content:
            logger.info("✅ SRT writing successful: output.srt created with correct content")
            return True
        else:
            logger.error("❌ SRT writing failed: output file missing expected content")
            return False
    else:
        logger.error("❌ SRT writing failed: output.srt not created")
        return False


def test_cli_entry_point():
    """Test CLI entry point"""
    logger.info("🔧 Testing CLI entry point...")

    try:
        import importlib.util

        spec = importlib.util.find_spec("srt_translator.core.main")
        if spec is None:
            raise ImportError("Module not found")

        # Import to verify it's actually importable
        from srt_translator.core.main import translate_srt_files  # noqa: F401

        logger.info("✅ CLI main function found and importable")
        return True
    except ImportError as e:
        logger.error("❌ CLI main function import failed: %s", e)
        return False


def test_version_information():
    """Test version information"""
    logger.info("📋 Testing version information...")

    try:
        from srt_translator import __version__

        logger.info("✅ Version information available: %s", __version__)
        return True
    except ImportError as e:
        logger.error("❌ Version information import failed: %s", e)
        return False


def main():
    """Run all smoke tests"""
    logger.info("🧪 Starting SRT Translator smoke test...")

    # Create test directory
    test_dir = f"smoke_test_{os.getpid()}"
    os.makedirs(test_dir, exist_ok=True)
    original_dir = os.getcwd()
    os.chdir(test_dir)

    logger.info("📁 Created test directory: %s", test_dir)

    try:
        # Run tests
        tests = [
            test_srt_parsing,
            test_srt_writing,
            test_cli_entry_point,
            test_version_information,
        ]

        results = []
        for test in tests:
            results.append(test())

        # Cleanup
        os.chdir(original_dir)
        shutil.rmtree(test_dir)

        # Report results
        logger.info("")
        if all(results):
            logger.info("🎉 All smoke tests passed!")
            logger.info("✅ SRT parsing works")
            logger.info("✅ SRT writing works")
            logger.info("✅ CLI entry point available")
            logger.info("✅ Version information accessible")
            logger.info("")
            logger.info("🚀 SRT Translator is ready for basic operations")
            return 0
        else:
            logger.error("❌ Some smoke tests failed")
            return 1

    except Exception as e:
        logger.error("❌ Smoke test failed with error: %s", e)
        os.chdir(original_dir)
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
        return 1


if __name__ == "__main__":
    sys.exit(main())
