# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

ROOT = Path.cwd()
ENTRY = str(ROOT / "srt_translator" / "gui" / "app.py")

# Bundle data if present (adjust/remove if you don't use it)
DATAS = []
# NEW: collect from the package so dev/wheel/frozen all match
DATAS.extend(collect_data_files("srt_translator.config", includes=["*.json", "*.yaml"]))

# Bring in dynamic packages defensively
HIDDEN_IMPORTS = []
for pkg in ("srt_translator.core", "srt_translator.gui"):
    try:
        HIDDEN_IMPORTS += collect_submodules(pkg)
    except Exception:
        pass

block_cipher = None

a = Analysis(
    [ENTRY],
    pathex=[str(ROOT)],
    binaries=[],
    datas=DATAS,
    hiddenimports=HIDDEN_IMPORTS,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name="SRT_Translator",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,   # GUI app
)

# Platform-specific packaging
import sys
is_win = sys.platform.startswith("win")
is_macos = sys.platform == "darwin"

if is_macos:
    app = BUNDLE(
        exe,
        name="SRT Translator.app",
        icon=str(ROOT / "srt_translator" / "gui" / "assets" / "app.icns") if (ROOT / "srt_translator" / "gui" / "assets" / "app.icns").exists() else None,
        info_plist={
            "CFBundleName": "SRT Translator",
            "NSHighResolutionCapable": "True",
            "LSApplicationCategoryType": "public.app-category.productivity",
        },
    )
    coll = COLLECT(app, a.binaries, a.zipfiles, a.datas, name="SRT-Translator")
else:
    # Windows onefile (and Linux if you build it): DO NOT define COLLECT.
    # Leaving the spec ending with `exe` produces a single-file executable in dist/.
    pass
