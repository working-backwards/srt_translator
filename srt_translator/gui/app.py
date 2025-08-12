#!/usr/bin/env python3
"""
GUI Entry Point for SRT Translator
"""

import argparse
import logging
import sys

# Set up logging - ALWAYS include this
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Get logger for this module
logger = logging.getLogger(__name__)


def main() -> None:
    """Launch the GUI application with lazy dependency loading"""
    # Parse command line arguments first
    parser = argparse.ArgumentParser(description="SRT Translator GUI", prog="srtx")
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

    # No more environment variable setting - GUI will use the new config system
    # Core engine receives TranslationConfig objects directly
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
