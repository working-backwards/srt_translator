from __future__ import annotations

import json
from functools import lru_cache
from importlib.resources import as_file, files
from typing import Any

import yaml

# All resource access for the app goes through this module.
# Works identically in dev, wheels, Windows onefile EXE, and macOS .app.

_PKG = "srt_translator.config"
_LANGS = "languages.json"
_RUBRIC = "translation_rubric.yaml"


def _read_text(fname: str) -> str:
    with as_file(files(_PKG) / fname) as p:
        return p.read_text(encoding="utf-8")


@lru_cache
def load_language_catalog() -> dict[str, Any]:
    """Parsed languages.json (read-only)."""
    return json.loads(_read_text(_LANGS))


@lru_cache
def load_evaluation_rubric() -> dict[str, Any]:
    """Parsed translation_rubric.yaml (read-only)."""
    return yaml.safe_load(_read_text(_RUBRIC))


def sanity_check() -> None:
    """Fail fast if essentials are missing/malformed."""
    langs = load_language_catalog()
    if not isinstance(langs, dict) or not langs:
        raise RuntimeError("languages.json missing/empty")
    if "languages" not in langs or not isinstance(langs["languages"], dict):
        raise RuntimeError("languages.json missing 'languages' key")
    if not all(isinstance(v, dict) and "name" in v for v in langs["languages"].values()):
        raise RuntimeError("languages.json: each language requires a 'name'")
    rb = load_evaluation_rubric()
    if not isinstance(rb, dict) or "caps" not in rb:
        raise RuntimeError("translation_rubric.yaml missing 'caps'")
