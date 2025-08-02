"""
API Configuration Section
Handles OpenAI API key input and connection testing
"""

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class APISection(QGroupBox):
    """API Configuration section with collapsible content"""

    def __init__(self, settings_manager):
        super().__init__("API Configuration")
        self.settings_manager = settings_manager
        self.setObjectName("apiSection")
        self.is_connected = False

        self.setup_ui()

    def setup_ui(self):
        """Set up the API section UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)

        # Header with status and toggle button
        header_layout = QHBoxLayout()

        # Status indicator and title
        self.status_label = QLabel("🔑 API Configuration")
        self.status_label.setObjectName("subHeaderLabel")

        # Status indicator (✅ Connected or ⏳ Not Connected)
        self.status_indicator = QLabel("⏳ Not Connected")
        self.status_indicator.setObjectName("statusIndicator")

        # Toggle button
        self.toggle_btn = QPushButton("▼")
        self.toggle_btn.setObjectName("secondaryButton")
        self.toggle_btn.setFixedSize(30, 30)

        header_layout.addWidget(self.status_label)
        header_layout.addWidget(self.status_indicator)
        header_layout.addStretch()
        header_layout.addWidget(self.toggle_btn)

        # Content area (initially visible for setup)
        self.content = QWidget()
        content_layout = QVBoxLayout(self.content)
        content_layout.setSpacing(10)

        # API Key input
        api_input_layout = QHBoxLayout()
        api_label = QLabel("API Key:")
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setPlaceholderText("Enter your OpenAI API key")
        self.api_key_input.setObjectName("apiKeyInput")

        self.test_connection_btn = QPushButton("Test Connection")
        self.test_connection_btn.setObjectName("primaryButton")

        api_input_layout.addWidget(api_label)
        api_input_layout.addWidget(self.api_key_input)
        api_input_layout.addWidget(self.test_connection_btn)

        # Action buttons for connected state
        self.action_buttons = QHBoxLayout()

        self.edit_key_btn = QPushButton("Edit Settings")
        self.edit_key_btn.setObjectName("secondaryButton")
        self.edit_key_btn.setVisible(False)  # Initially hidden

        self.test_connection_btn_connected = QPushButton("Test Connection")
        self.test_connection_btn_connected.setObjectName("secondaryButton")
        self.test_connection_btn_connected.setVisible(False)  # Initially hidden

        self.action_buttons.addWidget(self.edit_key_btn)
        self.action_buttons.addWidget(self.test_connection_btn_connected)
        self.action_buttons.addStretch()

        # Status label (for error messages)
        self.status_label = QLabel("")
        self.status_label.setObjectName("statusLabel")

        # Add layouts to main layout
        content_layout.addLayout(api_input_layout)
        content_layout.addLayout(self.action_buttons)
        content_layout.addWidget(self.status_label)

        layout.addLayout(header_layout)
        layout.addWidget(self.content)

    def connect_signals(
        self, test_connection_callback, edit_key_callback, toggle_callback
    ):
        """Connect button signals to callbacks"""
        self.test_connection_btn.clicked.connect(test_connection_callback)
        self.test_connection_btn_connected.clicked.connect(test_connection_callback)
        self.edit_key_btn.clicked.connect(edit_key_callback)
        self.toggle_btn.clicked.connect(toggle_callback)

    def get_api_key(self) -> str:
        """Get the current API key from input field"""
        return self.api_key_input.text().strip()

    def set_api_key(self, api_key: str):
        """Set the API key in the input field"""
        self.api_key_input.setText(api_key)

    def toggle_expansion(self):
        """Toggle the API Configuration section expansion"""
        if self.is_connected:
            # If connected, toggle between collapsed and expanded
            self.content.setVisible(not self.content.isVisible())
            self.toggle_btn.setText("▲" if self.content.isVisible() else "▼")
        else:
            # If not connected, always show content for setup
            self.content.setVisible(True)
            self.toggle_btn.setText("▲")

    def set_connected_status(self, connected: bool):
        """Set the connected status and update UI accordingly"""
        self.is_connected = connected
        if connected:
            self.status_indicator.setText("✅ Connected")
            self.status_indicator.setStyleSheet("color: green; font-weight: bold;")
            # Show action buttons, hide input
            self.test_connection_btn.setVisible(False)
            self.api_key_input.setVisible(False)
            self.edit_key_btn.setVisible(True)
            self.test_connection_btn_connected.setVisible(True)
            # Collapse content by default
            self.content.setVisible(False)
            self.toggle_btn.setText("▼")
        else:
            self.status_indicator.setText("⏳ Not Connected")
            self.status_indicator.setStyleSheet("color: orange; font-weight: bold;")
            # Show input, hide action buttons
            self.test_connection_btn.setVisible(True)
            self.api_key_input.setVisible(True)
            self.edit_key_btn.setVisible(False)
            self.test_connection_btn_connected.setVisible(False)
            # Show content for setup
            self.content.setVisible(True)
            self.toggle_btn.setText("▲")

    def show_error(self, error_message: str):
        """Show error message"""
        self.status_label.setText(error_message)
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        self.status_label.setVisible(True)

    def clear_error(self):
        """Clear error message"""
        self.status_label.setText("")
        self.status_label.setVisible(False)

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
