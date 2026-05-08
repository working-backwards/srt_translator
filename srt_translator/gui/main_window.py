#!/usr/bin/env python3
"""
Main window for the SRT Translator application.

Uses a tabbed wizard layout with 4 tabs:
1. Files — browse and select SRT files
2. Languages — choose target languages
3. Translation Settings — generate/edit DNT terms and termbase
4. Translate — run translations and view progress
"""

import logging
import os
import time
from pathlib import Path

import psutil
from PySide6.QtCore import QObject, Qt, QThread, QTimer, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from srt_translator.core.config.utils import normalize_target_languages
from srt_translator.core.constants import (
    AI_CONFIG_BASE_COST,
    BYTES_TO_TOKENS_RATIO,
    PRICE_PER_1K_TOKENS,
    TRANSLATION_OVERHEAD_FACTOR,
)
from srt_translator.gui.ai_config import AIConfigGenerator
from srt_translator.gui.settings_manager import SettingsManager
from srt_translator.gui.styles.main_styles import MAIN_STYLESHEET
from srt_translator.gui.ui.ai_config_section import AIConfigSection
from srt_translator.gui.ui.file_section import FileSection
from srt_translator.gui.ui.language_section import LanguageSection
from srt_translator.gui.ui.settings_dialog import SettingsDialog
from srt_translator.gui.ui.translation_section import TranslationSection
from srt_translator.gui.utils.termbase_merger import (
    load_dnt_terms_from_file,
    load_termbase_from_file,
    merge_dnt_terms,
    merge_termbase,
)
from srt_translator.gui.utils.validation import (
    show_translation_error,
    show_translation_results,
    show_validation_error,
    validate_translation_inputs,
)
from srt_translator.gui.workers.translation_worker import TranslationWorker

# Tab indices
TAB_FILES = 0
TAB_LANGUAGES = 1
TAB_SETTINGS = 2
TAB_TRANSLATE = 3


