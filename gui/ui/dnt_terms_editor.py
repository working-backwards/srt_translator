#!/usr/bin/env python3
"""
DNT Terms Editor for the SRT Translator GUI.
"""

import logging
from typing import List

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class DNTTermsEditor(QWidget):
    """Widget for editing DNT terms that should remain in English."""

    # Signal emitted when terms are modified
    terms_changed = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.terms_list = []

        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel("DNT terms (will remain in original language)")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(10)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        # Terms count label
        self.count_label = QLabel("0 terms")
        self.count_label.setStyleSheet("color: #666; font-size: 9pt;")
        header_layout.addWidget(self.count_label)

        layout.addLayout(header_layout)

        # Terms list
        self.terms_list_widget = QListWidget()
        self.terms_list_widget.setMinimumHeight(150)
        self.terms_list_widget.setMaximumHeight(200)
        self.terms_list_widget.setAlternatingRowColors(True)
        self.terms_list_widget.setSelectionMode(
            QListWidget.SelectionMode.SingleSelection
        )
        layout.addWidget(self.terms_list_widget)

        # Buttons frame
        buttons_frame = QFrame()
        buttons_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        buttons_layout = QHBoxLayout(buttons_frame)
        buttons_layout.setContentsMargins(10, 10, 10, 10)
        buttons_layout.setSpacing(8)

        # Add button
        self.add_button = QPushButton("Add Term")
        self.add_button.setMinimumWidth(80)
        self.add_button.setStyleSheet(
            """
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """
        )
        buttons_layout.addWidget(self.add_button)

        # Edit button
        self.edit_button = QPushButton("Edit Selected")
        self.edit_button.setMinimumWidth(100)
        self.edit_button.setEnabled(False)
        self.edit_button.setStyleSheet(
            """
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
                color: #757575;
            }
        """
        )
        buttons_layout.addWidget(self.edit_button)

        # Remove button
        self.remove_button = QPushButton("Remove Selected")
        self.remove_button.setMinimumWidth(120)
        self.remove_button.setEnabled(False)
        self.remove_button.setStyleSheet(
            """
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:pressed {
                background-color: #c62828;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
                color: #757575;
            }
        """
        )
        buttons_layout.addWidget(self.remove_button)

        buttons_layout.addStretch()

        # Clear all button
        self.clear_button = QPushButton("Clear All")
        self.clear_button.setMinimumWidth(80)
        self.clear_button.setEnabled(False)
        self.clear_button.setStyleSheet(
            """
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
            QPushButton:pressed {
                background-color: #EF6C00;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
                color: #757575;
            }
        """
        )
        buttons_layout.addWidget(self.clear_button)

        layout.addWidget(buttons_frame)

        # Set size policy
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

    def connect_signals(self):
        """Connect widget signals."""
        self.add_button.clicked.connect(self.add_term)
        self.edit_button.clicked.connect(self.edit_selected_term)
        self.remove_button.clicked.connect(self.remove_selected_term)
        self.clear_button.clicked.connect(self.clear_all_terms)
        self.terms_list_widget.itemSelectionChanged.connect(self.update_button_states)

    def set_terms(self, terms: List[str]):
        """Set the list of DNT terms."""
        self.terms_list = terms.copy()
        self.refresh_display()
        self.terms_changed.emit(self.terms_list)

    def get_terms(self) -> List[str]:
        """Get the current list of DNT terms."""
        return self.terms_list.copy()

    def refresh_display(self):
        """Refresh the display of terms in the list widget."""
        self.terms_list_widget.clear()

        for term in sorted(self.terms_list):
            item = QListWidgetItem(term)
            item.setFlags(
                item.flags() | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
            )
            self.terms_list_widget.addItem(item)

        self.update_count_label()
        self.update_button_states()

    def update_count_label(self):
        """Update the terms count label."""
        count = len(self.terms_list)
        if count == 1:
            self.count_label.setText("1 term")
        else:
            self.count_label.setText(f"{count} terms")

    def update_button_states(self):
        """Update the enabled state of buttons based on current selection."""
        has_selection = len(self.terms_list_widget.selectedItems()) > 0
        has_terms = len(self.terms_list) > 0

        self.edit_button.setEnabled(has_selection)
        self.remove_button.setEnabled(has_selection)
        self.clear_button.setEnabled(has_terms)

    def add_term(self):
        """Add a new term to the list."""
        term, ok = QInputDialog.getText(
            self,
            "Add DNT Term",
            "Enter a term that should remain in English:",
            text="",
        )

        if ok and term.strip():
            term = term.strip()

            # Validate term
            if not self._validate_term(term):
                return

            # Check for duplicates
            if term.lower() in [t.lower() for t in self.terms_list]:
                QMessageBox.warning(
                    self, "Duplicate Term", f"The term '{term}' is already in the list."
                )
                return

            # Add term
            self.terms_list.append(term)
            self.refresh_display()
            self.terms_changed.emit(self.terms_list)

            self.logger.debug(f"Added DNT term: {term}")

    def edit_selected_term(self):
        """Edit the currently selected term."""
        selected_items = self.terms_list_widget.selectedItems()
        if not selected_items:
            return

        old_term = selected_items[0].text()
        new_term, ok = QInputDialog.getText(
            self, "Edit DNT Term", "Edit the term:", text=old_term
        )

        if ok and new_term.strip():
            new_term = new_term.strip()

            # Validate term
            if not self._validate_term(new_term):
                return

            # Check for duplicates (excluding the current term)
            other_terms = [t for t in self.terms_list if t != old_term]
            if new_term.lower() in [t.lower() for t in other_terms]:
                QMessageBox.warning(
                    self,
                    "Duplicate Term",
                    f"The term '{new_term}' is already in the list.",
                )
                return

            # Update term
            index = self.terms_list.index(old_term)
            self.terms_list[index] = new_term
            self.refresh_display()
            self.terms_changed.emit(self.terms_list)

            self.logger.debug(f"Edited DNT term: '{old_term}' -> '{new_term}'")

    def remove_selected_term(self):
        """Remove the currently selected term."""
        selected_items = self.terms_list_widget.selectedItems()
        if not selected_items:
            return

        term = selected_items[0].text()

        reply = QMessageBox.question(
            self,
            "Remove Term",
            f"Are you sure you want to remove '{term}' from the DNT terms?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.terms_list.remove(term)
            self.refresh_display()
            self.terms_changed.emit(self.terms_list)

            self.logger.debug(f"Removed DNT term: {term}")

    def clear_all_terms(self):
        """Clear all terms from the list."""
        if not self.terms_list:
            return

        reply = QMessageBox.question(
            self,
            "Clear All Terms",
            f"Are you sure you want to remove all {len(self.terms_list)} DNT terms?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.terms_list.clear()
            self.refresh_display()
            self.terms_changed.emit(self.terms_list)

            self.logger.debug("Cleared all DNT terms")

    def _validate_term(self, term: str) -> bool:
        """Validate a term before adding/editing."""
        if not term:
            QMessageBox.warning(self, "Invalid Term", "Term cannot be empty.")
            return False

        if len(term) > 50:
            QMessageBox.warning(
                self,
                "Invalid Term",
                "Term is too long. Please use 50 characters or less.",
            )
            return False

        # Check for invalid characters
        invalid_chars = ["<", ">", ":", '"', "|", "?", "*", "/", "\\"]
        for char in invalid_chars:
            if char in term:
                QMessageBox.warning(
                    self,
                    "Invalid Term",
                    f"Term contains invalid character: '{char}'\n"
                    f"Please use only letters, numbers, spaces, and common punctuation.",
                )
                return False

        return True

    def is_modified(self, original_terms: List[str]) -> bool:
        """Check if the terms have been modified from the original list."""
        if len(self.terms_list) != len(original_terms):
            return True

        return set(self.terms_list) != set(original_terms)
