#!/usr/bin/env python3
"""
Business Glossary Editor Widget

Provides a user interface for editing business glossary entries across multiple languages.
Allows adding, editing, and removing terms and their translations.
"""

import logging
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class BusinessGlossaryEditor(QWidget):
    """Widget for editing business glossary entries across multiple languages.

    The business glossary contains language-specific translations of English terms.
    Each language has its own set of translations for the same English terms.
    """

    glossary_changed = Signal(dict)  # Emitted when glossary is modified

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.glossary = {}  # {language: {english_term: translation}}
        self.languages = []
        self._updating_table = False  # Flag to prevent signal loops
        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Header
        header_layout = QHBoxLayout()
        self.title_label = QLabel("Termbase Editor")
        self.title_label.setObjectName("sectionTitle")
        self.count_label = QLabel("0 terms")
        self.count_label.setObjectName("secondaryText")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.count_label)
        layout.addLayout(header_layout)

        # Buttons
        button_layout = QHBoxLayout()
        self.add_term_btn = QPushButton("Add Term")
        self.add_term_btn.setObjectName("primaryButton")
        self.edit_term_btn = QPushButton("Edit Term")
        self.edit_term_btn.setObjectName("secondaryButton")
        self.remove_term_btn = QPushButton("Remove Term")
        self.remove_term_btn.setObjectName("dangerButton")
        self.clear_btn = QPushButton("Clear All")
        self.clear_btn.setObjectName("dangerButton")

        button_layout.addWidget(self.add_term_btn)
        button_layout.addWidget(self.edit_term_btn)
        button_layout.addWidget(self.remove_term_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.clear_btn)
        layout.addLayout(button_layout)

        # Table
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        # Initialize table
        self.refresh_table()
        self.update_button_states()

    def connect_signals(self):
        """Connect widget signals."""
        self.add_term_btn.clicked.connect(self.add_term)
        self.edit_term_btn.clicked.connect(self.edit_selected_term)
        self.remove_term_btn.clicked.connect(self.remove_selected_term)
        self.clear_btn.clicked.connect(self.clear_all_terms)
        self.table.itemSelectionChanged.connect(self.update_button_states)
        self.table.itemChanged.connect(self.on_table_item_changed)

    def set_glossary(self, glossary: Dict[str, Dict[str, str]]):
        """Set the business glossary data."""
        self.glossary = glossary.copy()
        self.languages = list(glossary.keys()) if glossary else []
        self.refresh_table()
        self.update_count_label()

    def get_glossary(self) -> Dict[str, Dict[str, str]]:
        """Get the current business glossary data."""
        return self.glossary.copy()

    def refresh_table(self):
        """Refresh the table display."""
        self._updating_table = True  # Prevent signal emissions during refresh

        self.table.clear()
        self.table.setRowCount(0)
        self.table.setColumnCount(0)

        if not self.glossary:
            self._updating_table = False
            return

        # Get all unique English terms across all languages
        all_terms = set()
        for language_glossary in self.glossary.values():
            all_terms.update(language_glossary.keys())

        if not all_terms:
            self._updating_table = False
            return

        # Set up table
        self.table.setColumnCount(len(self.languages) + 1)  # +1 for English terms
        headers = ["English Term"] + self.languages
        self.table.setHorizontalHeaderLabels(headers)

        # Add rows
        sorted_terms = sorted(all_terms)
        self.table.setRowCount(len(sorted_terms))

        for row, english_term in enumerate(sorted_terms):
            # English term (read-only)
            english_item = QTableWidgetItem(english_term)
            english_item.setFlags(english_item.flags() & ~Qt.ItemIsEditable)
            english_item.setBackground(QColor(240, 240, 240))
            self.table.setItem(row, 0, english_item)

            # Translations for each language
            for col, language in enumerate(self.languages, 1):
                translation = self.glossary.get(language, {}).get(english_term, "")
                item = QTableWidgetItem(translation)
                self.table.setItem(row, col, item)

        # Resize columns
        self.table.resizeColumnsToContents()

        self._updating_table = False  # Re-enable signal emissions

    def update_count_label(self):
        """Update the term count label."""
        total_terms = 0
        for language_glossary in self.glossary.values():
            total_terms += len(language_glossary)

        language_count = len(self.languages)
        self.count_label.setText(
            f"{total_terms} translations across {language_count} languages"
        )

    def update_button_states(self):
        """Update button enabled states based on selection."""
        has_selection = len(self.table.selectedItems()) > 0
        has_data = bool(self.glossary)

        self.edit_term_btn.setEnabled(has_selection)
        self.remove_term_btn.setEnabled(has_selection)
        self.clear_btn.setEnabled(has_data)

    def add_term(self):
        """Add a new term to the glossary."""
        dialog = AddTermDialog(self.languages, self)
        if dialog.exec():
            english_term, translations = dialog.get_data()
            if english_term:
                self._add_term_to_glossary(english_term, translations)
                self.refresh_table()
                self.update_count_label()
                self.update_button_states()
                self.glossary_changed.emit(self.glossary)

    def edit_selected_term(self):
        """Edit the selected term."""
        selected_items = self.table.selectedItems()
        if not selected_items:
            return

        # Get the English term from the first column
        row = selected_items[0].row()
        english_term_item = self.table.item(row, 0)
        if not english_term_item:
            return

        english_term = english_term_item.text()

        # Collect current translations
        current_translations = {}
        for col, language in enumerate(self.languages, 1):
            item = self.table.item(row, col)
            if item:
                current_translations[language] = item.text()

        dialog = EditTermDialog(
            english_term, current_translations, self.languages, self
        )
        if dialog.exec():
            new_translations = dialog.get_translations()
            self._update_term_translations(english_term, new_translations)
            self.refresh_table()
            self.update_count_label()
            self.glossary_changed.emit(self.glossary)

    def remove_selected_term(self):
        """Remove the selected term from all languages."""
        selected_items = self.table.selectedItems()
        if not selected_items:
            return

        row = selected_items[0].row()
        english_term_item = self.table.item(row, 0)
        if not english_term_item:
            return

        english_term = english_term_item.text()

        # Count how many languages have this term
        term_count = sum(
            1 for lang_gloss in self.glossary.values() if english_term in lang_gloss
        )

        reply = QMessageBox.question(
            self,
            "Remove Term",
            f"Remove '{english_term}' from {term_count} language(s)?\n\n"
            "This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            self._remove_term_from_glossary(english_term)
            self.refresh_table()
            self.update_count_label()
            self.update_button_states()
            self.glossary_changed.emit(self.glossary)

    def clear_all_terms(self):
        """Clear all terms from the glossary."""
        total_terms = sum(len(lang_gloss) for lang_gloss in self.glossary.values())

        reply = QMessageBox.question(
            self,
            "Clear All Terms",
            f"Remove all {total_terms} terms from the business glossary?\n\n"
            "This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            self.glossary.clear()
            self.languages.clear()
            self.refresh_table()
            self.update_count_label()
            self.update_button_states()
            self.glossary_changed.emit(self.glossary)

    def on_table_item_changed(self, item):
        """Handle table item changes (direct editing)."""
        # Skip if we're currently updating the table programmatically
        if self._updating_table:
            return

        if item.column() == 0:  # English term column is read-only
            return

        row = item.row()
        english_term_item = self.table.item(row, 0)
        if not english_term_item:
            return

        english_term = english_term_item.text()
        language = self.languages[item.column() - 1]  # -1 because column 0 is English
        translation = item.text()

        # Update the glossary
        if language not in self.glossary:
            self.glossary[language] = {}

        if translation.strip():
            self.glossary[language][english_term] = translation.strip()
        elif english_term in self.glossary[language]:
            del self.glossary[language][english_term]

        self.update_count_label()
        self.glossary_changed.emit(self.glossary)

    def _add_term_to_glossary(self, english_term: str, translations: Dict[str, str]):
        """Add a new term to the glossary."""
        for language, translation in translations.items():
            if language not in self.glossary:
                self.glossary[language] = {}
            if translation.strip():
                self.glossary[language][english_term] = translation.strip()

    def _update_term_translations(
        self, english_term: str, translations: Dict[str, str]
    ):
        """Update translations for an existing term."""
        for language, translation in translations.items():
            if language not in self.glossary:
                self.glossary[language] = {}

            if translation.strip():
                self.glossary[language][english_term] = translation.strip()
            elif english_term in self.glossary[language]:
                del self.glossary[language][english_term]

    def _remove_term_from_glossary(self, english_term: str):
        """Remove a term from all languages in the glossary."""
        for language_glossary in self.glossary.values():
            if english_term in language_glossary:
                del language_glossary[english_term]

    def is_modified(self, original_glossary: Dict[str, Dict[str, str]]) -> bool:
        """Check if the glossary has been modified from the original."""
        return self.glossary != original_glossary


class AddTermDialog(QDialog):
    """Dialog for adding a new English term and its translations to the business glossary."""

    def __init__(self, languages: List[str], parent=None):
        super().__init__(parent)
        self.languages = languages
        self.english_term = ""
        self.translations = {}
        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        """Set up the dialog interface."""
        self.setWindowTitle("Add Business Term")
        self.setModal(True)
        self.resize(500, 300)

        layout = QVBoxLayout(self)

        # English term input
        english_layout = QHBoxLayout()
        english_label = QLabel("English Term:")
        self.english_input = QLineEdit()
        self.english_input.setPlaceholderText("Enter the English term...")
        english_layout.addWidget(english_label)
        english_layout.addWidget(self.english_input)
        layout.addLayout(english_layout)

        # Translations section
        translations_label = QLabel("Translations:")
        translations_label.setObjectName("sectionTitle")
        layout.addWidget(translations_label)

        # Scrollable translations area
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        self.translations_layout = QGridLayout(scroll_widget)

        for i, language in enumerate(self.languages):
            label = QLabel(f"{language}:")
            self.translations[language] = QLineEdit()
            self.translations[language].setPlaceholderText(
                f"Enter {language} translation..."
            )
            self.translations_layout.addWidget(label, i, 0)
            self.translations_layout.addWidget(self.translations[language], i, 1)

        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(button_box)

        self.button_box = button_box

    def connect_signals(self):
        """Connect dialog signals."""
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.english_input.textChanged.connect(self.validate_input)

    def validate_input(self):
        """Validate the input and enable/disable OK button."""
        english_term = self.english_input.text().strip()
        has_translations = any(
            self.translations[lang].text().strip() for lang in self.languages
        )

        self.button_box.button(QDialogButtonBox.Ok).setEnabled(
            bool(english_term) and has_translations
        )

    def get_data(self) -> Tuple[str, Dict[str, str]]:
        """Get the entered data."""
        english_term = self.english_input.text().strip()
        translations = {
            language: self.translations[language].text().strip()
            for language in self.languages
        }
        return english_term, translations


class EditTermDialog(QDialog):
    """Dialog for editing an existing English term's translations across all languages."""

    def __init__(
        self,
        english_term: str,
        current_translations: Dict[str, str],
        languages: List[str],
        parent=None,
    ):
        super().__init__(parent)
        self.english_term = english_term
        self.languages = languages
        self.translations = {}
        self.setup_ui()
        self.populate_data(current_translations)
        self.connect_signals()

    def setup_ui(self):
        """Set up the dialog interface."""
        self.setWindowTitle(f"Edit Term: {self.english_term}")
        self.setModal(True)
        self.resize(500, 300)

        layout = QVBoxLayout(self)

        # English term display (read-only)
        english_layout = QHBoxLayout()
        english_label = QLabel("English Term:")
        english_term_label = QLabel(self.english_term)
        english_term_label.setObjectName("readOnlyText")
        english_layout.addWidget(english_label)
        english_layout.addWidget(english_term_label)
        english_layout.addStretch()
        layout.addLayout(english_layout)

        # Translations section
        translations_label = QLabel("Translations:")
        translations_label.setObjectName("sectionTitle")
        layout.addWidget(translations_label)

        # Scrollable translations area
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        self.translations_layout = QGridLayout(scroll_widget)

        for i, language in enumerate(self.languages):
            label = QLabel(f"{language}:")
            self.translations[language] = QLineEdit()
            self.translations[language].setPlaceholderText(
                f"Enter {language} translation..."
            )
            self.translations_layout.addWidget(label, i, 0)
            self.translations_layout.addWidget(self.translations[language], i, 1)

        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(button_box)

        self.button_box = button_box

    def populate_data(self, current_translations: Dict[str, str]):
        """Populate the dialog with current translation data."""
        for language in self.languages:
            translation = current_translations.get(language, "")
            self.translations[language].setText(translation)

    def connect_signals(self):
        """Connect dialog signals."""
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

    def get_translations(self) -> Dict[str, str]:
        """Get the current translations."""
        return {
            language: self.translations[language].text().strip()
            for language in self.languages
        }
