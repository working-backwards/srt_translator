import os
import sys
import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from srt_translator.gui.ui.ai_config_section import EditConfigurationDialog

# Set up logging
logging.basicConfig(level=logging.INFO)

"""
Integration test for both DNT Terms Editor and Termbase Editor
"""

sys.path.insert(0, ".")


class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Editors Integration Test")
        self.setGeometry(100, 100, 1000, 700)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Test data
        # DNT_TERMS: Language-agnostic terms that should not be translated
        self.test_dnt_terms = [
            "API",
            "CEO",
            "CFO",
            "Amazon",
            "Google",
            "Microsoft",
        ]

        # Termbase: Language-specific translations of English terms
        self.test_termbase = {
            "Spanish": {"API": "API", "CEO": "CEO", "CFO": "CFO", "Amazon": "Amazon"},
            "French": {
                "API": "API",
                "CEO": "PDG",  # French translation
                "CFO": "DF",  # French translation
                "Amazon": "Amazon",
            },
            "German": {
                "API": "API",
                "CEO": "Geschäftsführer",  # German translation
                "CFO": "CFO",
                "Amazon": "Amazon",
            },
        }

        # Instructions
        instructions = QLabel(
            "Click 'Open Edit Dialog' to test the integrated editors.\n"
            "The dialog will show both DNT Terms and Termbase editors in tabs."
        )
        instructions.setStyleSheet(
            "padding: 10px; background-color: #f0f0f0; border-radius: 5px;"
        )
        layout.addWidget(instructions)

        # Test buttons
        button_layout = QHBoxLayout()

        open_dialog_btn = QPushButton("Open Edit Dialog")
        open_dialog_btn.clicked.connect(self.open_edit_dialog)

        test_data_btn = QPushButton("Show Test Data")
        test_data_btn.clicked.connect(self.show_test_data)

        button_layout.addWidget(open_dialog_btn)
        button_layout.addWidget(test_data_btn)
        button_layout.addStretch()

        layout.addLayout(button_layout)

        # Status label
        self.status_label = QLabel("Ready to test editors integration")
        self.status_label.setStyleSheet("padding: 10px; color: #666;")
        layout.addWidget(self.status_label)

        layout.addStretch()

    def open_edit_dialog(self):
        """Open the EditConfigurationDialog with test data."""
        self.status_label.setText("Opening edit dialog...")

        dialog = EditConfigurationDialog(self.test_dnt_terms, self.test_termbase, self)

        if dialog.exec():
            modified_terms, modified_termbase = dialog.get_modified_config()
            has_changes = dialog.has_changes()

            if has_changes:
                self.status_label.setText(
                    f"Dialog closed with changes:\n"
                    f"Terms: {len(modified_terms)} (was {len(self.test_dnt_terms)})\n"
                    f"Termbase languages: {len(modified_termbase)} (was {len(self.test_termbase)})"
                )
                logger = logging.getLogger(__name__)
                logger.info(f"Modified terms: {modified_terms}")
                logger.info(f"Modified termbase: {modified_termbase}")
            else:
                self.status_label.setText("Dialog closed without changes")
        else:
            self.status_label.setText("Dialog cancelled")

    def show_test_data(self):
        """Display the test data being used."""
        logger = logging.getLogger(__name__)
        logger.info("=== Test Data ===")
        logger.info(f"DNT Terms ({len(self.test_dnt_terms)}): {self.test_dnt_terms}")
        logger.info(f"Termbase ({len(self.test_termbase)} languages):")
        for language, terms in self.test_termbase.items():
            logger.info(f"  {language}: {len(terms)} terms - {list(terms.keys())}")
        logger.info("================")

        self.status_label.setText("Test data displayed in console")


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(
        """
        QMainWindow { 
            background-color: #f5f5f5;
        }
        QPushButton {
            padding: 8px 16px;
            background-color: #0078d4;
            color: white;
            border: none;
            border-radius: 4px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #106ebe;
        }
        QPushButton:pressed {
            background-color: #005a9e;
        }
        QTabWidget::pane {
            border: 1px solid #d0d0d0;
            background-color: white;
        }
        QTabBar::tab {
            background-color: #f0f0f0;
            padding: 8px 16px;
            margin-right: 2px;
        }
        QTabBar::tab:selected {
            background-color: white;
            border-bottom: 2px solid #0078d4;
        }
    """
    )

    window = TestWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
