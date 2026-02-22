#!/usr/bin/env python3
"""
AI Configuration Section for the SRT Translator GUI.
"""

from PySide6.QtCore import Qt
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
    QSlider,
    QTabWidget,
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
            "User-provided terms will take precedence over AI-generated ones."
        )

        import_layout.addWidget(self.import_termbase_btn)
        import_layout.addWidget(self.import_dnt_btn)
        import_layout.addStretch()

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

        self.edit_btn = QPushButton("Edit/View Settings")
        self.edit_btn.setObjectName("secondaryButton")
        self.edit_btn.setEnabled(False)  # Will be enabled when config is generated
        self.edit_btn.setToolTip("Review and modify the AI-generated translation settings")

        self.regenerate_btn = QPushButton("Regenerate")
        self.regenerate_btn.setObjectName("secondaryButton")
        self.regenerate_btn.setEnabled(False)  # Will be enabled when config is generated
        self.regenerate_btn.setToolTip("Generate new translation settings based on current file selection")

        self.action_buttons.addWidget(self.edit_btn)
        self.action_buttons.addWidget(self.regenerate_btn)

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

        content_layout.addWidget(self.generate_btn)
        content_layout.addLayout(import_layout)
        content_layout.addLayout(tone_layout)
        content_layout.addLayout(self.action_buttons)
        content_layout.addWidget(self.progress_bar)
        content_layout.addWidget(self.progress_label)

        # --- Advanced Settings (collapsible) ---
        adv_separator = QFrame()
        adv_separator.setFrameShape(QFrame.Shape.HLine)
        adv_separator.setFrameShadow(QFrame.Shadow.Sunken)
        content_layout.addWidget(adv_separator)

        adv_header = QHBoxLayout()
        adv_label = QLabel("Advanced Settings")
        adv_label.setStyleSheet("font-weight: 500; color: #374151;")
        self.adv_toggle_btn = AnimatedToggleButton()
        adv_header.addWidget(adv_label)
        adv_header.addStretch()
        adv_header.addWidget(self.adv_toggle_btn)
        content_layout.addLayout(adv_header)

        self.adv_content = QFrame()
        self.adv_content.setVisible(False)
        adv_layout = QVBoxLayout(self.adv_content)
        adv_layout.setSpacing(8)

        # Model row
        model_row = QHBoxLayout()
        model_label = QLabel("Model:")
        model_label.setStyleSheet("font-weight: 500; color: #374151;")
        self.model_name_edit = QLineEdit()
        self.model_name_edit.setPlaceholderText("gpt-4o-mini")
        self.model_name_edit.setToolTip(
            "OpenAI model used for translation. Examples: gpt-4o-mini, gpt-4o, gpt-4.1-mini"
        )
        model_row.addWidget(model_label)
        model_row.addWidget(self.model_name_edit)
        adv_layout.addLayout(model_row)

        # Aggressiveness row
        agg_row = QHBoxLayout()
        agg_label = QLabel("Fix Aggressiveness:")
        agg_label.setStyleSheet("font-weight: 500; color: #374151;")
        self.aggressiveness_slider = QSlider(Qt.Orientation.Horizontal)
        self.aggressiveness_slider.setRange(0, 100)
        self.aggressiveness_slider.setValue(75)
        self.aggressiveness_slider.setToolTip(
            "How aggressively the system fixes placeholder issues. "
            "0.0 = lenient, 1.0 = strict. Recommended: 0.75"
        )
        self.aggressiveness_value_label = QLabel("0.75")
        self.aggressiveness_value_label.setFixedWidth(35)
        self.aggressiveness_slider.valueChanged.connect(self._on_aggressiveness_changed)
        agg_row.addWidget(agg_label)
        agg_row.addWidget(self.aggressiveness_slider)
        agg_row.addWidget(self.aggressiveness_value_label)
        adv_layout.addLayout(agg_row)

        # Reset to Defaults button
        self.reset_advanced_btn = QPushButton("Reset to Defaults")
        self.reset_advanced_btn.setObjectName("secondaryButton")
        self.reset_advanced_btn.setToolTip("Reset model and aggressiveness to default values")
        adv_layout.addWidget(self.reset_advanced_btn)

        content_layout.addWidget(self.adv_content)

        layout.addLayout(header_layout)
        layout.addWidget(self.content)

    def connect_signals(
        self,
        toggle_callback,
        generate_callback,
        edit_callback,
        regenerate_callback,
        help_callback,
        import_termbase_callback,
        import_dnt_callback,
    ):
        """Connect button signals to callbacks"""
        self.toggle_btn.clicked.connect(toggle_callback)
        self.generate_btn.clicked.connect(generate_callback)
        self.edit_btn.clicked.connect(edit_callback)
        self.regenerate_btn.clicked.connect(regenerate_callback)
        self.help_btn.clicked.connect(help_callback)
        self.import_termbase_btn.clicked.connect(import_termbase_callback)
        self.import_dnt_btn.clicked.connect(import_dnt_callback)

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

    def set_generate_button_enabled(self, enabled: bool):
        """Enable or disable the generate configuration button"""
        self.generate_btn.setEnabled(enabled)

    def set_action_buttons_enabled(self, enabled: bool):
        """Enable or disable all action buttons"""
        self.edit_btn.setEnabled(enabled)
        self.regenerate_btn.setEnabled(enabled)
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
        else:
            self.status_indicator.setText("⏳ Not Configured")
            self.status_indicator.setStyleSheet("color: #6B7280; font-weight: 500;")
            # Show generate button, hide action buttons
            self.generate_btn.setVisible(True)
            self.edit_btn.setVisible(False)
            self.regenerate_btn.setVisible(False)

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

    def toggle_advanced_expansion(self) -> None:
        """Toggle the Advanced Settings subsection visibility."""
        visible = not self.adv_content.isVisible()
        self.adv_content.setVisible(visible)
        self.adv_toggle_btn.set_expanded_state(visible)

    def get_model_name(self) -> str:
        """Get the current model name from the text field."""
        return self.model_name_edit.text().strip() or "gpt-4o-mini"

    def set_model_name(self, name: str) -> None:
        """Set the model name in the text field."""
        self.model_name_edit.setText(name)

    def get_aggressiveness(self) -> float:
        """Get the current aggressiveness value (0.0-1.0)."""
        return self.aggressiveness_slider.value() / 100.0

    def set_aggressiveness(self, value: float) -> None:
        """Set the aggressiveness slider value (0.0-1.0)."""
        int_val = max(0, min(100, int(round(value * 100))))
        self.aggressiveness_slider.setValue(int_val)
        self.aggressiveness_value_label.setText(f"{value:.2f}")

    def _on_aggressiveness_changed(self, value: int) -> None:
        """Update the value display label when slider moves."""
        self.aggressiveness_value_label.setText(f"{value / 100.0:.2f}")

    def _on_reset_advanced_defaults(self) -> None:
        """Reset both advanced fields to defaults."""
        self.model_name_edit.setText("gpt-4o-mini")
        self.aggressiveness_slider.setValue(75)
        self.aggressiveness_value_label.setText("0.75")


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
