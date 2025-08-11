# srt_core/config/resource_loader.py
from __future__ import annotations
import json
import os
from importlib import resources

REPO_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "config",
    "languages.json",
)


def load_languages():
    """
    Try to read languages.json as a package resource (frozen/installed).
    Fall back to repo path for 'clone & run'.
    """
    # 1) Package resource (works in PyInstaller if you add-data into package path)
    try:
        # Python 3.9+: resources.files
        data = (
            resources.files("srt_core.config")
            .joinpath("languages.json")
            .read_text(encoding="utf-8")
        )
        return json.loads(data)
    except Exception:
        pass

    # 2) Repo path for dev (clone & run)
    with open(REPO_PATH, "r", encoding="utf-8") as f:
        return json.load(f)
