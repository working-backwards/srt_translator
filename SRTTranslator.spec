# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['/Users/user/PycharmProjects/srt_translator/srt_translator/gui/app.py'],
    pathex=[],
    binaries=[],
    datas=[('/Users/user/PycharmProjects/srt_translator/srt_translator/config/languages.json', 'srt_translator/config'), ('/Users/user/PycharmProjects/srt_translator/srt_translator/config/translation_rubric.yaml', 'srt_translator/config')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SRTTranslator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
