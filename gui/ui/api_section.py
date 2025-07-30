"""
API Configuration Section
Handles OpenAI API key input and connection testing
"""

import logging
from PySide6.QtWidgets import (
    QGroupBox, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton
)
from PySide6.QtCore import Qt


class APISection(QGroupBox):
    """API key configuration section with status bar style"""
    
    def __init__(self, settings_manager):
        super().__init__("OpenAI API Configuration")
        self.settings_manager = settings_manager
        self.setObjectName("apiSection")
        
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the API section UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)  # Standard margins for input mode
        
        # API Key input (initially visible)
        self.api_input_widget = QWidget()
        self.api_input_layout = QHBoxLayout(self.api_input_widget)
        api_label = QLabel("API Key:")
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setPlaceholderText("Enter your OpenAI API key")
        self.api_key_input.setObjectName("apiKeyInput")
        
        self.test_connection_btn = QPushButton("Test Connection")
        self.test_connection_btn.setObjectName("primaryButton")
        
        self.api_input_layout.addWidget(api_label)
        self.api_input_layout.addWidget(self.api_key_input)
        self.api_input_layout.addWidget(self.test_connection_btn)
        
        # Status bar (initially hidden)
        self.api_status_widget = QWidget()
        self.api_status_widget.setFixedHeight(32)  # Compact height
        self.api_status_layout = QHBoxLayout(self.api_status_widget)
        self.api_status_layout.setContentsMargins(0, 0, 0, 0)
        
        # Status icon
        self.status_icon = QLabel("✓")
        self.status_icon.setObjectName("statusIcon")
        self.status_icon.setFixedSize(20, 20)
        
        # Status text
        self.api_status_text = QLabel("OpenAI API Connected")
        self.api_status_text.setObjectName("apiStatusText")
        
        # Edit button
        self.edit_key_btn = QPushButton("Edit Key")
        self.edit_key_btn.setObjectName("secondaryButton")
        
        self.api_status_layout.addWidget(self.status_icon)
        self.api_status_layout.addWidget(self.api_status_text)
        self.api_status_layout.addStretch()
        self.api_status_layout.addWidget(self.edit_key_btn)
        
        # Status label (for error messages)
        self.api_status_label = QLabel("")
        self.api_status_label.setObjectName("statusLabel")
        
        # Add layouts to main layout
        layout.addWidget(self.api_input_widget)
        layout.addWidget(self.api_status_widget)
        layout.addWidget(self.api_status_label)
        
        # Initially hide status bar
        self.api_status_widget.setVisible(False)
    
    def connect_signals(self, test_connection_callback, edit_key_callback):
        """Connect button signals to callbacks"""
        self.test_connection_btn.clicked.connect(test_connection_callback)
        self.edit_key_btn.clicked.connect(edit_key_callback)
    
    def get_api_key(self) -> str:
        """Get the current API key from input field"""
        return self.api_key_input.text().strip()
    
    def set_api_key(self, api_key: str):
        """Set the API key in the input field"""
        self.api_key_input.setText(api_key)
    
    def show_input_mode(self):
        """Show the API input field"""
        self.api_input_widget.setVisible(True)
        self.api_status_widget.setVisible(False)
        self.api_status_label.setText("")
        self.api_status_label.setVisible(False)
        self.api_key_input.setFocus()
        
        # Switch to input mode spacing
        layout = self.layout()
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)
    
    def show_status_mode(self, api_key: str):
        """Show the status bar when API key is valid"""
        self.api_input_widget.setVisible(False)
        self.api_status_widget.setVisible(True)
        self.api_status_label.setVisible(False)
        
        # Switch to compact status mode spacing
        layout = self.layout()
        layout.setSpacing(5)  # Reduced spacing
        layout.setContentsMargins(10, 8, 10, 8)  # Reduced margins
        
        # Update status icon and text
        self.status_icon.setText("✓")
        self.status_icon.setProperty("class", "success")
        self.api_status_text.setText("OpenAI API Connected")
        self.api_status_text.setProperty("class", "success")
        
        # Apply styling
        self.status_icon.style().unpolish(self.status_icon)
        self.status_icon.style().polish(self.status_icon)
        self.api_status_text.style().unpolish(self.api_status_text)
        self.api_status_text.style().polish(self.api_status_text)
    
    def show_error(self, error_message: str):
        """Show error message"""
        self.api_status_label.setText(error_message)
        self.api_status_label.setProperty("class", "error")
        self.api_status_label.style().unpolish(self.api_status_label)
        self.api_status_label.style().polish(self.api_status_label)
        self.api_status_label.setVisible(True)
    
    def load_saved_api_key(self):
        """Load and validate saved API key"""
        api_key = self.settings_manager.load_api_key()
        if api_key:
            self.set_api_key(api_key)
            # Check if the saved API key is valid and show status bar
            if api_key.startswith("sk-") and len(api_key) > 20:
                self.show_status_mode(api_key)
                return True
        return False 