"""
Main Window for SRT Translator GUI
Implements the complete user interface following the design specifications
"""

import os
import sys
import shutil
import subprocess
import logging
from typing import List, Dict, Optional
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QListWidget, QListWidgetItem,
    QCheckBox, QTextEdit, QFileDialog, QMessageBox, QProgressBar,
    QFrame, QScrollArea, QGroupBox, QSplitter
)
from PySide6.QtCore import Qt, QThread, QTimer, Signal as pyqtSignal
from PySide6.QtGui import QFont, QPalette, QColor, QPixmap

from .settings_manager import SettingsManager


class TranslationWorker(QThread):
    """Worker thread for running translations in background"""
    
    progress_updated = pyqtSignal(str)
    translation_completed = pyqtSignal(dict)
    translation_error = pyqtSignal(str)
    
    def __init__(self, api_key: str, selected_files: List[str], target_languages: Dict[str, str]):
        super().__init__()
        self.api_key = api_key
        self.selected_files = selected_files
        self.target_languages = target_languages
    
    def run(self):
        """Run the translation process"""
        try:
            # Set up environment for translation
            self.prepare_translation_environment()
            
            # Run the translation
            from srt_core.main import translate_srt_files
            
            # Capture output by redirecting stdout
            import io
            import sys
            from contextlib import redirect_stdout
            
            output = io.StringIO()
            with redirect_stdout(output):
                results = translate_srt_files(file_paths=self.selected_files)
            
            # Log the actual results
            logging.info(f"Translation results: {results}")
            self.progress_updated.emit(f"Translation results: {results}")
            
            # Emit progress updates
            output_text = output.getvalue()
            for line in output_text.split('\n'):
                if line.strip():
                    self.progress_updated.emit(line)
            
            self.translation_completed.emit(results)
            
        except Exception as e:
            self.translation_error.emit(str(e))
    
    def prepare_translation_environment(self):
        """Prepare the environment for translation"""
        # Set API key in environment
        os.environ['OPENAI_API_KEY'] = self.api_key
        # The translation function will use the selected files directly.
        logging.info("Using selected files for translation")
        self.progress_updated.emit("Using selected files for translation")
        # Update .env file with target languages
        self.update_env_languages()
    
    def update_env_languages(self):
        """Update .env file with selected target languages"""
        env_path = Path(".env")
        if env_path.exists():
            # Read existing .env file
            with open(env_path, 'r') as f:
                lines = f.readlines()
            
            # Update TARGET_LANGUAGES line
            new_lines = []
            languages_str = ", ".join([f'"{name}": "{code}"' for name, code in self.target_languages.items()])
            target_languages_line = f'TARGET_LANGUAGES = {{{languages_str}}}'
            
            found = False
            for line in lines:
                if line.startswith('TARGET_LANGUAGES'):
                    new_lines.append(target_languages_line + '\n')
                    found = True
                else:
                    new_lines.append(line)
            
            if not found:
                new_lines.append(target_languages_line + '\n')
            
            # Write back to .env file
            with open(env_path, 'w') as f:
                f.writelines(new_lines)


