import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
from gui.ui.excluded_terms_editor import ExcludedTermsEditor

#!/usr/bin/env python3
"""
Test script for Excluded Terms Editor
"""


    QApplication,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

# Add the gui directory to the path
sys.path.insert(0, "gui")



class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Excluded Terms Editor Test")
        self.setGeometry(100, 100, 600, 400)

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Create the excluded terms editor
        self.terms_editor = ExcludedTermsEditor()

        # Add some test terms
        test_terms = ["API", "CEO", "CFO", "Amazon", "Google", "Microsoft"]
        self.terms_editor.set_terms(test_terms)

        # Connect the terms_changed signal
        self.terms_editor.terms_changed.connect(self.on_terms_changed)

        # Add a test button
        test_button = QPushButton("Get Current Terms")
        test_button.clicked.connect(self.get_current_terms)

        # Add widgets to layout
        layout.addWidget(self.terms_editor)
        layout.addWidget(test_button)

    def on_terms_changed(self, terms):
        print(f"Terms changed: {terms}")

    def get_current_terms(self):
        terms = self.terms_editor.get_terms()
        print(f"Current terms: {terms}")


def main():
    app = QApplication(sys.argv)

    # Apply some basic styling
    app.setStyleSheet(
        """
        QMainWindow {
            background-color: #f5f5f5;
        }
    """
    )

    window = TestWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
