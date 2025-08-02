#!/usr/bin/env python3
"""
SRT Translator GUI Entry Point
"""

import sys
import os
import argparse
import logging
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