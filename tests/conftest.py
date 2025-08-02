"""
Pytest configuration for SRT Translator tests
"""
import os
import sys
import pytest

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Configure logging for tests
import logging
logging.basicConfig(level=logging.WARNING)  # Reduce noise during tests

@pytest.fixture
def sample_excluded_terms():
    """Sample excluded terms for testing"""
    return ["API", "CEO", "CFO", "Amazon", "GDPR", "ROI"]

@pytest.fixture
def sample_business_glossary():
    """Sample business glossary for testing"""
    return {
        "Spanish": {
            "API": "API",
            "Amazon": "Amazon",
            "Web Services": "Servicios Web"
        },
        "French": {
            "API": "API",
            "Amazon": "Amazon",
            "Web Services": "Services Web"
        }
    } 