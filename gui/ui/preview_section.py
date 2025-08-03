#!/usr/bin/env python3
"""
Preview Section Widget

Shows users a preview of how their AI-generated configuration will affect translations.
Provides before/after comparison to help users understand the impact.
"""

import logging
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QFont, QTextCursor
from PySide6.QtWidgets import (
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class PreviewWorker(QThread):
    """Worker thread for generating translation previews."""

    preview_ready = Signal(dict)  # Emitted when preview is ready
    preview_error = Signal(str)  # Emitted on error

    def __init__(
        self,
        sample_text: str,
        dnt_terms: List[str],
        termbase: Dict[str, Dict[str, str]],
        target_language: str,
    ):
        super().__init__()
        self.sample_text = sample_text
        self.dnt_terms = dnt_terms
        self.termbase = termbase
        self.target_language = target_language

    def run(self):
        """Generate the preview translation."""
        try:
            # Simulate translation with configuration applied
            preview_result = self._generate_preview()
            self.preview_ready.emit(preview_result)
        except Exception as e:
            self.preview_error.emit(str(e))

    def _generate_preview(self) -> Dict[str, str]:
        """Generate preview translation with configuration applied."""
        # This is a simplified preview - in a real implementation,
        # you might call the actual translation API with a small sample

        # For now, we'll simulate the effect of DNT terms and termbase
        original_text = self.sample_text
        configured_text = self._apply_configuration(original_text)

        return {
            "original": original_text,
            "configured": configured_text,
            "dnt_terms_applied": len(
                [
                    term
                    for term in self.dnt_terms
                    if term.lower() in original_text.lower()
                ]
            ),
            "termbase_terms_applied": self._count_termbase_terms_applied(original_text),
        }

    def _apply_configuration(self, text: str) -> str:
        """Apply DNT terms and termbase to the text."""
        # This simulates how the configuration would affect translation

        result = text
        processed_positions = set()  # Track which positions have been processed

        # Apply DNT terms first (mark them to stay in English)
        for term in self.dnt_terms:
            if term.lower() in result.lower():
                # Mark DNT terms with [brackets] to show they won't be translated
                result, processed_positions = self._highlight_term_with_tracking(
                    result, term, "[", "]", processed_positions
                )

        # Apply termbase terms (show translations) - but only if not already processed
        if self.target_language in self.termbase:
            termbase = self.termbase[self.target_language]
            for english_term, translation in termbase.items():
                if english_term.lower() in result.lower():
                    # Show termbase translations with {curly braces}
                    result, processed_positions = self._highlight_term_with_tracking(
                        result, english_term, "{", "}", processed_positions
                    )

        return result

    def _highlight_term_with_tracking(
        self, text: str, term: str, prefix: str, suffix: str, processed_positions: set
    ) -> tuple:
        """Highlight a term in the text with prefix and suffix, tracking processed positions."""
        import re

        def replace_func(match):
            start_pos = match.start()
            end_pos = match.end()

            # Check if this position has already been processed
            for pos in range(start_pos, end_pos):
                if pos in processed_positions:
                    return match.group(0)  # Return original, don't modify

            # Mark this position as processed
            for pos in range(start_pos, end_pos):
                processed_positions.add(pos)

            original = match.group(0)
            return f"{prefix}{original}{suffix}"

        # Use regex to find the term (case-insensitive) and replace it
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        result = pattern.sub(replace_func, text)
        return result, processed_positions

    def _highlight_term(self, text: str, term: str, prefix: str, suffix: str) -> str:
        """Highlight a term in the text with prefix and suffix."""
        # Case-insensitive replacement while preserving original case
        import re

        def replace_func(match):
            original = match.group(0)
            return f"{prefix}{original}{suffix}"

        # Use regex to find the term (case-insensitive) and replace it
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        return pattern.sub(replace_func, text)

    def _count_termbase_terms_applied(self, text: str) -> int:
        """Count how many termbase terms would be applied."""
        if self.target_language not in self.termbase:
            return 0

        termbase = self.termbase[self.target_language]
        count = 0
        for english_term in termbase.keys():
            if english_term.lower() in text.lower():
                count += 1

        return count


class PreviewSection(QWidget):
    """Widget for showing translation preview with configuration."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.preview_worker = None
        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel("Translation Preview")
        title_label.setObjectName("sectionTitle")
        self.preview_btn = QPushButton("Generate Preview")
        self.preview_btn.setObjectName("primaryButton")
        self.preview_btn.setEnabled(False)

        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.preview_btn)
        layout.addLayout(header_layout)

        # Progress bar (initially hidden)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        layout.addWidget(self.progress_bar)

        # Preview content area
        self.preview_content = QFrame()
        self.preview_content.setVisible(False)
        preview_layout = QVBoxLayout(self.preview_content)

        # Sample text selection
        sample_group = QGroupBox("Sample Text")
        sample_layout = QVBoxLayout(sample_group)

        self.sample_text_edit = QTextEdit()
        self.sample_text_edit.setMaximumHeight(100)
        self.sample_text_edit.setPlaceholderText(
            "Enter sample text to preview translation with your configuration..."
        )
        sample_layout.addWidget(self.sample_text_edit)

        # Sample text buttons
        sample_buttons_layout = QHBoxLayout()
        self.load_sample_btn = QPushButton("Load Sample")
        self.load_sample_btn.setObjectName("secondaryButton")
        self.clear_sample_btn = QPushButton("Clear")
        self.clear_sample_btn.setObjectName("secondaryButton")

        sample_buttons_layout.addWidget(self.load_sample_btn)
        sample_buttons_layout.addWidget(self.clear_sample_btn)
        sample_buttons_layout.addStretch()
        sample_layout.addLayout(sample_buttons_layout)

        preview_layout.addWidget(sample_group)

        # Preview results
        results_group = QGroupBox("Preview Results")
        results_layout = QVBoxLayout(results_group)

        # Splitter for before/after comparison
        self.splitter = QSplitter(Qt.Horizontal)

        # Original text
        original_frame = QFrame()
        original_layout = QVBoxLayout(original_frame)
        original_label = QLabel("Original Text:")
        original_label.setObjectName("subHeaderLabel")
        self.original_text = QTextEdit()
        self.original_text.setReadOnly(True)
        self.original_text.setMaximumHeight(200)
        original_layout.addWidget(original_label)
        original_layout.addWidget(self.original_text)

        # Configured text
        configured_frame = QFrame()
        configured_layout = QVBoxLayout(configured_frame)
        configured_label = QLabel("With Configuration Applied:")
        configured_label.setObjectName("subHeaderLabel")
        self.configured_text = QTextEdit()
        self.configured_text.setReadOnly(True)
        self.configured_text.setMaximumHeight(200)
        configured_layout.addWidget(configured_label)
        configured_layout.addWidget(self.configured_text)

        self.splitter.addWidget(original_frame)
        self.splitter.addWidget(configured_frame)
        self.splitter.setSizes([300, 300])

        results_layout.addWidget(self.splitter)

        # Statistics
        stats_layout = QHBoxLayout()
        self.stats_label = QLabel("Configuration Impact: ")
        self.stats_label.setObjectName("secondaryText")
        stats_layout.addWidget(self.stats_label)
        stats_layout.addStretch()
        results_layout.addLayout(stats_layout)

        preview_layout.addWidget(results_group)

        layout.addWidget(self.preview_content)

        # Load default sample text
        self._load_default_sample()

    def connect_signals(self):
        """Connect widget signals."""
        self.preview_btn.clicked.connect(self.generate_preview)
        self.load_sample_btn.clicked.connect(self.load_sample_text)
        self.clear_sample_btn.clicked.connect(self.clear_sample_text)
        self.sample_text_edit.textChanged.connect(self.on_sample_text_changed)

    def set_configuration(
        self, dnt_terms: List[str], termbase: Dict[str, Dict[str, str]]
    ):
        """Set the configuration to preview."""
        self.dnt_terms = dnt_terms
        self.termbase = termbase
        self.preview_btn.setEnabled(True)

    def on_sample_text_changed(self):
        """Handle sample text changes."""
        text = self.sample_text_edit.toPlainText().strip()
        self.preview_btn.setEnabled(bool(text) and hasattr(self, "dnt_terms"))

    def generate_preview(self):
        """Generate translation preview."""
        sample_text = self.sample_text_edit.toPlainText().strip()
        if not sample_text:
            QMessageBox.warning(
                self, "No Sample Text", "Please enter some sample text to preview."
            )
            return

        if not hasattr(self, "dnt_terms"):
            QMessageBox.warning(
                self,
                "No Configuration",
                "Please generate or load a configuration first.",
            )
            return

        # Show progress
        self.progress_bar.setVisible(True)
        self.preview_btn.setEnabled(False)

        # Start preview worker
        self.preview_worker = PreviewWorker(
            sample_text,
            self.dnt_terms,
            self.termbase,
            "Spanish",  # Default target language for preview
        )
        self.preview_worker.preview_ready.connect(self.on_preview_ready)
        self.preview_worker.preview_error.connect(self.on_preview_error)
        self.preview_worker.finished.connect(self.on_preview_finished)
        self.preview_worker.start()

    def on_preview_ready(self, result: Dict[str, str]):
        """Handle preview completion."""
        # Show preview content
        self.preview_content.setVisible(True)

        # Update text areas
        self.original_text.setText(result["original"])
        self.configured_text.setText(result["configured"])

        # Update statistics
        dnt_count = result["dnt_terms_applied"]
        termbase_count = result["termbase_terms_applied"]

        # Create more detailed statistics
        total_terms = dnt_count + termbase_count
        if total_terms > 0:
            stats_text = f"Configuration Impact: {dnt_count} DNT terms (stay in English), {termbase_count} termbase terms (will be translated)"
        else:
            stats_text = "Configuration Impact: No terms from your configuration found in this sample text"

        self.stats_label.setText(stats_text)

    def on_preview_error(self, error_message: str):
        """Handle preview error."""
        QMessageBox.warning(
            self, "Preview Error", f"Failed to generate preview: {error_message}"
        )

    def on_preview_finished(self):
        """Handle preview worker completion."""
        self.progress_bar.setVisible(False)
        self.preview_btn.setEnabled(True)

    def load_sample_text(self):
        """Load sample text for preview."""
        sample_texts = [
            "Welcome to our business course. The CEO will discuss the company's API integration with Amazon Web Services. The CFO has prepared the quarterly report.",
            "In this technical module, we'll explore UI/UX design principles and GDPR compliance requirements. Our IT team uses modern development practices.",
            "The marketing team is working on the ROI analysis for our new product launch. We need to coordinate with the sales department and external vendors.",
        ]

        # Use the first sample text
        self.sample_text_edit.setText(sample_texts[0])

    def clear_sample_text(self):
        """Clear the sample text."""
        self.sample_text_edit.clear()
        self.preview_content.setVisible(False)

    def _load_default_sample(self):
        """Load default sample text."""
        default_sample = "Welcome to our business course. The CEO will discuss the company's API integration with Amazon Web Services. The CFO has prepared the quarterly report."
        self.sample_text_edit.setText(default_sample)
