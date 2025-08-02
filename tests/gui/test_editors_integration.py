#!/usr/bin/env python3
"""
Integration test for both Excluded Terms Editor and Business Glossary Editor
"""
import sys
import os
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QHBoxLayout, QLabel
from PySide6.QtCore import Qt
sys.path.insert(0, '.')
from gui.ui.ai_config_section import EditConfigurationDialog


class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Editors Integration Test")
        self.setGeometry(100, 100, 1000, 700)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Test data
        # EXCLUDED_TERMS: Language-agnostic terms that should not be translated
        self.test_excluded_terms = ["API", "CEO", "CFO", "Amazon", "Google", "Microsoft"]
        
        # Business Glossary: Language-specific translations of English terms
        self.test_business_glossary = {
            "Spanish": {
                "API": "API",
                "CEO": "CEO",
                "CFO": "CFO", 
                "Amazon": "Amazon"
            },
            "French": {
                "API": "API",
                "CEO": "PDG",  # French translation
                "CFO": "DF",   # French translation
                "Amazon": "Amazon"
            },
            "German": {
                "API": "API",
                "CEO": "Geschäftsführer",  # German translation
                "CFO": "CFO",
                "Amazon": "Amazon"
            }
        }
        
        # Instructions
        instructions = QLabel(
            "Click 'Open Edit Dialog' to test the integrated editors.\n"
            "The dialog will show both Excluded Terms and Business Glossary editors in tabs."
        )
        instructions.setStyleSheet("padding: 10px; background-color: #f0f0f0; border-radius: 5px;")
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
        
        dialog = EditConfigurationDialog(
            self.test_excluded_terms, 
            self.test_business_glossary, 
            self
        )
        
        if dialog.exec():
            modified_terms, modified_glossary = dialog.get_modified_config()
            has_changes = dialog.has_changes()
            
            if has_changes:
                self.status_label.setText(
                    f"Dialog closed with changes:\n"
                    f"Terms: {len(modified_terms)} (was {len(self.test_excluded_terms)})\n"
                    f"Glossary languages: {len(modified_glossary)} (was {len(self.test_business_glossary)})"
                )
                print(f"Modified terms: {modified_terms}")
                print(f"Modified glossary: {modified_glossary}")
            else:
                self.status_label.setText("Dialog closed without changes")
        else:
            self.status_label.setText("Dialog cancelled")
    
    def show_test_data(self):
        """Display the test data being used."""
        print("=== Test Data ===")
        print(f"Excluded Terms ({len(self.test_excluded_terms)}): {self.test_excluded_terms}")
        print(f"Business Glossary ({len(self.test_business_glossary)} languages):")
        for language, terms in self.test_business_glossary.items():
            print(f"  {language}: {len(terms)} terms - {list(terms.keys())}")
        print("================")
        
        self.status_label.setText("Test data displayed in console")


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet("""
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
    """)
    
    window = TestWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main() 