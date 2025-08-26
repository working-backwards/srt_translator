# srt_translator/eval/tools.py
"""
Evaluation utilities for translated SRT files.

This module provides the core evaluation logic for individual (source, target) SRT pairs.
It writes per-language artifacts and generates per-pair summary reports.

Key Features:
- SRT parsing and timing analysis
- CPS (characters per second) calculation with configurable thresholds
- DNT and termbase coverage analysis
- Untranslated content detection
- Source language fragment identification
- Number integrity validation
- Comprehensive CSV and Markdown output

No logging here; callers (runner) handle logs via injected logger.
"""

from __future__ import annotations
import re
import json
import math
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional


@dataclass
class Cue:
    """Represents a single subtitle cue with timing and text."""

    index: int
    start_ms: int
    end_ms: int
    text: str


def _parse_time(t: str) -> int:
    """Parse SRT time format (HH:MM:SS,mmm) to milliseconds."""
    hh, mm, rest = t.split(":")
    ss, ms = rest.split(",")
    return (int(hh) * 3600 + int(mm) * 60 + int(ss)) * 1000 + int(ms)


def parse_srt(path: Path) -> List[Cue]:
    """
    Parse an SRT file into a list of Cue objects.

    Handles various SRT formatting quirks and normalizes line endings.
    Returns cues in order with proper timing information.
    """
    text = (
        path.read_text(encoding="utf-8", errors="ignore")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
    )
    blocks = re.split(r"\n\s*\n", text)
    cues: List[Cue] = []
    expected_idx = 1

    for b in blocks:
        b = b.strip()
        if not b:
            continue

        lines = b.split("\n")
        ti = 0

        # Handle optional subtitle index
        if "-->" not in lines[0]:
            try:
                idx = int(lines[0].strip())
                ti = 1
            except Exception:
                idx = expected_idx
        else:
            idx = expected_idx

        expected_idx += 1

        if ti >= len(lines) or "-->" not in lines[ti]:
            continue

        # Parse timing information
        m = re.match(
            r"\s*(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})", lines[ti]
        )
        if not m:
            continue

        start_ms = _parse_time(m.group(1))
        end_ms = _parse_time(m.group(2))
        txt = "\n".join(lines[ti + 1 :]).strip()

        cues.append(Cue(index=idx, start_ms=start_ms, end_ms=end_ms, text=txt))

    return cues


def cps_for_cue(c: Cue) -> float:
    """Calculate characters per second for a single cue."""
    dur_s = max(0.001, (c.end_ms - c.start_ms) / 1000.0)
    return len(c.text.replace("\n", "")) / dur_s


def percentile(values: List[float], p: float) -> float:
    """Calculate the p-th percentile of a list of values."""
    if not values:
        return 0.0
    v = sorted(values)
    k = (len(v) - 1) * p
    f = int(k)
    c = f if f == k else f + 1

    if f == c:
        return v[f]
    return v[f] * (c - k) + v[c] * (k - f)


def numbers_ok(src: str, tgt: str) -> bool:
    """Check if all numbers from source appear in target."""
    nums = re.findall(r"\d+", src or "")
    return all(re.search(re.escape(n), tgt or "") for n in nums)


def _nfkc_lower(s: str) -> str:
    """Normalize text to NFKC form and convert to lowercase."""
    import unicodedata
    import re as _re

    return _re.sub(r"\s+", " ", unicodedata.normalize("NFKC", s or "")).strip().lower()


def strip_terms(text: str, terms: List[str]) -> str:
    """Remove specified terms from text (case-insensitive)."""
    out = text or ""
    for t in terms or []:
        if t:
            out = re.sub(re.escape(t), "", out, flags=re.IGNORECASE)
    return out


def is_untranslated_after_dnt(src: str, tgt: str, dnt_terms: List[str]) -> bool:
    """Check if text is untranslated after removing DNT terms."""
    a = _nfkc_lower(strip_terms(src, dnt_terms))
    b = _nfkc_lower(strip_terms(tgt, dnt_terms))
    return (a != "") and (a == b)


