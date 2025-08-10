"""
AI Configuration Section
Handles AI-powered configuration generation and display
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
)

from srt_core.config.language_config import language_config


from .dnt_terms_editor import DNTTermsEditor
from .termbase_editor import TermbaseEditor
from .toggle_button import AnimatedToggleButton


class AIConfigSection(QGroupBox):
    """Translation Settings section with collapsible content"""

    def __init__(self):
        super().__init__("Translation Settings")
        self.setObjectName("translationSettingsSection")
        self.is_expanded = False
        self.is_configured = False

        self.setup_ui()

    def setup_ui(self):
        """Set up the AI configuration section UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Header with status and toggle button
        header_layout = QHBoxLayout()

        # Status indicator and title
        self.status_label = QLabel("⚙️ Translation Settings")
        self.status_label.setObjectName("subHeaderLabel")

        # Status indicator (✅ Configured or ⏳ Not Configured)
        self.status_indicator = QLabel("⏳ Not Configured")
        self.status_indicator.setObjectName("statusIndicator")
        self.status_indicator.setStyleSheet("color: #6B7280; font-weight: 500;")

        # Toggle button with chevron icon and animation
        self.toggle_btn = AnimatedToggleButton()

        header_layout.addWidget(self.status_label)
        header_layout.addWidget(self.status_indicator)
        header_layout.addStretch()
        header_layout.addWidget(self.toggle_btn)

        # Content area (initially hidden)
        self.content = QFrame()
        self.content.setVisible(False)
        content_layout = QVBoxLayout(self.content)
        content_layout.setSpacing(10)

        # Generate Translation Settings button
        self.generate_btn = QPushButton("Generate Translation Settings")
        self.generate_btn.setObjectName("primaryButton")
        self.generate_btn.setEnabled(False)  # Will be enabled when files are selected
        self.generate_btn.setToolTip(
            "Analyze your selected subtitle files to automatically identify:\n"
            "• Terms that should not be translated (company names, technical terms)\n"
            "• Important business vocabulary that needs consistent translation\n\n"
            "Takes 30-60 seconds. Requires OpenAI API key."
        )

        # Action buttons for configured state
        self.action_buttons = QHBoxLayout()

        self.edit_btn = QPushButton("Edit Settings")
        self.edit_btn.setObjectName("secondaryButton")
        self.edit_btn.setEnabled(False)  # Will be enabled when config is generated
        self.edit_btn.setToolTip(
            "Review and modify the AI-generated translation settings"
        )

        self.regenerate_btn = QPushButton("Regenerate")
        self.regenerate_btn.setObjectName("secondaryButton")
        self.regenerate_btn.setEnabled(
            False
        )  # Will be enabled when config is generated
        self.regenerate_btn.setToolTip(
            "Generate new translation settings based on current file selection"
        )

        self.view_details_btn = QPushButton("View Details")
        self.view_details_btn.setObjectName("secondaryButton")
        self.view_details_btn.setEnabled(
            False
        )  # Will be enabled when config is generated
        self.view_details_btn.setToolTip(
            "View detailed information about current translation settings"
        )

        self.action_buttons.addWidget(self.edit_btn)
        self.action_buttons.addWidget(self.regenerate_btn)
        self.action_buttons.addWidget(self.view_details_btn)

        # Help button
        self.help_btn = QPushButton("?")
        self.help_btn.setObjectName("helpButton")
        self.help_btn.setFixedSize(30, 30)
        self.help_btn.setToolTip("Get help with AI Configuration")
        self.help_btn.setEnabled(False)  # Will be enabled when config is generated
        self.action_buttons.addWidget(self.help_btn)

        self.action_buttons.addStretch()

        # Progress bar (initially hidden)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress

        # DNT (Do Not Translate) display
        dnt_label = QLabel(
            "🚫 Do Not Translate (DNT) - Terms that stay in original language:"
        )
        self.dnt_display = QTextEdit()
        self.dnt_display.setObjectName("dntDisplay")
        self.dnt_display.setReadOnly(True)
        self.dnt_display.setPlaceholderText("DNT terms will appear here...")
        self.dnt_display.setMaximumHeight(80)
        self.dnt_display.setToolTip(
            f"These terms will remain in the original language in all translated subtitles.\n"
            "Includes company names, people, technical acronyms, and branded terms.\n"
            f'Example: "Amazon" stays "Amazon" instead of being translated.'
        )

        # Termbase display
        termbase_label = QLabel("📚 Termbase - Consistent professional translations:")
        self.termbase_display = QTextEdit()
        self.termbase_display.setObjectName("termbaseDisplay")
        self.termbase_display.setToolTip(
            "These business terms will be translated consistently across all your course materials.\n"
            "Professional terminology appropriate for business and educational contexts.\n"
            'Example: "operating plan" → "plan operativo" (Spanish) throughout entire course.'
        )
        self.termbase_display.setReadOnly(True)
        self.termbase_display.setPlaceholderText("Termbase will appear here...")
        self.termbase_display.setMaximumHeight(120)

        content_layout.addWidget(self.generate_btn)
        content_layout.addLayout(self.action_buttons)
        content_layout.addWidget(self.progress_bar)
        content_layout.addWidget(dnt_label)
        content_layout.addWidget(self.dnt_display)
        content_layout.addWidget(termbase_label)
        content_layout.addWidget(self.termbase_display)

        layout.addLayout(header_layout)
        layout.addWidget(self.content)

    def connect_signals(
        self,
        toggle_callback,
        generate_callback,
        edit_callback,
        regenerate_callback,
        view_details_callback,
        help_callback,
    ):
        """Connect button signals to callbacks"""
        self.toggle_btn.clicked.connect(toggle_callback)
        self.generate_btn.clicked.connect(generate_callback)
        self.edit_btn.clicked.connect(edit_callback)
        self.regenerate_btn.clicked.connect(regenerate_callback)
        self.view_details_btn.clicked.connect(view_details_callback)
        self.help_btn.clicked.connect(help_callback)

    def toggle_expansion(self):
        """Toggle the Translation Settings section expansion"""
        self.is_expanded = not self.is_expanded
        self.content.setVisible(self.is_expanded)

        if self.is_expanded:
            # Expand to show full content
            self.content.setMaximumHeight(16777215)  # Qt's default maximum
        else:
            # Collapse to 0 height
            self.content.setMaximumHeight(0)

        # Animate the toggle button
        self.toggle_btn.set_expanded_state(self.is_expanded)

    def set_dnt_display(self, dnt_text: str):
        """Set the DNT display text"""
        self.dnt_display.setText(dnt_text)

    def set_termbase_display(self, termbase_text: str):
        """Set the termbase display text"""
        self.termbase_display.setText(termbase_text)

    def clear_displays(self):
        """Clear both DNT and termbase displays"""
        self.dnt_display.clear()
        self.termbase_display.clear()

    def set_generate_button_enabled(self, enabled: bool):
        """Enable or disable the generate configuration button"""
        self.generate_btn.setEnabled(enabled)

    def set_action_buttons_enabled(self, enabled: bool):
        """Enable or disable all action buttons"""
        self.edit_btn.setEnabled(enabled)
        self.regenerate_btn.setEnabled(enabled)
        self.view_details_btn.setEnabled(enabled)
        self.help_btn.setEnabled(enabled)

    def show_progress(self, show: bool):
        """Show or hide the progress bar"""
        self.progress_bar.setVisible(show)
        self.generate_btn.setEnabled(not show)

    def update_dnt_display(self, terms: list):
        """Update the DNT display with a list of terms"""
        if terms:
            terms_text = ", ".join(terms)
            self.dnt_display.setText(terms_text)
        else:
            self.dnt_display.setText("No DNT terms generated")

    def update_termbase_display(self, termbase: dict):
        """Update the termbase display with termbase data"""
        if termbase:
            # Show a summary of the termbase
            total_terms = sum(len(lang_termbase) for lang_termbase in termbase.values())
            languages = list(termbase.keys())
            summary = (
                f"Generated for {len(languages)} languages: {', '.join(languages[:3])}"
            )
            if len(languages) > 3:
                summary += f" (+{len(languages) - 3} more)"
            summary += f"\nTotal terms: {total_terms}"
            self.termbase_display.setText(summary)
        else:
            self.termbase_display.setText("No termbase generated")

    def set_configured_status(self, configured: bool):
        """Set the configured status and update UI accordingly"""
        self.is_configured = configured
        if configured:
            self.status_indicator.setText("✅ Configured")
            self.status_indicator.setStyleSheet("color: #065F46; font-weight: 600;")
            # Show action buttons, hide generate button
            self.generate_btn.setVisible(False)
            self.edit_btn.setVisible(True)
            self.regenerate_btn.setVisible(True)
            self.view_details_btn.setVisible(True)
        else:
            self.status_indicator.setText("⏳ Not Configured")
            self.status_indicator.setStyleSheet("color: #6B7280; font-weight: 500;")
            # Show generate button, hide action buttons
            self.generate_btn.setVisible(True)
            self.edit_btn.setVisible(False)
            self.regenerate_btn.setVisible(False)
            self.view_details_btn.setVisible(False)


