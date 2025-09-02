# tests/test_fixer_srt_first_unit.py
from __future__ import annotations

import json
from pathlib import Path

from srt_translator.core.translator.fixer import SRTFixer
from tests._util import find_files, grep_dir, read_json_utf8, write_utf8


def _make_temp_batch(tmp_path: Path) -> Path:
    batch = tmp_path / "temp-batch-fixer-demo"
    # Minimal ai_config.json with dnt_terms indices 0..6
    ai = {
        "version": "1.0.0",
        "dnt_terms": [
            "API",
            "CEO",
            "Alice",
            "Operating Cadence",
            "Q3",
            "2024",
            "Acme Corp",
        ],
    }
    write_utf8(batch / "ai_config.json", json.dumps(ai, ensure_ascii=False, indent=2))

    # Create language subdirectories and place SRT files there
    # 1) Curly quote + comma after token (U+201D)
    write_utf8(
        batch / "es" / "Operating Plan Module 0.es.srt",
        f"1\n00:00:00,000 --> 00:00:02,000\nHola __DNT_TERM_2__{chr(0x201D)} bienvenidos.\n",
    )
    # 2) Zero-width space U+200B inside token + fullwidth right paren U+FF09
    write_utf8(
        batch / "de" / "Operating Plan Module 1.de.srt",
        f"1\n00:00:00,000 --> 00:00:02,000\n"
        f"Hallo __DNT{chr(0x200B)}TERM_6__{chr(0xFF09)} und willkommen.\n",
    )
    # 3) Out-of-range index → removal
    write_utf8(
        batch / "vi" / "Operating Plan Module 2.vi.srt",
        "1\n00:00:00,000 --> 00:00:02,000\nXin chào __DNT_TERM_42__!\n",
    )
    # 4) Fullwidth underscores + CJK period
    write_utf8(
        batch / "ja" / "Operating Plan Module 3.ja.srt",
        f"1\n00:00:00,000 --> 00:00:02,000\nこんにちは ＿＿DNT_TERM_6＿＿{chr(0x3002)}\n",
    )
    return batch


def test_fixer_srt_first_dry_run_then_apply(tmp_path: Path):
    batch = _make_temp_batch(tmp_path)
    dnt = read_json_utf8(batch / "ai_config.json")["dnt_terms"]

    # Dry-run: no .bak created, file contents unchanged
    fixer = SRTFixer(log_file=str(batch / "fixer_dry_run.log"), translations_dir=str(batch))
    fixer.scan_and_fix_placeholders(batch_dir=batch, dnt_terms=dnt, dry_run=True)
    assert find_files(batch, "*.srt.bak") == []
    # Placeholders still present before apply
    hits = grep_dir(batch, "__DNT_TERM_")
    assert len(hits) >= 2  # at least two straightforward "__DNT_TERM_" occurrences

    # Apply: backups created for changed files; placeholders gone; replacements/removals correct
    fixer = SRTFixer(log_file=str(batch / "fixer_apply.log"), translations_dir=str(batch))
    fixer.scan_and_fix_placeholders(batch_dir=batch, dnt_terms=dnt, dry_run=False)

    # Expect .bak backups for the 4 files
    baks = find_files(batch, "*.srt.bak")
    assert len(baks) == 4

    # No tokens remain
    hits_after = grep_dir(batch, "__DNT_TERM_")
    assert hits_after == []

    # Spot-check final contents
    es = (batch / "es" / "Operating Plan Module 0.es.srt").read_text(encoding="utf-8")
    assert f"Hola Alice{chr(0x201D)} bienvenidos." in es

    de = (batch / "de" / "Operating Plan Module 1.de.srt").read_text(encoding="utf-8")
    # Keep punctuation/paren; token replaced by mapped term
    assert "Hallo Acme Corp" in de and chr(0xFF09) in de  # U+FF09

    vi = (batch / "vi" / "Operating Plan Module 2.vi.srt").read_text(encoding="utf-8")
    # Token removed; ex: "Xin chào !" (allow extra space)
    assert "Xin chào" in vi and "__DNT_TERM_" not in vi

    ja = (batch / "ja" / "Operating Plan Module 3.ja.srt").read_text(encoding="utf-8")
    # Fullwidth underscores + CJK period preserved
    assert "Acme Corp" in ja and chr(0x3002) in ja  # CJK period
