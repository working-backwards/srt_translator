"""
Test script for AI Configuration System
"""

import os
import sys
import logging

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui.ai_config import AIConfigGenerator
from gui.settings_manager import SettingsManager
from gui.config_manager import GUIConfigManager

# Set up logging
logging.basicConfig(level=logging.INFO)

def test_ai_config_system():
    """Test the AI configuration system"""
    print("Testing AI Configuration System...")
    
    # Test 1: Settings Manager
    print("\n1. Testing Settings Manager...")
    settings_manager = SettingsManager()
    
    # Test saving and loading AI config
    test_excluded_terms = ["API", "CEO", "CFO", "Amazon"]
    test_business_glossary = {
        "Spanish": {
            "operating plan": "plan operativo",
            "business review": "revisión de negocio"
        },
        "French": {
            "operating plan": "plan opérationnel",
            "business review": "revue d'affaires"
        }
    }
    
    settings_manager.save_ai_config(test_excluded_terms, test_business_glossary)
    loaded_terms, loaded_glossary = settings_manager.load_ai_config()
    
    print(f"Saved excluded terms: {test_excluded_terms}")
    print(f"Loaded excluded terms: {loaded_terms}")
    print(f"Terms match: {test_excluded_terms == loaded_terms}")
    
    print(f"Saved glossary languages: {list(test_business_glossary.keys())}")
    print(f"Loaded glossary languages: {list(loaded_glossary.keys())}")
    print(f"Glossary match: {test_business_glossary == loaded_glossary}")
    
    # Test 2: Config Manager
    print("\n2. Testing Config Manager...")
    config_manager = GUIConfigManager(settings_manager)
    
    # Test getting excluded terms (should return AI-generated ones)
    excluded_terms = config_manager.get_excluded_terms()
    print(f"Config manager excluded terms: {excluded_terms}")
    
    # Test getting business glossary
    spanish_glossary = config_manager.get_business_glossary("Spanish")
    print(f"Spanish glossary: {spanish_glossary}")
    
    # Test config summary
    summary = config_manager.get_config_summary()
    print(f"Config summary: {summary}")
    
    # Test 3: AI Config Generator (without API key)
    print("\n3. Testing AI Config Generator structure...")
    try:
        # This should fail without a valid API key, but we can test the structure
        ai_generator = AIConfigGenerator("test-key")
        print("AI Config Generator created successfully")
        print(f"Max content length: {ai_generator.MAX_CONTENT_LENGTH}")
        print(f"Supported languages: {len(ai_generator.SUPPORTED_LANGUAGES)}")
    except Exception as e:
        print(f"AI Config Generator test (expected error): {e}")
    
    print("\nAI Configuration System test completed!")

if __name__ == "__main__":
    test_ai_config_system() 