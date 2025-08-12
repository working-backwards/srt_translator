#!/usr/bin/env python3
"""
GUI Entry Point for SRT Translator
"""

import logging
import sys
import os
import argparse

# Set up logging - ALWAYS include this
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Get logger for this module
logger = logging.getLogger(__name__)


def main() -> None:
    """Launch the GUI application with lazy dependency loading"""
    # Parse command line arguments first
    parser = argparse.ArgumentParser(
        description="SRT Translator GUI", prog="srt-translator-gui"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__import__('srt_translator').__version__}",
    )

    # Parse args but ignore unknown args (Qt might add its own)
    args, _ = parser.parse_known_args()

    # Import heavy deps lazily so CLI users aren't penalized
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError as e:
        # Helpful error if GUI dependencies aren't installed
        raise SystemExit(
            "GUI dependencies not installed. Try: pip install srt-translator[gui]"
        ) from e

    # Import your actual GUI window/app code
    from srt_translator.gui.main_window import SRTTranslatorMainWindow

    # Set up environment variables from QSettings BEFORE importing any core modules
    def prepare_environment_from_settings():
        """Set environment variables from QSettings before calling core engine"""
        try:
            from PySide6.QtCore import QDir, QSettings, QStandardPaths

            settings = QSettings("SRTTranslator", "SRTTranslator")

            # Required parameters
            api_key = settings.value("api_key", "")
            if api_key:
                os.environ["OPENAI_API_KEY"] = api_key

            # Optional parameters with defaults
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

        except Exception as e:
            # If QSettings fails, we'll use defaults
            logger.warning(f"Warning: Could not load GUI settings: {e}")

    # Call the bridge BEFORE importing any core modules
    prepare_environment_from_settings()

    # Create and run the application
    app = QApplication(sys.argv)
    app.setApplicationName("SRT Translator")

    # Import version from core package
    from srt_translator import __version__

    app.setApplicationVersion(__version__)

    window = SRTTranslatorMainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