class SRTTranslatorMainWindow(QMainWindow):
    """Main window for SRT Translator GUI — tabbed wizard layout."""

    def __init__(self):
        super().__init__()

        self.logger = logging.getLogger(__name__)
        self.logger.info("SRT Translator GUI started")

        # Load language configuration once
        try:
            from srt_translator.config import load_language_catalog
            from srt_translator.core.config.language_config import LanguageConfig

            lang_data = load_language_catalog()
            self.language_config = LanguageConfig(lang_data)
            self.logger.info(
                "Loaded language configuration with %s languages",
                len(self.language_config.get_all_languages()),
            )
        except Exception as e:
            self.logger.error("Failed to load language configuration: %s", e)
            QMessageBox.critical(
                self,
                "Configuration Error",
                f"Failed to load language configuration: {e}\n\nPlease ensure the application is properly installed.",
            )
            raise RuntimeError(f"Language configuration load failed: {e}") from e

        # Initialize components
        self.settings_manager = SettingsManager(self.language_config)
        self.settings_manager.migrate_from_native_if_needed()

        self.ai_config_generator = None
        self.ai_config_thread = None
        self.ai_config_worker = None
        self.translation_worker = None
        self.translation_thread = None

        # Track the highest tab the user has successfully validated to
        self._max_visited_tab = TAB_FILES

        # Initialize memory monitoring
        self._proc = psutil.Process(os.getpid())
        self._rss0 = self._proc.memory_info().rss
        self._memory_warning_shown = False

        # Initialize HTML report tracking
        self._last_eval_json: Path | None = None
        self._last_eval_html: Path | None = None

        # Set up the window
        self.setup_window()
        self.setup_ui()
        self.connect_signals()
        self.load_previous_settings()
        self.update_cost_estimate()
        self.apply_styles()

        # Set up memory monitoring timer (paused by default; started on run)
        self.mem_timer = QTimer(self)
        self.mem_timer.timeout.connect(self._sample_memory)

    # ------------------------------------------------------------------ #
    #  Window setup
    # ------------------------------------------------------------------ #

    def setup_window(self):
        """Set up window properties."""
        self.setWindowTitle("SRT Translator")
        self.resize(820, 680)
        self.setMinimumSize(800, 650)
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)

    # ------------------------------------------------------------------ #
    #  UI construction
    # ------------------------------------------------------------------ #

    def setup_ui(self):
        """Build the tabbed wizard UI."""
        central_widget = QWidget()
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(0)

        # Title bar with settings button
        title_bar = self._create_title_bar()
        root_layout.addWidget(title_bar)

        # --- Tab widget ---
        self.tab_widget = QTabWidget()
        self.tab_widget.setObjectName("wizardTabs")

        # Create section widgets
        self.file_section = FileSection(self.settings_manager)
        self.language_section = LanguageSection(self.settings_manager, self.language_config)
        self.ai_config_section = AIConfigSection()
        self.translation_section = TranslationSection()

        # Build tab pages (section + nav buttons)
        files_page = self._wrap_tab_page(self.file_section, show_next=True, show_back=False)
        languages_page = self._wrap_tab_page(self.language_section, show_next=True, show_back=True)
        settings_page = self._wrap_tab_page(self.ai_config_section, show_next=True, show_back=True)
        translate_page = self._wrap_tab_page(self.translation_section, show_next=False, show_back=True)

        self.tab_widget.addTab(files_page, "1. Files")
        self.tab_widget.addTab(languages_page, "2. Languages")
        self.tab_widget.addTab(settings_page, "3. Translation Settings")
        self.tab_widget.addTab(translate_page, "4. Translate")

        # Disable forward tabs initially
        self._update_tab_enabled_states()

        root_layout.addWidget(self.tab_widget)
        self.setCentralWidget(central_widget)

    def _create_title_bar(self) -> QFrame:
        """Create the title bar with settings gear button on the right."""
        title_bar = QFrame()
        title_bar.setObjectName("titleBar")
        title_bar.setFixedHeight(60)

        layout = QHBoxLayout(title_bar)
        layout.setContentsMargins(20, 0, 20, 0)

        title_label = QLabel("SRT Translator")
        title_label.setObjectName("titleLabel")

        # Settings gear button
        self.settings_btn = QPushButton("\u2699")  # ⚙
        self.settings_btn.setObjectName("settingsButton")
        self.settings_btn.setFixedSize(36, 36)
        self.settings_btn.setToolTip("Application Settings (API key, model, etc.)")
        self.settings_btn.clicked.connect(self._open_settings_dialog)

        layout.addWidget(title_label)
        layout.addStretch()
        layout.addWidget(self.settings_btn)

        return title_bar

    def _wrap_tab_page(self, section_widget: QWidget, *, show_next: bool, show_back: bool) -> QWidget:
        """Wrap a section widget in a page with optional Back / Next buttons."""
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(30, 20, 30, 20)
        page_layout.setSpacing(20)

        page_layout.addWidget(section_widget)
        page_layout.addStretch()

        if show_back or show_next:
            nav = QHBoxLayout()
            if show_back:
                back_btn = QPushButton("Back")
                back_btn.setObjectName("backButton")
                back_btn.clicked.connect(self._go_back)
                nav.addWidget(back_btn)
            nav.addStretch()
            if show_next:
                next_btn = QPushButton("Next")
                next_btn.setObjectName("nextButton")
                next_btn.clicked.connect(self._go_next)
                nav.addWidget(next_btn)
            page_layout.addLayout(nav)

        return page

    # ------------------------------------------------------------------ #
    #  Tab navigation and validation
    # ------------------------------------------------------------------ #

    def _update_tab_enabled_states(self):
        """Enable tabs up to _max_visited_tab; disable the rest."""
        for i in range(self.tab_widget.count()):
            self.tab_widget.setTabEnabled(i, i <= self._max_visited_tab)

    def _go_next(self):
        """Validate current tab and advance to the next."""
        current = self.tab_widget.currentIndex()

        if current == TAB_FILES:
            if not self._validate_files_tab():
                return
        elif current == TAB_LANGUAGES:
            if not self._validate_languages_tab():
                return
        # TAB_SETTINGS has no validation on Next

        next_idx = current + 1
        if next_idx < self.tab_widget.count():
            # Unlock the next tab if it's further than we've been
            if next_idx > self._max_visited_tab:
                self._max_visited_tab = next_idx
                self._update_tab_enabled_states()
            self.tab_widget.setCurrentIndex(next_idx)

    def _go_back(self):
        """Go to the previous tab (always allowed)."""
        current = self.tab_widget.currentIndex()
        if current > 0:
            self.tab_widget.setCurrentIndex(current - 1)

    def _validate_files_tab(self) -> bool:
        """Validate: at least one valid .srt file selected."""
        selected_files = self.file_section.get_selected_files()
        if not selected_files:
            show_validation_error(self, "No Files Selected", "Please select at least one SRT file.")
            return False

        # Check all selected files are valid .srt files
        invalid = [f for f in selected_files if not f.lower().endswith(".srt")]
        if invalid:
            names = "\n".join(os.path.basename(f) for f in invalid)
            show_validation_error(
                self,
                "Invalid Files",
                f"The following files are not SRT files:\n{names}",
            )
            return False

        return True

    def _validate_languages_tab(self) -> bool:
        """Validate: at least one target language selected."""
        target_languages = self.language_section.get_target_languages()
        if not target_languages:
            show_validation_error(
                self,
                "No Languages Selected",
                "Please select at least one target language.",
            )
            return False
        return True

    # ------------------------------------------------------------------ #
    #  Settings dialog
    # ------------------------------------------------------------------ #

    def _open_settings_dialog(self):
        """Open the application-level settings dialog."""
        dialog = SettingsDialog(self.settings_manager, parent=self)
        dialog.exec()

    # ------------------------------------------------------------------ #
    #  Signal wiring
    # ------------------------------------------------------------------ #

    def connect_signals(self):
        """Connect all component signals to their handlers."""
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

        # AI Config Section signals
        self.ai_config_section.connect_signals(
            self.toggle_translation_settings,
            self.generate_translation_settings,
            self.edit_translation_settings,
            self.regenerate_translation_settings,
            self.show_ai_config_help,
            self.import_termbase_file,
            self.import_dnt_file,
        )

        # Translation Section signals
        self.translation_section.connect_signals(self.start_translation, self._open_html_report)

        # Tab change — update cost when arriving at Translate tab
        self.tab_widget.currentChanged.connect(self._on_tab_changed)

    def _on_tab_changed(self, index: int):
        """Handle tab change events."""
        if index == TAB_TRANSLATE:
            self.update_cost_estimate()

    # ------------------------------------------------------------------ #
    #  Load previous settings
    # ------------------------------------------------------------------ #

    def load_previous_settings(self):
        """Load previous settings from storage."""
        # Load selected files
        self.file_section.load_saved_files()

        # Load output directory
        self.file_section.load_saved_output_directory()

        # Load target languages
        self.language_section.load_saved_languages()

        # Load and display existing Translation Settings if available
        dnt_terms, termbase, _ = self.settings_manager.load_ai_config()
        if dnt_terms or termbase:
            self.ai_config_section.set_action_buttons_enabled(True)
            self.ai_config_section.set_configured_status(True)

        # Load saved tone setting and connect change handler
        saved_tone = self.settings_manager.load_tone()
        self.ai_config_section.set_tone(saved_tone)
        self.ai_config_section.connect_tone_changed(self.on_tone_changed)

        # Unlock tabs based on previously saved state
        self._restore_tab_access()

    def _restore_tab_access(self):
        """Unlock tabs based on what the user previously configured."""
        # If files are loaded, unlock Languages tab
        if self.file_section.get_selected_files():
            self._max_visited_tab = max(self._max_visited_tab, TAB_LANGUAGES)

        # If languages are selected, unlock Translation Settings tab
        if self.language_section.get_target_languages():
            self._max_visited_tab = max(self._max_visited_tab, TAB_SETTINGS)

        # Translation Settings tab has no validation, so if we can reach it
        # we can also reach Translate
        if self._max_visited_tab >= TAB_SETTINGS:
            self._max_visited_tab = TAB_TRANSLATE

        self._update_tab_enabled_states()

    # ------------------------------------------------------------------ #
    #  Handlers — tone
    # ------------------------------------------------------------------ #

    def on_tone_changed(self, tone: str) -> None:
        self.settings_manager.save_tone(tone)

    # ------------------------------------------------------------------ #
    #  Handlers — files
    # ------------------------------------------------------------------ #

    def browse_files(self):
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
        # Get selected files and target languages from UI

        selected_files = self.file_section.get_selected_files()
        target_codes = self._get_target_codes_from_ui()
        api_key = self.settings_manager.load_api_key()

        self.logger.info(
            "Starting AI configuration generation with %s files and %s languages",
            len(selected_files),
            len(target_codes),
        )

        # Validate inputs
        if not selected_files:
            show_validation_error(self, "No Files Selected", "Please select SRT files for AI analysis.")
            return

        if not api_key:
            show_validation_error(
                self,
                "No API Key",
                "Please set an OpenAI API key in Settings (gear icon).",
            )
            return

        if not target_codes:
            show_validation_error(
                self,
                "No Target Languages",
                "Please select at least one target language.",
            )
            return

        self.logger.info("Selected files: %s", [os.path.basename(f) for f in selected_files])

        # Load user-provided termbase and DNT terms if they exist
        user_termbase = self.settings_manager.load_user_termbase()
        user_dnt_terms = self.settings_manager.load_user_dnt_terms()

        if user_termbase:
            self.logger.info("User-provided termbase will be merged: %s languages", len(user_termbase))
        if user_dnt_terms:
            self.logger.info("User-provided DNT terms will be merged: %s terms", len(user_dnt_terms))

        # Initialize AI config generator if not already done
        generation_model_name = self.settings_manager.load_generation_model_name()

        self.ai_config_generator = AIConfigGenerator(
            api_key=api_key,
            language_config=self.language_config,
            generation_model_name=generation_model_name,
            temperature=self.settings_manager.load_aggressiveness(),
        )

        self.logger.debug(
            "DEBUG: Generator using generation model=%s temperature=%s",
            self.ai_config_generator.generation_model_name,
            self.ai_config_generator.temperature,
        )

        self.ai_config_section.show_progress(True)

        # Worker class for background generation
        class AIConfigWorker(QObject):
            finished = Signal(tuple)
            error = Signal(str)
            progress = Signal(str)

            def __init__(self, ai_generator, files, languages, user_termbase, user_dnt_terms):
                super().__init__()
                self.ai_generator = ai_generator
                self.files = files
                self.languages = languages
                self.user_termbase = user_termbase
                self.user_dnt_terms = user_dnt_terms
                self.logger = logging.getLogger(__name__)
                self._setup_logging_bridge()

            def run(self):
                try:
                    self.progress.emit("AI Config Worker: Starting batch-level AI config generation")
                    self.logger.info("AI Config Worker: Starting batch-level AI config generation")

                    batch_config = self.ai_generator.generate_batch_ai_config(
                        source_file_paths=self.files, target_lang_codes=self.languages
                    )

                    merged_dnt = merge_dnt_terms(
                        ai_generated=batch_config.dnt_terms,
                        user_provided=self.user_dnt_terms,
                    )
                    merged_termbase = merge_termbase(
                        ai_generated=batch_config.termbase,
                        user_provided=self.user_termbase,
                    )

                    requested_lang_count = len(self.languages)
                    succeeded_lang_count = len(batch_config.termbase)
                    progress_msg = (
                        f"AI Config Worker: Generated {len(batch_config.dnt_terms)} AI DNT terms "
                        f"(merged to {len(merged_dnt)} total) and termbase for "
                        f"{succeeded_lang_count} of {requested_lang_count} requested languages "
                        f"(merged to {len(merged_termbase)} languages)"
                    )
                    if batch_config.failed_languages:
                        progress_msg += (
                            f"; AI generation failed for: {', '.join(sorted(batch_config.failed_languages))}"
                        )
                    self.progress.emit(progress_msg)
                    self.logger.info(progress_msg)

                    self.finished.emit(
                        (
                            merged_dnt,
                            merged_termbase,
                            batch_config.source_language,
                            list(batch_config.failed_languages),
                        )
                    )
                except Exception as e:
                    error_msg = f"AI Config Worker: Error during generation: {e}"
                    self.progress.emit(error_msg)
                    self.logger.error(error_msg)
                    self.error.emit(str(e))

            def _setup_logging_bridge(self):
                try:
                    class ProgressLogHandler(logging.Handler):
                        def __init__(self, worker):
                            super().__init__()
                            self.worker = worker
                            self._emission_failed_logged = False

                        def emit(self, record):
                            try:
                                msg = self.format(record)
                                self.worker.progress.emit(msg)
                            except Exception as e:
                                if not self._emission_failed_logged:
                                    self.worker.logger.debug("Progress emission failed (ignored): %s", e)
                                    self._emission_failed_logged = True

                    progress_handler = ProgressLogHandler(self)
                    progress_handler.setLevel(logging.INFO)
                    formatter = logging.Formatter("%(message)s")
                    progress_handler.setFormatter(formatter)

                    ai_logger = logging.getLogger("srt_translator.gui.ai_config")
                    ai_logger.addHandler(progress_handler)
                    ai_logger.setLevel(logging.INFO)
                    self.logger.addHandler(progress_handler)
                except Exception as e:
                    self.logger.warning("Failed to set up logging bridge: %s", e)

        self.ai_config_thread = QThread()
        self.ai_config_worker = AIConfigWorker(
            self.ai_config_generator, selected_files, target_codes, user_termbase, user_dnt_terms
        )
        self.ai_config_worker.moveToThread(self.ai_config_thread)

        self.ai_config_thread.started.connect(self.ai_config_worker.run)
        self.ai_config_worker.progress.connect(self.ai_config_section.update_progress)
        self.ai_config_worker.finished.connect(self.ai_config_generation_finished)
        self.ai_config_worker.error.connect(self.ai_config_generation_error)
        self.ai_config_worker.finished.connect(self.ai_config_thread.quit)
        self.ai_config_worker.error.connect(self.ai_config_thread.quit)

        self.ai_config_thread.finished.connect(self.ai_config_worker.deleteLater)
        self.ai_config_thread.finished.connect(self.ai_config_thread.deleteLater)

        self.ai_config_thread.start()

    def ai_config_generation_finished(self, result):
        """Handle AI configuration generation completion."""
        # Tuple is (merged_dnt, merged_termbase, source_language, failed_languages).
        # failed_languages may be an empty list on a clean run.
        dnt_terms, termbase, source_language, failed_languages = result

        self.logger.info(
            "AI configuration generation completed: %s DNT terms, %s languages in termbase",
            len(dnt_terms),
            len(termbase),
        )
        if failed_languages:
            self.logger.warning(
                "AI generation failed for %d languages (no termbase entries produced): %s",
                len(failed_languages),
                ", ".join(sorted(failed_languages)),
            )

        self.ai_config_section.show_progress(False)
        self.settings_manager.save_ai_config(dnt_terms, termbase, source_language)
        self.logger.info("AI configuration saved to settings")

        target_languages = self._target_langs_from_ui()
        self.settings_manager.save_target_languages(target_languages)

        self.ai_config_section.set_action_buttons_enabled(True)
        self.ai_config_section.set_configured_status(True)

        QMessageBox.information(
            self,
            "Translation Settings Generated",
            f"Successfully generated Translation Settings:\n"
            f"\u2022 {len(dnt_terms)} DNT terms\n"
            f"\u2022 Termbase for {len(termbase)} languages\n\n"
            f"The settings will be used automatically for translation.\n"
            f"You can now click 'Edit Settings' to review and modify the results.",
        )

    def ai_config_generation_error(self, error_message: str):
        self.logger.error("AI configuration generation failed: %s", error_message)
        self.ai_config_section.show_progress(False)

        if self.ai_config_generator is not None:
            try:
                error_details = self.ai_config_generator.get_error_details(Exception(error_message))
                title = error_details.get("title", "AI Configuration Failed")
                message = error_details.get("message", error_message)
                suggestion = error_details.get("suggestion", "")
                QMessageBox.warning(self, title, f"{message}\n\n{suggestion}" if suggestion else message)
                return
            except Exception as e:
                print(f"Warning: Failed to show detailed error message: {e}")  # noqa: T201

        QMessageBox.warning(
            self,
            "AI Configuration Failed",
            f"An error occurred while generating translation settings:\n\n{error_message}",
        )

    def edit_translation_settings(self):
        dnt_terms, termbase, _ = self.settings_manager.load_ai_config()

        if not dnt_terms and not termbase:
            QMessageBox.warning(
                self,
                "No Translation Settings",
                "No Translation Settings have been generated yet.\nPlease generate settings first.",
            )
            return

        from srt_translator.gui.ui.ai_config_section import EditConfigurationDialog

        dialog = EditConfigurationDialog(self.settings_manager, dnt_terms, termbase)

        if dialog.exec():
            modified_terms, modified_termbase = dialog.get_modified_config()
            if dialog.has_changes():
                dnt_terms, termbase, source_language = self.settings_manager.load_ai_config()
                self.settings_manager.save_ai_config(modified_terms, modified_termbase, source_language)
                QMessageBox.information(
                    self,
                    "Translation Settings Updated",
                    "Your changes have been saved and will be used for translation.",
                )
                logging.info(
                    "Translation Settings updated: %s terms, %s languages",
                    len(modified_terms),
                    len(modified_termbase),
                )

    def regenerate_translation_settings(self):
        if not self.ai_config_section.is_expanded:
            self.ai_config_section.toggle_expansion()
        self.generate_translation_settings()

    def import_termbase_file(self):
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        file_dialog.setNameFilter("JSON Files (*.json)")

        if file_dialog.exec():
            file_path = file_dialog.selectedFiles()[0]
            try:
                termbase = load_termbase_from_file(file_path, self.logger, language_config=self.language_config)
                if not self._validate_termbase_structure(termbase):
                    raise ValueError("Invalid termbase structure")
                if termbase:
                    self.settings_manager.save_user_termbase(termbase)
                    ai_dnt, ai_tb, source_lang = self.settings_manager.load_ai_config()
                    merged = merge_termbase(ai_generated=ai_tb, user_provided=termbase)
                    self.settings_manager.save_ai_config(ai_dnt, merged, source_lang)

                    # Persisted state is now configured — flip the UI to match
                    # without waiting for the next app launch.
                    self.ai_config_section.set_action_buttons_enabled(True)
                    self.ai_config_section.set_configured_status(True)

                    QMessageBox.information(
                        self,
                        "Termbase Imported",
                        f"Successfully imported termbase with {len(termbase)} languages.\n"
                        f"Total entries: {sum(len(tb) for tb in termbase.values())}\n\n"
                        f"The termbase has been merged with existing AI-generated settings.",
                    )
                else:
                    QMessageBox.warning(
                        self,
                        "Import Failed",
                        "Failed to load termbase from the selected file.\n"
                        "Please ensure the file is valid JSON with the format:\n"
                        '{"lang_code": {"source_term": "translation", ...}, ...}',
                    )
            except Exception as e:
                self.logger.error("Termbase import failed: %s", e)
                QMessageBox.critical(
                    self,
                    "Invalid Termbase File",
                    "Termbase format is invalid.\n\nExpected:\n{ 'lang': { 'source': 'translation' } }",
                )

    def import_dnt_file(self):
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        file_dialog.setNameFilter("JSON Files (*.json);;Text Files (*.txt);;All Files (*)")

        last_dir = self.settings_manager.load_last_input_directory()
        if last_dir and os.path.exists(last_dir):
            file_dialog.setDirectory(last_dir)
        else:
            file_dialog.setDirectory(os.getcwd())

        if not file_dialog.exec():
            return

        file_path = file_dialog.selectedFiles()[0]
        self.logger.info("Importing DNT terms from %s", file_path)

        try:
            dnt_terms = load_dnt_terms_from_file(file_path, self.logger)
            if not self._validate_dnt_structure(dnt_terms):
                raise ValueError("Invalid termbase structure")

            self.settings_manager.save_user_dnt_terms(dnt_terms)
            ai_dnt, ai_tb, source_lang = self.settings_manager.load_ai_config()
            merged = merge_dnt_terms(ai_generated=ai_dnt, user_provided=dnt_terms)
            self.settings_manager.save_ai_config(merged, ai_tb, source_lang)

            # Persisted state is now configured — flip the UI to match
            # without waiting for the next app launch.
            self.ai_config_section.set_action_buttons_enabled(True)
            self.ai_config_section.set_configured_status(True)

            QMessageBox.information(
                self,
                "DNT Terms Imported",
                f"Successfully imported {len(dnt_terms)} DNT terms.",
            )
        except Exception as e:
            self.logger.exception("DNT import failed: %s", e)
            QMessageBox.warning(
                self,
                "Invalid DNT file",
                "Invalid DNT file.\n\nExpected:\n\u2022 JSON array of strings\n",
            )

    def show_ai_config_help(self):
        QMessageBox.information(
            self,
            "AI Configuration Help",
            """
<h3>What AI Configuration Does</h3>
<p>Analyzes your course content and automatically generates optimal translation settings:</p>

<h4>DNT Terms</h4>
<ul>
<li>Company names (Amazon, Google, Microsoft)</li>
<li>People's names (Jeff Bezos, instructor names)</li>
<li>Technical terms (API, CEO, Excel)</li>
<li>Brands better known in English internationally</li>
</ul>

<h4>Termbase</h4>
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

<p><em>Analysis takes 30-60 seconds and significantly improves translation quality.</em></p>
""",
        )

    # ------------------------------------------------------------------ #
    #  Validation helpers
    # ------------------------------------------------------------------ #

    def _validate_dnt_structure(self, dnt_terms: list) -> bool:
        if not isinstance(dnt_terms, list) or len(dnt_terms) == 0:
            return False
        return all(isinstance(t, str) and t.strip() for t in dnt_terms)

    def _validate_termbase_structure(self, termbase: dict) -> bool:
        if not isinstance(termbase, dict):
            return False
        for lang, entries in termbase.items():
            if not isinstance(lang, str) or not isinstance(entries, dict):
                return False
            for k, v in entries.items():
                if not isinstance(k, str) or not isinstance(v, str):
                    return False
        return True

    # ------------------------------------------------------------------ #
    #  Cost estimate
    # ------------------------------------------------------------------ #

    def update_cost_estimate(self):
        selected_files = self.file_section.get_selected_files()
        target_languages = self.language_section.get_target_languages()

        if not selected_files or not target_languages:
            self.translation_section.update_cost_estimate("$0.00")
            self.translation_section.cost_estimate.setVisible(True)
            return

        total_bytes = 0
        for f in selected_files:
            try:
                total_bytes += Path(f).stat().st_size
            except OSError:
                continue

        estimated_tokens = total_bytes * BYTES_TO_TOKENS_RATIO
        total_languages = len(target_languages)
        estimated_tokens *= total_languages
        estimated_tokens *= TRANSLATION_OVERHEAD_FACTOR
        estimated_cost = (estimated_tokens / 1000) * PRICE_PER_1K_TOKENS

        dnt_terms, termbase, _ = self.settings_manager.load_ai_config()
        if not dnt_terms and not termbase:
            estimated_cost += AI_CONFIG_BASE_COST

        cost_text = f"${estimated_cost:.3f}"
        self.translation_section.update_cost_estimate(cost_text)

    # ------------------------------------------------------------------ #
    #  Translation
    # ------------------------------------------------------------------ #

    def start_translation(self):
        if self.mem_timer and not self.mem_timer.isActive():
            self.mem_timer.start(300000)

        self.translation_section.open_html_btn.setEnabled(False)

        selected_files = self.file_section.get_selected_files()
        target_languages = self._target_langs_from_ui()
        target_codes = list(target_languages.values())
        self.logger.info("Translation requested with %s languages: %s", len(target_codes), target_codes)

        api_key = self.settings_manager.load_api_key()

        is_valid, error_message = validate_translation_inputs(api_key, selected_files, target_codes)
        if not is_valid:
            show_validation_error(self, "Validation Error", error_message)
            return

        # Lock tabs 1-3 during translation
        self._set_tabs_locked(True)

        self.translation_section.start_translation()

        output_directory = self.file_section.get_output_directory()

        self.translation_worker = TranslationWorker(
            api_key,
            selected_files,
            target_languages,
            self.settings_manager,
            output_directory,
        )

        self.translation_thread = QThread()
        self.translation_worker.moveToThread(self.translation_thread)

        self.translation_worker.progress_updated.connect(self.translation_section.update_log_output)
        self.translation_worker.translation_completed.connect(self.translation_finished)
        self.translation_worker.translation_error.connect(self.translation_error)
        self.translation_worker.eval_report_ready.connect(self._after_eval_finished)

        self.translation_worker.translation_completed.connect(self.translation_thread.quit)
        self.translation_worker.translation_error.connect(self.translation_thread.quit)
        self.translation_thread.finished.connect(self.translation_worker.deleteLater)
        self.translation_thread.finished.connect(self.translation_thread.deleteLater)

        self.translation_thread.started.connect(self.translation_worker.run)
        self.translation_thread.start()

    def _set_tabs_locked(self, locked: bool):
        """Disable/enable tabs 0-2 during translation."""
        for i in range(TAB_TRANSLATE):
            self.tab_widget.setTabEnabled(i, not locked)

    def translation_finished(self, results: dict):
        self.translation_section.finish_translation()
        self._set_tabs_locked(False)

        if self.mem_timer and self.mem_timer.isActive():
            self.mem_timer.stop()

        target_languages = self._target_langs_from_ui()
        self.settings_manager.save_target_languages(target_languages)

        logging.info("Processing translation results: %s", results)
        self.translation_section.update_log_output(f"Processing translation results: {results}")

        show_translation_results(self, results)

    def translation_error(self, error_message: str):
        self.translation_section.finish_translation()
        self._set_tabs_locked(False)

        if self.mem_timer and self.mem_timer.isActive():
            self.mem_timer.stop()

        self.translation_section.open_html_btn.setEnabled(False)
        show_translation_error(self, error_message)

    def _after_eval_finished(self, report_paths: dict):
        self.logger.info("Evaluation completed - reports available:")
        for name, path in report_paths.items():
            self.logger.info("  %s: %s", name, path)

        self._last_eval_json = Path(report_paths.get("eval_report_json", ""))
        self._last_eval_html = Path(report_paths.get("eval_report_html", ""))

        if self._last_eval_html and self._last_eval_html.exists():
            self.translation_section.open_html_btn.setEnabled(True)
            self.translation_section.open_html_btn.clicked.connect(lambda: self._open_html_report())

    def _open_html_report(self):
        if self._last_eval_html and self._last_eval_html.exists():
            import webbrowser
            webbrowser.open(f"file://{self._last_eval_html.absolute()}")
        else:
            QMessageBox.warning(self, "Report Not Available", "HTML report not found.")

    # ------------------------------------------------------------------ #
    #  Styles
    # ------------------------------------------------------------------ #

    def apply_styles(self):
        self.setStyleSheet(MAIN_STYLESHEET)

    # ------------------------------------------------------------------ #
    #  Close event
    # ------------------------------------------------------------------ #

    def closeEvent(self, event):
        if hasattr(self, "translation_worker") and self.translation_worker is not None:
            self.translation_worker.request_stop()

        try:
            thread = getattr(self, "translation_thread", None)
            if thread is not None and thread.isRunning():
                thread.quit()
                thread.wait(10000)
        except RuntimeError:
            pass
        finally:
            if hasattr(self, "translation_worker"):
                self.translation_worker = None
            if hasattr(self, "translation_thread"):
                self.translation_thread = None

        # Save current settings
        self.settings_manager.save_selected_files(self.file_section.selected_files)
        target_languages = self._target_langs_from_ui()
        self.settings_manager.save_target_languages(target_languages)

        event.accept()

    # ------------------------------------------------------------------ #
    #  Memory monitoring
    # ------------------------------------------------------------------ #

    def _sample_memory(self):
        try:
            rss = self._proc.memory_info().rss
            growth_mb = (rss - self._rss0) / (1024 * 1024)

            now = time.time()
            if not hasattr(self, "_last_mem_sample_time"):
                self._last_mem_sample_time = now

            if now - self._last_mem_sample_time >= 300:
                self._last_mem_sample_time = now
                self.logger.debug("Memory usage: %.1f MB growth since start", growth_mb)

            if growth_mb > 1000 and not self._memory_warning_shown:
                if not getattr(self, "_memory_warning_shown", False):
                    self._memory_warning_shown = True
                    self.logger.warning("High memory usage detected: %.1f MB growth", growth_mb)
                    QMessageBox.warning(
                        self,
                        "High Memory Usage",
                        f"Memory usage has grown significantly ({growth_mb:.1f} MB).\n"
                        "Consider restarting the application after completing the current "
                        "translation.\n\n"
                        "This helps prevent crashes during long translation sessions.",
                    )
        except Exception as e:
            self.logger.error("Error sampling memory: %s", e)

    # ------------------------------------------------------------------ #
    #  Language helpers
    # ------------------------------------------------------------------ #

    def _get_target_codes_from_ui(self) -> list[str]:
        langs = self.language_section.get_target_languages()
        return sorted(langs.values())

    def _target_langs_from_ui(self) -> dict[str, str]:
        self.language_section.update_target_languages_from_ui()
        langs = self.language_section.get_target_languages()
        target_languages = normalize_target_languages(langs)
        target_languages = dict(sorted(target_languages.items(), key=lambda kv: kv[1]))
        self.logger.info("Target languages (UI): %s", list(target_languages.values()))
        return target_languages
