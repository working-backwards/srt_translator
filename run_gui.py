#!/usr/bin/env python3
"""
SRT Translator GUI Entry Point
"""

import sys
import os
import argparse
import logging
import json

# Set up environment variables from QSettings BEFORE importing any core modules
def prepare_environment_from_settings():
    """Set environment variables from QSettings before calling core engine"""
    try:
        from PySide6.QtCore import QSettings, QStandardPaths, QDir
        
        settings = QSettings("SRTTranslator", "SRTTranslator")
        
        # Required parameters
        api_key = settings.value("api_key", "")
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
        
        # Optional parameters with defaults
        os.environ["SOURCE_LANG"] = settings.value("source_lang", "en")
        os.environ["OPENAI_MODEL"] = settings.value("openai_model", "gpt-4o-mini")
        os.environ["AGGRESSIVENESS"] = str(settings.value("aggressiveness", 0.75))
        os.environ["BATCH_SIZE"] = str(settings.value("batch_size", 5))
        os.environ["LOG_MODE"] = "Standard"  # GUI always uses standard logging
        
        # Output directory (use per-user path)
        output_dir = settings.value("output_directory", "")
        if not output_dir:
            # Use platform-specific default
            base = QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)
            output_dir = QDir(base).filePath("SRTTranslator/TranslatedFiles")
            QDir().mkpath(output_dir)
        os.environ["OUTPUT_DIRECTORY"] = output_dir
        
        # Log directory (use platform-specific path)
        try:
            from platformdirs import user_log_dir
            log_dir = user_log_dir("SRTTranslator", appauthor=False)
            os.makedirs(log_dir, exist_ok=True)
            os.environ["LOGS_DIRECTORY"] = log_dir
        except ImportError:
            # Fallback if platformdirs not available
            import tempfile
            log_dir = os.path.join(tempfile.gettempdir(), "SRTTranslator", "logs")
            os.makedirs(log_dir, exist_ok=True)
            os.environ["LOGS_DIRECTORY"] = log_dir
            
    except Exception as e:
        # If QSettings fails, we'll use defaults
        print(f"Warning: Could not load GUI settings: {e}")

# Call the bridge BEFORE importing any core modules
prepare_environment_from_settings()

# Debug: Check what environment variables were set
print("DEBUG: Environment variables after prepare_environment_from_settings:")
print(f"OPENAI_API_KEY: {'SET' if os.environ.get('OPENAI_API_KEY') else 'NOT SET'}")
print(f"SOURCE_LANG: {os.environ.get('SOURCE_LANG', 'NOT SET')}")
print(f"OUTPUT_DIRECTORY: {os.environ.get('OUTPUT_DIRECTORY', 'NOT SET')}")

from PySide6.QtWidgets import QApplication
from gui.main_window import SRTTranslatorMainWindow

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="SRT Translator GUI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_gui.py                    # Run GUI normally
  python run_gui.py --debug            # Run GUI with debug logging
  python run_gui.py -d                 # Short form for debug mode
        """
    )
    
    parser.add_argument(
        '--debug', '-d',
        action='store_true',
        help='Enable debug mode with verbose logging'
    )
    
    return parser.parse_args()

def main():
    """Main GUI application entry point"""
    args = parse_arguments()
    
    # Set debug mode if requested
    if args.debug:
        # Keep standard mode to filter out noisy HTTP messages from libraries
        os.environ['LOG_MODE'] = 'Standard'
        # Set Python logging level to DEBUG to show all application log messages
        logging.basicConfig(level=logging.DEBUG)
        print("Debug mode enabled - DEBUG level logging will be shown (HTTP messages filtered)")
    
    app = QApplication(sys.argv)
    app.setApplicationName("SRT Translator")
    app.setApplicationVersion("1.0.0")
    
    window = SRTTranslatorMainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()