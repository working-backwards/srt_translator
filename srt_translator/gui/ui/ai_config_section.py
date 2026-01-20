#!/usr/bin/env python3
"""
AI Configuration Section for the SRT Translator GUI.
"""

from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
)

from srt_translator.gui.settings_manager import SettingsManager
from srt_translator.gui.ui.dnt_terms_editor import DNTTermsEditor
from srt_translator.gui.ui.termbase_editor import TermbaseEditor
from srt_translator.gui.ui.toggle_button import AnimatedToggleButton


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
            "Takes 30-60 seconds. Requires OpenAI API key.\n\n"
            "Note: If you have imported termbase/DNT files, they will be merged with AI-generated results."
        )

        # Import buttons layout
        import_layout = QHBoxLayout()
        self.import_termbase_btn = QPushButton("Import Termbase")
        self.import_termbase_btn.setObjectName("secondaryButton")
        self.import_termbase_btn.setToolTip(
            "Import your own termbase JSON file.\n"
            'Format: {"lang_code": {"source_term": "translation", ...}, ...}\n'
            "User-provided entries will take precedence over AI-generated ones."
        )

        self.import_dnt_btn = QPushButton("Import DNT Terms")
        self.import_dnt_btn.setObjectName("secondaryButton")
        self.import_dnt_btn.setToolTip(
            "Import your own DNT (Do Not Translate) terms.\n"
            'Supports JSON array format: ["term1", "term2", ...]\n'
            "Or text file: one term per line.\n"
            "User-provided terms will take precedence over AI-generated ones."
        )

        import_layout.addWidget(self.import_termbase_btn)
        import_layout.addWidget(self.import_dnt_btn)
        import_layout.addStretch()

        # URL fetch section
        url_layout = QVBoxLayout()
        url_layout.setSpacing(8)

        url_label = QLabel("Or fetch from URL:")
        url_label.setStyleSheet("color: #6B7280; font-size: 12px; font-weight: 500;")

        # Termbase URL
        termbase_url_layout = QHBoxLayout()
        termbase_url_label = QLabel("Termbase URL:")
        termbase_url_label.setMinimumWidth(100)
        self.termbase_url_input = QLineEdit()
        self.termbase_url_input.setPlaceholderText("https://example.com/termbase.json")
        self.termbase_url_input.setToolTip(
            "Enter a URL to fetch termbase JSON from.\n"
            "The URL will be saved and fetched automatically when generating settings."
        )
        self.fetch_termbase_btn = QPushButton("Fetch")
        self.fetch_termbase_btn.setObjectName("secondaryButton")
        self.fetch_termbase_btn.setFixedWidth(80)
        self.fetch_termbase_btn.setToolTip("Fetch termbase from the URL above")

        termbase_url_layout.addWidget(termbase_url_label)
        termbase_url_layout.addWidget(self.termbase_url_input)
        termbase_url_layout.addWidget(self.fetch_termbase_btn)

        # DNT URL
        dnt_url_layout = QHBoxLayout()
        dnt_url_label = QLabel("DNT Terms URL:")
        dnt_url_label.setMinimumWidth(100)
        self.dnt_url_input = QLineEdit()
        self.dnt_url_input.setPlaceholderText("https://example.com/dnt_terms.json")
        self.dnt_url_input.setToolTip(
            "Enter a URL to fetch DNT terms from.\n"
            "Supports JSON array or text format.\n"
            "The URL will be saved and fetched automatically when generating settings."
        )
        self.fetch_dnt_btn = QPushButton("Fetch")
        self.fetch_dnt_btn.setObjectName("secondaryButton")
        self.fetch_dnt_btn.setFixedWidth(80)
        self.fetch_dnt_btn.setToolTip("Fetch DNT terms from the URL above")

        dnt_url_layout.addWidget(dnt_url_label)
        dnt_url_layout.addWidget(self.dnt_url_input)
        dnt_url_layout.addWidget(self.fetch_dnt_btn)

        url_layout.addWidget(url_label)
        url_layout.addLayout(termbase_url_layout)
        url_layout.addLayout(dnt_url_layout)

        # Tone selection (horizontal radio button group)
        tone_layout = QHBoxLayout()
        tone_layout.setSpacing(15)

        tone_label = QLabel("Tone:")
        tone_label.setStyleSheet("font-weight: 500; color: #374151;")
        tone_layout.addWidget(tone_label)

        self.tone_button_group = QButtonGroup(self)

        self.tone_casual = QRadioButton("Casual")
        self.tone_casual.setToolTip("Informal, conversational style")
        self.tone_casual.setObjectName("toneRadio")

        self.tone_neutral = QRadioButton("Neutral (recommended)")
        self.tone_neutral.setToolTip("Professional and approachable — recommended for business training.")
        self.tone_neutral.setObjectName("toneRadio")
        self.tone_neutral.setChecked(True)  # Default selection

        self.tone_formal = QRadioButton("Formal")
        self.tone_formal.setToolTip("Polite, official style (may use honorifics in some languages)")
        self.tone_formal.setObjectName("toneRadio")

        self.tone_button_group.addButton(self.tone_casual, 0)
        self.tone_button_group.addButton(self.tone_neutral, 1)
        self.tone_button_group.addButton(self.tone_formal, 2)

        tone_layout.addWidget(self.tone_casual)
        tone_layout.addWidget(self.tone_neutral)
        tone_layout.addWidget(self.tone_formal)
        tone_layout.addStretch()

        # Action buttons for configured state
        self.action_buttons = QHBoxLayout()

        self.edit_btn = QPushButton("Edit Settings")
        self.edit_btn.setObjectName("secondaryButton")
        self.edit_btn.setEnabled(False)  # Will be enabled when config is generated
        self.edit_btn.setToolTip("Review and modify the AI-generated translation settings")

        self.regenerate_btn = QPushButton("Regenerate")
        self.regenerate_btn.setObjectName("secondaryButton")
        self.regenerate_btn.setEnabled(False)  # Will be enabled when config is generated
        self.regenerate_btn.setToolTip("Generate new translation settings based on current file selection")

        self.view_details_btn = QPushButton("View Details")
        self.view_details_btn.setObjectName("secondaryButton")
        self.view_details_btn.setEnabled(False)  # Will be enabled when config is generated
        self.view_details_btn.setToolTip("View detailed information about current translation settings")

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

        # Progress text label (initially hidden)
        self.progress_label = QLabel("")
        self.progress_label.setVisible(False)
        self.progress_label.setWordWrap(True)
        self.progress_label.setStyleSheet("color: #6B7280; font-size: 12px;")

        # DNT (Do Not Translate) display
        dnt_label = QLabel("🚫 Do Not Translate (DNT) - Terms that stay in original language:")
        self.dnt_display = QTextEdit()
        self.dnt_display.setObjectName("dntDisplay")
        self.dnt_display.setReadOnly(True)
        self.dnt_display.setPlaceholderText("DNT terms will appear here...")
        self.dnt_display.setMaximumHeight(80)
        self.dnt_display.setToolTip(
            "These terms will remain in the original language in all translated subtitles.\n"
            "Includes company names, people, technical acronyms, and branded terms.\n"
            'Example: "Amazon" stays "Amazon" instead of being translated.'
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
        content_layout.addLayout(import_layout)
        content_layout.addLayout(url_layout)
        content_layout.addLayout(tone_layout)
        content_layout.addLayout(self.action_buttons)
        content_layout.addWidget(self.progress_bar)
        content_layout.addWidget(self.progress_label)
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
        import_termbase_callback,
        import_dnt_callback,
        fetch_termbase_callback,
        fetch_dnt_callback,
    ):
        """Connect button signals to callbacks"""
        self.toggle_btn.clicked.connect(toggle_callback)
        self.generate_btn.clicked.connect(generate_callback)
        self.edit_btn.clicked.connect(edit_callback)
        self.regenerate_btn.clicked.connect(regenerate_callback)
        self.view_details_btn.clicked.connect(view_details_callback)
        self.help_btn.clicked.connect(help_callback)
        self.import_termbase_btn.clicked.connect(import_termbase_callback)
        self.import_dnt_btn.clicked.connect(import_dnt_callback)
        self.fetch_termbase_btn.clicked.connect(fetch_termbase_callback)
        self.fetch_dnt_btn.clicked.connect(fetch_dnt_callback)

    def get_termbase_url(self) -> str:
        """Get the termbase URL from the input field"""
        return self.termbase_url_input.text().strip()

    def set_termbase_url(self, url: str) -> None:
        """Set the termbase URL in the input field"""
        self.termbase_url_input.setText(url)

    def get_dnt_url(self) -> str:
        """Get the DNT URL from the input field"""
        return self.dnt_url_input.text().strip()

    def set_dnt_url(self, url: str) -> None:
        """Set the DNT URL in the input field"""
        self.dnt_url_input.setText(url)

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
        self.progress_label.setVisible(show)
        self.generate_btn.setEnabled(not show)

    def update_progress(self, message: str):
        """Update the progress text with a message"""
        self.progress_label.setText(message)
        self.progress_label.setVisible(True)

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
            summary = f"Generated for {len(languages)} languages: {', '.join(languages[:3])}"
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

    def get_tone(self) -> str:
        """Get the currently selected tone"""
        if self.tone_casual.isChecked():
            return "casual"
        elif self.tone_formal.isChecked():
            return "formal"
        else:
            return "neutral"

    def set_tone(self, tone: str) -> None:
        """Set the tone selection"""
        tone_lower = (tone or "neutral").lower().strip()
        if tone_lower == "casual":
            self.tone_casual.setChecked(True)
        elif tone_lower == "formal":
            self.tone_formal.setChecked(True)
        else:
            self.tone_neutral.setChecked(True)

    def connect_tone_changed(self, callback) -> None:
        """Connect a callback to be called when tone selection changes"""
        self.tone_button_group.buttonClicked.connect(lambda: callback(self.get_tone()))


class EditConfigurationDialog(QDialog):
    """Dialog for editing AI-generated configuration."""

    def __init__(
        self,
        settings_manager: SettingsManager,
        dnt_terms: list,
        termbase: dict,
        parent=None,
    ):
        super().__init__(parent)
        self.dnt_terms = dnt_terms.copy()
        self.termbase = termbase.copy()
        self.modified_terms = dnt_terms.copy()
        self.modified_termbase = termbase.copy()

        self.settings_manager = settings_manager
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
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
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
        self.settings_manager.save_ai_config(dnt_terms=self.modified_terms, termbase=self.modified_termbase)

    def get_modified_config(self) -> tuple:
        """Get the modified configuration."""
        return self.modified_terms, self.modified_termbase

    def has_changes(self) -> bool:
        """Check if any changes were made."""
        return self.terms_editor.is_modified(self.dnt_terms) or self.termbase_editor.is_modified(self.termbase)
