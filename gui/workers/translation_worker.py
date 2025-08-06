"""
Translation Worker Thread
Handles background translation processing
"""

import logging
import os
from pathlib import Path
from typing import Dict, List

from PySide6.QtCore import QThread
from PySide6.QtCore import Signal as pyqtSignal

# Import fixer for automatic cleanup after translation
from srt_core.translator.fixer import SRTFixer


class TranslationWorker(QThread):
    """Worker thread for running translations in background"""

    progress_updated = pyqtSignal(str)
    translation_completed = pyqtSignal(dict)
    translation_error = pyqtSignal(str)

    def __init__(
        self,
        api_key: str,
        selected_files: List[str],
        target_languages: Dict[str, str],
        config_manager=None,
        output_directory: str = None,
    ):
        super().__init__()
        self.api_key = api_key
        self.selected_files = selected_files
        self.target_languages = target_languages
        self.config_manager = config_manager
        self.output_directory = output_directory
        self.translation_successful = False
        self.log_file = None
        # Store output directory for fixer to use
        # The fixer needs to know where the translated files are located

    def run(self):
        """Run the translation process"""
        try:
            # Debug logging for target languages
            logging.info(f"TranslationWorker received target_languages: {self.target_languages}")
            logging.info(f"Number of target languages: {len(self.target_languages)}")
            logging.info(f"Target language names: {list(self.target_languages.keys())}")
            logging.info(f"Target language codes: {list(self.target_languages.values())}")
            
            # Set up environment for translation
            self.prepare_translation_environment()

            # Reset logging configuration and set up proper logging
            logging.getLogger().handlers.clear()  # Clear existing handlers
            from srt_core.utils.logging_setup import setup_logging

            log_file = setup_logging()

            # Debug logging
            logging.info(
                f"Starting translation with {len(self.selected_files)} files and {len(self.target_languages)} languages"
            )
            self.progress_updated.emit(
                f"Starting translation with {len(self.selected_files)} files and {len(self.target_languages)} languages"
            )

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
                results = translate_srt_files(file_paths=self.selected_files)

            # Remove our custom handler
            logging.getLogger().removeHandler(log_handler)

            # Log the actual results
            logging.info(f"Translation results: {results}")
            self.progress_updated.emit(f"Translation results: {results}")

            # Emit any remaining stdout output
            output_text = output.getvalue()
            for line in output_text.split("\n"):
                if line.strip():
                    self.progress_updated.emit(line)

            # Mark translation as successful
            self.translation_successful = True

            # Run fixer to clean up phantom placeholders and other issues
            # GUI uses hardcoded aggressiveness of 0.75 for consistent fixing behavior
            self.run_fixer()

            self.translation_completed.emit(results)

        except Exception as e:
            logging.error(f"Translation error: {str(e)}")
            self.progress_updated.emit(f"Translation error: {str(e)}")
            self.translation_error.emit(str(e))

    def prepare_translation_environment(self):
        """Prepare the environment for translation"""
        # Set API key in environment
        os.environ["OPENAI_API_KEY"] = self.api_key
        
        # Set GUI mode to skip external prompt files
        os.environ["GUI_MODE"] = "true"
        logging.info(f"Set GUI_MODE environment variable to: {os.getenv('GUI_MODE')}")

        # Set output directory if provided
        if self.output_directory:
            os.environ["OUTPUT_DIRECTORY"] = self.output_directory
            logging.info(f"Using output directory: {self.output_directory}")
            self.progress_updated.emit(f"Using output directory: {self.output_directory}")

        # Update environment variables with target languages FIRST (current selection)
        self.update_env_languages()
        logging.info(f"Set TARGET_LANGUAGES to: {os.getenv('TARGET_LANGUAGES')}")
        
        # Use AI configuration if available (as resource, not to override language selection)
        if self.config_manager:
            self.setup_ai_configuration()

        # The translation function will use the selected files directly.
        logging.info("Using selected files for translation")
        self.progress_updated.emit("Using selected files for translation")
        
        # Store log file path for fixer to use later
        # The fixer needs the log file to identify issues to fix
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        from srt_core.config.settings import LOG_DIRECTORY
        self.log_file = os.path.join(LOG_DIRECTORY, f"translation_issues_{timestamp}.log")



    def setup_ai_configuration(self):
        """Set up AI-generated configuration for translation"""
        try:
            # Get DNT terms from config manager
            dnt_terms = self.config_manager.get_dnt_terms()
            if dnt_terms:
                self.progress_updated.emit(
                    f"Using AI-generated DNT terms: {', '.join(dnt_terms)}"
                )

                # Update environment variables with DNT terms
                self.update_env_dnt_terms(dnt_terms)

            # Get termbase for each target language
            for language_name in self.target_languages.keys():
                termbase = self.config_manager.get_termbase(language_name)
                if termbase:
                    self.progress_updated.emit(
                        f"Using AI-generated termbase for {language_name}: {len(termbase)} terms"
                    )
                    # Update termbase.json with AI-generated terms
                    self.update_termbase(language_name, termbase)

            # Get DNT terms from config manager
            dnt_terms = self.config_manager.get_dnt_terms()
            if dnt_terms:
                self.progress_updated.emit(
                    f"Using AI-generated DNT terms: {', '.join(dnt_terms)}"
                )
                # Update environment variables with DNT terms
                self.update_env_dnt_terms(dnt_terms)

        except Exception as e:
            logging.error(f"Error setting up AI configuration: {e}")
            self.progress_updated.emit(
                f"Warning: Could not set up AI configuration: {e}"
            )

    def update_env_dnt_terms(self, dnt_terms: List[str]):
        """Update environment variables with DNT terms"""
        # Set environment variable in simple comma-separated format (same as CLI)
        dnt_terms_str = ",".join(dnt_terms)
        os.environ["DNT_TERMS"] = dnt_terms_str

    def update_termbase(self, language: str, termbase: Dict[str, str]):
        """Update termbase.json with AI-generated terms"""
        termbase_file = Path("termbase.json")

        # Load existing termbase
        existing_termbase = {}
        if termbase_file.exists():
            try:
                import json

                with open(termbase_file, "r", encoding="utf-8") as f:
                    existing_termbase = json.load(f)
            except Exception as e:
                logging.warning(f"Could not load existing termbase.json: {e}")

        # Update with AI-generated terms
        if language not in existing_termbase:
            existing_termbase[language] = {}

        existing_termbase[language].update(termbase)

        # Write back to file
        try:
            import json

            with open(termbase_file, "w", encoding="utf-8") as f:
                json.dump(existing_termbase, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"Could not write termbase.json: {e}")

    def update_env_languages(self):
        """Update environment variables with selected target languages"""
        # Use proper JSON formatting for the environment variable
        import json
        os.environ["TARGET_LANGUAGES"] = json.dumps(self.target_languages)
        logging.info(f"Set TARGET_LANGUAGES environment variable: {os.environ['TARGET_LANGUAGES']}")

    def run_fixer(self):
        """Run the fixer to clean up translation issues"""
        try:
            self.progress_updated.emit("Running fixer to clean up translation issues...")
            
            # Create fixer instance with the log file and output directory
            fixer = SRTFixer(self.log_file, self.output_directory)
            
            # Parse the log file for issues
            fixer.parse_log_file()
            
            if fixer.issues or fixer.phantoms:
                # Run fixer with hardcoded aggressiveness of 0.75 for GUI mode
                # This ensures consistent fixing behavior without exposing technical parameters to users
                fixer.fix_srt_files(aggressiveness=0.75)
                
                # Report fixer results
                self.progress_updated.emit(
                    f"Fixer completed: {fixer.fixed_count} regular issues and {fixer.phantom_fixed_count} phantom placeholders fixed"
                )
            else:
                self.progress_updated.emit("No issues found - files are clean")
                
        except FileNotFoundError:
            logging.warning("Log file not found - skipping fixer step")
            self.progress_updated.emit("Translation completed (fixer step skipped)")
        except Exception as e:
            logging.error(f"Error running fixer: {e}")
            self.progress_updated.emit(f"Translation completed with fixer warning: {e}")
