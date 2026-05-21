#!/usr/bin/env python3
"""
Application Settings Dialog for the SRT Translator GUI.

Contains API key configuration and advanced settings (generation model,
aggressiveness) that were previously inline in the main window.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSlider,
    QVBoxLayout,
)

from srt_translator.config.model_config_loader import MODEL_CONFIG, get_model_config
from srt_translator.core.constants import DEFAULT_GENERATION_MODEL, DEFAULT_TEMPERATURE


class SettingsDialog(QDialog):
    """Application-level settings dialog with API key and advanced settings."""

    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self._original_api_key = settings_manager.load_api_key() or ""
        self._original_model = settings_manager.load_generation_model_name()
        self._original_aggressiveness = settings_manager.load_aggressiveness()

        self.setup_ui()
        self._load_current_values()

    def setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.resize(550, 380)

        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(24, 24, 24, 24)

        # --- API Configuration ---
        api_header = QLabel("API Configuration")
        api_header.setObjectName("subHeaderLabel")
        api_header.setStyleSheet("font-size: 15px; font-weight: 600; color: #1E293B;")
        layout.addWidget(api_header)

        # API key row
        api_row = QHBoxLayout()
        api_label = QLabel("API Key:")
        api_label.setFixedWidth(80)
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setPlaceholderText("Enter your OpenAI API key")
        self.api_key_input.setObjectName("apiKeyInput")

        self.test_btn = QPushButton("Test Connection")
        self.test_btn.setObjectName("secondaryButton")
        self.test_btn.clicked.connect(self._test_connection)

        api_row.addWidget(api_label)
        api_row.addWidget(self.api_key_input)
        api_row.addWidget(self.test_btn)
        layout.addLayout(api_row)

        # Storage disclosure — visible at the moment the user pastes the key,
        # so the local-plaintext storage characteristic is impossible to miss.
        api_storage_note = QLabel(
            "Stored locally in app settings (not encrypted). Rotate the key at platform.openai.com if exposed."
        )
        api_storage_note.setObjectName("storageDisclosureLabel")
        api_storage_note.setStyleSheet("color: #64748B; font-size: 11px;")
        api_storage_note.setWordWrap(True)
        layout.addWidget(api_storage_note)

        # API status
        self.api_status_label = QLabel("")
        self.api_status_label.setObjectName("statusLabel")
        layout.addWidget(self.api_status_label)

        # --- Separator ---
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(sep)

        # --- Advanced Settings ---
        adv_header = QLabel("Advanced Settings")
        adv_header.setObjectName("subHeaderLabel")
        adv_header.setStyleSheet("font-size: 15px; font-weight: 600; color: #1E293B;")
        layout.addWidget(adv_header)

        # Generation model row
        model_row = QHBoxLayout()
        model_label = QLabel("Generation Model:")
        model_label.setStyleSheet("font-weight: 500; color: #374151;")
        model_label.setFixedWidth(130)
        self.generation_model_dropdown = QComboBox()
        self.generation_model_dropdown.addItems(list(MODEL_CONFIG.keys()))
        self.generation_model_dropdown.setToolTip(
            "OpenAI model used for DNT/termbase generation.\n"
            "Examples: gpt-4o-mini, gpt-4o, gpt-4.1-mini, gpt-5-mini\n\n"
            "Note: gpt-5-mini does not support custom temperature —\n"
            "the Fix Aggressiveness option will be hidden for that model."
        )
        self.generation_model_dropdown.currentTextChanged.connect(self._on_model_changed)
        model_row.addWidget(model_label)
        model_row.addWidget(self.generation_model_dropdown)
        layout.addLayout(model_row)

        # Aggressiveness row
        self.agg_row_frame = QFrame()
        agg_row = QHBoxLayout(self.agg_row_frame)
        agg_row.setContentsMargins(0, 0, 0, 0)
        agg_label = QLabel("Fix Aggressiveness:")
        agg_label.setStyleSheet("font-weight: 500; color: #374151;")
        agg_label.setFixedWidth(130)
        self.aggressiveness_slider = QSlider(Qt.Orientation.Horizontal)
        self.aggressiveness_slider.setRange(0, 100)
        self.aggressiveness_slider.setToolTip(
            "How aggressively the system fixes placeholder issues.\n0.0 = lenient, 1.0 = strict. Recommended: 0.75"
        )
        self.aggressiveness_value_label = QLabel("")
        self.aggressiveness_value_label.setFixedWidth(35)
        self.aggressiveness_slider.valueChanged.connect(self._on_agg_slider_changed)
        agg_row.addWidget(agg_label)
        agg_row.addWidget(self.aggressiveness_slider)
        agg_row.addWidget(self.aggressiveness_value_label)
        layout.addWidget(self.agg_row_frame)

        # Reset defaults
        self.reset_btn = QPushButton("Reset to Defaults")
        self.reset_btn.setObjectName("secondaryButton")
        self.reset_btn.clicked.connect(self._reset_defaults)
        layout.addWidget(self.reset_btn, alignment=Qt.AlignLeft)

        layout.addStretch()

        # --- Bottom buttons ---
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("secondaryButton")
        self.cancel_btn.clicked.connect(self.reject)

        self.save_btn = QPushButton("Save")
        self.save_btn.setObjectName("primaryButton")
        self.save_btn.clicked.connect(self._save_and_close)

        btn_row.addWidget(self.cancel_btn)
        btn_row.addWidget(self.save_btn)
        layout.addLayout(btn_row)

        # Trigger initial visibility
        self._on_model_changed(self.generation_model_dropdown.currentText())

    def _load_current_values(self):
        """Load current settings into the dialog."""
        self.api_key_input.setText(self._original_api_key)
        self.generation_model_dropdown.setCurrentText(self._original_model)

        int_val = max(0, min(100, int(round(self._original_aggressiveness * 100))))
        self.aggressiveness_slider.setValue(int_val)
        self.aggressiveness_value_label.setText(f"{self._original_aggressiveness:.2f}")

        # Show API status
        if self._original_api_key and self._original_api_key.startswith("sk-") and len(self._original_api_key) > 20:
            self.api_status_label.setText("API key saved")
            self.api_status_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.api_status_label.setText("")

    def _on_model_changed(self, model_name: str):
        cfg = get_model_config(model_name or "")
        self.agg_row_frame.setVisible(cfg.get("supports_temperature", True))

    def _on_agg_slider_changed(self, value: int):
        self.aggressiveness_value_label.setText(f"{value / 100.0:.2f}")

    def _reset_defaults(self):
        self.generation_model_dropdown.setCurrentText(DEFAULT_GENERATION_MODEL)
        self.aggressiveness_slider.setValue(int(DEFAULT_TEMPERATURE * 100))
        self.aggressiveness_value_label.setText(str(DEFAULT_TEMPERATURE))

    def _test_connection(self):
        """Test the OpenAI API connection."""
        api_key = self.api_key_input.text().strip()
        if not api_key:
            self.api_status_label.setText("Please enter an API key")
            self.api_status_label.setStyleSheet("color: red; font-weight: bold;")
            return

        self.api_status_label.setText("Testing connection...")
        self.api_status_label.setStyleSheet("color: #6B7280;")
        # Force UI update
        from PySide6.QtWidgets import QApplication

        QApplication.processEvents()

        try:
            from openai import OpenAI
            from openai._exceptions import AuthenticationError

            client = OpenAI(api_key=api_key)
            client.models.list()
            self.api_status_label.setText("Connected successfully")
            self.api_status_label.setStyleSheet("color: green; font-weight: bold;")
        except AuthenticationError:
            self.api_status_label.setText("Invalid API key")
            self.api_status_label.setStyleSheet("color: red; font-weight: bold;")
        except Exception as e:
            self.api_status_label.setText(str(e))
            self.api_status_label.setStyleSheet("color: red; font-weight: bold;")

    def _save_and_close(self):
        """Save all settings and close."""
        api_key = self.api_key_input.text().strip()
        model_name = self.generation_model_dropdown.currentText()
        aggressiveness = self.aggressiveness_slider.value() / 100.0

        # Validate model
        if model_name not in MODEL_CONFIG:
            QMessageBox.warning(
                self,
                "Invalid Model",
                f"The model '{model_name}' is not supported.\n\n"
                "Supported models:\n" + "\n".join(f"  - {n}" for n in MODEL_CONFIG.keys()),
            )
            return

        self.settings_manager.save_api_key(api_key)
        self.settings_manager.save_generation_model_name(model_name)
        self.settings_manager.save_aggressiveness(aggressiveness)

        self.accept()

    # --- Public accessors for the main window ---

    def get_api_key(self) -> str:
        return self.api_key_input.text().strip()

    def get_generation_model_name(self) -> str:
        return self.generation_model_dropdown.currentText()

    def get_aggressiveness(self) -> float:
        return self.aggressiveness_slider.value() / 100.0
