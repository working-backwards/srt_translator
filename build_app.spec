# -*- mode: python ; coding: utf-8 -*-
import os
import glob

# -----------------------------
# Project paths (cross-platform)
# -----------------------------
project_root = os.getcwd()  # Use current working directory
config_dir = os.path.join(project_root, 'srt_translator', 'config')

# -----------------------------
# Dynamically collect all files in config folder (recursively)
# -----------------------------
datas = []

for root, _, files in os.walk(config_dir):
    for f in files:
        filepath = os.path.join(root, f)
        # Compute relative path inside the package
        rel_path = os.path.relpath(root, project_root)
        target_path = rel_path.replace("\\", "/")  # Normalize for cross-platform
        datas.append((filepath, target_path))

# -----------------------------
# PyInstaller spec setup
# -----------------------------
block_cipher = None

a = Analysis(
    ['srt_translator/gui/app.py'],
    pathex=[project_root],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SRTTranslator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # set False if GUI only
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='SRTTranslator'
)
