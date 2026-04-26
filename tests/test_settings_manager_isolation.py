"""Regression tests for SettingsManager test isolation.

Bug history (2026-04-26): SettingsManager constructed QSettings via
`QSettings("SRTTranslator", "SRTTranslator")`, which uses the platform
default format. On Windows that's NativeFormat (registry); on macOS, plist.
QSettings.setPath() only redirects IniFormat — meaning the autouse
isolation fixture in tests/conftest.py was a silent no-op on Windows and
macOS. Test runs clobbered the user's real AI-generated termbase and DNT
config in the registry.

Fix: SettingsManager now constructs QSettings with explicit IniFormat,
which setPath() can redirect uniformly across all platforms.

These tests assert the contract that makes the fix work. If they break,
production tests have started leaking into real user storage again.
"""

from pathlib import Path

from PySide6.QtCore import QSettings

from srt_translator.core.config.language_config import LanguageConfig
from srt_translator.gui.settings_manager import SettingsManager


def _sm() -> SettingsManager:
    return SettingsManager(LanguageConfig({"languages": {}}))


def test_settings_use_ini_format():
    """IniFormat is the only format setPath() can redirect — NativeFormat
    writes go to registry/plist regardless of any redirect attempt."""
    assert _sm().settings.format() == QSettings.IniFormat


def test_settings_file_lives_inside_pytest_tmp(tmp_path):
    """The conftest autouse fixture redirects IniFormat UserScope to
    tmp_path. If the redirect is working, every save lands inside tmp_path.

    A failing assertion here means either:
      - SettingsManager has reverted to NativeFormat (un-redirectable), or
      - The conftest fixture stopped running for some reason.
    Either way: real user data is at risk on the next test run."""
    sm = _sm()
    sm.save_ai_config(
        ["__sentinel_dnt__"],
        {"xx": {"__sentinel_term__": "__sentinel_value__"}},
    )
    # Qt returns POSIX-style paths even on Windows; tmp_path uses native
    # separators. Resolve both to a common form before comparing.
    file_path = Path(sm.settings.fileName()).resolve()
    tmp_resolved = tmp_path.resolve()
    assert tmp_resolved in file_path.parents, (
        f"SettingsManager wrote to {file_path}, which is outside the test "
        f"tmp_path {tmp_resolved}. This means tests are clobbering real "
        f"user config. Check that SettingsManager constructs QSettings with "
        f"explicit IniFormat and that tests/conftest.py is being loaded."
    )


def test_save_and_load_round_trip_in_isolation(tmp_path):
    """Smoke test: write+read works under the isolation fixture, and the
    read-back values match what was written (i.e. the redirect didn't drop
    writes silently)."""
    sm = _sm()
    dnt = ["sentinel_dnt"]
    tb = {"es": {"sentinel": "centinela"}}
    sm.save_ai_config(dnt, tb)

    loaded_dnt, loaded_tb, _ = sm.load_ai_config()
    assert loaded_dnt == dnt
    assert loaded_tb == tb


def test_migration_skipped_when_ini_already_has_data(tmp_path):
    """migrate_from_native_if_needed() is a one-shot: if Ini already has
    keys, it must not overwrite them with stale NativeFormat data."""
    sm = _sm()
    sm.save_ai_config(["existing"], {"es": {"existing": "existente"}})

    # Migration should no-op because Ini has keys.
    sm.migrate_from_native_if_needed()

    loaded_dnt, loaded_tb, _ = sm.load_ai_config()
    assert loaded_dnt == ["existing"]
    assert loaded_tb == {"es": {"existing": "existente"}}
