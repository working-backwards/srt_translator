#!/usr/bin/env python3
"""
Main window for the SRT Translator application.
"""

import logging
import os
import sys

import psutil
from PySide6.QtCore import QObject, Qt, QThread, QTimer, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from srt_translator.gui.ai_config import AIConfigGenerator
from srt_translator.gui.config_manager import GUIConfigManager
from srt_translator.gui.settings_manager import SettingsManager
from srt_translator.gui.styles.main_styles import MAIN_STYLESHEET
from srt_translator.gui.ui.ai_config_section import AIConfigSection
from srt_translator.gui.ui.api_section import APISection
from srt_translator.gui.ui.file_section import FileSection
from srt_translator.gui.ui.language_section import LanguageSection
from srt_translator.gui.ui.translation_section import TranslationSection
from srt_translator.gui.utils.validation import (
    show_translation_error,
    show_translation_results,
    show_validation_error,
    validate_translation_inputs,
)
from srt_translator.gui.workers.translation_worker import TranslationWorker


class SRTTranslatorMainWindow(QMainWindow):
    """Main window for SRT Translator GUI - Refactored"""

    def __init__(self):
        super().__init__()

        # Set up logging for the GUI application (only once in worker;
        # avoid duplicate files)
        self.log_file = None
        self.logger = logging.getLogger(__name__)
        self.logger.info("SRT Translator GUI started")

        # Load language configuration once
        try:
            import json
            from srt_translator.core.config.language_config import LanguageConfig

            languages_path = "config/languages.json"
            with open(languages_path, "r", encoding="utf-8") as f:
                lang_data = json.load(f)
            self.language_config = LanguageConfig(lang_data)
            self.logger.info(
                f"Loaded language configuration with {len(self.language_config.get_all_languages())} languages"
            )
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.logger.error(f"Failed to load language configuration: {e}")
            QMessageBox.critical(
                self,
                "Configuration Error",
                f"Failed to load language configuration: {e}\n\nPlease ensure config/languages.json exists and is valid.",
            )
            raise RuntimeError(f"Language configuration load failed: {e}")

        # Initialize components
        self.settings_manager = SettingsManager(self.language_config)
        self.config_manager = GUIConfigManager(
            self.settings_manager, self.language_config
        )

        self.ai_config_generator = None
        self.ai_config_thread = None
        self.ai_config_worker = None
        self.translation_worker = None
        self.translation_thread = None

        # Initialize memory monitoring
        self._proc = psutil.Process(os.getpid())
        self._rss0 = self._proc.memory_info().rss
        self._memory_warning_shown = False
        self._mem_sample_count = 0

        # Set up the window
        self.setup_window()
        self.setup_ui()
        self.connect_signals()
        self.load_previous_settings()
        self.apply_styles()

        # Set up memory monitoring timer (paused by default; started on run)
        self.mem_timer = QTimer(self)
        self.mem_timer.timeout.connect(self._sample_memory)

    def setup_window(self):
        """Set up window properties according to style guide"""
        self.setWindowTitle("SRT Translator")
        self.resize(800, 700)  # Initial size, but now resizable
        self.setMinimumSize(800, 700)  # Prevent window from becoming too small
        self.setWindowFlags(
            Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint
        )

    def setup_ui(self):
        """Set up the user interface using modular components"""
        # Create central widget with scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)  # 10px margin from edges
        main_layout.setSpacing(20)  # 20px vertical spacing between sections

        # Create title bar
        title_bar = self.create_title_bar()
        main_layout.addWidget(title_bar)

        # Create main content container (780px × 620px as per style guide)
        content_container = QFrame()
        content_container.setObjectName("contentContainer")
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(
            30, 20, 30, 20
        )  # 30px from left edge, 20px other margins
        content_layout.setSpacing(20)  # 20px vertical spacing between sections

        # Create modular sections
        self.api_section = APISection(self.settings_manager)
        self.file_section = FileSection(self.settings_manager)
        self.language_section = LanguageSection(
            self.settings_manager, self.language_config
        )
        self.ai_config_section = AIConfigSection()
        self.translation_section = TranslationSection()

        content_layout.addWidget(self.file_section)
        content_layout.addWidget(self.language_section)
        content_layout.addWidget(self.api_section)
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
            self.test_api_connection, self.show_api_input, self.toggle_api_configuration
        )

        # File Section signals
        self.file_section.connect_signals(
            self.browse_files,
            self.select_all_files,
            self.clear_all_files,
            self.on_file_selection_changed,
            self.browse_output_directory,
        )

        # Language Section signals
        self.language_section.connect_signals(
            self.on_language_toggled,
            self.on_language_list_selection_changed,
            self.on_language_search_changed,
        )

        # Translation Settings Section signals
        self.ai_config_section.connect_signals(
            self.toggle_translation_settings,
            self.generate_translation_settings,
            self.edit_translation_settings,
            self.regenerate_translation_settings,
            self.view_translation_settings_details,
            self.show_ai_config_help,
        )

        # Translation Section signals
        self.translation_section.connect_signals(self.start_translation)

    def load_previous_settings(self):
        """Load previous settings from storage"""
        # Load API key and set connection status
        api_key = self.settings_manager.load_api_key()
        if api_key and api_key.startswith("sk-") and len(api_key) > 20:
            self.api_section.set_api_key(api_key)
            self.api_section.set_connected_status(True)
        else:
            self.api_section.load_saved_api_key()
            self.api_section.set_connected_status(False)

        # Load selected files
        self.file_section.load_saved_files()

        # Load output directory
        self.file_section.load_saved_output_directory()

        # Load target languages
        self.language_section.load_saved_languages()

        # Load and display existing Translation Settings if available
        dnt_terms, termbase, _ = self.settings_manager.load_ai_config()
        if dnt_terms or termbase:
            self.ai_config_section.update_dnt_display(dnt_terms)
            self.ai_config_section.update_termbase_display(termbase)
            self.ai_config_section.set_action_buttons_enabled(True)
            self.ai_config_section.set_configured_status(True)

    def apply_styles(self):
        """Apply the complete style guide to the application"""
        self.setStyleSheet(MAIN_STYLESHEET)

    # API Section Handlers
    def toggle_api_configuration(self):
        """Toggle the API Configuration section expansion"""
        self.api_section.toggle_expansion()

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
            self.api_section.set_connected_status(True)
            self.api_section.clear_error()
        else:
            self.api_section.show_error("Invalid API key format")

    def show_api_input(self):
        """Show the API input field when Edit Settings is clicked"""
        self.api_section.set_connected_status(False)  # Switch to input mode

    # File Section Handlers
    def browse_files(self):
        """Browse for SRT files"""
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.ExistingFiles)
        file_dialog.setNameFilter("SRT Files (*.srt)")

        last_dir = self.settings_manager.load_last_input_directory()
        if last_dir and os.path.exists(last_dir):
            file_dialog.setDirectory(last_dir)
        else:
            file_dialog.setDirectory(os.getcwd())

        if file_dialog.exec():
            selected_files = file_dialog.selectedFiles()
            for file_path in selected_files:
                self.file_section.add_file(file_path)

            # Save directory
            if selected_files:
                last_dir = os.path.dirname(selected_files[0])
                self.settings_manager.save_last_input_directory(last_dir)

    def browse_output_directory(self):
        """Browse for output directory"""
        self.file_section.browse_output_directory()

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

        # Enable/disable Translation Settings generation based on file selection
        selected_files = self.file_section.get_selected_files()
        self.ai_config_section.set_generate_button_enabled(len(selected_files) > 0)

        # Check if we have existing Translation Settings and enable action buttons
        dnt_terms, termbase, _ = self.settings_manager.load_ai_config()
        has_translation_settings = bool(dnt_terms or termbase)
        self.ai_config_section.set_action_buttons_enabled(has_translation_settings)

        # Update cost estimate
        self.update_cost_estimate()

    # Language Section Handlers
    def on_language_toggled(self):
        """Handle language checkbox toggling"""
        self.language_section.update_target_languages_from_ui()
        # Check for adaptive updates after language selection
        self.language_section.check_for_adaptive_updates()
        self.update_cost_estimate()

    def on_language_list_selection_changed(self):
        """Handle language list selection changes"""
        self.language_section.update_target_languages_from_ui()
        # Check for adaptive updates after language selection
        self.language_section.check_for_adaptive_updates()
        self.update_cost_estimate()

    def on_language_search_changed(self):
        """Handle language search text changes"""
        self.language_section.filter_languages()

    # AI Config Section Handlers
    def toggle_translation_settings(self):
        """Toggle the Translation Settings section expansion"""
        self.ai_config_section.toggle_expansion()

    def generate_translation_settings(self):
        """Generate Translation Settings for the selected files"""
        # Get selected files and target languages
        selected_files = self.file_section.get_selected_files()
        target_languages = self.language_section.get_target_languages()
        api_key = self.settings_manager.load_api_key()

        self.logger.info(
            f"Starting AI configuration generation with {len(selected_files)} "
            f"files and {len(target_languages)} languages"
        )

        # Validate inputs
        if not selected_files:
            show_validation_error(
                self, "No Files Selected", "Please select SRT files for AI analysis."
            )
            return

        if not api_key:
            show_validation_error(
                self,
                "No API Key",
                "Please enter an OpenAI API key to generate Translation Settings.",
            )
            return

        if not target_languages:
            show_validation_error(
                self,
                "No Target Languages",
                "Please select at least one target language.",
            )
            return

        self.logger.info(
            f"Selected files: {[os.path.basename(f) for f in selected_files]}"
        )
        self.logger.info(f"Target languages: {list(target_languages.values())}")

        # Initialize AI config generator if not already done
        if not self.ai_config_generator:
            self.ai_config_generator = AIConfigGenerator(api_key, self.language_config)

        # Show progress and disable button
        self.ai_config_section.show_progress(True)

        # Start AI configuration generation in a separate thread

        class AIConfigWorker(QObject):
            finished = Signal(tuple)  # (dnt_terms, termbase, source_language)
            error = Signal(str)
            progress = Signal(str)  # Add progress signal for GUI updates

            def __init__(self, ai_generator, files, languages):
                super().__init__()
                self.ai_generator = ai_generator
                self.files = files
                self.languages = languages
                self.logger = logging.getLogger(__name__)

                # Set up logging bridge to capture AI config logs
                self._setup_logging_bridge()

            def run(self):
                try:
                    self.progress.emit(
                        "AI Config Worker: Starting batch-level AI config generation"
                    )
                    self.logger.info(
                        "AI Config Worker: Starting batch-level AI config generation"
                    )

                    # Generate ONE batch-level DNT list and ONE termbase for ALL target languages
                    batch_config = self.ai_generator.generate_batch_ai_config(
                        source_file_paths=self.files, target_lang_codes=self.languages
                    )

                    progress_msg = f"AI Config Worker: Generated {len(batch_config.dnt_terms)} DNT terms and termbase for {len(batch_config.termbase)} languages (batch-level)"
                    self.progress.emit(progress_msg)
                    self.logger.info(progress_msg)

                    self.finished.emit(
                        (
                            batch_config.dnt_terms,
                            batch_config.termbase,
                            batch_config.source_language,
                        )
                    )

                except Exception as e:
                    error_msg = f"AI Config Worker: Error during generation: {e}"
                    self.progress.emit(error_msg)
                    self.logger.error(error_msg)
                    self.error.emit(str(e))

            def _setup_logging_bridge(self):
                """Set up logging bridge to capture AI config logs and send to GUI"""
                try:
                    # Create a custom handler that emits progress signals
                    class ProgressLogHandler(logging.Handler):
                        def __init__(self, worker):
                            super().__init__()
                            self.worker = worker

                        def emit(self, record):
                            try:
                                msg = self.format(record)
                                self.worker.progress.emit(msg)
                            except Exception:
                                pass

                    # Set up the handler for AI config logs
                    progress_handler = ProgressLogHandler(self)
                    progress_handler.setLevel(logging.INFO)

                    # Format the logs nicely
                    formatter = logging.Formatter("%(message)s")
                    progress_handler.setFormatter(formatter)

                    # Add handler to AI config logger
                    ai_logger = logging.getLogger("srt_translator.gui.ai_config")
                    ai_logger.addHandler(progress_handler)
                    ai_logger.setLevel(logging.INFO)

                    # Also capture our own worker logs
                    self.logger.addHandler(progress_handler)

                except Exception as e:
                    # Fallback if logging bridge fails
                    self.logger.warning(f"Failed to set up logging bridge: {e}")

        # Create and start worker thread
        self.ai_config_thread = QThread()
        self.ai_config_worker = AIConfigWorker(
            self.ai_config_generator, selected_files, list(target_languages.values())
        )
        self.ai_config_worker.moveToThread(self.ai_config_thread)

        self.ai_config_thread.started.connect(self.ai_config_worker.run)
        self.ai_config_worker.progress.connect(self.ai_config_section.update_progress)
        self.ai_config_worker.finished.connect(self.ai_config_generation_finished)
        self.ai_config_worker.error.connect(self.ai_config_generation_error)
        self.ai_config_worker.finished.connect(self.ai_config_thread.quit)
        self.ai_config_worker.error.connect(self.ai_config_thread.quit)

        # Ensure proper teardown:
        self.ai_config_thread.finished.connect(self.ai_config_worker.deleteLater)
        self.ai_config_thread.finished.connect(self.ai_config_thread.deleteLater)

        self.ai_config_thread.start()

    def ai_config_generation_finished(self, result):
        """Handle AI configuration generation completion"""
        dnt_terms, termbase, source_language = result

        self.logger.info(
            f"AI configuration generation completed: {len(dnt_terms)} DNT terms, "
            f"{len(termbase)} languages in termbase"
        )

        # Hide progress
        self.ai_config_section.show_progress(False)

        # Save AI configuration
        self.settings_manager.save_ai_config(dnt_terms, termbase, source_language)
        self.logger.info("AI configuration saved to settings")

        # Update displays
        self.ai_config_section.update_dnt_display(dnt_terms)
        self.ai_config_section.update_termbase_display(termbase)

        # Enable action buttons and set configured status
        self.ai_config_section.set_action_buttons_enabled(True)
        self.ai_config_section.set_configured_status(True)

        # Show success message
        QMessageBox.information(
            self,
            "Translation Settings Generated",
            f"Successfully generated Translation Settings:\n"
            f"• {len(dnt_terms)} DNT terms\n"
            f"• Termbase for {len(termbase)} languages\n\n"
            f"The settings will be used automatically for translation.\n"
            f"You can now click 'Edit Settings' to review and modify the results.",
        )

    def ai_config_generation_error(self, error_message: str):
        """Handle AI configuration generation errors"""
        self.logger.error(f"AI configuration generation failed: {error_message}")

        # Hide progress
        self.ai_config_section.show_progress(False)

        # Get detailed error information
        if self.ai_config_generator is not None:
            try:
                error_details = self.ai_config_generator.get_error_details(
                    Exception(error_message)
                )
                title = error_details.get("title", "AI Configuration Failed")
                message = error_details.get("message", error_message)
                suggestion = error_details.get("suggestion", "")

                # Show detailed error message
                QMessageBox.warning(
                    self, title, f"{message}\n\n{suggestion}" if suggestion else message
                )
                return
            except Exception:
                # Fallback to simple error message
                pass

        # Fallback to simple error message
        QMessageBox.warning(
            self,
            "AI Configuration Failed",
            f"An error occurred while generating translation settings:\n\n{error_message}",
        )

    def edit_translation_settings(self):
        """Open the Translation Settings editor dialog."""
        # Get current Translation Settings
        dnt_terms, termbase, _ = self.settings_manager.load_ai_config()

        if not dnt_terms and not termbase:
            QMessageBox.warning(
                self,
                "No Translation Settings",
                "No Translation Settings have been generated yet.\n"
                "Please generate settings first.",
            )
            return

        # Import the dialog class
        from srt_translator.gui.ui.ai_config_section import EditConfigurationDialog

        # Create and show the edit dialog
        dialog = EditConfigurationDialog(dnt_terms, termbase, self)

        if dialog.exec():
            # User clicked OK, get modified configuration
            modified_terms, modified_termbase = dialog.get_modified_config()

            if dialog.has_changes():
                # Save the modified configuration (preserve existing source language)
                dnt_terms, termbase, source_language = (
                    self.settings_manager.load_ai_config()
                )
                self.settings_manager.save_ai_config(
                    modified_terms, modified_termbase, source_language
                )

                # Update displays
                self.ai_config_section.update_dnt_display(modified_terms)
                self.ai_config_section.update_termbase_display(modified_termbase)

                # Show confirmation
                QMessageBox.information(
                    self,
                    "Translation Settings Updated",
                    "Your changes have been saved and will be used for translation.",
                )

                logging.info(
                    f"Translation Settings updated: {len(modified_terms)} terms, "
                    f"{len(modified_termbase)} languages"
                )

    def regenerate_translation_settings(self):
        """Regenerate Translation Settings for selected files"""
        # This is essentially the same as generate, but we'll expand the section first
        if not self.ai_config_section.is_expanded:
            self.ai_config_section.toggle_expansion()  # Ensure section is expanded
        self.generate_translation_settings()

    def view_translation_settings_details(self):
        """View detailed Translation Settings"""
        # Get current configuration
        dnt_terms, termbase, _ = self.settings_manager.load_ai_config()

        if not dnt_terms and not termbase:
            QMessageBox.warning(
                self,
                "No Translation Settings",
                "No Translation Settings have been generated yet.\nPlease generate settings first.",
            )
            return

        # Expand the section to show details
        if not self.ai_config_section.is_expanded:
            self.ai_config_section.toggle_expansion()

        # Show detailed information
        dnt_text = ", ".join(dnt_terms) if dnt_terms else "No DNT terms"
        termbase_text = ""
        if termbase:
            for language, terms in termbase.items():
                termbase_text += f"{language}:\n"
                for english_term, translation in terms.items():
                    termbase_text += f"  • {english_term} → {translation}\n"
                termbase_text += "\n"
        else:
            termbase_text = "No termbase entries"

        # Update displays with full details
        self.ai_config_section.set_dnt_display(dnt_text)
        self.ai_config_section.set_termbase_display(termbase_text)

    def show_ai_config_help(self):
        """Show help dialog for AI Configuration"""
        QMessageBox.information(
            self,
            "AI Configuration Help",
            """
<h3>What AI Configuration Does</h3>
<p>Analyzes your course content and automatically generates optimal translation settings:</p>

<h4>📝 DNT Terms</h4>
<ul>
<li>Company names (Amazon, Google, Microsoft)</li>
<li>People's names (Jeff Bezos, instructor names)</li>
<li>Technical terms (API, CEO, Excel)</li>
<li>Brands better known in English internationally</li>
</ul>

<h4>📚 Termbase</h4>
<ul>
<li>Consistent professional translations for key terms</li>
<li>Business vocabulary specific to your course</li>
<li>Industry terminology that needs standardization</li>
</ul>

<h3>What You Need</h3>
<ul>
<li><strong>OpenAI API Key:</strong> Get one at platform.openai.com (~$2-10 per course)</li>
<li><strong>Multiple Files:</strong> 2-5 subtitle files work best for analysis</li>
<li><strong>Representative Content:</strong> Files containing your key terminology</li>
</ul>

<h3>Best For</h3>
<ul>
<li>Business courses with case studies</li>
<li>Technical training with software names</li>
<li>Professional development courses</li>
<li>Any course with specialized vocabulary</li>
</ul>

<p><em>Analysis takes 30-60 seconds and significantly improves translation quality.</em></p>
""",
        )

    def update_cost_estimate(self):
        """Update the cost estimate based on current selection"""
        selected_files = self.file_section.get_selected_files()
        target_languages = self.language_section.get_target_languages()

        if not selected_files or not target_languages:
            self.translation_section.update_cost_estimate("$0.00")
            return

        # Simple cost estimation: $0.002 per 1K tokens
        # Assume average of 1000 tokens per SRT file per language
        total_files = len(selected_files)
        total_languages = len(target_languages)
        estimated_tokens = total_files * total_languages * 1000
        estimated_cost = (estimated_tokens / 1000) * 0.002

        # Add AI configuration cost if not already generated
        dnt_terms, termbase, _ = self.settings_manager.load_ai_config()
        if not dnt_terms and not termbase:
            estimated_cost += 0.10  # AI configuration cost

        cost_text = f"${estimated_cost:.2f}"
        self.translation_section.update_cost_estimate(cost_text)

    # Translation Section Handlers
    def start_translation(self):
        """Start the translation process"""
        # Start memory sampling for this run
        if self.mem_timer and not self.mem_timer.isActive():
            self.mem_timer.start(30000)
        # Get currently selected files from the file section
        selected_files = self.file_section.get_selected_files()

        # Update target languages from UI state to ensure synchronization
        self.language_section.update_target_languages_from_ui()
        # DO NOT call check_for_adaptive_updates() here as it can override current selections

        # Get target languages from the language section
        target_languages = self.language_section.get_target_languages()

        # Update SettingsManager with current state (single source of truth)
        self.settings_manager.update_target_languages(target_languages)

        # Debug logging to track language selection
        self.logger.info(f"Translation requested with languages: {target_languages}")
        self.logger.info(f"Language names: {list(target_languages.keys())}")
        self.logger.info(f"Language codes: {list(target_languages.values())}")
        self.logger.info(f"Number of languages selected: {len(target_languages)}")

        # Get API key from settings manager
        api_key = self.settings_manager.load_api_key()

        # Validate inputs
        is_valid, error_message = validate_translation_inputs(
            api_key, selected_files, target_languages
        )
        if not is_valid:
            show_validation_error(self, "Validation Error", error_message)
            return

        # Start translation
        self.translation_section.start_translation()

        # Get output directory from file section
        output_directory = self.file_section.get_output_directory()

        # Start translation worker with settings manager (not config manager)
        # The worker will automatically run the fixer after translation completes
        # with hardcoded aggressiveness of 0.75 for consistent behavior
        self.translation_worker = TranslationWorker(
            api_key,
            selected_files,
            target_languages,
            self.settings_manager,  # Use settings_manager instead of config_manager
            output_directory,
        )

        # Create QThread for proper lifecycle management
        self.translation_thread = QThread()
        self.translation_worker.moveToThread(self.translation_thread)

        # Connect worker signals to handlers
        self.translation_worker.progress_updated.connect(
            self.translation_section.update_log_output
        )
        self.translation_worker.translation_completed.connect(self.translation_finished)
        self.translation_worker.translation_error.connect(self.translation_error)

        # Connect thread lifecycle signals for proper cleanup
        self.translation_worker.translation_completed.connect(
            self.translation_thread.quit
        )
        self.translation_worker.translation_error.connect(self.translation_thread.quit)
        self.translation_thread.finished.connect(self.translation_worker.deleteLater)
        self.translation_thread.finished.connect(self.translation_thread.deleteLater)

        # Connect thread start to worker run
        self.translation_thread.started.connect(self.translation_worker.run)

        # Start the thread
        self.translation_thread.start()

    def translation_finished(self, results: dict):
        """Handle translation completion"""
        self.translation_section.finish_translation()

        # Pause memory sampling after run completes
        if self.mem_timer and self.mem_timer.isActive():
            self.mem_timer.stop()

        # Log the results being processed
        logging.info(f"Processing translation results: {results}")
        self.translation_section.update_log_output(
            f"Processing translation results: {results}"
        )

        # Show results dialog
        show_translation_results(self, results)

        # Qt deleteLater handles cleanup automatically

    def translation_error(self, error_message: str):
        """Handle translation error"""
        self.translation_section.finish_translation()
        # Pause memory sampling on error as well
        if self.mem_timer and self.mem_timer.isActive():
            self.mem_timer.stop()
        show_translation_error(self, error_message)

        # Qt deleteLater handles cleanup automatically

    def closeEvent(self, event):
        """Handle window close event"""
        # Request cooperative stop of translation worker
        if hasattr(self, "translation_worker") and self.translation_worker is not None:
            self.translation_worker.request_stop()

        # Stop any running translation thread with proper cleanup
        try:
            thread = getattr(self, "translation_thread", None)
            if thread is not None and thread.isRunning():
                thread.quit()
                thread.wait(10000)  # Wait up to 10 seconds for cooperative stop
        except RuntimeError:
            # Thread already deleted; ignore
            pass
        finally:
            # Clear references to avoid calling methods on deleted Qt objects
            if hasattr(self, "translation_worker"):
                self.translation_worker = None
            if hasattr(self, "translation_thread"):
                self.translation_thread = None
            # Never use terminate() - let Qt handle cleanup properly

        # Save current settings
        self.settings_manager.save_api_key(self.api_section.get_api_key())
        self.settings_manager.save_selected_files(self.file_section.selected_files)
        self.settings_manager.save_target_languages(
            self.language_section.target_languages
        )

        event.accept()

    def _sample_memory(self):
        """Sample memory usage and warn if it grows too much"""
        try:
            rss = self._proc.memory_info().rss
            growth_mb = (rss - self._rss0) / (1024 * 1024)

            # Log memory usage every 5 minutes (10 samples)
            if hasattr(self, "_mem_sample_count"):
                self._mem_sample_count += 1
            else:
                self._mem_sample_count = 1

            if self._mem_sample_count % 10 == 0:  # Every 5 minutes
                self.logger.debug(
                    f"Memory usage: {growth_mb:.1f} MB growth since start"
                )

            # Warn if memory growth exceeds 1GB
            if growth_mb > 1000 and not self._memory_warning_shown:
                self._memory_warning_shown = True
                self.logger.warning(
                    f"High memory usage detected: {growth_mb:.1f} MB growth"
                )

                # Show warning to user
                QMessageBox.warning(
                    self,
                    "High Memory Usage",
                    f"Memory usage has grown significantly ({growth_mb:.1f} MB).\n"
                    "Consider restarting the application after completing the current "
                    "translation.\n\n"
                    "This helps prevent crashes during long translation sessions.",
                )
        except Exception as e:
            self.logger.error(f"Error sampling memory: {e}")


def main(argv=None):
    """Main function for the GUI application"""
    import argparse
    from importlib.metadata import PackageNotFoundError, version

    def _print_version():
        try:
            print(f"SRT Translator {version('srt-translator')}")
        except PackageNotFoundError:
            # Fallback if running from source without installed dist name
            print("SRT Translator")

    def launch_gui():
        try:
            from PySide6.QtWidgets import QApplication
        except ImportError as e:
            print(
                "PySide6 is required for the GUI. Install with: pip install 'srt-translator[gui]'",
                flush=True,
            )
            raise SystemExit(1) from e

        app = QApplication(sys.argv)
        window = SRTTranslatorMainWindow()
        window.show()
        sys.exit(app.exec())

    parser = argparse.ArgumentParser(
        prog="srtx",
        description=(
            "Launch the SRT Translator graphical user interface.\n"
            "Use the GUI to select subtitle files, choose target languages,\n"
            "and configure translation settings."
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--version",
        "-v",
        action="store_true",
        help="Show the application version and exit.",
    )

    args = parser.parse_args(argv)

    if args.version:
        _print_version()
        return 0  # argparse already uses stdout; exit code 0

    # Default: launch GUI
    launch_gui()
