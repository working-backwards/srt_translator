import pytest

try:
    from PySide6.QtCore import QSettings
except ImportError:
    QSettings = None


@pytest.fixture(autouse=True)
def _isolate_qsettings(tmp_path):
    # SettingsManager uses QSettings("SRTTranslator", ...), which on Windows
    # writes to HKCU\Software\SRTTranslator and on macOS to ~/Library/Preferences.
    # Without this, any test that calls save_* clobbers the user's real app
    # settings. IniFormat + setPath redirects on every platform; XDG_CONFIG_HOME
    # alone is silently ignored on Windows/macOS.
    #
    # Guarded import: lighter CI jobs (Stage 0 prompt snapshots, golden SRT
    # tests) install without the [gui] extra. Tests that touch QSettings
    # already pull PySide6 in via [gui], so the no-op path can't reach them.
    if QSettings is None:
        yield
        return
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp_path))
    yield
