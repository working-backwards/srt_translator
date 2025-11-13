# -*- mode: python ; coding: utf-8 -*-
import os

project_root = os.getcwd()
config_dir = os.path.join(project_root, 'srt_translator', 'config')

# Collect all config files dynamically
datas = []
for root, _, files in os.walk(config_dir):
    for f in files:
        filepath = os.path.join(root, f)
        rel_path = os.path.relpath(root, project_root)
        target_path = rel_path.replace("\\", "/")
        datas.append((filepath, target_path))

block_cipher = None

a = Analysis(
    ['srt_translator/gui/app.py'],
    pathex=[project_root],
    binaries=[],            # No extra binaries
    datas=datas,            # include configs
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
    a.binaries,            # include binaries here
    a.zipfiles,
    a.datas,
    name='SRTTranslator',
    debug=False,
    strip=False,
    upx=True,
    console=False,          # GUI only
)

