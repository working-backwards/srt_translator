#!/usr/bin/env python3
"""
Validation Section Widget

Displays validation results and quality metrics for AI-generated configuration.
Shows confidence scores, issues, and suggestions for improvement.
"""

import logging
from typing import Dict, List, Optional

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QFont, QPalette
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

from ..validation import ConfigurationValidator


class ValidationWorker(QThread):
    """Worker thread for running validation checks."""

    validation_complete = Signal(dict)
    validation_error = Signal(str)

    def __init__(
        self,
        dnt_terms: List[str],
        business_glossary: Dict[str, Dict[str, str]],
        source_files: List[str],
    ):
        super().__init__()
        self.dnt_terms = dnt_terms
        self.business_glossary = business_glossary
        self.source_files = source_files

    def run(self):
        """Run validation checks."""
        try:
            validator = ConfigurationValidator()
            results = validator.get_validation_summary(
                self.dnt_terms, self.business_glossary, self.source_files
            )
            self.validation_complete.emit(results)
        except Exception as e:
            self.validation_error.emit(str(e))


class ValidationSection(QWidget):
    """Widget for displaying configuration validation results."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.validation_worker = None
        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel("Configuration Validation")
        title_label.setObjectName("sectionTitle")
        self.validate_btn = QPushButton("Run Validation")
        self.validate_btn.setObjectName("primaryButton")
        self.validate_btn.setEnabled(False)

        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.validate_btn)
        layout.addLayout(header_layout)

        # Progress bar (initially hidden)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        layout.addWidget(self.progress_bar)

        # Validation content area
        self.validation_content = QFrame()
        self.validation_content.setVisible(False)
        validation_layout = QVBoxLayout(self.validation_content)

        # Overall status
        self.status_group = QGroupBox("Overall Status")
        status_layout = QVBoxLayout(self.status_group)

        self.overall_status_label = QLabel("Configuration Status: ")
        self.overall_status_label.setObjectName("subHeaderLabel")
        status_layout.addWidget(self.overall_status_label)

        self.confidence_layout = QHBoxLayout()
        self.confidence_label = QLabel("Confidence Score:")
        self.confidence_bar = QProgressBar()
        self.confidence_bar.setRange(0, 100)
        self.confidence_bar.setFormat("%.0f%%")

        self.confidence_layout.addWidget(self.confidence_label)
        self.confidence_layout.addWidget(self.confidence_bar)
        self.confidence_layout.addStretch()
        status_layout.addLayout(self.confidence_layout)

        validation_layout.addWidget(self.status_group)

        # Statistics
        self.stats_group = QGroupBox("Configuration Statistics")
        stats_layout = QVBoxLayout(self.stats_group)

        self.stats_text = QTextEdit()
        self.stats_text.setMaximumHeight(100)
        self.stats_text.setReadOnly(True)
        stats_layout.addWidget(self.stats_text)

        validation_layout.addWidget(self.stats_group)

        # Issues and suggestions
        issues_group = QGroupBox("Issues & Suggestions")
        issues_layout = QVBoxLayout(issues_group)

        # Splitter for issues and suggestions
        self.issues_splitter = QSplitter(Qt.Horizontal)

        # Issues
        issues_frame = QFrame()
        issues_inner_layout = QVBoxLayout(issues_frame)
        issues_label = QLabel("Issues Found:")
        issues_label.setObjectName("subHeaderLabel")
        self.issues_text = QTextEdit()
        self.issues_text.setReadOnly(True)
        self.issues_text.setMaximumHeight(200)

        issues_inner_layout.addWidget(issues_label)
        issues_inner_layout.addWidget(self.issues_text)

        # Suggestions
        suggestions_frame = QFrame()
        suggestions_inner_layout = QVBoxLayout(suggestions_frame)
        suggestions_label = QLabel("Suggestions:")
        suggestions_label.setObjectName("subHeaderLabel")
        self.suggestions_text = QTextEdit()
        self.suggestions_text.setReadOnly(True)
        self.suggestions_text.setMaximumHeight(200)

        suggestions_inner_layout.addWidget(suggestions_label)
        suggestions_inner_layout.addWidget(self.suggestions_text)

        self.issues_splitter.addWidget(issues_frame)
        self.issues_splitter.addWidget(suggestions_frame)
        self.issues_splitter.setSizes([300, 300])

        issues_layout.addWidget(self.issues_splitter)
        validation_layout.addWidget(issues_group)

        layout.addWidget(self.validation_content)

    def connect_signals(self):
        """Connect widget signals."""
        self.validate_btn.clicked.connect(self.run_validation)

    def set_configuration(
        self, dnt_terms: List[str], business_glossary: Dict[str, Dict[str, str]]
    ):
        """Set the configuration to validate."""
        self.dnt_terms = dnt_terms
        self.business_glossary = business_glossary
        self.validate_btn.setEnabled(True)

    def set_source_files(self, source_files: List[str]):
        """Set the source files for validation."""
        self.source_files = source_files

    def run_validation(self):
        """Run configuration validation."""
        if not hasattr(self, "dnt_terms") or not hasattr(self, "source_files"):
            QMessageBox.warning(
                self,
                "No Configuration",
                "Please generate or load a configuration first.",
            )
            return

        # Show progress
        self.progress_bar.setVisible(True)
        self.validate_btn.setEnabled(False)

        # Start validation worker
        self.validation_worker = ValidationWorker(
            self.dnt_terms, self.business_glossary, self.source_files
        )
        self.validation_worker.validation_complete.connect(self.on_validation_complete)
        self.validation_worker.validation_error.connect(self.on_validation_error)
        self.validation_worker.finished.connect(self.on_validation_finished)
        self.validation_worker.start()

    def on_validation_complete(self, results: Dict[str, any]):
        """Handle validation completion."""
        # Show validation content
        self.validation_content.setVisible(True)

        # Update overall status
        if results["overall_valid"]:
            self.overall_status_label.setText("Configuration Status: ✅ Valid")
            self.overall_status_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.overall_status_label.setText("Configuration Status: ⚠️ Issues Found")
            self.overall_status_label.setStyleSheet("color: orange; font-weight: bold;")

        # Update confidence bar
        confidence_percent = int(results["overall_confidence"] * 100)
        self.confidence_bar.setValue(confidence_percent)

        # Color code confidence bar
        if confidence_percent >= 80:
            self.confidence_bar.setStyleSheet(
                "QProgressBar::chunk { background-color: green; }"
            )
        elif confidence_percent >= 60:
            self.confidence_bar.setStyleSheet(
                "QProgressBar::chunk { background-color: orange; }"
            )
        else:
            self.confidence_bar.setStyleSheet(
                "QProgressBar::chunk { background-color: red; }"
            )

        # Update statistics
        stats = results["statistics"]
        stats_text = f"""Configuration Statistics:
