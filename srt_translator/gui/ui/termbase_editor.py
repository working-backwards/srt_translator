#!/usr/bin/env python3
"""
Termbase Editor for the SRT Translator GUI.
"""

import json
import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class TermbaseEditor(QWidget):
    """Widget for editing termbase entries across multiple languages.

    The termbase contains language-specific translations of source language terms.
    Each language has its own set of translations for the same source language terms.
    """

    termbase_changed = Signal(dict)  # Emitted when termbase is modified

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.termbase: dict[str, dict[str, str]] = {}  # {language: {source_term: translation}}
        self.languages: list[str] = []
        self.source_language_name: str = "Source"  # Will be updated dynamically
        self._updating_table = False  # Flag to prevent signal loops
        self.setup_ui()
        self.connect_signals()

    def set_source_language(self, source_language_info: dict[str, object]):
        """Set the source language information for display purposes."""
        if source_language_info and "name" in source_language_info:
            self.source_language_name = str(source_language_info["name"])
        else:
            self.source_language_name = "Source"
        self.refresh_table()

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
        self.export_btn = QPushButton("Export")
        self.export_btn.setObjectName("secondaryButton")

        button_layout.addWidget(self.add_term_btn)
        button_layout.addWidget(self.edit_term_btn)
        button_layout.addWidget(self.remove_term_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.export_btn)
        button_layout.addWidget(self.clear_btn)
        layout.addLayout(button_layout)

        # Table
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)  # type: ignore[attr-defined]
        self.table.setSelectionMode(QTableWidget.SingleSelection)  # type: ignore[attr-defined]
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)  # type: ignore[attr-defined]
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
        self.export_btn.clicked.connect(self.export_termbase)
        self.table.itemSelectionChanged.connect(self.update_button_states)
        self.table.itemChanged.connect(self.on_table_item_changed)

    def set_termbase(self, termbase: dict):
        """Set the termbase data."""
        self.termbase = termbase.copy()
        self.languages = list(termbase.keys()) if termbase else []
        self.refresh_table()
        self.update_count_label()
        self.update_button_states()
        # Emit signal to notify of changes
        if not self._updating_table:
            self.termbase_changed.emit(self.termbase)

    def get_termbase(self) -> dict:
        """Get the current termbase data."""
        return self.termbase.copy()

    def refresh_table(self):
        """Refresh the table display."""
        self._updating_table = True  # Prevent signal emissions during refresh

        self.table.clear()
        self.table.setRowCount(0)
        self.table.setColumnCount(0)

        if not self.termbase:
            self._updating_table = False
            return

            # Get all unique source terms across all languages (deduplicated)
        all_terms: set[str] = set()
        for language_termbase in self.termbase.values():
            all_terms.update(language_termbase.keys())

        # Ensure case-insensitive deduplication and proper sorting
        unique_terms = set()
        for term in all_terms:
            # Check if we already have a case-insensitive version
            term_lower = term.lower()
            if not any(existing.lower() == term_lower for existing in unique_terms):
                unique_terms.add(term)

        all_terms = unique_terms

        if not all_terms:
            self._updating_table = False
            return

        # Set up table - terms in column 0, languages in columns 1-N
        self.table.setColumnCount(len(self.languages) + 1)  # +1 for source language terms
        headers = [f"{self.source_language_name} Term"] + self.languages
        self.table.setHorizontalHeaderLabels(headers)

        # Add rows - one row per unique source term (deduplicated and alphabetically sorted)
        sorted_terms = sorted(all_terms, key=str.lower)  # Case-insensitive alphabetical sorting
        self.table.setRowCount(len(sorted_terms))

        for row, source_term in enumerate(sorted_terms):
            # Source term (read-only) in column 0
            source_item = QTableWidgetItem(source_term)
            source_item.setFlags(source_item.flags() & ~Qt.ItemIsEditable)  # type: ignore[attr-defined]
            source_item.setBackground(QColor(240, 240, 240))
            self.table.setItem(row, 0, source_item)

            # Translations for each language in columns 1-N
            for col, language in enumerate(self.languages, 1):
                translation = self.termbase.get(language, {}).get(source_term, "")
                item = QTableWidgetItem(translation)
                self.table.setItem(row, col, item)

        # Resize columns
        self.table.resizeColumnsToContents()

        self._updating_table = False  # Re-enable signal emissions

    def update_count_label(self):
        """Update the term count label."""
        total_terms = 0
        for language_termbase in self.termbase.values():
            total_terms += len(language_termbase)

        language_count = len(self.languages)
        self.count_label.setText(f"{total_terms} translations across {language_count} languages")

    def update_button_states(self):
        """Update button enabled states based on selection."""
        has_selection = len(self.table.selectedItems()) > 0
        has_data = bool(self.termbase)

        self.edit_term_btn.setEnabled(has_selection)
        self.remove_term_btn.setEnabled(has_selection)
        self.clear_btn.setEnabled(has_data)
        self.export_btn.setEnabled(has_data)

    def add_term(self):
        """Add a new term to the termbase."""
        dialog = AddTermDialog(list(self.termbase.keys()), self)
        if dialog.exec():
            source_term, translations = dialog.get_data()
            if source_term:
                # Add to termbase
                for language, translation in translations.items():
                    if language not in self.termbase:
                        self.termbase[language] = {}
                    if translation.strip():
                        self.termbase[language][source_term] = translation.strip()
                self.refresh_table()
                self.update_count_label()
                self.update_button_states()
                self.termbase_changed.emit(self.termbase)
                QMessageBox.information(
                    self,
                    "Term Added",
                    f"The term '{source_term}' was successfully added to the termbase."
                )

    def edit_selected_term(self):
        """Edit the selected term."""
        selected_items = self.table.selectedItems()
        if not selected_items:
            return

        row = selected_items[0].row()
        source_term_item = self.table.item(row, 0)
        if not source_term_item:
            return

        source_term = source_term_item.text()

        # Current translations
        current_translations = {}
        for col, language in enumerate(self.languages, 1):
            item = self.table.item(row, col)
            if item:
                current_translations[language] = item.text()

        dialog = EditTermDialog(source_term, current_translations, self.languages, self)
        if dialog.exec():
            new_translations = dialog.get_translations()

            # Update termbase
            for language, translation in new_translations.items():
                if language not in self.termbase:
                    self.termbase[language] = {}
                if translation.strip():
                    self.termbase[language][source_term] = translation.strip()
                elif source_term in self.termbase.get(language, {}):
                    del self.termbase[language][source_term]

            # Update UI
            self.refresh_table()
            self.update_count_label()
            self.update_button_states()
            self.termbase_changed.emit(self.termbase)

            QMessageBox.information(
                self,
                "Term edited",
                f"The term '{source_term}' was successfully edited the termbase."
            )

    def remove_selected_term(self):
        """Remove the selected term from all languages."""
        selected_items = self.table.selectedItems()
        if not selected_items:
            return

        row = selected_items[0].row()
        source_term_item = self.table.item(row, 0)
        if not source_term_item:
            return

        source_term = source_term_item.text()

        term_count = sum(1 for lang_termbase in self.termbase.values() if source_term in lang_termbase)

        reply = QMessageBox.question(
            self,
            "Remove Term",
            f"Remove '{source_term}' from {term_count} language(s)?\n\nThis action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            # Remove from termbase
            for lang_termbase in self.termbase.values():
                if source_term in lang_termbase:
                    del lang_termbase[source_term]

            # Update UI
            self.refresh_table()
            self.update_count_label()
            self.update_button_states()
            self.termbase_changed.emit(self.termbase)

            QMessageBox.information(
                self,
                "Term removed",
                f"The term '{source_term}' was successfully removed from the termbase."
            )

    def clear_all_terms(self):
        """Clear all terms from the termbase."""
        total_terms = sum(len(lang_termbase) for lang_termbase in self.termbase.values())

        reply = QMessageBox.question(
            self,
            "Clear All Terms",
            f"Remove all {total_terms} terms from the termbase?\n\nThis action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,  # type: ignore[attr-defined]
            QMessageBox.No,  # type: ignore[attr-defined]
        )

        if reply == QMessageBox.Yes:
            for lang_termbase in self.termbase.values():
                lang_termbase.clear()
            self.refresh_table()
            self.update_count_label()
            self.update_button_states()
            self.termbase_changed.emit(self.termbase)

    def on_table_item_changed(self, item):
        """Handle table item changes (direct editing)."""
        # Skip if we're currently updating the table programmatically
        if self._updating_table:
            return

        if item.column() == 0:  # Source term column is read-only
            return

        row = item.row()
        source_term_item = self.table.item(row, 0)
        if not source_term_item:
            return

        source_term = source_term_item.text()
        language = self.languages[item.column() - 1]  # -1 because column 0 is source term
        translation = item.text()

        # Update the termbase
        if language not in self.termbase:
            self.termbase[language] = {}

        if translation.strip():
            self.termbase[language][source_term] = translation.strip()
        elif source_term in self.termbase[language]:
            del self.termbase[language][source_term]

        self.update_count_label()
        self.termbase_changed.emit(self.termbase)

    def export_termbase(self):
        """Export termbase to a JSON file."""
        if not self.termbase:
            QMessageBox.warning(
                self,
                "No Termbase to Export",
                "There is no termbase data to export.",
            )
            return

        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.AnyFile)
        file_dialog.setAcceptMode(QFileDialog.AcceptSave)
        file_dialog.setNameFilter("JSON Files (*.json)")
        file_dialog.setDefaultSuffix("json")

        if file_dialog.exec():
            file_path = file_dialog.selectedFiles()[0]

            try:
                # Export as JSON object format: {"lang_code": {"source_term": "translation", ...}, ...}
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(self.termbase, f, indent=2, ensure_ascii=False)

                total_entries = sum(len(lang_termbase) for lang_termbase in self.termbase.values())
                QMessageBox.information(
                    self,
                    "Export Successful",
                    f"Exported termbase with {len(self.termbase)} language(s) "
                    f"and {total_entries} total entries to:\n{file_path}",
                )
                self.logger.info(
                    "Exported termbase: %s languages, %s entries to %s",
                    len(self.termbase),
                    total_entries,
                    file_path,
                )

            except Exception as e:
                self.logger.error("Failed to export termbase: %s", e)
                QMessageBox.critical(
                    self,
                    "Export Failed",
                    f"Failed to export termbase:\n{str(e)}",
                )

    def is_modified(self, original_termbase: dict) -> bool:
        """Check if the termbase has been modified from the original."""
        return self.termbase != original_termbase