class SRTTranslatorMainWindow(QMainWindow):
    """Main window for SRT Translator GUI"""
    
    def __init__(self):
        super().__init__()
        self.settings_manager = SettingsManager()
        self.selected_files = []
        self.target_languages = {}
        self.translation_worker = None
        
        self.setup_window()
        self.setup_ui()
        self.load_previous_settings()
        self.apply_styles()
    
    def setup_window(self):
        """Set up window properties"""
        self.setWindowTitle("SRT Translator")
        self.setFixedSize(800, 700)
        # Removed problematic icon setting - will use default icon
    
    def setup_ui(self):
        """Set up the user interface"""
        # Create central widget with scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(20)
        
        # Create title bar
        title_bar = self.create_title_bar()
        main_layout.addWidget(title_bar)
        
        # Create main content container
        content_container = QFrame()
        content_container.setObjectName("contentContainer")
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(30, 20, 30, 20)
        content_layout.setSpacing(20)
        
        # Create sections
        api_section = self.create_api_section()
        file_section = self.create_file_section()
        language_section = self.create_language_section()
        translation_section = self.create_translation_section()
        
        content_layout.addWidget(api_section)
        content_layout.addWidget(file_section)
        content_layout.addWidget(language_section)
        content_layout.addWidget(translation_section)
        
        main_layout.addWidget(content_container)
        scroll_area.setWidget(central_widget)
        self.setCentralWidget(scroll_area)
    
    def create_title_bar(self) -> QFrame:
        """Create the title bar"""
        title_bar = QFrame()
        title_bar.setObjectName("titleBar")
        title_bar.setFixedHeight(60)
        
        layout = QHBoxLayout(title_bar)
        layout.setContentsMargins(20, 0, 20, 0)
        
        title_label = QLabel("SRT Translator")
        title_label.setObjectName("titleLabel")
        title_label.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(title_label)
        return title_bar
    
    def create_api_section(self) -> QGroupBox:
        """Create the API key section"""
        group = QGroupBox("OpenAI API Configuration")
        group.setObjectName("apiSection")
        
        layout = QVBoxLayout(group)
        layout.setSpacing(15)
        
        # API Key input
        api_layout = QHBoxLayout()
        api_label = QLabel("API Key:")
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setPlaceholderText("Enter your OpenAI API key")
        self.api_key_input.setObjectName("apiKeyInput")
        
        self.test_connection_btn = QPushButton("Test Connection")
        self.test_connection_btn.setObjectName("primaryButton")
        self.test_connection_btn.clicked.connect(self.test_api_connection)
        
        api_layout.addWidget(api_label)
        api_layout.addWidget(self.api_key_input)
        api_layout.addWidget(self.test_connection_btn)
        
        # Status label
        self.api_status_label = QLabel("")
        self.api_status_label.setObjectName("statusLabel")
        
        layout.addLayout(api_layout)
        layout.addWidget(self.api_status_label)
        
        return group
    
    def create_file_section(self) -> QGroupBox:
        """Create the file selection section"""
        group = QGroupBox("Source Files")
        group.setObjectName("fileSection")
        
        layout = QVBoxLayout(group)
        layout.setSpacing(15)
        
        # File selection buttons
        button_layout = QHBoxLayout()
        self.browse_files_btn = QPushButton("Browse Files")
        self.browse_files_btn.setObjectName("secondaryButton")
        self.browse_files_btn.clicked.connect(self.browse_files)
        
        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.setObjectName("secondaryButton")
        self.select_all_btn.clicked.connect(self.select_all_files)
        
        self.clear_all_btn = QPushButton("Clear All")
        self.clear_all_btn.setObjectName("secondaryButton")
        self.clear_all_btn.clicked.connect(self.clear_all_files)
        
        button_layout.addWidget(self.browse_files_btn)
        button_layout.addWidget(self.select_all_btn)
        button_layout.addWidget(self.clear_all_btn)
        button_layout.addStretch()
        
        # File list
        self.file_list = QListWidget()
        self.file_list.setObjectName("fileList")
        self.file_list.setSelectionMode(QListWidget.MultiSelection)
        
        # File count label
        self.file_count_label = QLabel("No files selected")
        self.file_count_label.setObjectName("fileCountLabel")
        
        layout.addLayout(button_layout)
        layout.addWidget(self.file_list)
        layout.addWidget(self.file_count_label)
        
        return group
    
    def create_language_section(self) -> QGroupBox:
        """Create the language selection section"""
        group = QGroupBox("Target Languages")
        group.setObjectName("languageSection")
        
        layout = QVBoxLayout(group)
        layout.setSpacing(15)
        
        # Popular languages grid
        popular_label = QLabel("Popular Languages")
        popular_label.setObjectName("subHeaderLabel")
        layout.addWidget(popular_label)
        
        popular_grid = QGridLayout()
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
            checkbox.toggled.connect(self.on_language_toggled)
            self.language_checkboxes[code] = checkbox
            popular_grid.addWidget(checkbox, i // 3, i % 3)
        
        layout.addLayout(popular_grid)
        
        # Search box
        search_layout = QHBoxLayout()
        search_label = QLabel("Search Languages:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Type to search languages...")
        self.search_input.setObjectName("searchInput")
        self.search_input.textChanged.connect(self.filter_languages)
        
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        
        layout.addLayout(search_layout)
        
        # Full language list
        self.language_list = QListWidget()
        self.language_list.setObjectName("languageList")
        self.language_list.setSelectionMode(QListWidget.MultiSelection)
        self.language_list.setMaximumHeight(150)
        self.language_list.itemSelectionChanged.connect(self.on_language_list_selection_changed)
        
        # Populate full language list
        self.populate_language_list()
        
        layout.addWidget(self.language_list)
        
        # Language count
        self.language_count_label = QLabel("No languages selected")
        self.language_count_label.setObjectName("languageCountLabel")
        layout.addWidget(self.language_count_label)
        
        return group
    
    def create_translation_section(self) -> QGroupBox:
        """Create the translation section"""
        group = QGroupBox("Translation")
        group.setObjectName("translationSection")
        
        layout = QVBoxLayout(group)
        layout.setSpacing(15)
        
        # Translate button
        self.translate_btn = QPushButton("Translate All Files")
        self.translate_btn.setObjectName("mainActionButton")
        self.translate_btn.setFixedHeight(50)
        self.translate_btn.clicked.connect(self.start_translation)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setObjectName("progressBar")
        
        # Log output
        self.log_output = QTextEdit()
        self.log_output.setObjectName("logOutput")
        self.log_output.setMaximumHeight(200)
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText("Translation progress will appear here...")
        
        layout.addWidget(self.translate_btn)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.log_output)
        
        return group
    
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
    
    def apply_styles(self):
        """Apply the style guide to the application"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #F8FAFC;
            }
            
            #titleBar {
                background-color: #2563EB;
                border-radius: 0px;
            }
            
            #titleLabel {
                color: white;
                font-size: 20px;
                font-weight: bold;
            }
            
            #contentContainer {
                background-color: white;
                border-radius: 8px;
                border: 1px solid #E5E7EB;
            }
            
            QGroupBox {
                font-size: 16px;
                font-weight: 600;
                color: #1E293B;
                border: 1px solid #E5E7EB;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            
            #subHeaderLabel {
                font-size: 14px;
                font-weight: 600;
                color: #374151;
            }
            
            QLabel {
                color: #374151;
                font-size: 13px;
            }
            
            #apiKeyInput, #searchInput {
                background-color: white;
                border: 1px solid #E5E7EB;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
                height: 40px;
            }
            
            #apiKeyInput:focus, #searchInput:focus {
                border-color: #2563EB;
                outline: none;
            }
            
            #primaryButton, #mainActionButton {
                background-color: #2563EB;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: 500;
                height: 40px;
            }
            
            #mainActionButton {
                height: 50px;
                font-size: 14px;
                font-weight: 600;
            }
            
            #primaryButton:hover, #mainActionButton:hover {
                background-color: #1D4ED8;
            }
            
            #secondaryButton {
                background-color: #F3F4F6;
                color: #374151;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 500;
                height: 36px;
            }
            
            #secondaryButton:hover {
                background-color: #E5E7EB;
            }
            
            #fileList, #languageList {
                background-color: #F9FAFB;
                border: 1px solid #E5E7EB;
                border-radius: 6px;
                padding: 5px;
                font-size: 13px;
            }
            
            #fileList::item, #languageList::item {
                padding: 5px;
                border-radius: 4px;
            }
            
            #fileList::item:selected, #languageList::item:selected {
                background-color: #DBEAFE;
                color: #1E293B;
            }
            
            #languageCheckbox {
                font-size: 13px;
                color: #374151;
                spacing: 8px;
            }
            
            #languageCheckbox::indicator {
                width: 16px;
                height: 16px;
            }
            
            #languageCheckbox::indicator:unchecked {
                border: 2px solid #D1D5DB;
                border-radius: 3px;
                background-color: white;
            }
            
            #languageCheckbox::indicator:checked {
                border: 2px solid #2563EB;
                border-radius: 3px;
                background-color: #2563EB;
            }
            
            #progressBar {
                border: 1px solid #E5E7EB;
                border-radius: 6px;
                text-align: center;
                background-color: #F9FAFB;
            }
            
            #progressBar::chunk {
                background-color: #2563EB;
                border-radius: 5px;
            }
            
            #logOutput {
                background-color: #F9FAFB;
                border: 1px solid #E5E7EB;
                border-radius: 6px;
                padding: 10px;
                font-family: "Consolas", "Monaco", monospace;
                font-size: 12px;
                color: #374151;
            }
            
            #statusLabel {
                font-size: 12px;
                color: #6B7280;
            }
            
            #fileCountLabel, #languageCountLabel {
                font-size: 12px;
                color: #6B7280;
                font-style: italic;
            }
        """)
    
    def load_previous_settings(self):
        """Load previous settings from storage"""
        # Load API key
        api_key = self.settings_manager.load_api_key()
        if api_key:
            self.api_key_input.setText(api_key)
        
        # Load selected files
        saved_files = self.settings_manager.load_selected_files()
        for file_path in saved_files:
            if os.path.exists(file_path):
                self.selected_files.append(file_path)
                self.add_file_to_list(file_path)
        
        # Load target languages
        saved_languages = self.settings_manager.load_target_languages()
        for name, code in saved_languages.items():
            if code in self.language_checkboxes:
                self.language_checkboxes[code].setChecked(True)
            # Note: List items will be handled by the checkbox logic
        
        self.update_file_count()
        self.update_language_count()
    
    def test_api_connection(self):
        """Test the OpenAI API connection"""
        api_key = self.api_key_input.text().strip()
        if not api_key:
            self.api_status_label.setText("Please enter an API key")
            self.api_status_label.setStyleSheet("color: #DC2626;")
            return
        
        # Save API key
        self.settings_manager.save_api_key(api_key)
        
        # Test connection (simplified - just check if key is valid format)
        if api_key.startswith("sk-") and len(api_key) > 20:
            self.api_status_label.setText("✓ API key format is valid")
            self.api_status_label.setStyleSheet("color: #065F46;")
        else:
            self.api_status_label.setText("✗ Invalid API key format")
            self.api_status_label.setStyleSheet("color: #DC2626;")
    
    def browse_files(self):
        """Browse for SRT files"""
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.ExistingFiles)
        file_dialog.setNameFilter("SRT Files (*.srt)")
        
        last_dir = self.settings_manager.load_last_input_directory()
        if last_dir and os.path.exists(last_dir):
            file_dialog.setDirectory(last_dir)
        
        if file_dialog.exec():
            selected_files = file_dialog.selectedFiles()
            logging.info(f"File dialog returned: {selected_files}")
            
            for file_path in selected_files:
                if file_path not in self.selected_files:
                    self.selected_files.append(file_path)
                    self.add_file_to_list(file_path)
                    logging.info(f"Added file to selection: {file_path}")
                else:
                    logging.info(f"File already selected: {file_path}")
            
            # Save directory
            if selected_files:
                self.settings_manager.save_last_input_directory(os.path.dirname(selected_files[0]))
            
            logging.info(f"Total selected files: {self.selected_files}")
            self.update_file_count()
            self.settings_manager.save_selected_files(self.selected_files)
    
    def add_file_to_list(self, file_path: str):
        """Add a file to the file list"""
        item = QListWidgetItem(os.path.basename(file_path))
        item.setData(Qt.UserRole, file_path)
        self.file_list.addItem(item)
    
    def select_all_files(self):
        """Select all files in the list"""
        for i in range(self.file_list.count()):
            self.file_list.item(i).setSelected(True)
    
    def clear_all_files(self):
        """Clear all selected files"""
        self.selected_files.clear()
        self.file_list.clear()
        self.update_file_count()
        self.settings_manager.save_selected_files([])
    
    def update_file_count(self):
        """Update the file count label"""
        count = len(self.selected_files)
        if count == 0:
            self.file_count_label.setText("No files selected")
        elif count == 1:
            self.file_count_label.setText("1 file selected")
        else:
            self.file_count_label.setText(f"{count} files selected")
    
    def on_language_toggled(self):
        """Handle language checkbox toggling"""
        self.update_target_languages_from_ui()
    
    def on_language_list_selection_changed(self):
        """Handle language list selection changes"""
        self.update_target_languages_from_ui()
    
    def update_target_languages_from_ui(self):
        """Update target languages from both checkboxes and list selection"""
        self.target_languages.clear()
        
        # Add languages from checkboxes
        for code, checkbox in self.language_checkboxes.items():
            if checkbox.isChecked():
                self.target_languages[checkbox.text()] = code
        
        # Add languages from list selection
        for item in self.language_list.selectedItems():
            name = item.text()
            code = item.data(Qt.UserRole)
            self.target_languages[name] = code
        
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
    
    def start_translation(self):
        """Start the translation process"""
        # Validate inputs
        if not self.validate_translation_inputs():
            return
        
        # Disable UI during translation
        self.translate_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.log_output.clear()
        
        # Start translation worker
        self.translation_worker = TranslationWorker(
            self.api_key_input.text().strip(),
            self.selected_files,
            self.target_languages
        )
        
        self.translation_worker.progress_updated.connect(self.update_log_output)
        self.translation_worker.translation_completed.connect(self.translation_finished)
        self.translation_worker.translation_error.connect(self.translation_error)
        
        self.translation_worker.start()
    
    def validate_translation_inputs(self) -> bool:
        """Validate translation inputs"""
        if not self.api_key_input.text().strip():
            QMessageBox.warning(self, "Missing API Key", "Please enter your OpenAI API key.")
            return False
        
        if not self.selected_files:
            QMessageBox.warning(self, "No Files Selected", "Please select at least one SRT file to translate.")
            return False
        
        if not self.target_languages:
            QMessageBox.warning(self, "No Languages Selected", "Please select at least one target language.")
            return False
        
        return True
    
    def update_log_output(self, message: str):
        """Update the log output with a message"""
        self.log_output.append(message)
        # Auto-scroll to bottom
        scrollbar = self.log_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def translation_finished(self, results: dict):
        """Handle translation completion"""
        self.progress_bar.setVisible(False)
        self.translate_btn.setEnabled(True)
        
        # Log the results being processed
        logging.info(f"Processing translation results: {results}")
        self.update_log_output(f"Processing translation results: {results}")
        
        # Show results dialog
        success_count = results.get("completed", 0)
        error_count = results.get("failed", 0)
        total_files = results.get("total_files", 0)
        
        logging.info(f"Success count: {success_count}, Error count: {error_count}, Total files: {total_files}")
        self.update_log_output(f"Success count: {success_count}, Error count: {error_count}, Total files: {total_files}")
        
        if error_count == 0:
            QMessageBox.information(
                self,
                "Translation Complete",
                f"Successfully translated {success_count} files!\n\n"
                f"Output files are available in the 'translated_srt_files' directory."
            )
        else:
            QMessageBox.warning(
                self,
                "Translation Complete with Errors",
                f"Translated {success_count} files successfully.\n"
                f"Encountered {error_count} errors.\n\n"
                f"Check the log output above for details."
            )
    
    def translation_error(self, error_message: str):
        """Handle translation error"""
        self.progress_bar.setVisible(False)
        self.translate_btn.setEnabled(True)
        
        QMessageBox.critical(
            self,
            "Translation Error",
            f"An error occurred during translation:\n\n{error_message}"
        )
    
    def closeEvent(self, event):
        """Handle window close event"""
        # Save current settings
        self.settings_manager.save_api_key(self.api_key_input.text().strip())
        self.settings_manager.save_selected_files(self.selected_files)
        self.settings_manager.save_target_languages(self.target_languages)
        
        event.accept()


def main():
    """Main function for testing the GUI"""
    import sys
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    window = SRTTranslatorMainWindow()
    window.show()
    sys.exit(app.exec())