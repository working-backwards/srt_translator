#!/usr/bin/env python3
"""
CLI configuration loader for SRT Translator.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from dotenv import dotenv_values, find_dotenv

from srt_translator.config import load_language_catalog

DEFAULT_LANGS = {
    "Spanish": "es",
    "French": "fr",
    "German": "de",
    "Chinese (Simplified)": "zh-Hans",
}


def _load_language_policies(selected_codes: list[str]) -> dict[str, Any]:
    """Shared loader used by CLI paths; reads from packaged resources."""
    raw = load_language_catalog()
    if "languages" not in raw:
        raise RuntimeError("languages.json missing 'languages' key")
    # policy_defaults is recommended to avoid per-lang bloat
    defaults = raw.get("policy_defaults", {})
    langs = raw["languages"]
    # Validate required keys for selected targets
    missing = {}
    for code in selected_codes:
        entry = langs.get(code, {})
        need = []
        # policy knobs may come from defaults or overrides
        for k in (
            "target_batch_size",
            "max_batch_size",
            "allow_placeholder_apostrophe",
        ):
            if k not in entry and k not in defaults:
                need.append(k)
        # cps_cap must be defined per language (used by formatter)
        if "cps_cap" not in entry:
            need.append("cps_cap")
        if need:
            missing[code] = need
    if missing:
        raise RuntimeError(f"languages.json missing required keys: {missing}")
    return raw  # type: ignore[no-any-return]


def collect_cli_raw() -> dict[str, Any]:
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
    api_key: str | None = (
        os.getenv("OPENAI_API_KEY")
        or os.getenv("OPEN_AI_KEY")  # optional legacy alias
        or env_file.get("OPENAI_API_KEY")
        or env_file.get("OPEN_AI_KEY")
    )

    if not api_key:
        raise ValueError("OPENAI_API_KEY is required (set via OS env or .env).")

    # Load termbase data directly from file
    termbase_data: dict[str, Any] = {}
    termbase_path: str = env_file.get("TERMBASE_PATH") or "termbase.json"

    if not os.path.isabs(termbase_path):
        # Find project root by looking for pyproject.toml or setup.py
        current_dir = Path.cwd()
        project_root: Path | None = None

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
            with open(termbase_path, encoding="utf-8") as f:
                termbase_data = json.load(f)
        except Exception as e:
            # Log warning but continue with empty termbase
            print(f"Warning: Failed to load termbase from {termbase_path}: {e}")
            termbase_data = {}
    else:
        print(f"Warning: Termbase file not found at {termbase_path}")

    # Load per-language policy (batch size, apostrophe flag, cps cap)
    target_map: dict[str, str] = {}
    try:
        target_langs_str = env_file.get("TARGET_LANGUAGES") or json.dumps(DEFAULT_LANGS)
        target_map = json.loads(target_langs_str)
    except Exception as e:
        print(f"Warning: Failed to parse TARGET_LANGUAGES, using defaults: {e}")
        target_map = DEFAULT_LANGS

    language_policies: dict[str, Any] = {}
    try:
        language_policies = _load_language_policies(list(target_map.values()))
    except Exception as e:
        print(f"Warning: Failed to load language policies, using defaults: {e}")
        # Continue with empty policies - will use defaults

    return {
        "api_key": api_key,
        "openai_model": env_file.get("OPENAI_MODEL", "gpt-4o-mini"),
        # batch size now set per language during orchestration
        "aggressiveness": env_file.get("AGGRESSIVENESS", "0.75"),
        "log_mode": env_file.get("LOG_MODE", "Standard"),
        "output_directory": env_file.get("OUTPUT_DIRECTORY", "translated_srt_files"),
        "input_directory": env_file.get("INPUT_DIRECTORY", "original_captions"),
        "target_languages": target_map,
        "dnt_terms": env_file.get("DNT_TERMS", "[]"),
        "termbase": termbase_data,  # Actual data, not file path
        "language_policies": language_policies,
    }
