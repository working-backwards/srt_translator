from __future__ import annotations

from pathlib import Path


def build_eval_html(json_path: Path, out_path: Path | None = None) -> Path:
    """Design-only placeholder.

    Intended behavior:
    - Read eval_report.json
    - Render deterministic HTML with inline CSS
    - Return path to eval_report.html
    - Raise on missing/invalid inputs/assets (no partial files)
    """
    raise NotImplementedError("HTML presenter not implemented in this scaffold.")
