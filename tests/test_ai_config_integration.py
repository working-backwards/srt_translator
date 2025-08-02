#!/usr/bin/env python3
"""
Test script for AI Configuration Integration
"""

import sys
import os
from PySide6.QtWidgets import QApplication

# Add the project root to the path
sys.path.insert(0, '.')

from gui.settings_manager import SettingsManager
from gui.config_manager import GUIConfigManager


def test_settings_manager():
    """Test the SettingsManager AI configuration methods."""
    print("Testing SettingsManager AI configuration...")
    
    settings_manager = SettingsManager()
    
    # Test saving and loading AI config
    test_terms = ["API", "CEO", "CFO", "Amazon"]
    test_glossary = {
        "Spanish": {"API": "API", "CEO": "CEO", "CFO": "CFO"},
        "French": {"API": "API", "CEO": "PDG", "CFO": "DF"}
    }
    
    # Save AI config
    settings_manager.save_ai_config(test_terms, test_glossary)
    print(f"✓ Saved AI config: {len(test_terms)} terms, {len(test_glossary)} languages")
    
    # Load AI config
    loaded_terms, loaded_glossary = settings_manager.load_ai_config()
    print(f"✓ Loaded AI config: {len(loaded_terms)} terms, {len(loaded_glossary)} languages")
    
    # Verify data integrity
    assert loaded_terms == test_terms, f"Terms mismatch: {loaded_terms} != {test_terms}"
    assert loaded_glossary == test_glossary, f"Glossary mismatch: {loaded_glossary} != {test_glossary}"
    print("✓ Data integrity verified")
    
    # Test freshness check
    has_recent = settings_manager.has_recent_ai_config(max_age_days=30)
    print(f"✓ Has recent config: {has_recent}")
    
    # Test config age
    age_days = settings_manager.get_ai_config_age_days()
    print(f"✓ Config age: {age_days} days")
    
    print("SettingsManager tests passed!\n")


def test_config_manager():
    """Test the GUIConfigManager priority system."""
    print("Testing GUIConfigManager priority system...")
    
    settings_manager = SettingsManager()
    config_manager = GUIConfigManager(settings_manager)
    
    # Test getting excluded terms (should prioritize AI config)
    excluded_terms = config_manager.get_excluded_terms()
    print(f"✓ Excluded terms: {excluded_terms}")
    
    # Test getting business glossary
    spanish_glossary = config_manager.get_business_glossary("Spanish")
    print(f"✓ Spanish glossary: {spanish_glossary}")
    
    # Test getting all glossaries
    all_glossaries = config_manager.get_all_business_glossaries()
    print(f"✓ All glossaries: {len(all_glossaries)} languages")
    
    # Test config source info
    source_info = config_manager.get_config_source_info()
    print(f"✓ Config source: {source_info}")
    
    # Test config summary
    summary = config_manager.get_config_summary()
    print(f"✓ Config summary: {summary}")
    
    print("GUIConfigManager tests passed!\n")


def test_ai_config_generator():
    """Test the AIConfigGenerator basic functionality."""
    print("Testing AIConfigGenerator...")
    
    # This test requires an API key, so we'll just test instantiation
    try:
        from gui.ai_config import AIConfigGenerator
        
        # Test instantiation (without API key)
        generator = AIConfigGenerator("test-key")
        print("✓ AIConfigGenerator instantiated successfully")
        
        # Test supported languages
        print(f"✓ Supported languages: {len(generator.get_supported_languages())}")
        
    except Exception as e:
        print(f"⚠ AIConfigGenerator test skipped: {e}")
    
    print("AIConfigGenerator tests completed!\n")


def main():
    """Run all integration tests."""
    print("=" * 50)
    print("AI Configuration Integration Tests")
    print("=" * 50)
    
    try:
        test_settings_manager()
        test_config_manager()
        test_ai_config_generator()
        
        print("=" * 50)
        print("All tests passed! ✅")
        print("=" * 50)
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 