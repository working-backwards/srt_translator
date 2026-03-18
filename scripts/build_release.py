#!/usr/bin/env python3
"""
GUI-only release packager for SRT Translator.

What it does:
  * Never references .env or CLI artifacts.
  * Windows: copies one-file EXE from dist/, optionally zips it.
  * macOS: creates a drag-to-Applications DMG from the .app bundle.
  * Version is read from pyproject.toml.
  * Outputs go to release/.

Usage (from repo root):
  python scripts/build_release.py            # package for the current OS
  python scripts/build_release.py --rebuild  # rebuild via build_gui.py if needed
  python scripts/build_release.py --zip-win  # (Windows) also produce a zip containing the EXE
"""

from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
from pathlib import Path

# ----------------------------
# Constants & Paths
# ----------------------------
REPO_ROOT = Path(__file__).resolve().parents[1]
DIST = REPO_ROOT / "dist"
RELEASE = REPO_ROOT / "release"
BUILD_GUI = REPO_ROOT / "scripts" / "build_gui.py"
PYPROJECT = REPO_ROOT / "pyproject.toml"

# GUI artifact names produced by your PyInstaller spec
WIN_EXE = DIST / "SRT-Translator.exe"
MAC_APP = DIST / "SRT-Translator.app"


# ----------------------------
# Utilities
# ----------------------------
def log(msg: str) -> None:
    print(msg, flush=True)


