"""
Main Window for SRT Translator GUI - Refactored Version
Uses modular components for better maintainability
"""

import os
import logging
from typing import List, Dict
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QScrollArea, QFileDialog
)
from PySide6.QtCore import Qt

from .settings_manager import SettingsManager
from .workers.translation_worker import TranslationWorker
from .styles.main_styles import MAIN_STYLESHEET
from .ui.api_section import APISection
from .ui.file_section import FileSection
from .ui.language_section import LanguageSection
from .ui.ai_config_section import AIConfigSection
from .ui.translation_section import TranslationSection
from .utils.validation import (
    validate_translation_inputs, show_validation_error,
    show_translation_results, show_translation_error
)


class SRTTranslatorMainWindow(QMainWindow):
    """Main window for SRT Translator GUI - Refactored"""
    
    def __init__(self):
        super().__init__()
        self.settings_manager = SettingsManager()
        self.translation_worker = None
        
        self.setup_window()
        self.setup_ui()
        self.connect_signals()
        self.load_previous_settings()
        self.apply_styles()
    
    def setup_window(self):
        """Set up window properties according to style guide"""
        self.setWindowTitle("SRT Translator")
        self.setFixedSize(800, 700)  # Fixed size as per style guide
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)
    
    def setup_ui(self):
        """Set up the user interface using modular components"""
        # Create central widget with scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)  # 10px margin from window edges
        main_layout.setSpacing(20)  # 20px vertical spacing between sections
        
        # Create title bar
        title_bar = self.create_title_bar()
        main_layout.addWidget(title_bar)
        
        # Create main content container (780px × 620px as per style guide)
        content_container = QFrame()
        content_container.setObjectName("contentContainer")
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(30, 20, 30, 20)  # 30px from left edge, 20px other margins
        content_layout.setSpacing(20)  # 20px vertical spacing between sections
        
        # Create modular sections
        self.api_section = APISection(self.settings_manager)
        self.file_section = FileSection(self.settings_manager)
        self.language_section = LanguageSection(self.settings_manager)
        self.ai_config_section = AIConfigSection()
        self.translation_section = TranslationSection()
        
        content_layout.addWidget(self.api_section)
        content_layout.addWidget(self.file_section)
        content_layout.addWidget(self.language_section)
        content_layout.addWidget(self.ai_config_section)
        content_layout.addWidget(self.translation_section)
        
        main_layout.addWidget(content_container)
        scroll_area.setWidget(central_widget)
        self.setCentralWidget(scroll_area)
    
    def create_title_bar(self) -> QFrame:
        """Create the title bar according to style guide"""
        title_bar = QFrame()
        title_bar.setObjectName("titleBar")
        title_bar.setFixedHeight(60)  # 60px height as per style guide
        
        layout = QHBoxLayout(title_bar)
        layout.setContentsMargins(20, 0, 20, 0)
        
        title_label = QLabel("SRT Translator")
        title_label.setObjectName("titleLabel")
        title_label.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(title_label)
        return title_bar
    
    def connect_signals(self):
        """Connect all component signals to their handlers"""
        # API Section signals
        self.api_section.connect_signals(
            self.test_api_connection,
            self.show_api_input
        )
        
        # File Section signals
        self.file_section.connect_signals(
            self.browse_files,
            self.select_all_files,
            self.clear_all_files,
            self.on_file_selection_changed
        )
        
        # Language Section signals
        self.language_section.connect_signals(
            self.on_language_toggled,
            self.on_language_list_selection_changed,
            self.on_language_search_changed
        )
        
        # AI Config Section signals
        self.ai_config_section.connect_signals(
            self.toggle_ai_config
        )
        
        # Translation Section signals
        self.translation_section.connect_signals(
            self.start_translation
        )
    
    def load_previous_settings(self):
        """Load previous settings from storage"""
        # Load API key
        self.api_section.load_saved_api_key()
        
        # Load selected files
        self.file_section.load_saved_files()
        
        # Load target languages
        self.language_section.load_saved_languages()
    
    def apply_styles(self):
        """Apply the complete style guide to the application"""
        self.setStyleSheet(MAIN_STYLESHEET)
    
    # API Section Handlers
    def test_api_connection(self):
        """Test the OpenAI API connection"""
        api_key = self.api_section.get_api_key()
        if not api_key:
            self.api_section.show_error("Please enter an API key")
            return
        
        # Save API key
        self.settings_manager.save_api_key(api_key)
        
        # Test connection (simplified - just check if key is valid format)
        if api_key.startswith("sk-") and len(api_key) > 20:
            self.api_section.show_status_mode(api_key)
        else:
            self.api_section.show_error("✗ Invalid API key format")
    
    def show_api_input(self):
        """Show the API input field when Edit Key is clicked"""
        self.api_section.show_input_mode()
    
    # File Section Handlers
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
                self.file_section.add_file(file_path)
            
            # Save directory
            if selected_files:
                self.settings_manager.save_last_input_directory(os.path.dirname(selected_files[0]))
            
            logging.info(f"Total selected files: {self.file_section.selected_files}")
            self.file_section.update_file_count_from_selection()
            self.settings_manager.save_selected_files(self.file_section.selected_files)
    
    def select_all_files(self):
        """Select all files in the list"""
        self.file_section.select_all_files()
    
    def clear_all_files(self):
        """Clear all selected files"""
        self.file_section.clear_all_files()
    
    def on_file_selection_changed(self):
        """Handle file selection changes"""
        self.file_section.update_file_count_from_selection()
        self.file_section.sync_selection_with_visual()
    
    # Language Section Handlers
    def on_language_toggled(self):
        """Handle language checkbox toggling"""
        self.language_section.update_target_languages_from_ui()
    
    def on_language_list_selection_changed(self):
        """Handle language list selection changes"""
        self.language_section.update_target_languages_from_ui()
    
    def on_language_search_changed(self):
        """Handle language search text changes"""
        self.language_section.filter_languages()
    
    # AI Config Section Handlers
    def toggle_ai_config(self):
        """Toggle the AI configuration section expansion"""
        self.ai_config_section.toggle_expansion()
    
    # Translation Section Handlers
    def start_translation(self):
        """Start the translation process"""
        # Get currently selected files from the file section
        selected_files = self.file_section.get_selected_files()
        
        # Update target languages from UI state to ensure synchronization
        self.language_section.update_target_languages_from_ui()
        
        # Get target languages from the language section
        target_languages = self.language_section.get_target_languages()
        
        # Get API key from settings manager
        api_key = self.settings_manager.load_api_key()
        
        # Validate inputs
        is_valid, error_message = validate_translation_inputs(api_key, selected_files, target_languages)
        if not is_valid:
            show_validation_error(self, "Validation Error", error_message)
            return
        
        # Start translation
        self.translation_section.start_translation()
        
        # Start translation worker
        self.translation_worker = TranslationWorker(
            api_key,
            selected_files,
            target_languages
        )
        
        self.translation_worker.progress_updated.connect(self.translation_section.update_log_output)
        self.translation_worker.translation_completed.connect(self.translation_finished)
        self.translation_worker.translation_error.connect(self.translation_error)
        
        self.translation_worker.start()
    
    def translation_finished(self, results: dict):
        """Handle translation completion"""
        self.translation_section.finish_translation()
        
        # Log the results being processed
        logging.info(f"Processing translation results: {results}")
        self.translation_section.update_log_output(f"Processing translation results: {results}")
        
        # Show results dialog
        show_translation_results(self, results)
    
    def translation_error(self, error_message: str):
        """Handle translation error"""
        self.translation_section.finish_translation()
        show_translation_error(self, error_message)
    
    def closeEvent(self, event):
        """Handle window close event"""
        # Stop any running translation thread
        if self.translation_worker and self.translation_worker.isRunning():
            self.translation_worker.quit()
            self.translation_worker.wait(1000)  # Wait up to 1 second
            if self.translation_worker.isRunning():
                self.translation_worker.terminate()  # Force terminate if needed
        
        # Save current settings
        self.settings_manager.save_api_key(self.api_section.get_api_key())
        self.settings_manager.save_selected_files(self.file_section.selected_files)
        self.settings_manager.save_target_languages(self.language_section.target_languages)
        
        event.accept()


def main():
    """Main function for testing the GUI"""
    import sys
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    window = SRTTranslatorMainWindow()
    window.show()
    sys.exit(app.exec()) 