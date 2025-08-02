#!/usr/bin/env python3
"""
Test script for Business Glossary Editor
"""
import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QHBoxLayout
from PySide6.QtCore import Qt
sys.path.insert(0, 'gui')
from gui.ui.business_glossary_editor import BusinessGlossaryEditor


class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Business Glossary Editor Test")
        self.setGeometry(100, 100, 800, 600)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create the business glossary editor
        self.glossary_editor = BusinessGlossaryEditor()
        
        # Test data - Business glossary with language-specific translations
        # Note: EXCLUDED_TERMS would be separate and language-agnostic
        test_glossary = {
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
            }
        }
        
        self.glossary_editor.set_glossary(test_glossary)
        self.glossary_editor.glossary_changed.connect(self.on_glossary_changed)
        
        # Test buttons
        button_layout = QHBoxLayout()
        
        get_btn = QPushButton("Get Current Glossary")
        get_btn.clicked.connect(self.get_current_glossary)
        
        clear_btn = QPushButton("Clear Glossary")
        clear_btn.clicked.connect(self.clear_glossary)
        
        button_layout.addWidget(get_btn)
        button_layout.addWidget(clear_btn)
        button_layout.addStretch()
        
        layout.addWidget(self.glossary_editor)
        layout.addLayout(button_layout)
    
    def on_glossary_changed(self, glossary):
        print(f"Glossary changed: {len(glossary)} languages")
        for language, terms in glossary.items():
            print(f"  {language}: {len(terms)} terms")
    
    def get_current_glossary(self):
        glossary = self.glossary_editor.get_glossary()
        print(f"Current glossary: {len(glossary)} languages")
        for language, terms in glossary.items():
            print(f"  {language}: {terms}")
    
    def clear_glossary(self):
        self.glossary_editor.set_glossary({})


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet("""
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
    """)
    
    window = TestWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main() 