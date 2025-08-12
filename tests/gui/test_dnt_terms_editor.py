"""
Tests for the DNT Terms Editor.
"""

import logging

import pytest
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QWidget

from srt_translator.gui.ui.dnt_terms_editor import DNTTermsEditor

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestDNTTermsEditor:
    """Test class for DNT Terms Editor functionality."""

    def test_editor_creation(self, qapp):
        """Test that the DNT terms editor can be created."""
        editor = DNTTermsEditor()
        assert editor is not None
        assert hasattr(editor, "get_terms")
        assert hasattr(editor, "set_terms")

    def test_set_and_get_terms(self, qapp):
        """Test setting and getting terms."""
        editor = DNTTermsEditor()
        test_terms = ["API", "CEO", "CFO", "Amazon", "Google", "Microsoft"]

        editor.set_terms(test_terms)
        retrieved_terms = editor.get_terms()

        assert retrieved_terms == test_terms

    def test_terms_changed_signal(self, qapp):
        """Test that the terms_changed signal is emitted."""
        editor = DNTTermsEditor()
        received_terms = []

        def on_terms_changed(terms):
            received_terms.append(terms)

        editor.terms_changed.connect(on_terms_changed)

        # Set terms to trigger signal
        test_terms = ["API", "CEO"]
        editor.set_terms(test_terms)

        # Process events to allow signal to be emitted
        qapp.processEvents()

        assert len(received_terms) > 0
        assert received_terms[-1] == test_terms

    def test_empty_terms(self, qapp):
        """Test handling of empty terms list."""
        editor = DNTTermsEditor()

        editor.set_terms([])
        retrieved_terms = editor.get_terms()

        assert retrieved_terms == []

    def test_editor_integration(self, qapp):
        """Test editor integration in a window context."""
        window = QMainWindow()
        window.setWindowTitle("DNT Terms Editor Test")
        window.setGeometry(100, 100, 600, 400)

        # Create central widget
        central_widget = QWidget()
        window.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Create the DNT terms editor
        editor = DNTTermsEditor()
        layout.addWidget(editor)

        # Test terms
        test_terms = ["API", "CEO", "CFO", "Amazon", "Google", "Microsoft"]
        editor.set_terms(test_terms)

        # Verify terms were set
        retrieved_terms = editor.get_terms()
        assert retrieved_terms == test_terms

        # Clean up
        window.close()
