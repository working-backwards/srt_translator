# Windows GUI — one-file EXE
# Build via: pyinstaller build_specs/srt_translator_gui_win.spec
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

datas = []
# Bundle internal config (no external files for creators)
datas += collect_data_files("srt_translator.config", includes=["*.json", "*.yaml"])
# Bundle HTML presenter assets (for eval_report.html styling)
datas += collect_data_files("srt_translator.presenters.eval_html.assets", includes=["*.css"])

a = Analysis(
    ['../srt_translator/gui/app.py'],   # path from build_specs/ → project root
    pathex=['..'],                      # search the project root for imports
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
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
    name='SRT-Translator',
    console=False,
    icon='icon.ico',                    # icon lives in build_specs/
)
# NOTE: No COLLECT == one-file EXE.