class EditConfigurationDialog(QDialog):
    """Dialog for editing AI-generated configuration."""

    def __init__(
        self,
        dnt_terms: list,
        termbase: dict,
        parent=None,
    ):
        super().__init__(parent)
        self.dnt_terms = dnt_terms.copy()
        self.termbase = termbase.copy()
        self.modified_terms = dnt_terms.copy()
        self.modified_termbase = termbase.copy()

        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("Translation Settings")
        self.setModal(True)
        self.resize(800, 600)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Header
        header_label = QLabel("Edit Translation Settings")
        header_label.setObjectName("subHeaderLabel")
        layout.addWidget(header_label)

        # Tab widget for organizing editors
        self.tab_widget = QTabWidget()

        # DNT Tab
        self.terms_editor = DNTTermsEditor()
        self.terms_editor.set_terms(self.dnt_terms)
        self.tab_widget.addTab(self.terms_editor, "DNT")

        # Termbase Tab
        self.termbase_editor = TermbaseEditor()
        self.termbase_editor.set_termbase(self.termbase)
        self.tab_widget.addTab(self.termbase_editor, "Termbase")

        layout.addWidget(self.tab_widget)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def connect_signals(self):
        """Connect widget signals."""
        self.terms_editor.terms_changed.connect(self.on_terms_changed)
        self.termbase_editor.termbase_changed.connect(self.on_termbase_changed)

    def on_terms_changed(self, terms: list):
        """Handle terms changes."""
        self.modified_terms = terms

    def on_termbase_changed(self, termbase: dict):
        """Handle termbase changes."""
        self.modified_termbase = termbase

    def get_modified_config(self) -> tuple:
        """Get the modified configuration."""
        return self.modified_terms, self.modified_termbase

    def has_changes(self) -> bool:
        """Check if any changes were made."""
        return self.terms_editor.is_modified(
            self.dnt_terms
        ) or self.termbase_editor.is_modified(self.termbase)
