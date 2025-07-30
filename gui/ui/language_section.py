"""
Language Selection Section
Handles target language selection and management
"""

import logging
from typing import Dict
from PySide6.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QListWidget, QListWidgetItem, QCheckBox
)
from PySide6.QtCore import Qt


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
        """Set up the language section UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Popular languages grid
        popular_label = QLabel("Popular Languages")
        popular_label.setObjectName("subHeaderLabel")
        layout.addWidget(popular_label)
        
        popular_grid = QGridLayout()
        popular_grid.setVerticalSpacing(25)  # 25px between checkbox rows as per style guide
        popular_languages = [
            ("Spanish", "es"), ("French", "fr"), ("German", "de"),
            ("Italian", "it"), ("Portuguese", "pt"), ("Russian", "ru"),
            ("Japanese", "ja"), ("Korean", "ko"), ("Chinese", "zh"),
            ("Arabic", "ar"), ("Hindi", "hi"), ("Dutch", "nl")
        ]
        
        self.language_checkboxes = {}
        for i, (name, code) in enumerate(popular_languages):
            checkbox = QCheckBox(name)
            checkbox.setObjectName("languageCheckbox")
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
    
    def connect_signals(self, checkbox_toggled_callback, list_selection_changed_callback, search_changed_callback):
        """Connect signals to callbacks"""
        # Connect checkboxes
        for checkbox in self.language_checkboxes.values():
            checkbox.toggled.connect(checkbox_toggled_callback)
        
        # Connect list selection
        self.language_list.itemSelectionChanged.connect(list_selection_changed_callback)
        
        # Connect search
        self.search_input.textChanged.connect(search_changed_callback)
    
    def populate_language_list(self):
        """Populate the full language list"""
        all_languages = {
            "Spanish": "es", "French": "fr", "German": "de", "Italian": "it",
            "Portuguese": "pt", "Russian": "ru", "Japanese": "ja", "Korean": "ko",
            "Chinese": "zh", "Arabic": "ar", "Hindi": "hi", "Dutch": "nl",
            "Swedish": "sv", "Norwegian": "no", "Danish": "da", "Finnish": "fi",
            "Polish": "pl", "Czech": "cs", "Hungarian": "hu", "Romanian": "ro",
            "Bulgarian": "bg", "Greek": "el", "Turkish": "tr", "Hebrew": "he",
            "Thai": "th", "Vietnamese": "vi", "Indonesian": "id", "Malay": "ms",
            "Filipino": "fil", "Ukrainian": "uk", "Belarusian": "be", "Slovak": "sk",
            "Slovenian": "sl", "Croatian": "hr", "Serbian": "sr", "Macedonian": "mk",
            "Albanian": "sq", "Estonian": "et", "Latvian": "lv", "Lithuanian": "lt",
            "Icelandic": "is", "Irish": "ga", "Welsh": "cy", "Breton": "br",
            "Catalan": "ca", "Galician": "gl", "Basque": "eu", "Occitan": "oc"
        }
        
        for name, code in all_languages.items():
            if code not in self.language_checkboxes:  # Don't duplicate popular languages
                item = QListWidgetItem(name)
                item.setData(Qt.UserRole, code)
                self.language_list.addItem(item)
    
    def get_target_languages(self) -> Dict[str, str]:
        """Get the current target languages"""
        return self.target_languages.copy()
    
    def update_target_languages_from_ui(self):
        """Update target languages from both checkboxes and list selection"""
        self.target_languages.clear()
        
        # Add languages from checkboxes
        for code, checkbox in self.language_checkboxes.items():
            if checkbox.isChecked():
                self.target_languages[checkbox.text()] = code
                logging.info(f"Added checkbox language: {checkbox.text()} -> {code}")
        
        # Add languages from list selection
        for item in self.language_list.selectedItems():
            name = item.text()
            code = item.data(Qt.UserRole)
            self.target_languages[name] = code
            logging.info(f"Added list language: {name} -> {code}")
        
        logging.info(f"Total target languages: {self.target_languages}")
        self.update_language_count()
        self.settings_manager.save_target_languages(self.target_languages)
    
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
        """Load previously selected languages"""
        saved_languages = self.settings_manager.load_target_languages()
        for name, code in saved_languages.items():
            if code in self.language_checkboxes:
                self.language_checkboxes[code].setChecked(True)
        
        # Update the target_languages dictionary from UI state
        self.update_target_languages_from_ui() 