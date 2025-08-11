import logging
import os
import sys

import pytest

#!/usr/bin/env python3
"""
Pytest configuration for SRT Translator tests
"""


# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Configure logging for tests

logging.basicConfig(level=logging.WARNING)  # Reduce noise during tests


@pytest.fixture
def sample_dnt_terms():
    """Sample DNT terms for testing"""
    return ["API", "CEO", "CFO", "Amazon", "GDPR", "ROI"]


@pytest.fixture
def sample_termbase():
    """Sample termbase for testing"""
    return {
        "Spanish": {"API": "API", "Amazon": "Amazon", "Web Services": "Servicios Web"},
        "French": {"API": "API", "Amazon": "Amazon", "Web Services": "Services Web"},
    }
