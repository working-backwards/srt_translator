"""
AI Configuration Section
Handles AI-powered configuration generation and display
"""

from PySide6.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QFrame,
    QProgressBar
)
from PySide6.QtCore import Qt


class AIConfigSection(QGroupBox):
    """AI Configuration section with collapsible content"""
    
    def __init__(self):
        super().__init__("AI Configuration")
        self.setObjectName("aiConfigSection")
        self.ai_config_expanded = False
        
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the AI configuration section UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Header with toggle button
        header_layout = QHBoxLayout()
        header_label = QLabel("AI Terms & Glossary")
        header_label.setObjectName("subHeaderLabel")
        
        self.ai_toggle_btn = QPushButton("▼")
        self.ai_toggle_btn.setObjectName("secondaryButton")
        self.ai_toggle_btn.setFixedSize(30, 30)
        
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        header_layout.addWidget(self.ai_toggle_btn)
        
        # Content area (initially hidden)
        self.ai_content = QFrame()
        self.ai_content.setVisible(False)
        ai_content_layout = QVBoxLayout(self.ai_content)
        ai_content_layout.setSpacing(10)
        
        # Generate Configuration button
        self.generate_btn = QPushButton("Generate Configuration")
        self.generate_btn.setObjectName("primaryButton")
        self.generate_btn.setEnabled(False)  # Will be enabled when files are selected
        
        # Progress bar (initially hidden)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        
        # AI-generated terms display
        terms_label = QLabel("AI-Generated Terms:")
        self.terms_display = QTextEdit()
        self.terms_display.setObjectName("aiTermsDisplay")
        self.terms_display.setReadOnly(True)
        self.terms_display.setPlaceholderText("AI-generated terms will appear here...")
        self.terms_display.setMaximumHeight(60)
        
        # Glossary display
        glossary_label = QLabel("Glossary:")
        self.glossary_display = QTextEdit()
        self.glossary_display.setObjectName("glossaryDisplay")
        self.glossary_display.setReadOnly(True)
        self.glossary_display.setPlaceholderText("Glossary will appear here...")
        self.glossary_display.setMaximumHeight(60)
        
        ai_content_layout.addWidget(self.generate_btn)
        ai_content_layout.addWidget(self.progress_bar)
        ai_content_layout.addWidget(terms_label)
        ai_content_layout.addWidget(self.terms_display)
        ai_content_layout.addWidget(glossary_label)
        ai_content_layout.addWidget(self.glossary_display)
        
        layout.addLayout(header_layout)
        layout.addWidget(self.ai_content)
    
    def connect_signals(self, toggle_callback, generate_callback):
        """Connect button signals to callbacks"""
        self.ai_toggle_btn.clicked.connect(toggle_callback)
        self.generate_btn.clicked.connect(generate_callback)
    
    def toggle_expansion(self):
        """Toggle the AI configuration section expansion"""
        self.ai_config_expanded = not self.ai_config_expanded
        self.ai_content.setVisible(self.ai_config_expanded)
        
        if self.ai_config_expanded:
            self.ai_toggle_btn.setText("▲")
            # Expand to 150px height as per style guide
            self.ai_content.setMaximumHeight(150)
        else:
            self.ai_toggle_btn.setText("▼")
            # Collapse to 70px height as per style guide
            self.ai_content.setMaximumHeight(70)
    
    def set_terms_display(self, terms_text: str):
        """Set the terms display text"""
        self.terms_display.setText(terms_text)
    
    def set_glossary_display(self, glossary_text: str):
        """Set the glossary display text"""
        self.glossary_display.setText(glossary_text)
    
    def clear_displays(self):
        """Clear both terms and glossary displays"""
        self.terms_display.clear()
        self.glossary_display.clear()
    
    def set_generate_button_enabled(self, enabled: bool):
        """Enable or disable the generate configuration button"""
        self.generate_btn.setEnabled(enabled)
    
    def show_progress(self, show: bool):
        """Show or hide the progress bar"""
        self.progress_bar.setVisible(show)
        self.generate_btn.setEnabled(not show)
    
    def update_terms_display(self, terms: list):
        """Update the terms display with a list of terms"""
        if terms:
            terms_text = ", ".join(terms)
            self.terms_display.setText(terms_text)
        else:
            self.terms_display.setText("No terms generated")
    
    def update_glossary_display(self, glossary: dict):
        """Update the glossary display with glossary data"""
        if glossary:
            # Show a summary of the glossary
            total_terms = sum(len(lang_glossary) for lang_glossary in glossary.values())
            languages = list(glossary.keys())
            summary = f"Generated for {len(languages)} languages: {', '.join(languages[:3])}"
            if len(languages) > 3:
                summary += f" (+{len(languages) - 3} more)"
            summary += f"\nTotal terms: {total_terms}"
            self.glossary_display.setText(summary)
        else:
            self.glossary_display.setText("No glossary generated") 