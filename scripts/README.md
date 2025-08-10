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

### `build_release.py`
Builds release packages for distribution.

### `fix_formatting.py`
Fixes code formatting issues across the project.

### `fix_imports.py`
Fixes import statement issues.

### `lint.py`
Runs linting checks on the codebase.

### `run_fixer_only.py`
Runs only the auto-fixer without other checks.

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
