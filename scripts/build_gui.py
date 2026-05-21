#!/usr/bin/env python3
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC_WIN = ROOT / "build_specs" / "srt_translator_gui_win.spec"
SPEC_MAC = ROOT / "build_specs" / "srt_translator_gui_mac.spec"


def main() -> None:
    print("🚀 Building SRT Translator GUI Executable")
    osname = platform.system()
    print(f"Platform: {osname} {platform.machine()}")
    if osname == "Windows":
        spec = SPEC_WIN
    elif osname == "Darwin":
        spec = SPEC_MAC
    else:
        raise SystemExit("Unsupported OS for GUI build (Windows/macOS only).")
    if not spec.exists():
        raise SystemExit(f"Spec not found: {spec}")
    cmd = [sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm", str(spec)]
    print("🔨", " ".join(cmd))
    subprocess.run(cmd, check=True)
    print("✅ Build complete.")


if __name__ == "__main__":
    main()
