#!/usr/bin/env python3
"""
Smoke test script for SRT Translator
Tests basic functionality: parse SRT, verify structure, write output
"""

import sys
import os
import tempfile
import shutil

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_srt_parsing():
    """Test SRT parsing functionality"""
    print("🔍 Testing SRT parsing...")
    
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
        print(f"✅ SRT parsing successful: found {len(subtitles)} subtitles")
        for i, sub in enumerate(subtitles, 1):
            print(f"   {i}. {sub.start} --> {sub.end}: \"{sub.content}\"")
        return True
    else:
        print(f"❌ SRT parsing failed: expected 2 subtitles, got {len(subtitles)}")
        return False

def test_srt_writing():
    """Test SRT writing functionality"""
    print("💾 Testing SRT writing...")
    
    from srt_translator.core.translator.srt_parser import SRTParser
    
    # Parse the test file
    subtitles = SRTParser.parse_file("test.srt")
    
    # Write to output file
    SRTParser.write_file("output.srt", subtitles)
    
    # Verify output file exists and has content
    if os.path.exists("output.srt"):
        with open("output.srt", "r", encoding="utf-8") as f:
            content = f.read()
        if "Hello world" in content and "Testing SRT parser" in content:
            print("✅ SRT writing successful: output.srt created with correct content")
            return True
        else:
            print("❌ SRT writing failed: output file missing expected content")
            return False
    else:
        print("❌ SRT writing failed: output.srt not created")
        return False

def test_cli_entry_point():
    """Test CLI entry point"""
    print("🔧 Testing CLI entry point...")
    
    try:
        from srt_translator.core.main import main
        print("✅ CLI main function found and importable")
        return True
    except ImportError as e:
        print(f"❌ CLI main function import failed: {e}")
        return False

def test_version_information():
    """Test version information"""
    print("📋 Testing version information...")
    
    try:
        from srt_translator import __version__
        print(f"✅ Version information available: {__version__}")
        return True
    except ImportError as e:
        print(f"❌ Version information import failed: {e}")
        return False

def main():
    """Run all smoke tests"""
    print("🧪 Starting SRT Translator smoke test...")
    
    # Create test directory
    test_dir = f"smoke_test_{os.getpid()}"
    os.makedirs(test_dir, exist_ok=True)
    original_dir = os.getcwd()
    os.chdir(test_dir)
    
    print(f"📁 Created test directory: {test_dir}")
    
    try:
        # Run tests
        tests = [
            test_srt_parsing,
            test_srt_writing,
            test_cli_entry_point,
            test_version_information
        ]
        
        results = []
        for test in tests:
            results.append(test())
        
        # Cleanup
        os.chdir(original_dir)
        shutil.rmtree(test_dir)
        
        # Report results
        print("")
        if all(results):
            print("🎉 All smoke tests passed!")
            print("✅ SRT parsing works")
            print("✅ SRT writing works")
            print("✅ CLI entry point available")
            print("✅ Version information accessible")
            print("")
            print("🚀 SRT Translator is ready for basic operations")
            return 0
        else:
            print("❌ Some smoke tests failed")
            return 1
            
    except Exception as e:
        print(f"❌ Smoke test failed with error: {e}")
        os.chdir(original_dir)
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
        return 1

if __name__ == "__main__":
    sys.exit(main())
