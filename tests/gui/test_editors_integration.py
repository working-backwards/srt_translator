"""
Tests for Editors Integration.
"""

import logging

from PySide6.QtWidgets import (
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from srt_translator.gui.ui.dnt_terms_editor import DNTTermsEditor
from srt_translator.gui.ui.termbase_editor import TermbaseEditor

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestEditorsIntegration:
    """Test class for Editors Integration functionality."""

    def test_editors_creation(self, qapp):
        """Test that both editors can be created together."""
        dnt_editor = DNTTermsEditor()
        termbase_editor = TermbaseEditor()

        assert dnt_editor is not None
        assert termbase_editor is not None

    def test_editors_integration_window(self, qapp, sample_dnt_terms, sample_termbase):
        """Test that both editors work together in a window."""
        window = QMainWindow()
        window.setWindowTitle("Editors Integration Test")
        window.setGeometry(100, 100, 1000, 700)

        # Create central widget
        central_widget = QWidget()
        window.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Create both editors
        dnt_editor = DNTTermsEditor()
        termbase_editor = TermbaseEditor()

        # Add editors to layout
        layout.addWidget(dnt_editor)
        layout.addWidget(termbase_editor)

        # Test data
        dnt_editor.set_terms(sample_dnt_terms)
        termbase_editor.set_termbase(sample_termbase)

        # Verify data was set
        retrieved_dnt_terms = dnt_editor.get_terms()
        retrieved_termbase = termbase_editor.get_termbase()

        assert retrieved_dnt_terms == sample_dnt_terms
        assert retrieved_termbase == sample_termbase

        # Clean up
        window.close()

    def test_editors_signals(self, qapp, sample_dnt_terms, sample_termbase):
        """Test that both editors emit signals correctly."""
        dnt_editor = DNTTermsEditor()
        termbase_editor = TermbaseEditor()

        dnt_received = []
        termbase_received = []

        def on_dnt_changed(terms):
            dnt_received.append(terms)

        def on_termbase_changed(termbase):
            termbase_received.append(termbase)

        dnt_editor.terms_changed.connect(on_dnt_changed)
        termbase_editor.termbase_changed.connect(on_termbase_changed)

        # Trigger signals
        dnt_editor.set_terms(sample_dnt_terms)
        termbase_editor.set_termbase(sample_termbase)

        # Process events
        qapp.processEvents()

        assert len(dnt_received) > 0
        assert len(termbase_received) > 0
        assert dnt_received[-1] == sample_dnt_terms
        assert termbase_received[-1] == sample_termbase

    def test_editors_data_consistency(self, qapp):
        """Test that editors maintain data consistency."""
        dnt_editor = DNTTermsEditor()
        termbase_editor = TermbaseEditor()

        # Set initial data
        initial_dnt = ["API", "CEO"]
        initial_termbase = {"Spanish": {"API": "API"}}

        dnt_editor.set_terms(initial_dnt)
        termbase_editor.set_termbase(initial_termbase)

        # Verify initial state
        assert dnt_editor.get_terms() == initial_dnt
        assert termbase_editor.get_termbase() == initial_termbase

        # Change data
        new_dnt = ["API", "CEO", "CFO"]
        new_termbase = {"Spanish": {"API": "API", "CEO": "CEO"}}

        dnt_editor.set_terms(new_dnt)
        termbase_editor.set_termbase(new_termbase)

        # Verify new state
        assert dnt_editor.get_terms() == new_dnt
        assert termbase_editor.get_termbase() == new_termbase