def _occurrences(cues: List[Cue], term: str) -> List[int]:
    """Find all cue indices where a term appears."""
    norm = _nfkc_lower(term)
    # Tolerate space<->hyphen for Latin keys
    base = re.escape(norm).replace(r"\ ", r"[ \-]?")
    poss = r"(?:'s|'s|s')?"
    pat = re.compile(rf"(?<!\w){base}{poss}(?!\w)", re.IGNORECASE)

    hits = []
    for c in cues:
        if pat.search(_nfkc_lower(c.text)):
            hits.append(c.index)
    return hits


def _localized_hits(cues: List[Cue], localized: str) -> List[int]:
    """Find all cue indices where localized term appears."""
    pat = re.compile(re.escape(localized))
    return [c.index for c in cues if pat.search(c.text)]


def load_dnt(path: Optional[Path]) -> List[str]:
    """Load DNT terms from JSON file."""
    if not path or not path.exists():
        return []

    data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))

    if isinstance(data, dict) and "filtered_for_translation" in data:
        return list(data["filtered_for_translation"].get("terms", []))
    if isinstance(data, dict) and "terms" in data:
        return list(data["terms"])

    return []


def load_tb(path: Optional[Path], lang: str) -> Dict[str, str]:
    """Load termbase mappings from JSON file."""
    if not path or not path.exists():
        return {}

    data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))

    if isinstance(data, dict) and "filtered_for_translation" in data:
        langs = data["filtered_for_translation"].get("languages", {})
        return dict(langs.get(lang, langs.get(lang.split("-")[0], {})))
    if isinstance(data, dict):
        return dict(data.get(lang, data.get(lang.split("-")[0], {})))

    return {}