• DNT Terms: {stats['dnt_terms_count']}
• Glossary Languages: {stats['glossary_languages']}
• Total Glossary Terms: {stats['total_glossary_terms']}
• Source Files: {stats['source_files_count']}

Validation Scores:
• DNT Terms: {results['dnt_terms']['score']:.1%} ({results['dnt_terms']['confidence']:.1%} confidence)
• Business Glossary: {results['business_glossary']['score']:.1%} ({results['business_glossary']['confidence']:.1%} confidence)
• Overall Quality: {results['quality']['score']:.1%} ({results['quality']['confidence']:.1%} confidence)"""

        self.stats_text.setText(stats_text)

        # Update issues
        all_issues = []
        if results["dnt_terms"]["issues"]:
            all_issues.extend(
                [
                    f"DNT Terms: {issue}"
                    for issue in results["dnt_terms"]["issues"]
                ]
            )
        if results["business_glossary"]["issues"]:
            all_issues.extend(
                [
                    f"Business Glossary: {issue}"
                    for issue in results["business_glossary"]["issues"]
                ]
            )
        if results["quality"]["issues"]:
            all_issues.extend(
                [f"Quality: {issue}" for issue in results["quality"]["issues"]]
            )

        if all_issues:
            self.issues_text.setText("\n\n".join(all_issues))
        else:
            self.issues_text.setText("✅ No issues found!")

        # Update suggestions
        all_suggestions = []
        if results["dnt_terms"]["suggestions"]:
            all_suggestions.extend(
                [
                    f"• {suggestion}"
                    for suggestion in results["dnt_terms"]["suggestions"]
                ]
            )
        if results["business_glossary"]["suggestions"]:
            all_suggestions.extend(
                [
                    f"• {suggestion}"
                    for suggestion in results["business_glossary"]["suggestions"]
                ]
            )
        if results["quality"]["suggestions"]:
            all_suggestions.extend(
                [f"• {suggestion}" for suggestion in results["quality"]["suggestions"]]
            )

        if all_suggestions:
            self.suggestions_text.setText("\n".join(all_suggestions))
        else:
            self.suggestions_text.setText("✅ Configuration looks good!")

    def on_validation_error(self, error_message: str):
        """Handle validation error."""
        QMessageBox.warning(
            self, "Validation Error", f"Failed to run validation: {error_message}"
        )

    def on_validation_finished(self):
        """Handle validation worker completion."""
        self.progress_bar.setVisible(False)
        self.validate_btn.setEnabled(True)
