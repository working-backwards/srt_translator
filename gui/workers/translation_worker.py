"""
Translation Worker Thread
Handles background translation processing
"""

import logging
import os
import uuid
from pathlib import Path
from typing import Dict, List

from PySide6.QtCore import QThread
from PySide6.QtCore import Signal as pyqtSignal

# Import fixer for automatic cleanup after translation
from srt_core.translator.fixer import SRTFixer
from srt_core.config.translation_config import build_config_from_gui


class TranslationWorker(QThread):
    """Worker thread for running translations in background"""

    progress_updated = pyqtSignal(str)
    translation_completed = pyqtSignal(dict)
    translation_error = pyqtSignal(str)
    log_message = pyqtSignal(str)

    def __init__(
        self,
        api_key: str,
        selected_files: List[str],
        target_languages: Dict[str, str],
        settings_manager=None,
        output_directory: str = None,
    ):
        super().__init__()
        self.api_key = api_key
        self.selected_files = selected_files
        self.target_languages = target_languages
        self.settings_manager = settings_manager
        self.output_directory = output_directory
        self.translation_successful = False
        self.log_file = None
        self.session_id = str(uuid.uuid4())[:8]
        self.logger = logging.getLogger(f"translation.{self.session_id}")

    def run(self):
        """Run the translation process"""
        try:
            # Debug logging for target languages
            self.logger.info(f"TranslationWorker received target_languages: {self.target_languages}")
            self.logger.info(f"Number of target languages: {len(self.target_languages)}")
            self.logger.info(f"Target language names: {list(self.target_languages.keys())}")
            self.logger.info(f"Target language codes: {list(self.target_languages.values())}")
            
            # Emit progress via signal (thread-safe)
            self.progress_updated.emit(f"Starting translation to {len(self.target_languages)} languages")
            
            # Reset logging configuration and set up proper logging
            logging.getLogger().handlers.clear()  # Clear existing handlers
            from srt_core.utils.logging_setup import setup_logging

            log_file = setup_logging()

            # Debug logging
            self.logger.info(
                f"Starting translation with {len(self.selected_files)} files and {len(self.target_languages)} languages"
            )
            self.progress_updated.emit(
                f"Starting translation with {len(self.selected_files)} files and {len(self.target_languages)} languages"
            )

            # Build configuration from GUI settings manager
            if self.settings_manager:
                config = build_config_from_gui(self.settings_manager)
                self.logger.info(f"Using configuration from settings manager: {config.to_log_string()}")
            else:
                # Fallback to direct parameters
                from srt_core.config.translation_config import build_config_from_parameters
                config = build_config_from_parameters(
                    target_languages=self.target_languages,
                    api_key=self.api_key,
                    output_directory=self.output_directory
                )
                self.logger.info(f"Using configuration from direct parameters: {config.to_log_string()}")

            # Run the translation
            # Capture both stdout and logging output
            import io
            import sys
            from contextlib import redirect_stdout

            from srt_core.main import translate_srt_files

            # Create a custom log handler to capture log messages
            class LogCaptureHandler(logging.Handler):
                def __init__(self, signal_emitter):
                    super().__init__()
                    self.signal_emitter = signal_emitter
                    self.captured_messages = []

                def emit(self, record):
                    msg = self.format(record)
                    self.captured_messages.append(msg)
                    self.signal_emitter.emit(msg)

            # Add our custom handler to capture log messages
            log_handler = LogCaptureHandler(self.progress_updated)
            log_handler.setFormatter(logging.Formatter("%(message)s"))
            logging.getLogger().addHandler(log_handler)

            # Capture stdout output
            output = io.StringIO()
            with redirect_stdout(output):
                # Call translation with configuration object
                results = translate_srt_files(
                    file_paths=self.selected_files, 
                    config=config
                )

            # Remove our custom handler
            logging.getLogger().removeHandler(log_handler)

            # Capture any stdout output
            stdout_output = output.getvalue()
            if stdout_output.strip():
                self.progress_updated.emit(f"Translation output: {stdout_output.strip()}")

            # Store results for potential fixer use
            self.translation_results = results
            self.log_file = log_file

            # Emit completion via signal (thread-safe)
            self.translation_completed.emit(results)

        except Exception as e:
            error_msg = f"Translation failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            # Emit error via signal (thread-safe)
            self.translation_error.emit(error_msg)

    def prepare_translation_environment(self):
        """Prepare environment for translation (minimal setup only)"""
        try:
            # Set only essential environment variables for file paths and API key
            # DO NOT set runtime state variables like TARGET_LANGUAGES, DNT_TERMS, TERMBASE
            
            # API key is required for translation
            os.environ["OPENAI_API_KEY"] = self.api_key
            self.logger.info("Set OPENAI_API_KEY environment variable")
            
            # Set GUI mode flag
            os.environ["GUI_MODE"] = "true"
            self.logger.info(f"Set GUI_MODE environment variable to: {os.getenv('GUI_MODE')}")
            
            # Set output directory if provided
            if self.output_directory:
                os.environ["OUTPUT_DIRECTORY"] = self.output_directory
                self.logger.info(f"Set OUTPUT_DIRECTORY to: {self.output_directory}")
            
            # DO NOT set TARGET_LANGUAGES - this will be passed as parameter
            # DO NOT set DNT_TERMS - this will be passed as parameter  
            # DO NOT set TERMBASE - this will be passed as parameter
            
        except Exception as e:
            self.logger.error(f"Error preparing translation environment: {e}")
            raise

    def setup_ai_configuration(self):
        """Set up AI configuration from settings manager (if available)"""
        if not self.settings_manager:
            self.logger.warning("No settings manager available for AI configuration")
            return

        try:
            # Get current state from settings manager (thread-safe)
            config_state = self.settings_manager.get_current_state()
            
            self.logger.info(f"Using AI configuration from settings manager")
            self.logger.info(f"DNT terms count: {len(config_state.dnt_terms)}")
            self.logger.info(f"Termbase languages: {list(config_state.termbase.keys())}")
            
            # Note: We don't set environment variables anymore
            # The translation functions will receive this configuration directly as parameters
            
        except Exception as e:
            self.logger.error(f"Error setting up AI configuration: {e}")
            # Don't raise - this is not critical for translation

    def update_env_dnt_terms(self, dnt_terms: List[str]):
        """Update DNT terms (DEPRECATED - use settings manager instead)"""
        self.logger.warning("update_env_dnt_terms() is deprecated - use settings manager instead")
        # This method is kept for backward compatibility but does nothing
        # DNT terms should be passed directly to translation functions

    def update_termbase(self, language: str, termbase: Dict[str, str]):
        """Update termbase (DEPRECATED - use settings manager instead)"""
        self.logger.warning("update_termbase() is deprecated - use settings manager instead")
        # This method is kept for backward compatibility but does nothing
        # Termbase should be passed directly to translation functions

    def update_env_languages(self):
        """Update environment languages (DEPRECATED - use direct parameters instead)"""
        self.logger.warning("update_env_languages() is deprecated - use direct parameters instead")
        # This method is kept for backward compatibility but does nothing
        # Languages are now passed directly to translate_srt_files()

    def run_fixer(self):
        """Run the fixer to clean up translation issues"""
        if not hasattr(self, 'translation_results') or not self.log_file:
            self.logger.warning("No translation results or log file available for fixing")
            return

        try:
            self.progress_updated.emit("Running automatic fixes on translated files...")
            
            # Create fixer instance
            fixer = SRTFixer(self.log_file, self.output_directory or "translated_srt_files")
            
            # Parse log file for issues
            fixer.parse_log_file()
            
            # Run fixes
            fixer.fix_srt_files(aggressiveness=0.75)
            
            # Report status
            fixer.report_status()
            
            self.progress_updated.emit("Automatic fixes completed")
            
        except Exception as e:
            error_msg = f"Error running fixer: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            self.progress_updated.emit(f"Warning: {error_msg}")
