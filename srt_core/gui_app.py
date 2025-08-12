#!/usr/bin/env python3
"""
GUI Application for SRT Translator
This module provides the main GUI entry point within the installed package.
"""

import sys
import os


def main() -> None:
    """Launch the GUI application with lazy dependency loading"""
    # Import heavy deps lazily so CLI users aren't penalized
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError as e:
        # Helpful error if GUI dependencies aren't installed
        raise SystemExit(
            "GUI dependencies not installed. Try: pip install srt-translator[gui]"
        ) from e

    # Import your actual GUI window/app code
    from srt_core.gui.main_window import SRTTranslatorMainWindow

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
            # Note: logging not available yet at this point, so we'll use stderr
            import sys
            sys.stderr.write(f"Warning: Could not load GUI settings: {e}\n")

    # Call the bridge BEFORE importing any core modules
    prepare_environment_from_settings()

    # Create and run the application
    app = QApplication(sys.argv)
    app.setApplicationName("SRT Translator")

    # Import version from core package
    from srt_core import __version__

    app.setApplicationVersion(__version__)

    window = SRTTranslatorMainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
