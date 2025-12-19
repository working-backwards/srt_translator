import os
import platform
import PyInstaller.__main__
from pathlib import Path

# ------------------------------
# Project root
# ------------------------------
ROOT = Path(__file__).resolve().parent

# Entry point
ENTRY = ROOT / "srt_translator" / "gui" / "app.py"

if not ENTRY.exists():
    raise FileNotFoundError(f"Entry script not found: {ENTRY}")

# Config files
LANG_FILE = ROOT / "srt_translator" / "config" / "languages.json"
RUBRIC_FILE = ROOT / "srt_translator" / "config" / "translation_rubric.yaml"

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

ADD_DATA_1 = f"{LANG_FILE}{SEP}srt_translator/config"
ADD_DATA_2 = f"{RUBRIC_FILE}{SEP}srt_translator/config"

# ------------------------------
# Build arguments
# ------------------------------
args = [
    "--clean",
    "--name=SRTTranslator",
    f"--add-data={ADD_DATA_1}",
    f"--add-data={ADD_DATA_2}",
]

if OS_NAME == "Darwin":
    # macOS → produce .app bundle
    args += [
        "--windowed",          # REQUIRED for .app bundle
        "--noconfirm",
    ]
else:
    # Windows → produce single .exe
    args += [
        "--onefile",
        "--windowed",
        "--noconfirm",
    ]

args.append(str(ENTRY))

# ------------------------------
# Run PyInstaller
# ------------------------------
PyInstaller.__main__.run(args)

print("\n✅ Build complete")
print("Output directory: dist/")