def run(cmd: list[str] | tuple[str, ...]) -> None:
    """Run a command, raising on failure, echoing output on error."""
    log(f"$ {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        raise SystemExit(f"Command failed ({e.returncode}): {' '.join(cmd)}") from e


def read_version() -> str:
    """Return project version from pyproject.toml."""
    if not PYPROJECT.exists():
        raise SystemExit("pyproject.toml not found.")
    try:
        # Python 3.11+: tomllib in stdlib
        import tomllib  # type: ignore[attr-defined]
    except ModuleNotFoundError:
        # Fallback if someone runs with <3.11 locally
        try:
            import tomli as tomllib  # type: ignore[no-redef]
        except ModuleNotFoundError as exc:
            raise SystemExit("tomllib/tomli not available; use Python 3.11+ or `pip install tomli`.") from exc

    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    # PEP 621: [project] version
    version = data.get("project", {}).get("version")
    if not version:
        # Some teams store version in tool.poetry or similar – add more lookups if needed
        raise SystemExit("Version not found in [project].version of pyproject.toml.")
    return version


def ensure_gui_built() -> None:
    """Ensure the GUI artifact exists; rebuild if needed."""
    system = platform.system()
    if system == "Windows":
        need = WIN_EXE
    elif system == "Darwin":
        need = MAC_APP
    else:
        raise SystemExit(f"Unsupported OS: {system}")

    if need.exists():
        log(f"✅ Found existing GUI artifact: {need}")
        return

    log("🛠  GUI artifact missing; invoking scripts/build_gui.py ...")
    if not BUILD_GUI.exists():
        raise SystemExit("scripts/build_gui.py not found.")
    run([sys.executable, str(BUILD_GUI)])
    if not need.exists():
        raise SystemExit(f"Expected GUI artifact not found after build: {need}")
    log(f"✅ Built: {need}")


def copy_common_docs(dst_dir: Path) -> None:
    """
    Copy lightweight docs into the release folder (no .env, no CLI).
    """
    dst_dir.mkdir(parents=True, exist_ok=True)
    # Keep it minimal and GUI-focused
    for name in ("README.md", "LICENSE", "NOTICE.md"):
        src = REPO_ROOT / name
        if src.exists():
            shutil.copy2(src, dst_dir / src.name)


def write_quickstart(dst_dir: Path, version: str) -> None:
    """
    Write a tiny quickstart guide into the release folder.
    Keeps guidance GUI-only; no .env references.
    """
    txt = f"""SRT Translator {version} — Quick Start
========================================

Windows:
  1) Run SRT-Translator.exe

macOS:
  1) Open the DMG, drag "SRT Translator.app" into Applications
  2) Launch the app (signed and notarized for Gatekeeper compatibility)

Notes:
  • This GUI build has no external config; required resources are bundled.
  • See README.md for details and troubleshooting.
"""
    (dst_dir / "QUICKSTART.txt").write_text(txt, encoding="utf-8")


# ----------------------------
# Windows packaging
# ----------------------------
def package_windows(version: str, zip_win: bool) -> list[Path]:
    """
    Copy the one-file EXE into release/, optionally zip it alongside docs.
    Returns the list of created artifacts.
    """
    artifacts: list[Path] = []
    RELEASE.mkdir(parents=True, exist_ok=True)

    exe_out = RELEASE / f"SRT-Translator-{version}-win.exe"
    log(f"📦 Copying EXE → {exe_out.name}")
    shutil.copy2(WIN_EXE, exe_out)
    artifacts.append(exe_out)

    # Drop a small set of docs next to it
    copy_common_docs(RELEASE)
    write_quickstart(RELEASE, version)

    if zip_win:
        zip_path = RELEASE / f"SRT-Translator-{version}-win.zip"
        log(f"🗜  Zipping EXE + docs → {zip_path.name}")
        # Build a temp staging folder to control the zip content names
        stage = RELEASE / f"SRT-Translator-{version}-win"
        if stage.exists():
            shutil.rmtree(stage)
        stage.mkdir(parents=True)
        shutil.copy2(exe_out, stage / exe_out.name.replace(f"-{version}-win", ""))  # name as SRT-Translator.exe
        for name in ("README.md", "LICENSE", "NOTICE.md", "QUICKSTART.txt"):
            p = RELEASE / name
            if p.exists():
                shutil.copy2(p, stage / p.name)
        shutil.make_archive(str(zip_path.with_suffix("")), "zip", root_dir=RELEASE, base_dir=stage.name)
        shutil.rmtree(stage, ignore_errors=True)
        artifacts.append(zip_path)

    log("✅ Windows packaging complete.")
    return artifacts


# ----------------------------
# macOS packaging (DMG)
# ----------------------------
def make_applications_symlink(dmgroot: Path) -> None:
    # Use 'ln -s' via shell for portability of the symlink target.
    apps_link = dmgroot / "Applications"
    if apps_link.exists():
        try:
            if apps_link.is_symlink() or apps_link.is_file():
                apps_link.unlink()
            elif apps_link.is_dir():
                shutil.rmtree(apps_link)
        except (OSError, PermissionError):
            pass
    run(["ln", "-s", "/Applications", str(apps_link)])


def package_macos(version: str) -> list[Path]:
    """
    Create a read-only DMG with the .app and an Applications symlink.
    Returns the list of created artifacts (the DMG).
    """
    artifacts: list[Path] = []
    RELEASE.mkdir(parents=True, exist_ok=True)

    # Stage a minimal DMG root
    dmgroot = RELEASE / f"SRT-Translator-{version}-mac-dmgroot"
    if dmgroot.exists():
        shutil.rmtree(dmgroot)
    dmgroot.mkdir(parents=True)

    # Copy the .app into the dmg root
    app_dst = dmgroot / "SRT Translator.app"
    log("📦 Copying .app into DMG root …")
    if app_dst.exists():
        shutil.rmtree(app_dst)
    shutil.copytree(MAC_APP, app_dst, symlinks=True)

    # Add docs inside the DMG root (optional, light)
    copy_common_docs(dmgroot)
    write_quickstart(dmgroot, version)
    make_applications_symlink(dmgroot)

    # Build the DMG
    dmg_out = RELEASE / f"SRT-Translator-{version}-mac.dmg"
    if dmg_out.exists():
        dmg_out.unlink()
    log(f"💿 Creating DMG → {dmg_out.name}")
    run(
        [
            "hdiutil",
            "create",
            "-volname",
            "SRT Translator",
            "-srcfolder",
            str(dmgroot),
            "-ov",
            "-format",
            "UDZO",
            str(dmg_out),
        ]
    )

    # Cleanup staging
    shutil.rmtree(dmgroot, ignore_errors=True)
    artifacts.append(dmg_out)
    log("✅ macOS packaging complete.")
    return artifacts


# ----------------------------
# Main
# ----------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="Package GUI-only release artifacts (no CLI, no .env).")
    parser.add_argument(
        "--rebuild", action="store_true", help="Invoke scripts/build_gui.py if GUI artifacts are missing."
    )
    parser.add_argument(
        "--zip-win", action="store_true", help="On Windows, also produce a .zip containing the EXE + docs."
    )
    args = parser.parse_args()

    version = read_version()
    system = platform.system()
    log(f"📦 SRT Translator packaging | Version: {version} | OS: {system}")

    if args.rebuild:
        # Force a rebuild by removing existing artifacts first
        if DIST.exists():
            log("🧹 Removing dist/ for a clean rebuild …")
            shutil.rmtree(DIST)
        if (REPO_ROOT / "build").exists():
            shutil.rmtree(REPO_ROOT / "build")

    ensure_gui_built()

    if system == "Windows":
        created = package_windows(version, zip_win=args.zip_win)
    elif system == "Darwin":
        created = package_macos(version)
    else:
        raise SystemExit("Unsupported OS for packaging. Use Windows or macOS.")

    # Print a tiny summary
    log("\nArtifacts:")
    for p in created:
        try:
            size_mb = p.stat().st_size / (1024 * 1024)
            log(f"  • {p.relative_to(REPO_ROOT)}  ({size_mb:.1f} MB)")
        except FileNotFoundError:
            log(f"  • {p.relative_to(REPO_ROOT)}")

    log(
        "\nDone. Upload these from GitHub Releases if you're packaging locally.\n"
        "CI users: prefer the tag-driven release workflow that builds on Windows/macOS runners."
    )


if __name__ == "__main__":
    main()
