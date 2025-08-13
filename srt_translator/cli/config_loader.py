#!/usr/bin/env python3
"""
CLI configuration loader for SRT Translator.
"""

import json
import os
from pathlib import Path

from dotenv import dotenv_values, find_dotenv

DEFAULT_LANGS = {
    "Spanish": "es",
    "French": "fr",
    "German": "de",
    "Chinese (Simplified)": "zh-Hans",
}


def collect_cli_raw() -> dict:
    """
    Collect raw configuration for CLI mode.

    Precedence:
      - API key:   OS env > .env > error
      - Others:    .env > defaults (OS env ignored)
    No environment mutation.
    """
    env_path = find_dotenv(usecwd=True)
    env_file = dotenv_values(env_path) if env_path else {}

    # API key: OS env wins
    api_key = (
        os.getenv("OPENAI_API_KEY")
        or os.getenv("OPEN_AI_KEY")  # optional legacy alias
        or env_file.get("OPENAI_API_KEY")
        or env_file.get("OPEN_AI_KEY")
    )

    if not api_key:
        raise ValueError("OPENAI_API_KEY is required (set via OS env or .env).")

    # Load termbase data directly from file
    termbase_data = {}
    termbase_path = env_file.get("TERMBASE_PATH", "termbase.json")

    if not os.path.isabs(termbase_path):
        # Find project root by looking for pyproject.toml or setup.py
        current_dir = Path.cwd()
        project_root = None

        # Walk up directories to find project root
        for parent in [current_dir] + list(current_dir.parents):
            if (parent / "pyproject.toml").exists() or (parent / "setup.py").exists():
                project_root = parent
                break

        if project_root:
            termbase_path = str(project_root / termbase_path)
        else:
            # Fallback to current directory if project root not found
            termbase_path = str(current_dir / termbase_path)

    # Load the actual termbase data
    if os.path.exists(termbase_path):
        try:
            with open(termbase_path, "r", encoding="utf-8") as f:
                termbase_data = json.load(f)
        except Exception as e:
            # Log warning but continue with empty termbase
            print(f"Warning: Failed to load termbase from {termbase_path}: {e}")
            termbase_data = {}
    else:
        print(f"Warning: Termbase file not found at {termbase_path}")

    return {
        "api_key": api_key,
        "openai_model": env_file.get("OPENAI_MODEL", "gpt-4o-mini"),
        "batch_size": env_file.get("BATCH_SIZE", "5"),
        "aggressiveness": env_file.get("AGGRESSIVENESS", "0.75"),
        "log_mode": env_file.get("LOG_MODE", "Standard"),
        "output_directory": env_file.get("OUTPUT_DIRECTORY", "translated_srt_files"),
        "input_directory": env_file.get(
            "INPUT_DIRECTORY", "original_captions"
        ),  # ← Add this
        "target_languages": env_file.get("TARGET_LANGUAGES", json.dumps(DEFAULT_LANGS)),
        "dnt_terms": env_file.get("DNT_TERMS", "[]"),
        "termbase": termbase_data,  # Actual data, not file path
    }
