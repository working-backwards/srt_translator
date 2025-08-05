# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['../run_gui.py'],
    pathex=['..'],
    binaries=[],
    datas=[
        ('../config/languages.json', 'config'),
    ],
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtWidgets', 
        'PySide6.QtGui',
        'openai',
        'srt',
        'tiktoken',
        'dotenv',
        'psutil',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude sensitive files and directories
        '.env',
        'termbase.json',
        'translation_logs',
        'original_captions',
        'translated_srt_files',
        'translation_prompt.txt',
        'translation_prompt.example',
        '__pycache__',
        '*.pyc',
        '*.pyo',
        '*.pyd',
        '.pytest_cache',
        '.coverage',
        'htmlcov',
        'venv',
        '.venv',
        'env',
        '.env.local',
        '.env.production',
        '.env.development',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SRT-Translator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
