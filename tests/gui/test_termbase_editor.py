"""
Tests for the Termbase Editor.
"""

import logging

import pytest
from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QWidget

from srt_translator.gui.ui.termbase_editor import TermbaseEditor

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestTermbaseEditor:
    """Test class for Termbase Editor functionality."""

    def test_editor_creation(self, qapp):
        """Test that the termbase editor can be created."""
        editor = TermbaseEditor()
        assert editor is not None
        assert hasattr(editor, "get_termbase")
        assert hasattr(editor, "set_termbase")

    def test_set_and_get_termbase(self, qapp, sample_termbase):
        """Test setting and getting termbase."""
        editor = TermbaseEditor()

        editor.set_termbase(sample_termbase)
        retrieved_termbase = editor.get_termbase()

        assert retrieved_termbase == sample_termbase

    def test_empty_termbase(self, qapp):
        """Test handling of empty termbase."""
        editor = TermbaseEditor()

        editor.set_termbase({})
        retrieved_termbase = editor.get_termbase()

        assert retrieved_termbase == {}

    def test_termbase_changed_signal(self, qapp, sample_termbase):
        """Test that the termbase_changed signal is emitted."""
        editor = TermbaseEditor()
        received_termbase = []

        def on_termbase_changed(termbase):
            received_termbase.append(termbase)

        editor.termbase_changed.connect(on_termbase_changed)

        # Set termbase to trigger signal
        editor.set_termbase(sample_termbase)

        # Process events to allow signal to be emitted
        qapp.processEvents()

        assert len(received_termbase) > 0
        assert received_termbase[-1] == sample_termbase

    def test_editor_integration(self, qapp, sample_termbase):
        """Test editor integration in a window context."""
        window = QMainWindow()
        window.setWindowTitle("Termbase Editor Test")
        window.setGeometry(100, 100, 800, 600)

        # Create central widget
        central_widget = QWidget()
        window.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Create the termbase editor
        editor = TermbaseEditor()
        layout.addWidget(editor)

        # Test termbase
        editor.set_termbase(sample_termbase)

        # Verify termbase was set
        retrieved_termbase = editor.get_termbase()
        assert retrieved_termbase == sample_termbase

        # Clean up
        window.close()
