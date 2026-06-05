# SRT Translator Scripts

This directory contains utility scripts for the SRT Translator project.

## Available Scripts

### `clear_ai_config.py`
Clears AI-generated configuration (DNT terms and termbase) from the GUI settings.

**Usage:**
```bash
python scripts/clear_ai_config.py
```

**What it does:**
- Removes AI-generated DNT terms and termbase from persistent storage
- Resets the current GUI state to empty defaults
- Useful when you want to start fresh with AI configuration

**When to use:**
- After testing different AI configurations
- When you want to regenerate AI settings from scratch
- To clear old/stale AI-generated data

### `factory_reset.ps1` / `factory_reset.sh`
Wipes **all** SRT Translator settings so the next launch behaves like a
brand-new user opening the app for the first time. Unlike the `clear_ai_*.py`
scripts, these require **no Python environment** (handy for testing a built
`.exe`/`.dmg`) and clear **both** QSettings backends — the current IniFormat
store and the legacy NativeFormat store (registry on Windows, plist on macOS,
`.conf` on Linux) that the app otherwise migrates settings back from.

**Usage:**
```powershell
# Windows
.\scripts\factory_reset.ps1            # prompts, backs up, then wipes
.\scripts\factory_reset.ps1 -Force     # non-interactive
```
```bash
# macOS / Linux
bash scripts/factory_reset.sh          # prompts, backs up, then wipes
bash scripts/factory_reset.sh --force  # non-interactive
```

**Warning:** this erases your OpenAI API key (stored in plaintext) along with
all other settings. No backup is taken by default; pass `-Backup` / `--backup`
if you want a reversible timestamped copy first (note: that copy also contains
the plaintext API key).

See [`docs/developer/testing-clean-state.md`](../docs/developer/testing-clean-state.md)
for when and why to use this.

### `build_release.py`
Builds release packages for distribution.

## Modern Code Quality Tools

The project now uses modern, industry-standard tools instead of custom scripts:

### **Code Formatting & Linting**
```bash
# Format all code
ruff format .

# Check and fix linting issues
ruff check . --fix

# Type checking
mypy srt_translator

# Security scanning
bandit -r srt_translator
safety check --full-report

# Run all quality checks
pre-commit run --all-files
```

### **What These Tools Do**
- **Ruff**: Fast Python linter and formatter (replaces Black, isort, flake8)
- **MyPy**: Static type checker
- **Bandit**: Security linting for Python code
- **Safety**: Dependency vulnerability scanning
- **Pre-commit**: Automatically runs all tools on commit

### `verify_security.py`
Verifies security aspects of the codebase.

## Running Scripts

All scripts should be run from the **project root directory** (not from within the scripts directory):

```bash
# ✅ Correct - run from project root
python scripts/clear_ai_config.py

# ❌ Incorrect - don't run from scripts directory
cd scripts
python clear_ai_config.py
```

## Adding New Scripts

When adding new scripts:
1. Place them in this directory
2. Ensure they handle imports correctly (use relative paths to project root)
3. Add documentation to this README
4. Test that they work from the project root directory
