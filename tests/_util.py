# tests/_util.py
from __future__ import annotations

import json
from pathlib import Path


def write_utf8(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.replace("\r\n", "\n"), encoding="utf-8")


def read_json_utf8(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def grep_dir(root: Path, pattern: str, exts: tuple[str, ...] = (".srt",)) -> list[tuple[Path, int, str]]:
    out: list[tuple[Path, int, str]] = []
    for ext in exts:
        for p in root.rglob(f"*{ext}"):
            for i, line in enumerate(p.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                if pattern in line:
                    out.append((p, i, line))
    return out


def find_files(root: Path, glob: str) -> list[Path]:
    return list(root.rglob(glob))