class AddTermDialog(QDialog):
    """Dialog for adding a new source language term and its translations to the termbase."""

    def __init__(self, languages: list, parent=None):
        super().__init__(parent)
        self.languages = languages
        self.source_term = ""
        self.translations: dict[str, QLineEdit] = {}
        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        """Set up the dialog interface."""
        self.setWindowTitle("Add Business Term")
        self.setModal(True)
        self.resize(500, 300)

        layout = QVBoxLayout(self)

        # Source term input
        source_layout = QHBoxLayout()
        source_label = QLabel("Source Term:")
        self.source_input = QLineEdit()
        self.source_input.setPlaceholderText("Enter the source language term...")
        source_layout.addWidget(source_label)
        source_layout.addWidget(self.source_input)
        layout.addLayout(source_layout)

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
            self.translations[language].setPlaceholderText(f"Enter {language} translation...")
            self.translations_layout.addWidget(label, i, 0)
            self.translations_layout.addWidget(self.translations[language], i, 1)

        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)  # type: ignore[attr-defined]
        layout.addWidget(button_box)

        self.button_box = button_box

    def connect_signals(self):
        """Connect dialog signals."""
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.source_input.textChanged.connect(self.validate_input)

    def validate_input(self):
        """Validate the input and enable/disable OK button."""
        source_term = self.source_input.text().strip()
        has_translations = any(self.translations[lang].text().strip() for lang in self.languages)

        self.button_box.button(QDialogButtonBox.Ok).setEnabled(  # type: ignore[attr-defined]
            bool(source_term) and has_translations
        )

    def get_data(self) -> tuple[str, dict]:
        """Get the entered data."""
        source_term = self.source_input.text().strip()
        translations = {language: self.translations[language].text().strip() for language in self.languages}
        return source_term, translations


