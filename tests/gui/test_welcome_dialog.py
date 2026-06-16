"""Tests for the first-run API key onboarding dialog."""

from srt_translator.core.config.language_config import LanguageConfig
from srt_translator.gui.settings_manager import SettingsManager
from srt_translator.gui.ui.welcome_dialog import (
    WelcomeApiKeyDialog,
    looks_like_openai_key,
)

VALID_KEY = "sk-" + "x" * 40
VALID_PROJECT_KEY = "sk-proj-" + "y" * 40


def _settings_manager() -> SettingsManager:
    # The autouse _isolate_qsettings fixture redirects QSettings to a tmp path,
    # so this never touches the real user settings.
    return SettingsManager(LanguageConfig({"languages": {}}))


class TestLooksLikeOpenAIKey:
    def test_accepts_standard_key(self):
        assert looks_like_openai_key(VALID_KEY)

    def test_accepts_project_key(self):
        assert looks_like_openai_key(VALID_PROJECT_KEY)

    def test_rejects_empty_or_whitespace(self):
        assert not looks_like_openai_key("")
        assert not looks_like_openai_key("   ")
        assert not looks_like_openai_key(None)  # type: ignore[arg-type]

    def test_rejects_wrong_prefix(self):
        assert not looks_like_openai_key("pk-" + "x" * 40)

    def test_rejects_too_short(self):
        assert not looks_like_openai_key("sk-abc")


class TestWelcomeApiKeyDialog:
    def test_save_button_disabled_until_key_looks_valid(self, qapp):
        dlg = WelcomeApiKeyDialog(_settings_manager())
        assert not dlg.save_btn.isEnabled()

        dlg.api_key_input.setText("not-a-key")
        assert not dlg.save_btn.isEnabled()

        dlg.api_key_input.setText(VALID_KEY)
        assert dlg.save_btn.isEnabled()

    def test_save_persists_key(self, qapp):
        sm = _settings_manager()
        dlg = WelcomeApiKeyDialog(sm)
        dlg.api_key_input.setText(VALID_KEY)

        dlg._save_and_close()

        assert sm.load_api_key() == VALID_KEY
        assert dlg.result() == WelcomeApiKeyDialog.Accepted

    def test_save_rejects_malformed_key_without_persisting(self, qapp):
        sm = _settings_manager()
        dlg = WelcomeApiKeyDialog(sm)
        # Force a malformed value past the button gate and call save directly.
        dlg.api_key_input.setText("bogus")

        dlg._save_and_close()

        assert sm.load_api_key() == ""
        assert dlg.status_label.text()  # an error message is shown

    def test_skip_does_not_persist_key(self, qapp):
        sm = _settings_manager()
        dlg = WelcomeApiKeyDialog(sm)
        dlg.api_key_input.setText(VALID_KEY)

        dlg.reject()

        assert sm.load_api_key() == ""