def evaluate_pair(
    en_path: Path,
    tgt_path: Path,
    dnt_path: Optional[Path],
    tb_path: Optional[Path],
    lang: str,
    batch_label: str,
    out_dir: Path,
    cps_soft_hard: Optional[Tuple[int, int]] = None,
) -> Dict[str, Any]:
    """
    Evaluate one (source, target) pair and write artifacts into out_dir.

    Args:
        en_path: Path to source English SRT file
        tgt_path: Path to target language SRT file
        dnt_path: Optional path to DNT terms JSON
        tb_path: Optional path to termbase JSON
        lang: Target language code
        batch_label: Batch identifier for file naming
        out_dir: Directory to write evaluation artifacts
        cps_soft_hard: Optional (soft, hard) CPS thresholds from rubric

    Returns:
        Dict containing verdict, fail reasons, and artifact paths
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    en = parse_srt(en_path)
    tgt = parse_srt(tgt_path)

    # CPS caps: rubric override if provided; otherwise language defaults
    if cps_soft_hard:
        soft, hard = cps_soft_hard
    else:
        soft, hard = (12, 15) if lang.lower().startswith("zh") else (15, 20)

    dnt_terms = load_dnt(dnt_path)
    tb_map = load_tb(tb_path, lang)

    # Timing deltas analysis
    n = min(len(en), len(tgt))
    d_start, d_end = [], []
    timing_rows: List[List[Any]] = []

    for i in range(n):
        ds = tgt[i].start_ms - en[i].start_ms
        de = tgt[i].end_ms - en[i].end_ms
        d_start.append(abs(ds))
        d_end.append(abs(de))
        timing_rows.append(
            [
                i + 1,
                en[i].index,
                en[i].start_ms,
                en[i].end_ms,
                tgt[i].start_ms,
                tgt[i].end_ms,
                ds,
                de,
            ]
        )

    # Write timing analysis CSV
    timing_csv = out_dir / f"timing_{lang}_{batch_label}.csv"
    with timing_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "cue",
                "index",
                "start_en_ms",
                "end_en_ms",
                "start_tgt_ms",
                "end_tgt_ms",
                "delta_start_ms",
                "delta_end_ms",
            ]
        )
        w.writerows(timing_rows)

    # CPS distribution analysis
    cps_vals, over_soft, over_hard = [], 0, 0
    cps_rows: List[List[Any]] = []

    for c in tgt:
        cps = cps_for_cue(c)
        cps_vals.append(cps)
        if cps > soft:
            over_soft += 1
        if cps > hard:
            over_hard += 1
        cps_rows.append(
            [
                c.index,
                len(c.text.replace("\n", "")),
                max(0.001, (c.end_ms - c.start_ms) / 1000.0),
                f"{cps:.2f}",
            ]
        )

    # Write CPS analysis CSV
    cps_csv = out_dir / f"cps_{lang}_{batch_label}.csv"
    with cps_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["index", "chars", "duration_s", "cps"])
        w.writerows(cps_rows)

    # DNT coverage analysis
    dnt_rows = []
    if dnt_terms:
        for term in dnt_terms:
            occ = _occurrences(en, term)
            if not occ:
                continue
            hits = _occurrences(tgt, term)
            dnt_rows.append(
                [
                    term,
                    len(occ),
                    len(hits),
                    round(100.0 * len(hits) / max(1, len(occ)), 2),
                    occ[:3],
                    hits[:3],
                ]
            )

    # Write DNT coverage CSV
    dnt_csv = out_dir / f"dnt_coverage_{lang}_{batch_label}.csv"
    with dnt_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "term",
                "en_occurrences",
                "preserved",
                "preserved_pct",
                "example_en_idx",
                "example_hit_idx",
            ]
        )
        w.writerows(dnt_rows)

    # Termbase coverage analysis
    tb_rows = []
    if tb_map:
        for key, loc in tb_map.items():
            occ = _occurrences(en, key)
            if not occ:
                continue
            hits = _localized_hits(tgt, loc)
            tb_rows.append(
                [
                    key,
                    loc,
                    len(occ),
                    len(hits),
                    round(100.0 * len(hits) / max(1, len(occ)), 2),
                    occ[:3],
                    hits[:3],
                ]
            )

    # Write termbase coverage CSV
    tb_csv = out_dir / f"tb_coverage_{lang}_{batch_label}.csv"
    with tb_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "key",
                "localized",
                "en_occurrences",
                "localized_hits",
                "hit_pct",
                "example_en_idx",
                "example_hit_idx",
            ]
        )
        w.writerows(tb_rows)

    # Untranslated content detection
    untranslated_rows = []
    for i in range(n):
        if is_untranslated_after_dnt(en[i].text, tgt[i].text, dnt_terms):
            untranslated_rows.append(
                [
                    i + 1,
                    en[i].index,
                    en[i].text.replace("\n", " / "),
                    tgt[i].text.replace("\n", " / "),
                ]
            )

    # Write untranslated content CSV
    untranslated_csv = out_dir / f"untranslated_{lang}_{batch_label}.csv"
    with untranslated_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["cue", "index", "en_text", "target_text"])
        w.writerows(untranslated_rows)

    # Source language fragment detection (post-DNT removal)
    srcfrag_rows = []
    for i in range(n):
        # Detect fragments after DNT removal (>=6 ASCII letters)
        stripped = strip_terms(tgt[i].text, dnt_terms)
        m = re.search(r"[A-Za-z]{6,}", stripped)
        if m:
            srcfrag_rows.append(
                [i + 1, tgt[i].index, tgt[i].text.replace("\n", " / "), m.group(0)]
            )

    # Write source fragments CSV (include batch token for consistency)
    srcfrag_csv = out_dir / f"source_fragments_{lang}_{batch_label}.csv"
    with srcfrag_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["cue", "index", "target_text", "snippet"])
        w.writerows(srcfrag_rows)

    # Number integrity validation
    num_rows = []
    for i in range(n):
        if not numbers_ok(en[i].text, tgt[i].text):
            nums = ",".join(re.findall(r"\d+", en[i].text or ""))
            num_rows.append(
                [i + 1, en[i].index, nums, tgt[i].text.replace("\n", " / ")]
            )

    # Write number mismatch CSV
    num_csv = out_dir / f"number_mismatch_{lang}_{batch_label}.csv"
    with num_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["cue", "index", "en_digits", "target_text"])
        w.writerows(num_rows)

    # Generate evaluation summary
    d_start = d_start or [0.0]
    d_end = d_end or [0.0]

    med_ds = percentile(d_start, 0.5)
    p95_ds = percentile(d_start, 0.95)
    max_ds = max(d_start)

    med_de = percentile(d_end, 0.5)
    p95_de = percentile(d_end, 0.95)
    max_de = max(d_end)

    cps_mean = sum(cps_vals) / len(cps_vals) if cps_vals else 0.0
    cps_med = percentile(cps_vals, 0.5) if cps_vals else 0.0
    pct_over_soft = round(100.0 * (over_soft / len(tgt) if tgt else 0.0), 2)
    pct_over_hard = round(100.0 * (over_hard / len(tgt) if tgt else 0.0), 2)

    # Determine verdict based on hard gates
    fail_reasons = []
    if len(en) != len(tgt):
        fail_reasons.append(f"Cue parity mismatch: src={len(en)} tgt={len(tgt)}")
    if med_ds > 200 or med_de > 200 or p95_ds > 500 or p95_de > 500:
        fail_reasons.append("Timing drift too high (median or p95)")
    if untranslated_rows:
        fail_reasons.append(f"Untranslated cues after DNT: {len(untranslated_rows)}")
    if num_rows:
        fail_reasons.append(f"Number integrity failed: {len(num_rows)} cues")

    verdict = "PASS" if not fail_reasons else "FAIL"

    # Write evaluation summary Markdown
    summary_md = out_dir / f"eval_summary_{lang}_{batch_label}.md"
    with summary_md.open("w", encoding="utf-8") as f:
        f.write(f"# Evaluation Summary — {lang} — Batch {batch_label}\n\n")
        f.write(f"**Verdict:** {verdict}\n")

        if fail_reasons:
            for r in fail_reasons:
                f.write(f"- {r}\n")

        f.write("\n## Structure & Timing\n")
        f.write(f"- Cues: source={len(en)} target={len(tgt)}\n")
        f.write(
            f"- Δstart (abs ms): median={med_ds:.0f}, p95={p95_ds:.0f}, max={max_ds:.0f}\n"
        )
        f.write(
            f"- Δend   (abs ms): median={med_de:.0f}, p95={p95_de:.0f}, max={max_de:.0f}\n\n"
        )

        f.write("## Readability (CPS)\n")
        f.write(
            f"- mean={cps_mean:.2f}, median={cps_med:.2f}, >soft({soft})={pct_over_soft}%, >hard({hard})={pct_over_hard}%\n\n"
        )

        f.write("## Terminology\n")
        if dnt_rows:
            avg = round(sum(r[3] for r in dnt_rows) / len(dnt_rows), 2)
            f.write(f"- DNT preservation: {avg}%\n")
        else:
            f.write("- DNT preservation: n/a\n")

        if tb_rows:
            avg = round(sum(r[4] for r in tb_rows) / len(tb_rows), 2)
            f.write(f"- Termbase usage: {avg}%\n")
        else:
            f.write("- Termbase usage: n/a\n")

        f.write("\n## Integrity checks\n")
        f.write(f"- Untranslated cues after DNT removal: {len(untranslated_rows)}\n")
        f.write(f"- Source-language fragments after DNT removal: {len(srcfrag_rows)}\n")
        f.write(f"- Number mismatches: {len(num_rows)}\n")

    return {
        "verdict": verdict,
        "fail_reasons": fail_reasons,
        "summary_md": str(summary_md),
    }


def generate_eval(
    en_path: str,
    tgt_path: str,
    lang: str,
    batch_label: str,
    out_dir: str,
    dnt_path: Optional[str] = None,
    tb_path: Optional[str] = None,
    cps_soft: Optional[int] = None,
    cps_hard: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Convenience wrapper for evaluate_pair that accepts string paths.

    This is the main entry point for external callers.
    """
    cps = (cps_soft, cps_hard) if (cps_soft and cps_hard) else None
    return evaluate_pair(
        Path(en_path),
        Path(tgt_path),
        Path(dnt_path) if dnt_path else None,
        Path(tb_path) if tb_path else None,
        lang,
        batch_label,
        Path(out_dir),
        cps_soft_hard=cps,
    )
