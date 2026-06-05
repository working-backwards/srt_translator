#!/usr/bin/env python3
"""First-run onboarding dialog that prompts for the OpenAI API key.

SRT Translator cannot do anything without an OpenAI API key, so on first launch
(when no key is stored yet) we guide the user to enter one instead of letting
them discover the requirement via a downstream "No API Key" error. This is a
focused "welcome / set up" modal; ongoing key edits still happen in
SettingsDialog (the title-bar gear button).
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

OPENAI_API_KEYS_URL = "https://platform.openai.com/api-keys"


def looks_like_openai_key(key: str) -> bool:
    """Best-effort format check for an OpenAI API key.

    Matches the lenient check used by SettingsDialog: a non-empty value that
    starts with the OpenAI ``sk-`` prefix (covers ``sk-proj-`` project keys too)
    and is long enough to be plausible. This is a format gate only — a live
    check is available via "Test Connection".
    """
    key = (key or "").strip()
    return key.startswith("sk-") and len(key) > 20


class WelcomeApiKeyDialog(QDialog):
    """Focused first-run modal that collects the OpenAI API key."""

    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Welcome to SRT Translator")
        self.setModal(True)
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(28, 28, 28, 28)

        # Heading
        heading = QLabel("Welcome to SRT Translator")
        heading.setObjectName("subHeaderLabel")
        heading.setStyleSheet("font-size: 18px; font-weight: 700; color: #1E293B;")
        layout.addWidget(heading)

        # Rationale — explain *why* before asking for a secret.
        intro = QLabel(
            "SRT Translator uses OpenAI to translate your subtitles, so it needs "
            "your OpenAI API key to get started. Paste it below — you only have "
            "to do this once."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet("color: #374151; font-size: 13px;")
        layout.addWidget(intro)

        # "Where do I get one?" — the most common first-run friction.
        link = QLabel(f'<a href="{OPENAI_API_KEYS_URL}">Get an API key ↗</a>')
        link.setOpenExternalLinks(True)
        link.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        link.setStyleSheet("font-size: 13px;")
        layout.addWidget(link)

        # API key input + live test
        api_row = QHBoxLayout()
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setPlaceholderText("Enter your OpenAI API key (sk-...)")
        self.api_key_input.setObjectName("apiKeyInput")
        self.api_key_input.textChanged.connect(self._on_key_changed)

        self.test_btn = QPushButton("Test Connection")
        self.test_btn.setObjectName("secondaryButton")
        self.test_btn.clicked.connect(self._test_connection)

        api_row.addWidget(self.api_key_input)
        api_row.addWidget(self.test_btn)
        layout.addLayout(api_row)

        # Storage disclosure — mirror SettingsDialog wording so the
        # local-plaintext characteristic is visible at the moment of entry.
        storage_note = QLabel(
            "Stored locally in app settings (not encrypted). Rotate the key at "
            "platform.openai.com if exposed."
        )
        storage_note.setObjectName("storageDisclosureLabel")
        storage_note.setStyleSheet("color: #64748B; font-size: 11px;")
        storage_note.setWordWrap(True)
        layout.addWidget(storage_note)

        # Inline status (validation / connection test result)
        self.status_label = QLabel("")
        self.status_label.setObjectName("statusLabel")
        layout.addWidget(self.status_label)

        layout.addStretch()

        # Buttons. "Skip for now" lets a user without a key on hand continue
        # into the app rather than being trapped; the downstream generate /
        # translate guards (and the gear button) still apply.
        btn_row = QHBoxLayout()
        self.skip_btn = QPushButton("Skip for now")
        self.skip_btn.setObjectName("secondaryButton")
        self.skip_btn.setToolTip(
            "Continue without a key. You won't be able to generate settings or "
            "translate until you add one via the gear icon (top right)."
        )
        self.skip_btn.clicked.connect(self.reject)

        self.save_btn = QPushButton("Save & Continue")
        self.save_btn.setObjectName("primaryButton")
        self.save_btn.setDefault(True)
        self.save_btn.setEnabled(False)  # enabled once the key looks valid
        self.save_btn.clicked.connect(self._save_and_close)

        btn_row.addWidget(self.skip_btn)
        btn_row.addStretch()
        btn_row.addWidget(self.save_btn)
        layout.addLayout(btn_row)

    # ------------------------------------------------------------------ #

    def _on_key_changed(self, text: str):
        """Gate the primary button on a plausible key; clear stale status."""
        self.save_btn.setEnabled(looks_like_openai_key(text))
        if self.status_label.text():
            self._set_status("")

    def _test_connection(self):
        """Live-validate the key against OpenAI (same check as SettingsDialog)."""
        api_key = self.api_key_input.text().strip()
        if not api_key:
            self._set_status("Please enter an API key", error=True)
            return

        self._set_status("Testing connection...", muted=True)
        from PySide6.QtWidgets import QApplication

        QApplication.processEvents()

        try:
            from openai import OpenAI
            from openai._exceptions import AuthenticationError

            client = OpenAI(api_key=api_key)
            client.models.list()
            self._set_status("Connected successfully")
        except AuthenticationError:
            self._set_status("Invalid API key", error=True)
        except Exception as e:  # network or other transient failure
            self._set_status(str(e), error=True)

    def _set_status(self, text: str, *, error: bool = False, muted: bool = False):
        self.status_label.setText(text)
        if not text:
            self.status_label.setStyleSheet("")
        elif muted:
            self.status_label.setStyleSheet("color: #6B7280;")
        elif error:
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
        else:
            self.status_label.setStyleSheet("color: green; font-weight: bold;")

    def _save_and_close(self):
        api_key = self.api_key_input.text().strip()
        if not looks_like_openai_key(api_key):
            self._set_status(
                "That doesn't look like an OpenAI key (it should start with 'sk-').",
                error=True,
            )
            return
        self.settings_manager.save_api_key(api_key)
        self.accept()
