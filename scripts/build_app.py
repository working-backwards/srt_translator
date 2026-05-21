import os
import platform
from pathlib import Path

import PyInstaller.__main__

# ------------------------------
# Project root
# ------------------------------
ROOT = Path(__file__).resolve().parent.parent

# Entry point
ENTRY = ROOT / "srt_translator" / "gui" / "app.py"

if not ENTRY.exists():
    raise FileNotFoundError(f"Entry script not found: {ENTRY}")

# Config files
CONFIG_DIR = ROOT / "srt_translator" / "config"
LANG_FILE = CONFIG_DIR / "languages.json"
RUBRIC_FILE = CONFIG_DIR / "translation_rubric.yaml"

# Set environment variables
os.environ["LANGUAGE_CONFIG"] = str(LANG_FILE)
os.environ["TRANSLATION_RUBRIC"] = str(RUBRIC_FILE)

print(f"LANGUAGE_CONFIG={os.environ['LANGUAGE_CONFIG']}")
print(f"TRANSLATION_RUBRIC={os.environ['TRANSLATION_RUBRIC']}")

# ------------------------------
# Detect OS
# ------------------------------
OS_NAME = platform.system()
SEP = ";" if OS_NAME == "Windows" else ":"

# Bundle every JSON/YAML in srt_translator/config/ so new resource files
# (added by future commits) get packaged automatically. The original
# explicit list missed model_config.json when it was added in 2026-03 and
# silently shipped a broken settings dialog in built wheels.
CONFIG_RESOURCES = sorted(CONFIG_DIR.glob("*.json")) + sorted(CONFIG_DIR.glob("*.yaml"))
ADD_DATA_ARGS = [f"--add-data={f}{SEP}srt_translator/config" for f in CONFIG_RESOURCES]

print("Bundling config resources:")
for f in CONFIG_RESOURCES:
    print(f"  {f.name}")

# ------------------------------
# Build arguments
# ------------------------------
args = [
    "--clean",
    "--name=SRT-Translator",
    *ADD_DATA_ARGS,
]

if OS_NAME == "Darwin":
    # macOS → produce .app bundle
    args += [
        "--windowed",  # REQUIRED for .app bundle
        "--noconfirm",
    ]
else:
    # Windows → produce single .exe
    args += [
        "--onefile",
        "--windowed",  # REQUIRED for .app bundle
        "--noconfirm",
    ]

args.append(str(ENTRY))

# ------------------------------
# Run PyInstaller
# ------------------------------
PyInstaller.__main__.run(args)

print("\n✅ Build complete")
print("Output directory: dist/")
