"""Build the wheel, install it to a temp directory, and verify critical
imports work outside editable mode.

This catches packaging regressions like the model_config.json bug
(commit 4504c71, 2026-03-11) where a resource file was added to
srt_translator/config/ but never to pyproject.toml's package-data list.
Editable installs hide such bugs because they read directly from the
source tree; only a built-and-installed wheel reproduces the production
failure mode.

Usage:
    python scripts/smoke_test_wheel.py

Exits non-zero on any import failure or missing resource. Designed to
run both locally (developer pre-push) and in CI.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Stale build caches that can mask package-data regressions. setuptools reads
# srt_translator.egg-info/SOURCES.txt when it exists and uses it as the source
# of truth instead of consulting pyproject.toml fresh — so a developer running
# this script in a tree with a cached SOURCES.txt would get a false pass.
# Clean these unconditionally before each build.
STALE_BUILD_PATHS: list[str] = [
    "srt_translator.egg-info",
    "build",
]

# Modules that must import successfully from a built wheel. Each entry was
# (or could be) silently broken by missing package-data. Add to this list
# whenever a new module joins the import-time resource-load club.
SMOKE_IMPORTS: list[str] = [
    "srt_translator",
    "srt_translator.config.model_config_loader",
    "srt_translator.config.resources",
    "srt_translator.cli.app",
]

# Resource files that must be present in the installed package. Same
# motivation: if package-data drifts, this list surfaces it before users do.
SMOKE_RESOURCES: list[str] = [
    "srt_translator/config/model_config.json",
    "srt_translator/config/languages.json",
    "srt_translator/config/translation_rubric.yaml",
]


def _run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
    """Run a command, raising with full stderr if it fails."""
    result = subprocess.run(cmd, capture_output=True, text=True, **kwargs)
    if result.returncode != 0:
        sys.stderr.write(
            f"Command failed (exit {result.returncode}): {' '.join(cmd)}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}\n"
        )
        sys.exit(result.returncode)
    return result


def _clean_stale_builds() -> None:
    cleaned: list[str] = []
    for rel in STALE_BUILD_PATHS:
        path = REPO_ROOT / rel
        if path.exists():
            shutil.rmtree(path)
            cleaned.append(rel)
    if cleaned:
        print(f"      removed stale build caches: {', '.join(cleaned)}")


def _build_wheel(out_dir: Path) -> Path:
    print(f"[1/4] Building wheel into {out_dir}...")
    _clean_stale_builds()
    _run([sys.executable, "-m", "build", "--wheel", "--outdir", str(out_dir)], cwd=REPO_ROOT)
    wheels = list(out_dir.glob("srt_translator-*.whl"))
    if not wheels:
        sys.stderr.write(f"No wheel produced in {out_dir}\n")
        sys.exit(1)
    if len(wheels) > 1:
        sys.stderr.write(f"Multiple wheels in {out_dir}: {wheels}\n")
        sys.exit(1)
    print(f"      built {wheels[0].name}")
    return wheels[0]


def _install_wheel(wheel: Path, target: Path) -> None:
    print(f"[2/4] Installing {wheel.name} to {target}...")
    _run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--no-deps",
            "--force-reinstall",
            "--quiet",
            "--target",
            str(target),
            str(wheel),
        ]
    )


def _check_resources(install_root: Path) -> None:
    print("[3/4] Checking required resource files are present...")
    missing: list[str] = []
    for rel in SMOKE_RESOURCES:
        if not (install_root / rel).is_file():
            missing.append(rel)
    if missing:
        sys.stderr.write(
            "Missing resource files in installed wheel:\n"
            + "\n".join(f"  - {m}" for m in missing)
            + "\n"
            + "Add the file's pattern to pyproject.toml package-data.\n"
        )
        sys.exit(1)
    for rel in SMOKE_RESOURCES:
        print(f"      present: {rel}")


def _check_imports(install_root: Path) -> None:
    print("[4/4] Verifying critical imports outside editable mode...")
    # Use a fresh subprocess so the parent's editable install does not
    # mask the wheel install. PYTHONPATH points at the install target;
    # we strip the current working directory's source tree to be safe.
    script = (
        "import importlib, sys\n"
        + "\n".join(f"importlib.import_module({mod!r})" for mod in SMOKE_IMPORTS)
        + "\nprint('OK', len(sys.modules))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        env={
            **_env_without_pythonpath(),
            "PYTHONPATH": str(install_root),
            # On Windows, an empty PATH can break some C-extension loads;
            # inherit minimal PATH from parent.
        },
        cwd=str(REPO_ROOT.parent),  # cwd off the source tree
    )
    if result.returncode != 0:
        sys.stderr.write(f"Smoke import failed:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}\n")
        sys.exit(result.returncode)
    for mod in SMOKE_IMPORTS:
        print(f"      imported: {mod}")


def _env_without_pythonpath() -> dict[str, str]:
    import os

    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    return env


def main() -> int:
    # Ensure 'build' is available; install it on demand rather than as a
    # hard dev dependency, since this script is the only consumer.
    try:
        import build  # noqa: F401
    except ImportError:
        print("Installing 'build' (required for wheel smoke test)...")
        _run([sys.executable, "-m", "pip", "install", "--quiet", "build"])

    with tempfile.TemporaryDirectory(prefix="srtx_smoke_") as tmp:
        tmp_dir = Path(tmp)
        dist_dir = tmp_dir / "dist"
        install_dir = tmp_dir / "install"
        dist_dir.mkdir()
        install_dir.mkdir()

        wheel = _build_wheel(dist_dir)
        _install_wheel(wheel, install_dir)
        _check_resources(install_dir)
        _check_imports(install_dir)

    print("\nAll smoke checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