class EditTermDialog(QDialog):
    """Dialog for editing an existing source language term's translations across all languages."""

    def __init__(
        self,
        source_term: str,
        current_translations: dict,
        languages: list,
        parent=None,
    ):
        super().__init__(parent)
        self.source_term = source_term
        self.languages = languages
        self.translations: dict[str, QLineEdit] = {}
        self.setup_ui()
        self.populate_data(current_translations)
        self.connect_signals()

    def setup_ui(self):
        """Set up the dialog interface."""
        self.setWindowTitle(f"Edit Term: {self.source_term}")
        self.setModal(True)
        self.resize(500, 300)

        layout = QVBoxLayout(self)

        # Source term display (read-only)
        source_layout = QHBoxLayout()
        source_label = QLabel("Source Term:")
        source_term_label = QLabel(self.source_term)
        source_term_label.setObjectName("readOnlyText")
        source_layout.addWidget(source_label)
        source_layout.addWidget(source_term_label)
        source_layout.addStretch()
        layout.addLayout(source_layout)

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
            self.translations[language].setPlaceholderText(f"Enter {language} translation...")
            self.translations_layout.addWidget(label, i, 0)
            self.translations_layout.addWidget(self.translations[language], i, 1)

        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)  # type: ignore[attr-defined]
        layout.addWidget(button_box)

        self.button_box = button_box

    def populate_data(self, current_translations: dict):
        """Populate the dialog with current translation data."""
        for language in self.languages:
            translation = current_translations.get(language, "")
            self.translations[language].setText(translation)

    def connect_signals(self):
        """Connect dialog signals."""
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

    def get_translations(self) -> dict:
        """Get the current translations."""
        return {language: self.translations[language].text().strip() for language in self.languages}
