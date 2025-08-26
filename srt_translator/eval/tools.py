# srt_translator/eval/tools.py
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
import re, csv, json, math, unicodedata, yaml

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
        path.read_text(encoding="utf-8", errors="ignore")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
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
        m = re.match(
            r"\s*(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})", lines[ti]
        )
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


# ---------- DNT / TB helpers ----------


def strip_terms(text: str, terms: List[str]) -> str:
    out = text or ""
    for t in terms or []:
        if t:
            out = re.sub(re.escape(t), "", out, flags=re.IGNORECASE)
    return out


def is_untranslated_after_dnt(src: str, tgt: str, dnt_terms: List[str]) -> bool:
    a = _nfkc_lower(strip_terms(src, dnt_terms))
    b = _nfkc_lower(strip_terms(tgt, dnt_terms))
    return (a != "") and (a == b)


def numbers_ok(src: str, tgt: str) -> bool:
    nums = re.findall(r"\d+", src or "")
    return all(re.search(re.escape(n), tgt or "") for n in nums)


def _occurrences(cues: List[Cue], term: str) -> List[int]:
    norm = _nfkc_lower(term)
    base = re.escape(norm).replace(r"\ ", r"[ \-]?")
    poss = r"(?:'s|'s|s')?"
    pat = re.compile(rf"(?<!\w){base}{poss}(?!\w)", re.IGNORECASE)
    return [c.index for c in cues if pat.search(_nfkc_lower(c.text))]


def _localized_hits(cues: List[Cue], localized: str) -> List[int]:
    pat = re.compile(re.escape(localized))
    return [c.index for c in cues if pat.search(c.text)]


def load_dnt(path: Optional[Path]) -> Dict[str, Any]:
    """
    Returns dict with either:
      {"terms": [...]}  (global list)  OR
      {"languages": {"es":[...], "zh-Hans":[...]}}
    Unknown shapes are treated as no-terms.
    """
    if not path or not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        if isinstance(data, dict):
            if "languages" in data and isinstance(data["languages"], dict):
                return {"languages": data["languages"]}
            if "terms" in data and isinstance(data["terms"], list):
                return {"terms": data["terms"]}
    except Exception:
        pass
    return {}


def load_tb(path: Optional[Path]) -> Dict[str, Any]:
    """
    Returns dict with either:
      {"languages": {"es": {"A":"B", ...}, ...}}  OR
      {"es": {...}, "zh-Hans": {...}} (legacy)
    Unknown shapes are treated as empty.
    """
    if not path or not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        if isinstance(data, dict):
            if "languages" in data and isinstance(data["languages"], dict):
                return {"languages": data["languages"]}
            # legacy direct top-level per-language map
            return {"languages": data}
    except Exception:
        pass
    return {}


def _dnt_terms_for_lang(dnt_obj: Dict[str, Any], lang: str) -> List[str]:
    if "languages" in dnt_obj:
        langs = dnt_obj["languages"]
        return list(langs.get(lang) or langs.get(lang.split("-")[0]) or [])
    return list(dnt_obj.get("terms", []))


