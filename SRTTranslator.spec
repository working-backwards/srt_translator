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
    [],
    exclude_binaries=True,
    name='SRTTranslator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SRTTranslator',
)
app = BUNDLE(
    coll,
    name='SRTTranslator.app',
    icon=None,
    bundle_identifier=None,
)
