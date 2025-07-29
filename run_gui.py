#!/usr/bin/env python3
"""
SRT Translator GUI Entry Point
"""

import sys
from PySide6.QtWidgets import QApplication
from gui.main_window import SRTTranslatorMainWindow

def main():
    """Main GUI application entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("SRT Translator")
    app.setApplicationVersion("1.0.0")
    
    window = SRTTranslatorMainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()