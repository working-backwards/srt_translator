"""
Pytest configuration for GUI tests.
"""

import sys

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    """Create a QApplication instance for the test session."""
    if not QApplication.instance():
        app = QApplication(sys.argv)
        yield app
        app.quit()
    else:
        yield QApplication.instance()


@pytest.fixture
def sample_dnt_terms():
    """Sample DNT terms for testing."""
    return ["API", "CEO", "CFO", "Amazon", "GDPR", "ROI"]


@pytest.fixture
def sample_termbase():
    """Sample termbase for testing."""
    return {
        "Spanish": {"API": "API", "Amazon": "Amazon", "Web Services": "Servicios Web"},
        "French": {"API": "API", "Amazon": "Amazon", "Web Services": "Services Web"},
    }