def _tb_map_for_lang(tb_obj: Dict[str, Any], lang: str) -> Dict[str, str]:
    if "languages" in tb_obj:
        langs = tb_obj["languages"]
        return dict(langs.get(lang) or langs.get(lang.split("-")[0]) or {})
    return {}


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
        except Exception:
            pass
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
    dnt_path: Optional[Path],
    tb_path: Optional[Path],
    lang: str,
    batch_label: str,
    out_dir: Path,
    cps_soft_hard: Optional[Tuple[int, int]] = None,
    rubric: Optional[Dict] = None,
) -> Dict[str, Any]:
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
        cps_soft_cap, cps_hard_cap = (
            (12, 15) if lang.lower().startswith("zh") else (15, 20)
        )

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

    # DNT/TB inputs
    dnt_obj = load_dnt(dnt_path)
    tb_obj = load_tb(tb_path)
    dnt_terms = _dnt_terms_for_lang(dnt_obj, lang)
    tb_map = _tb_map_for_lang(tb_obj, lang)

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
    with (out_dir / f"timing_{lang}_{batch}.csv").open(
        "w", encoding="utf-8", newline=""
    ) as f:
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
    with (out_dir / f"cps_{lang}_{batch}.csv").open(
        "w", encoding="utf-8", newline=""
    ) as f:
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
    with (out_dir / f"tb_coverage_{lang}_{batch}.csv").open(
        "w", encoding="utf-8", newline=""
    ) as f:
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

    # --- Untranslated after DNT + source fragments (global policy) ---
    untranslated_after_dnt_rows, source_fragment_rows = [], []
    proj_root = Path(__file__).resolve().parents[2]
    frag_cfg = _load_frag_cfg(proj_root)
    mode = frag_cfg.get("mode", "auto_non_latin")
    min_run = int(frag_cfg.get("min_ascii_run", 6))
    emit_frags = (mode == "always") or (
        mode == "auto_non_latin" and _target_is_non_latin(target_cues)
    )

    for cue_idx in range(cue_count):
        # Check untranslated after DNT removal
        src_after_dnt = strip_terms(source_cues[cue_idx].text, dnt_terms)
        status, note = untranslated_after_dnt_check(
            src_after_dnt, target_cues[cue_idx].text, rubric
        )
        if status == "fail":
            untranslated_after_dnt_rows.append(
                [
                    cue_idx + 1,
                    source_cues[cue_idx].index,
                    source_cues[cue_idx].text.replace("\n", " / "),
                    target_cues[cue_idx].text.replace("\n", " / "),
                ]
            )
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

    with (out_dir / f"untranslated_{lang}_{batch}.csv").open(
        "w", encoding="utf-8", newline=""
    ) as f:
        w = csv.writer(f)
        w.writerow(["cue", "index", "original_text", "target_text"])
        w.writerows(untranslated_after_dnt_rows)

    # Fragments: only emit when rubric says so AND there is at least one row
    if should_emit_fragments(
        lang, {"fragments": {"mode": mode}}, len(source_fragment_rows)
    ):
        with (out_dir / f"source_fragments_{lang}_{batch}.csv").open(
            "w", encoding="utf-8", newline=""
        ) as f:
            w = csv.writer(f)
            w.writerow(["cue", "index", "target_text", "snippet"])
            w.writerows(source_fragment_rows)

    # --- Numbers integrity (pure digits only) ---
    number_mismatch_rows: List[List[Any]] = []
    for cue_idx in range(cue_count):
        mismatch, note = numbers_integrity_check(
            source_cues[cue_idx].text, target_cues[cue_idx].text, rubric
        )
        if mismatch:
            nums = ",".join(extract_pure_digits(source_cues[cue_idx].text))
            number_mismatch_rows.append(
                [
                    cue_idx + 1,
                    source_cues[cue_idx].index,
                    nums,
                    target_cues[cue_idx].text.replace("\n", " / "),
                ]
            )
    with (out_dir / f"number_mismatch_{lang}_{batch}.csv").open(
        "w", encoding="utf-8", newline=""
    ) as f:
        w = csv.writer(f)
        w.writerow(["cue", "index", "original_digits", "target_text"])
        w.writerows(number_mismatch_rows)

    # --- Verdict (structural + integrity gates only) ---
    timing_delta_start_ms = timing_delta_start_ms or [0.0]
    timing_delta_end_ms = timing_delta_end_ms or [0.0]
    med_ds = percentile(timing_delta_start_ms, 0.5)
    p95_ds = percentile(timing_delta_start_ms, 0.95)
    med_de = percentile(timing_delta_end_ms, 0.5)
    p95_de = percentile(timing_delta_end_ms, 0.95)

    fail_reasons: List[str] = []
    if len(source_cues) != len(target_cues):
        fail_reasons.append(
            f"Cue parity mismatch: src={len(source_cues)} tgt={len(target_cues)}"
        )
    if med_ds > 200 or med_de > 200 or p95_ds > 500 or p95_de > 500:
        fail_reasons.append("Timing drift too high (median or p95)")
    if untranslated_after_dnt_rows:
        fail_reasons.append(
            f"Untranslated after DNT: {len(untranslated_after_dnt_rows)}"
        )
    if number_mismatch_rows:
        fail_reasons.append(f"Numbers mismatch: {len(number_mismatch_rows)} cues")
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
    dnt_path: Optional[str] = None,
    tb_path: Optional[str] = None,
    cps_soft: Optional[int] = None,
    cps_hard: Optional[int] = None,
    rubric: Optional[Dict] = None,
):
    cps = (
        (cps_soft, cps_hard)
        if (cps_soft is not None and cps_hard is not None)
        else None
    )
    return evaluate_pair(
        Path(source_path),
        Path(target_path),
        Path(dnt_path) if dnt_path else None,
        Path(tb_path) if tb_path else None,
        lang,
        batch_label,
        Path(out_dir),
        cps_soft_hard=cps,
        rubric=rubric,
    )


# ---------- New evaluation helpers for PR polish ----------

PURE_DIGIT = re.compile(
    r"(?<![A-Za-z])\d+(?![A-Za-z])"
)  # digits not adjacent to letters
UPPER_ACRO = re.compile(r"^[A-Z0-9]{2,8}\.?$")


def extract_pure_digits(s: str) -> List[str]:
    return PURE_DIGIT.findall(s or "")


def is_upper_acronym(token: str) -> bool:
    return bool(UPPER_ACRO.match((token or "").strip()))


def numbers_integrity_check(src: str, tgt: str, rubric: Dict) -> Tuple[bool, str]:
    """Pure digits must match as a multiset; mixed alphanumerics (Q3/A4) are not failures."""
    s = extract_pure_digits(src)
    t = extract_pure_digits(tgt)
    if sorted(s) != sorted(t):
        return True, "Pure digit mismatch (missing/changed numerals)."
    return False, ""


def untranslated_after_dnt_check(
    src_after_dnt: str, tgt: str, rubric: Dict
) -> Tuple[str, str]:
    """
    Returns one of: ('fail'|'info'|'pass', note).
    - Ignore trivial one-word cognates below min length.
    - ALL-CAPS acronyms are INFO unless they're in DNT/TB.
    """
    s = (src_after_dnt or "").strip()
    t = (tgt or "").strip()
    if not s:
        return "pass", ""
    if s == t:
        toks = s.split()
        if len(toks) == 1:
            tok = toks[0]
            min_len = int(
                rubric.get("untranslated_after_dnt", {}).get("min_remainder_len", 5)
            )
            if len(tok) < min_len:
                return "pass", ""
            if is_upper_acronym(tok):
                sev = rubric.get("untranslated_after_dnt", {}).get(
                    "uppercase_acronym_treated_as", "info"
                )
                return sev, "Uppercase acronym carried through."
        return "fail", "Identical to original after DNT removal."
    return "pass", ""


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
