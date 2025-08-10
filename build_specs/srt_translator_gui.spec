# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

ROOT = Path.cwd()
ENTRY = str(ROOT / "run_gui.py")

# Bundle data if present (adjust/remove if you don't use it)
DATAS = []
lang_json = ROOT / "config" / "languages.json"
if lang_json.exists():
    # put inside runtime temp under srt_core/config
    DATAS.append((str(lang_json), "srt_core/config"))

# Bring in dynamic packages defensively
HIDDEN_IMPORTS = []
for pkg in ("srt_core", "gui"):
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

# Keep COLLECT: it lets PyInstaller put outputs into dist/
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    name="SRT_Translator",
    # You can hardcode dist/work paths here if you prefer, but I recommend CLI:
    # distpath="build_specs/dist/windows",
    # workpath="build_specs/build/windows",
)
