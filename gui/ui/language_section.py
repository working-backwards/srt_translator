"""
Language Selection Section
Handles target language selection and management using unified language configuration
"""

import logging
from typing import Dict

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

from srt_core.config.language_config import language_config


class LanguageSection(QGroupBox):
    """Language selection section with popular languages and search"""

    def __init__(self, settings_manager):
        super().__init__("Target Languages")
        self.settings_manager = settings_manager
        self.setObjectName("languageSection")
        self.target_languages = {}

        self.setup_ui()
        self.populate_language_list()

    def setup_ui(self):
        """Set up the language section UI using unified language configuration"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Popular languages grid
        popular_label = QLabel("Popular Languages")
        popular_label.setObjectName("subHeaderLabel")
        layout.addWidget(popular_label)

        popular_grid = QGridLayout()
        popular_grid.setVerticalSpacing(
            25
        )  # 25px between checkbox rows as per style guide

        # Get adaptive popular languages from settings manager
        popular_language_codes = self.settings_manager.get_adaptive_popular_languages()

        self.language_checkboxes = {}
        for i, code in enumerate(popular_language_codes):
            name = language_config.get_language_name(code)
            checkbox = QCheckBox(name)
            checkbox.setObjectName("languageCheckbox")
            checkbox.setProperty(
                "language_code", code
            )  # Store language code for tracking
            self.language_checkboxes[code] = checkbox
            popular_grid.addWidget(checkbox, i // 3, i % 3)

        layout.addLayout(popular_grid)

        # Search box
        search_layout = QHBoxLayout()
        search_label = QLabel("Search Languages:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Type to search languages...")
        self.search_input.setObjectName("searchInput")

        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)

        layout.addLayout(search_layout)

        # Full language list
        self.language_list = QListWidget()
        self.language_list.setObjectName("languageList")
        self.language_list.setSelectionMode(QListWidget.MultiSelection)
        self.language_list.setMinimumHeight(100)  # 100-120px as per style guide
        self.language_list.setMaximumHeight(120)

        layout.addWidget(self.language_list)

        # Language count
        self.language_count_label = QLabel("No languages selected")
        self.language_count_label.setObjectName("languageCountLabel")
        layout.addWidget(self.language_count_label)

    def connect_signals(
        self,
        checkbox_toggled_callback,
        list_selection_changed_callback,
        search_changed_callback,
    ):
        """Connect signals to callbacks"""
        # Connect checkboxes
        for checkbox in self.language_checkboxes.values():
            checkbox.toggled.connect(checkbox_toggled_callback)

        # Connect list selection
        self.language_list.itemSelectionChanged.connect(list_selection_changed_callback)

        # Connect search
        self.search_input.textChanged.connect(search_changed_callback)

    def populate_language_list(self):
        """Populate the full language list using unified language configuration"""
        # Get all languages from unified config
        all_languages = language_config.get_language_names()

        # Sort languages alphabetically by display name
        sorted_languages = sorted(all_languages.items(), key=lambda x: x[1])

        # Add all languages to the list (including popular ones) in alphabetical order
        # Users should be able to see and select any language
        for code, name in sorted_languages:
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, code)
            self.language_list.addItem(item)

    def get_target_languages(self) -> Dict[str, str]:
        """Get the current target languages"""
        return self.target_languages.copy()

    def update_target_languages_from_ui(self):
        """Update target_languages dictionary from current UI state"""
        self.target_languages.clear()

        # Add languages from checkboxes
        for code, checkbox in self.language_checkboxes.items():
            if checkbox.isChecked():
                self.target_languages[checkbox.text()] = code

        # Add languages from list selection
        for item in self.language_list.selectedItems():
            name = item.text()
            code = item.data(Qt.UserRole)
            if code and name not in self.target_languages:  # Avoid duplicates
                self.target_languages[name] = code

        # Update the display
        self.update_language_count()

        # Save to settings manager (single source of truth)
        self.settings_manager.save_target_languages(self.target_languages)

        # Update SettingsManager current state (thread-safe)
        self.settings_manager.update_target_languages(self.target_languages)

        # Log the update for debugging
        logging.info(f"Updated target languages from UI: {self.target_languages}")

    def filter_languages(self):
        """Filter the language list based on search text"""
        search_text = self.search_input.text().lower()

        for i in range(self.language_list.count()):
            item = self.language_list.item(i)
            item.setHidden(search_text not in item.text().lower())

    def update_language_count(self):
        """Update the language count label"""
        count = len(self.target_languages)
        if count == 0:
            self.language_count_label.setText("No languages selected")
        elif count == 1:
            self.language_count_label.setText("1 language selected")
        else:
            self.language_count_label.setText(f"{count} languages selected")

    def load_saved_languages(self):
        """Load previously selected languages using unified language configuration"""
        saved_languages = self.settings_manager.load_target_languages()

        # Temporarily block signals to prevent interference during loading
        for checkbox in self.language_checkboxes.values():
            checkbox.blockSignals(True)
        self.language_list.blockSignals(True)

        try:
            # Clear existing selections
            for checkbox in self.language_checkboxes.values():
                checkbox.setChecked(False)

            # Load saved languages
            for name, code in saved_languages.items():
                if code in self.language_checkboxes:
                    self.language_checkboxes[code].setChecked(True)
                else:
                    # If it's not in popular languages, try to select it in the list
                    # This handles cases where languages were moved from popular to non-popular
                    for i in range(self.language_list.count()):
                        item = self.language_list.item(i)
                        if item.data(Qt.UserRole) == code:
                            item.setSelected(True)
                            break

            # Update the target_languages dictionary from UI state (without triggering adaptive updates)
            self.target_languages.clear()

            # Add languages from checkboxes
            for code, checkbox in self.language_checkboxes.items():
                if checkbox.isChecked():
                    self.target_languages[checkbox.text()] = code

            # Add languages from list selection
            for item in self.language_list.selectedItems():
                name = item.text()
                code = item.data(Qt.UserRole)
                if code and name not in self.target_languages:  # Avoid duplicates
                    self.target_languages[name] = code

            # Update the display without triggering adaptive updates
            self.update_language_count()

            # Update SettingsManager current state (thread-safe)
            self.settings_manager.update_target_languages(self.target_languages)

            logging.info(f"Loaded saved languages: {self.target_languages}")

            # Debug: Verify synchronization
            total_checkboxes = len(self.language_checkboxes)
            checked_checkboxes = sum(
                1
                for checkbox in self.language_checkboxes.values()
                if checkbox.isChecked()
            )
            logging.info(
                f"Load verification: {checked_checkboxes}/{total_checkboxes} checkboxes checked, {len(self.target_languages)} languages in target_languages"
            )

        finally:
            # Re-enable signals after loading is complete
            for checkbox in self.language_checkboxes.values():
                checkbox.blockSignals(False)
            self.language_list.blockSignals(False)

    def refresh_popular_languages(self):
        """
        Refresh the popular languages section when adaptive preferences change
        This is called when the adaptive system updates the popular languages
        """
        # Get current adaptive popular languages
        new_popular_codes = self.settings_manager.get_adaptive_popular_languages()
        current_popular_codes = list(self.language_checkboxes.keys())

        # If popular languages haven't changed, no need to refresh
        if new_popular_codes == current_popular_codes:
            return

        # Store ALL current selections (both from checkboxes and list)
        current_selections = {}

        # Get selections from current checkboxes
        for code, checkbox in self.language_checkboxes.items():
            if checkbox.isChecked():
                current_selections[code] = checkbox.text()

        # Get selections from list items
        for item in self.language_list.selectedItems():
            code = item.data(Qt.UserRole)
            if code:
                current_selections[code] = item.text()

        # Clear the current popular languages grid
        layout = self.layout()
        popular_grid = layout.itemAt(1)  # Popular languages grid is at index 1

        # Remove all widgets from the grid
        while popular_grid.count():
            child = popular_grid.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Clear the checkboxes dictionary
        self.language_checkboxes.clear()

        # Recreate popular languages grid with new languages
        for i, code in enumerate(new_popular_codes):
            name = language_config.get_language_name(code)
            checkbox = QCheckBox(name)
            checkbox.setObjectName("languageCheckbox")
            checkbox.setProperty("language_code", code)

            # Restore previous selection if this language was selected
            if code in current_selections:
                checkbox.setChecked(True)

            self.language_checkboxes[code] = checkbox
            popular_grid.addWidget(checkbox, i // 3, i % 3)

        # Update target languages to reflect the changes
        self.update_target_languages_from_ui()

        logging.debug(f"Refreshed popular languages: {new_popular_codes}")

    def check_for_adaptive_updates(self):
        """
        Check if adaptive popular languages have been updated and refresh if needed
        This should be called periodically or after language selections
        """
        # Get current adaptive popular languages
        current_adaptive = self.settings_manager.get_adaptive_popular_languages()
        current_displayed = list(self.language_checkboxes.keys())

        # If they don't match, refresh the display
        if current_adaptive != current_displayed:
            self.refresh_popular_languages()
