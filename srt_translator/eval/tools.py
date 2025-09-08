# srt_translator/eval/tools.py
from __future__ import annotations

import csv
import math
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Literal, Tuple

import yaml

# -----------------------------
# Roll-up helpers (normalization & evidence)
# -----------------------------
RollupClass = Literal["BENIGN_ROLLUP", "SUSPECT_ROLLUP", "MISSING"]

# Strings that should count as "empty" in targets for eval purposes
PLACEHOLDER_EMPTY_STRINGS = {"(none)", "(null)", "n/a", "—", "–", "…"}

# Lightweight discourse markers as evidence that a sentence moved across cues
DISCOURSE_MARKERS = {
    "en": {"first", "second", "third"},
    "az": {"birincisi", "ikincisi", "üçüncüsü"},
    "ar": {"أولًا", "ثانيًا", "ثالثًا"},
}


def normalize_for_empty_check(text: str) -> str:
    """
    Normalize text solely to decide if a target cue is effectively empty:
    - trim, lowercase, strip bidi/zero-width, map placeholder strings to ''
    """
    if not text:
        return ""
    t = (text or "").strip().lower()
    t = re.sub(r"[\u200b-\u200f\u061C\u2066-\u2069]", "", t)  # zero-width/bidi
    return "" if t in PLACEHOLDER_EMPTY_STRINGS else t


def is_numbers_or_punct_only(text: str) -> bool:
    """True if text is only whitespace/punctuation/digits (Latin or Arabic-Indic)."""
    if not text:
        return True
    arabic_indic = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
    t = text.translate(arabic_indic)
    return bool(re.fullmatch(r"[\s\W\d]+", t))


def extract_numbers(text: str) -> List[str]:
    """Extract number tokens (Latin & Arabic-Indic digits)."""
    if not text:
        return []
    arabic_indic = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
    t = text.translate(arabic_indic)
    return re.findall(r"\d+(?:[.,]\d+)?", t)


def has_discourse_marker(lang: str, text: str) -> bool:
    """Check for known discourse markers (e.g., First/Birincisi/أولًا)."""
    markers = DISCOURSE_MARKERS.get(lang, set())
    if not markers or not text:
        return False
    norm = (text or "").strip().lower()
    return any(norm.startswith(m) or f" {m} " in f" {norm} " for m in markers)


def termbase_hit_in_text(tb_map: Dict[str, str], text: str) -> bool:
    """
    Termbase presence: True if ANY target-side term appears in `text`, allowing
    trailing punctuation (e.g., 'OKRs?' matches 'OKRs'). Uses word-ish boundaries.
    """
    if not tb_map or not text:
        return False
    tnorm = (text or "").lower()
    for tgt in tb_map.values():
        if not tgt:
            continue
        patt = re.escape(tgt.strip().lower())
        # (?<!\w) no letter/number before; (?=\W|$) allows punctuation or end after
        if re.search(rf"(?<!\w){patt}(?=\W|$)", tnorm):
            return True
    return False


# ---------- SRT parsing & basic utilities ----------


@dataclass
class Cue:
    index: int
    start_ms: int
    end_ms: int
    text: str


def _parse_time(t: str) -> int:
    hh, mm, rest = t.split(":")
    ss, ms = rest.split(",")
    return (int(hh) * 3600 + int(mm) * 60 + int(ss)) * 1000 + int(ms)


def parse_srt(path: Path) -> List[Cue]:
    txt = (
        path.read_text(encoding="utf-8", errors="ignore").replace("\r\n", "\n").replace("\r", "\n")
    )
    blocks = re.split(r"\n\s*\n", txt)
    cues: List[Cue] = []
    expected_idx = 1
    for b in blocks:
        b = b.strip()
        if not b:
            continue
        lines = b.split("\n")
        ti = 0
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
        m = re.match(r"\s*(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})", lines[ti])
        if not m:
            continue
        start_ms = _parse_time(m.group(1))
        end_ms = _parse_time(m.group(2))
        text = "\n".join(lines[ti + 1 :]).strip()
        cues.append(Cue(index=idx, start_ms=start_ms, end_ms=end_ms, text=text))
    return cues


def cps_for_cue(c: Cue) -> float:
    dur_s = max(0.001, (c.end_ms - c.start_ms) / 1000.0)
    return len(c.text.replace("\n", "")) / dur_s


def percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0
    v = sorted(values)
    k = (len(v) - 1) * p
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return v[int(k)]
    return v[f] * (c - k) + v[c] * (k - f)


def _nfkc_lower(s: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", s or "")).strip().lower()


def median_expansion_ratio(source_after_dnt: List[str], target_norm: List[str]) -> float:
    """
    Robust expansion ratio R = median(len(target)/len(source_after_dnt))
    over cues where both sides are non-empty.
    """
    vals: List[float] = []
    for s, t in zip(source_after_dnt, target_norm):
        if not s or not t:
            continue
        vals.append(len(t) / max(1, len(s)))
    if not vals:
        return 1.0
    import statistics

    try:
        return statistics.median(vals)
    except statistics.StatisticsError:
        return 1.0


def classify_empty_target_rollup(
    *,
    lang: str,
    cue_index: int,
    source_cues: List[Cue],
    target_cues: List[Cue],
    do_not_translate_terms: List[str],
    termbase_map_for_lang: Dict[str, str],
    length_ratio_alpha: float = 0.8,
) -> Tuple[RollupClass, str]:
    """
    Classify a normalized-empty target cue as:
      - BENIGN_ROLLUP: sufficient neighbor length + at least one evidence signal
      - SUSPECT_ROLLUP: sufficient neighbor length but no evidence
      - MISSING: neither sufficiency nor evidence
    Evidence signals: discourse marker, numbers, termbase hit, or tiny remainder after DNT.
    """
    i = cue_index
    if i < 0 or i >= len(source_cues):
        return "MISSING", "index out of range"

    # Simple guard to align with runner: if either neighbor is non-empty, treat as roll-up.
    prev_norm = normalize_for_empty_check(target_cues[i - 1].text or "") if i > 0 else ""
    next_norm = (
        normalize_for_empty_check(target_cues[i + 1].text or "")
        if (i + 1) < len(target_cues)
        else ""
    )
    if prev_norm or next_norm:
        return "BENIGN_ROLLUP", "neighbor non-empty (simple guard)"

    # Ignore very short source fragments (common in re-segmentation).
    src_norm = normalize_for_empty_check(source_cues[i].text or "")
    if len(src_norm) < 12:
        return "BENIGN_ROLLUP", "short source (simple guard)"

    # Precompute normalized lists for ratio estimation
    src_after_all = [strip_terms(c.text, do_not_translate_terms) for c in source_cues]
    tgt_norm_all = [normalize_for_empty_check(c.text) for c in target_cues]
    R = median_expansion_ratio(src_after_all, tgt_norm_all)

    src_this_after = src_after_all[i] or ""
    # Tiny remainder: accept roll-up if a neighbor exists and is non-empty
    if not src_this_after or len(src_this_after) <= 5 or is_numbers_or_punct_only(src_this_after):
        if i > 0 and tgt_norm_all[i - 1]:
            return "BENIGN_ROLLUP", "tiny remainder rolled up to previous cue"
        if i + 1 < len(target_cues) and tgt_norm_all[i + 1]:
            return "BENIGN_ROLLUP", "tiny remainder rolled up to next cue"
        return "MISSING", "tiny remainder but no non-empty neighbors"

    # Prefer previous neighbor; otherwise next
    neighbor = (
        i - 1
        if (i > 0 and tgt_norm_all[i - 1])
        else (i + 1 if (i + 1 < len(target_cues) and tgt_norm_all[i + 1]) else -1)
    )
    if neighbor == -1:
        return "MISSING", "no non-empty neighbors"

    # Evidence signals
    evidence: List[str] = []
    if has_discourse_marker(lang, source_cues[i].text or "") and has_discourse_marker(
        lang, target_cues[neighbor].text or ""
    ):
        evidence.append("discourse-marker")
    src_nums = set(extract_numbers(source_cues[i].text or ""))
    tgt_nums = set(extract_numbers(target_cues[neighbor].text or ""))
    if src_nums and (src_nums & tgt_nums):
        evidence.append("numbers")
    if termbase_hit_in_text(termbase_map_for_lang, target_cues[neighbor].text or ""):
        evidence.append("termbase-hit")

    # Sufficiency: neighbor should be large enough to plausibly include *this* missing cue.
    # Using only src_this_after makes the classifier robust to real-world resegmentations
    # where the neighbor's own source was merged elsewhere (earlier/later cues).
    required_len = len(src_this_after) * R * length_ratio_alpha
    neighbor_len = len(tgt_norm_all[neighbor])
    sufficient = neighbor_len >= required_len

    if sufficient and evidence:
        return "BENIGN_ROLLUP", f"sufficient length + evidence: {','.join(evidence)}"
    if sufficient and not evidence:
        return "SUSPECT_ROLLUP", "sufficient length but no content evidence"
    return "MISSING", "insufficient neighbor length to justify roll-up"


# ---------- DNT / TB helpers ----------


def strip_terms(text: str, terms: List[str]) -> str:
    """
    Boundary-aware, case-insensitive removal of DNT terms from text
    to assess "what remains to be translated".
    """
    out = text or ""
    for t in terms or []:
        if not t:
            continue
        # allow space/hyphen variants, enforce word-ish boundaries
        patt = re.escape(t).replace(r"\ ", r"[ \-]")
        out = re.sub(rf"(?<!\w){patt}(?!\w)", "", out, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", out).strip()


def _occurrences(cues: List[Cue], term: str) -> List[int]:
    norm = _nfkc_lower(term)
    base = re.escape(norm).replace(r"\ ", r"[ \-]?")
    poss = r"(?:'s|'s|s')?"
    pat = re.compile(rf"(?<!\w){base}{poss}(?!\w)", re.IGNORECASE)
    return [c.index for c in cues if pat.search(_nfkc_lower(c.text))]


def _localized_hits(cues: List[Cue], localized: str) -> List[int]:
    pat = re.compile(re.escape(localized))
    return [c.index for c in cues if pat.search(c.text)]


# ---------- Fragments global policy ----------


def _load_frag_cfg(project_root: Path) -> Dict[str, Any]:
    cfg = {"mode": "auto_non_latin", "min_ascii_run": 6}
    rb = project_root / "config" / "translation_rubric.yaml"
    if rb.exists():
        try:
            y = yaml.safe_load(rb.read_text(encoding="utf-8"))
            if isinstance(y, dict) and "fragments" in y:
                f = y["fragments"]
                mode = str(f.get("mode", "auto_non_latin")).strip()
                if mode not in ("auto_non_latin", "always", "never"):
                    mode = "auto_non_latin"
                cfg["mode"] = mode
                cfg["min_ascii_run"] = int(f.get("min_ascii_run", 6))
        except Exception as e:
            # Fallback to defaults if YAML loading fails
            print(f"Warning: Failed to load YAML config: {e}")  # noqa: T201
    return cfg


def _target_is_non_latin(cues: List[Cue]) -> bool:
    """
    Heuristic: if majority of letters are outside Basic Latin, treat as non-Latin script.
    """
    latin = nonlatin = 0
    for c in cues:
        for ch in c.text:
            if ch.isalpha():
                if "A" <= ch <= "z":
                    latin += 1
                else:
                    nonlatin += 1
    # If no letters at all, default to False (Latin)
    total = latin + nonlatin
    if total == 0:
        return False
    return (nonlatin / total) >= 0.6


# ---------- Main evaluation (single pair) ----------


def evaluate_pair(
    source_path: Path,
    target_path: Path,
    lang: str,
    batch_label: str,
    out_dir: Path,
    *,
    dnt_terms: list[str],
    tb_map: dict[str, str],
    cps_soft_hard: tuple[int, int] | None = None,
    rubric: dict | None = None,
) -> dict[str, Any]:
    """
    Evaluate one (source,target) pair and write artifacts into out_dir.
    Returns verdict + fail reasons + path to per-file MD summary.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    source_cues = parse_srt(source_path)
    target_cues = parse_srt(target_path)

    # CPS caps
    if cps_soft_hard:
        cps_soft_cap, cps_hard_cap = cps_soft_hard
    else:
        cps_soft_cap, cps_hard_cap = (12, 15) if lang.lower().startswith("zh") else (15, 20)

    # Load rubric if not provided
    if rubric is None:
        try:
            project_root = Path(__file__).resolve().parents[2]
            rubric_file = project_root / "config" / "translation_rubric.yaml"
            if rubric_file.exists():
                import yaml

                rubric = yaml.safe_load(rubric_file.read_text(encoding="utf-8")) or {}
            else:
                rubric = {}
        except Exception:
            rubric = {}

    # DNT/TB inputs - use passed values directly
    dnt_terms = dnt_terms or []
    tb_map = tb_map or {}

    batch = batch_label

    # --- Timing deltas ---
    cue_count = min(len(source_cues), len(target_cues))
    timing_delta_start_ms, timing_delta_end_ms = [], []
    timing_rows: List[List[Any]] = []
    for cue_idx in range(cue_count):
        delta_start_ms = target_cues[cue_idx].start_ms - source_cues[cue_idx].start_ms
        delta_end_ms = target_cues[cue_idx].end_ms - source_cues[cue_idx].end_ms
        timing_delta_start_ms.append(abs(delta_start_ms))
        timing_delta_end_ms.append(abs(delta_end_ms))
        timing_rows.append(
            [
                cue_idx + 1,
                source_cues[cue_idx].index,
                source_cues[cue_idx].start_ms,
                source_cues[cue_idx].end_ms,
                target_cues[cue_idx].start_ms,
                target_cues[cue_idx].end_ms,
                delta_start_ms,
                delta_end_ms,
            ]
        )
    with (out_dir / f"timing_{lang}_{batch}.csv").open("w", encoding="utf-8", newline="") as f:
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

    # --- CPS distribution ---
    cps_values, over_soft_count, over_hard_count = [], 0, 0
    cps_rows: List[List[Any]] = []
    for cue in target_cues:
        cps = cps_for_cue(cue)
        cps_values.append(cps)
        if cps > cps_soft_cap:
            over_soft_count += 1
        if cps > cps_hard_cap:
            over_hard_count += 1
        cps_rows.append(
            [
                cue.index,
                len(cue.text.replace("\n", "")),
                max(0.001, (cue.end_ms - cue.start_ms) / 1000.0),
                f"{cps:.2f}",
            ]
        )
    with (out_dir / f"cps_{lang}_{batch}.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["index", "chars", "duration_s", "cps"])
        w.writerows(cps_rows)

    # --- DNT coverage (always write CSV, even empty) ---
    dnt_rows: List[List[Any]] = []
    if dnt_terms:
        source_occurrence_cache = {}  # small cache to avoid re-scanning
        for term in dnt_terms:
            if term not in source_occurrence_cache:
                source_occurrence_cache[term] = _occurrences(source_cues, term)
            term_occurrences = source_occurrence_cache[term]
            if not term_occurrences:
                continue
            term_hits = _occurrences(target_cues, term)
            dnt_rows.append(
                [
                    term,
                    len(term_occurrences),
                    len(term_hits),
                    round(100.0 * len(term_hits) / max(1, len(term_occurrences)), 2),
                    term_occurrences[:3],
                    term_hits[:3],
                ]
            )
    with (out_dir / f"dnt_coverage_{lang}_{batch}.csv").open(
        "w", encoding="utf-8", newline=""
    ) as f:
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

    # --- Termbase coverage (always write CSV, even empty) ---
    tb_rows: List[List[Any]] = []
    if tb_map:
        source_occurrence_cache = {}
        for key, loc in tb_map.items():
            if key not in source_occurrence_cache:
                source_occurrence_cache[key] = _occurrences(source_cues, key)
            term_occurrences = source_occurrence_cache[key]
            if not term_occurrences:
                continue
            term_hits = _localized_hits(target_cues, loc)
            tb_rows.append(
                [
                    key,
                    loc,
                    len(term_occurrences),
                    len(term_hits),
                    round(100.0 * len(term_hits) / max(1, len(term_occurrences)), 2),
                    term_occurrences[:3],
                    term_hits[:3],
                ]
            )
    with (out_dir / f"tb_coverage_{lang}_{batch}.csv").open("w", encoding="utf-8", newline="") as f:
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

    # --- Source fragments (global policy) ---
    source_fragment_rows = []
    proj_root = Path(__file__).resolve().parents[2]
    frag_cfg = _load_frag_cfg(proj_root)
    mode = frag_cfg.get("mode", "auto_non_latin")
    min_run = int(frag_cfg.get("min_ascii_run", 6))
    emit_frags = (mode == "always") or (
        mode == "auto_non_latin" and _target_is_non_latin(target_cues)
    )

    for cue_idx in range(cue_count):
        if emit_frags:
            stripped = strip_terms(target_cues[cue_idx].text, dnt_terms)
            m = re.search(rf"[A-Za-z]{{{min_run},}}", stripped)
            if m:
                source_fragment_rows.append(
                    [
                        cue_idx + 1,
                        target_cues[cue_idx].index,
                        target_cues[cue_idx].text.replace("\n", " / "),
                        m.group(0),
                    ]
                )

    # Fragments: only emit when rubric says so AND there is at least one row
    if should_emit_fragments(lang, {"fragments": {"mode": mode}}, len(source_fragment_rows)):
        with (out_dir / f"source_fragments_{lang}_{batch}.csv").open(
            "w", encoding="utf-8", newline=""
        ) as f:
            w = csv.writer(f)
            w.writerow(["cue", "index", "target_text", "snippet"])
            w.writerows(source_fragment_rows)

    # --- Verdict (structural + integrity gates only) ---
    timing_delta_start_ms = timing_delta_start_ms or [0.0]
    timing_delta_end_ms = timing_delta_end_ms or [0.0]
    # Convert to float lists for percentile function
    start_floats = [float(x) for x in timing_delta_start_ms]
    end_floats = [float(x) for x in timing_delta_end_ms]
    med_ds = percentile(start_floats, 0.5)
    p95_ds = percentile(start_floats, 0.95)
    med_de = percentile(end_floats, 0.5)
    p95_de = percentile(end_floats, 0.95)

    fail_reasons: List[str] = []
    if len(source_cues) != len(target_cues):
        fail_reasons.append(f"Cue parity mismatch: src={len(source_cues)} tgt={len(target_cues)}")
    if med_ds > 200 or med_de > 200 or p95_ds > 500 or p95_de > 500:
        fail_reasons.append("Timing drift too high (median or p95)")

    verdict = "PASS" if not fail_reasons else "FAIL"

    # Per-pair audit summary (not the creator-facing report)
    summary_md = out_dir / f"eval_summary_{lang}_{batch}.md"
    with summary_md.open("w", encoding="utf-8") as f:
        f.write(f"# Evaluation Summary — {lang} — Batch {batch}\n\n")
        f.write(f"**Verdict:** {verdict}\n")
        for r in fail_reasons:
            f.write(f"- {r}\n")
        f.write("\n(See CSVs in this folder for details.)\n")

    return {
        "verdict": verdict,
        "fail_reasons": fail_reasons,
        "summary_md": str(summary_md),
        "fragments_rows": len(source_fragment_rows),
    }


# Thin wrapper kept for compatibility with caller
def generate_eval(
    source_path: str,
    target_path: str,
    lang: str,
    batch_label: str,
    out_dir: str,
    *,
    dnt_terms: list[str],
    tb_map: dict[str, str],
    cps_soft: int | None = None,
    cps_hard: int | None = None,
    rubric: dict | None = None,
):
    """
    v1.0: accepts in-memory DNT and termbase map; no file-path inputs.
    """
    cps = (cps_soft, cps_hard) if (cps_soft is not None and cps_hard is not None) else None

    return evaluate_pair(
        Path(source_path),
        Path(target_path),
        lang,
        batch_label,
        Path(out_dir),
        dnt_terms=dnt_terms or [],
        tb_map=tb_map or {},
        cps_soft_hard=cps,
        rubric=rubric,
    )


def should_emit_fragments(lang_code: str, rubric: dict, rows: int) -> bool:
    if rows <= 0:
        return False
    mode = rubric.get("fragments", {}).get("mode", "never")
    if mode == "never":
        return False
    if mode == "always":
        return True
    if mode == "auto_non_latin":
        return (lang_code or "").lower() in {
            "zh-hans",
            "zh-hant",
            "ja",
            "ko",
            "ru",
            "uk",
            "ar",
            "he",
            "fa",
            "hi",
            "th",
            "bn",
            "ta",
            "te",
            "kn",
            "ml",
            "gu",
            "pa",
        }
    return False


def srt_ts_to_ms(ts: str) -> int:
    """
    Convert 'HH:MM:SS,mmm' (or 'HH:MM:SS.mmm') to milliseconds.
    Strict but fast; raises ValueError on malformed input.
    """
    ts = ts.strip()
    if len(ts) < 12:
        raise ValueError(f"Bad SRT timestamp: {ts!r}")
    # allow comma or dot as decimal separator
    hh = int(ts[0:2])
    mm = int(ts[3:5])
    ss = int(ts[6:8])
    sep = ts[8]
    if sep not in {",", "."}:
        raise ValueError(f"Bad SRT timestamp separator in {ts!r}")
    ms = int(ts[9:12])
    return ((hh * 60 + mm) * 60 + ss) * 1000 + ms
