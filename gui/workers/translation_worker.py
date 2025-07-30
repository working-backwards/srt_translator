"""
Translation Worker Thread
Handles background translation processing
"""

import os
import logging
from typing import List, Dict
from pathlib import Path
from PySide6.QtCore import QThread, Signal as pyqtSignal


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
            
            # Reset logging configuration and set up proper logging
            logging.getLogger().handlers.clear()  # Clear existing handlers
            from srt_core.utils.logging_setup import setup_logging
            log_file = setup_logging()
            
            # Debug logging
            logging.info(f"Starting translation with {len(self.selected_files)} files and {len(self.target_languages)} languages")
            self.progress_updated.emit(f"Starting translation with {len(self.selected_files)} files and {len(self.target_languages)} languages")
            
            # Run the translation
            from srt_core.main import translate_srt_files
            
            # Capture both stdout and logging output
            import io
            import sys
            from contextlib import redirect_stdout
            
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
            log_handler.setFormatter(logging.Formatter('%(message)s'))
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
            for line in output_text.split('\n'):
                if line.strip():
                    self.progress_updated.emit(line)
            
            self.translation_completed.emit(results)
            
        except Exception as e:
            logging.error(f"Translation error: {str(e)}")
            self.progress_updated.emit(f"Translation error: {str(e)}")
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