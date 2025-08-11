#!/usr/bin/env python3
"""
Test script for Termbase Editor
"""

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gui.ui.termbase_editor import TermbaseEditor

"""
Test script for Termbase Editor
"""

sys.path.insert(0, "gui")


class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Termbase Editor Test")
        self.setGeometry(100, 100, 800, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Create the termbase editor
        self.termbase_editor = TermbaseEditor()

        # Test data - Termbase with language-specific translations
        # Note: DNT_TERMS would be separate and language-agnostic
        test_termbase = {
            "Spanish": {"API": "API", "CEO": "CEO", "CFO": "CFO", "Amazon": "Amazon"},
            "French": {
                "API": "API",
                "CEO": "PDG",  # French translation
                "CFO": "DF",  # French translation
                "Amazon": "Amazon",
            },
        }

        self.termbase_editor.set_termbase(test_termbase)
        self.termbase_editor.termbase_changed.connect(self.on_termbase_changed)

        # Test buttons
        button_layout = QHBoxLayout()

        get_btn = QPushButton("Get Current Termbase")
        get_btn.clicked.connect(self.get_current_termbase)

        clear_btn = QPushButton("Clear Termbase")
        clear_btn.clicked.connect(self.clear_termbase)

        button_layout.addWidget(get_btn)
        button_layout.addWidget(clear_btn)
        button_layout.addStretch()

        layout.addWidget(self.termbase_editor)
        layout.addLayout(button_layout)

    def on_termbase_changed(self, termbase):
        print(f"Termbase changed: {len(termbase)} languages")
        for language, terms in termbase.items():
            print(f"  {language}: {len(terms)} terms")

    def get_current_termbase(self):
        termbase = self.termbase_editor.get_termbase()
        print(f"Current termbase: {len(termbase)} languages")
        for language, terms in termbase.items():
            print(f"  {language}: {terms}")

    def clear_termbase(self):
        self.termbase_editor.set_termbase({})


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(
        """
        QMainWindow { 
            background-color: #f5f5f5;
        }
        QTableWidget {
            background-color: white;
            gridline-color: #d0d0d0;
        }
        QTableWidget::item {
            padding: 4px;
        }
        QTableWidget::item:selected {
            background-color: #0078d4;
            color: white;
        }
        QHeaderView::section {
            background-color: #f0f0f0;
            padding: 6px;
            border: 1px solid #d0d0d0;
            font-weight: bold;
        }
    """
    )

    window = TestWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
