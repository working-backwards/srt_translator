# srt_translator/eval/report.py
from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, Tuple, List
import json
import re
from srt_translator.core.config.language_config import LanguageConfig
from srt_translator.eval.tools import parse_srt


# -----------------------------
# Helpers to keep Markdown errors-only
# -----------------------------
def _only_errors_list(issues: List[dict]) -> List[dict]:
    """Return only ERROR-severity issues for Markdown rendering."""
    return [
        i for i in (issues or []) if str(i.get("severity", "ERROR")).upper() == "ERROR"
    ]


# -----------------------------
# Context-window helpers (prev2/current/next2), boundary-safe
# -----------------------------


def _load_ai_config(batch_root: Path) -> Dict[str, Any]:
    """Read ai_config.json to derive source language name (optional)."""
    cfg_path = batch_root / "ai_config.json"
    if cfg_path.exists():
        try:
            return json.loads(cfg_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _source_language_name(batch_root: Path) -> str:
    """
    Try to resolve a friendly source language name from ai_config.json;
    fallback to 'English' (current app default).
    """
    cfg = _load_ai_config(batch_root)
    for key in ("source_language_name", "source_lang_name", "source_language"):
        val = cfg.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    code = cfg.get("source_language_code") or cfg.get("source_lang") or "en"
    try:
        return lang_to_name(code)
    except Exception:
        return "English"


def _window_indices(
    center_index: int, min_index: int, max_index: int, radius: int = 2
) -> Tuple[int, int]:
    """Return clamped (start, end) indices for a symmetric window around center_index."""
    start_idx = max(min_index, center_index - radius)
    end_idx = min(max_index, center_index + radius)
    return start_idx, end_idx


def _render_window_block(cues: List[Any], start_idx: int, end_idx: int) -> str:
    """Render window of cue texts as 'NN: text' lines (collapsing inner whitespace)."""
    by_num = {c.index: (c.text or "").strip() for c in cues}
    lines: List[str] = []
    for n in range(start_idx, end_idx + 1):
        txt = by_num.get(n, "")
        clean = re.sub(r"\s+", " ", txt).strip()
        lines.append(f"{n}: {clean}")
    return "\n".join(lines)


def _context_blocks_for_issue(
    *,
    batch_root: Path,
    source_file: str,
    target_file: str,
    cue_number: int,
    radius: int = 2,
) -> Tuple[str, str]:
    """
    Return (target_context_block, source_context_block) containing prev {radius},
    current, next {radius} cues. Bounds are clamped at file edges.
    """
    src_path = Path(batch_root) / source_file
    tgt_path = Path(batch_root) / target_file
    source_cues = parse_srt(src_path)
    target_cues = parse_srt(tgt_path)
    if not source_cues:
        return "", ""
    min_idx = source_cues[0].index
    max_idx = source_cues[-1].index
    start_idx, end_idx = _window_indices(
        int(cue_number), min_idx, max_idx, radius=radius
    )
    target_block = _render_window_block(target_cues, start_idx, end_idx)
    source_block = _render_window_block(source_cues, start_idx, end_idx)
    return target_block, source_block


def render_consolidated_punchlist(languages: Dict, *, batch_root: Path) -> str:
    """
    Top-of-report list of issues with suggested fixes.
    Markdown shows ERRORs only (no INFO/WARN) and includes a contextual check.
    """
    # Flatten ERROR issues across languages/files
    error_issues: List[dict] = []
    for lang, entry in languages.items():
        for f in entry.get("files", []) or []:
            # Defensive: ensure f is a dictionary
            if not isinstance(f, dict):
                continue
            issues = f.get("issues", {}) or {}
            # Only render missing_translation and untranslated_after_dnt
            for issue in issues.get("missing_translation", []) or []:
                i = dict(issue)
                i["_lang"] = lang
                i["_target_file"] = f.get("target_file", f.get("file_name", ""))
                i["_source_file"] = f.get("source_file", "")
                error_issues.append(i)
            for issue in issues.get("untranslated_after_dnt", []) or []:
                i = dict(issue)
                i["_lang"] = lang
                i["_target_file"] = f.get("target_file", f.get("file_name", ""))
                i["_source_file"] = f.get("source_file", "")
                error_issues.append(i)

    if not error_issues:
        return "Everything looks great. Your translated files are **ready for use**."

    total = len(error_issues)
    lines = []
    lines.append(
        f"Some files need attention. Below is a consolidated punch list of **{total}** issue(s). For each cue, we show the original and the translation with a contextual suggested check.\n"
    )
    for issue in error_issues:
        lang = issue["_lang"]
        target_file = issue["_target_file"]
        source_file = issue["_source_file"]
        cue = issue.get("cue") or issue.get("idx")
        orig = issue.get("src") or issue.get("original") or ""
        tgt = issue.get("tgt") or issue.get("target") or ""
        lines.append(f"### {_lang_label(lang)} ({lang})\n")
        lines.append(f"#### {target_file}")
        lines.append(
            f"- cue {cue}:\n  `Original: {orig}`\n  `{_lang_label(lang)}: {tgt}`\n"
        )
        # Contextual "Suggested check" (prev2/current/next2), boundary-safe
        try:
            tgt_block, src_block = _context_blocks_for_issue(
                batch_root=batch_root,
                source_file=source_file,
                target_file=target_file,
                cue_number=int(cue),
                radius=2,
            )
            if tgt_block and src_block:
                src_lang_name = _source_language_name(batch_root)
                lines.append(
                    f"\n_Suggested check:_ Copy the **Target context** below into your AI assistant and ask for a translation into **{src_lang_name}**, then compare it to the **Source context**.\n"
                )
                lines.append("**Target context (prev 2 / current / next 2):**")
                lines.append("```")
                lines.append(tgt_block)
                lines.append("```")
                lines.append("**Source context (prev 2 / current / next 2):**")
                lines.append("```")
                lines.append(src_block)
                lines.append("```")
        except Exception:
            # Never let context rendering break the report; skip on error
            pass
        lines.append("")  # spacing
    return "\n".join(lines)


def render_issue_sections(languages: Dict, *, batch_root: Path) -> str:
    """
    Render ERROR sections grouped by language/file with contextual "Suggested check".
    INFO/WARN are intentionally omitted from Markdown.
    """
    lines: List[str] = []
    for lang, entry in languages.items():
        lines.append(f"## {_lang_label(lang)} ({lang})\n")
        for f in entry.get("files", []) or []:
            # Defensive: ensure f is a dictionary
            if not isinstance(f, dict):
                continue
            target_file = f.get("target_file", f.get("file_name", "—"))
            source_file = f.get("source_file", "—")
            issues = f.get("issues", {}) or {}
            # Only render missing_translation and untranslated_after_dnt
            errs_flat = []
            errs_flat += issues.get("missing_translation", []) or []
            errs_flat += issues.get("untranslated_after_dnt", []) or []
            if not errs_flat:
                continue
            lines.append(f"### {target_file}")
            lines.append("**Blocking issues**\n")
            src_lang_name = _source_language_name(batch_root)
            for issue in errs_flat:
                cue = issue.get("cue") or issue.get("idx")
                orig = issue.get("src") or issue.get("original") or ""
                tgt = issue.get("tgt") or issue.get("target") or ""
                lines.append(
                    f"- cue {cue}:\n  `Original: {orig}`\n  `{_lang_label(lang)}: {tgt}`\n"
                )
                # Contextual suggested check (prev2/current/next2)
                try:
                    tgt_block, src_block = _context_blocks_for_issue(
                        batch_root=batch_root,
                        source_file=source_file,
                        target_file=target_file,
                        cue_number=int(cue),
                        radius=2,
                    )
                    if tgt_block and src_block:
                        lines.append(
                            f"\n_Suggested check:_ Copy the **Target context** below into your AI assistant and ask for a translation into **{src_lang_name}**, then compare it to the **Source context**.\n"
                        )
                        lines.append("**Target context (prev 2 / current / next 2):**")
                        lines.append("```")
                        lines.append(tgt_block)
                        lines.append("```")
                        lines.append("**Source context (prev 2 / current / next 2):**")
                        lines.append("```")
                        lines.append(src_block)
                        lines.append("```")
                except Exception:
                    pass
            lines.append("")  # spacing
    return "\n".join(lines)


def _get_language_info(code: str) -> Dict[str, str]:
    """Get language info using the language config abstraction."""
    try:
        # Load languages.json from project root
        project_root = Path(__file__).resolve().parents[2]
        languages_file = project_root / "config" / "languages.json"
        if languages_file.exists():
            data = json.loads(languages_file.read_text(encoding="utf-8"))
            # Simple lookup without full LanguageConfig dependency
            languages = data.get("languages", {})
            lang_info = languages.get(code, {})
            name = lang_info.get("name")
            return {"name": name if name else code, "code": code}
    except Exception:
        pass
    return {"name": code, "code": code}


def _lang_label(code: str) -> str:
    """Get friendly language name for display."""
    try:
        # Load languages.json from project root
        project_root = Path(__file__).resolve().parents[2]
        languages_file = project_root / "config" / "languages.json"
        if languages_file.exists():
            data = json.loads(languages_file.read_text(encoding="utf-8"))
            config = LanguageConfig(data)
            name = config.get_language_name(code)
            return name if name else code
    except Exception:
        pass
    return code or "Original"


def _resolve_source_label(batch_root: Path, rollup: Dict[str, Any]) -> str:
    """Prefer rollup original_language, then manifest original_language name/code if present."""
    # First check the rollup data (which already has resolved source language)
    rollup_src = rollup.get("original_language") or {}
    if isinstance(rollup_src, dict):
        name = (rollup_src.get("name") or "").strip()
        code = (rollup_src.get("code") or "").strip()
        if name:
            return name
        if code:
            return _lang_label(code)

    # Fall back to manifest.json if rollup doesn't have source language
    manifest = batch_root / "manifest.json"
    if manifest.exists():
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            ol = data.get("original_language") or {}
            if isinstance(ol, dict):
                name = (ol.get("name") or "").strip()
                code = (ol.get("code") or "").strip()
                if name:
                    return name
                if code:
                    return _lang_label(code)
        except (json.JSONDecodeError, KeyError, TypeError):
            # Log the specific error for debugging
            pass
    return "Original language"


def _status_label(per_file: Dict[str, Any]) -> str:
    """
    Ready? depends ONLY on ERROR categories present in per_file['issues'] and parity/timing.
    """
    issues = per_file.get("issues", {}) or {}
    error_total = 0
    error_total += len(issues.get("untranslated_after_dnt", []) or [])
    error_total += len(issues.get("missing_translation", []) or [])
    if issues.get("timing_fail"):
        error_total += 1
    if not per_file.get("metrics", {}).get("parity_ok", True):
        error_total += 1
    return "✅ Ready" if error_total == 0 else "❌ Not ready"


def _collect_issue_count(file_entry: Dict[str, Any]) -> int:
    issues = file_entry.get("issues", {})
    n = 0
    n += len(issues.get("untranslated_after_dnt", []))
    n += len(issues.get("missing_translation", []))
    n += 1 if issues.get("timing_fail") else 0
    if not file_entry.get("metrics", {}).get("parity_ok", True):
        n += 1
    return n


def _write_json_report(batch_root: Path, rollup: Dict[str, Any], logger) -> Path:
    """
    Write eval_report.json with structured data including coverage information.

    Args:
        batch_root: Path to the batch directory
        rollup: Evaluation rollup data
        logger: Logger instance

    Returns:
        Path to the written JSON report
    """
    log = logger.getChild("report.json")

    # Create the JSON report with all required fields
    json_report = {
        "batch_label": rollup.get("batch_label"),
        "config_source": rollup.get("config_source", "unknown"),
        "dnt_coverage": rollup.get("dnt_coverage", "unknown"),
        "termbase_coverage": rollup.get("termbase_coverage", "unknown"),
        "termbase_entry_counts": rollup.get("termbase_entry_counts", {}),
        "original_language": rollup.get("original_language", {}),
        "languages": rollup.get("languages", {}),
        "timestamp": rollup.get("timestamp", "unknown"),
        "version": rollup.get("version", "unknown"),
    }

    # Write to artifacts directory
    artifacts_dir = batch_root / "artifacts"
    artifacts_dir.mkdir(exist_ok=True)

    json_path = artifacts_dir / "eval_report.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_report, f, ensure_ascii=False, indent=2)

    log.info("Wrote eval_report.json", extra={"path": str(json_path)})
    return json_path


def write_batch_report(batch_root: Path, rollup: Dict[str, Any], logger) -> Path:
    """
    Write eval_report.md with a clear intro + full punch list. Summary count equals rendered items.
    """
    log = logger.getChild("report")
    batch_root = Path(batch_root)
    batch = rollup.get("batch_label", batch_root.name)
    langs = rollup.get("languages", {})
    src = rollup.get("original_language") or {}

    out = []
    src_label = _resolve_source_label(batch_root, rollup)

    # Render header
    out.append("# Evaluation Report\n")

    # Header/intro now that we know total_items
    intro = [f"*Detected source language:* **{src_label}**"]

    # Add coverage information from v1.0 evaluation policy
    config_source = rollup.get("config_source", "unknown")
    dnt_coverage = rollup.get("dnt_coverage", "unknown")
    termbase_coverage = rollup.get("termbase_coverage", "unknown")

    intro.append(f"*Configuration source:* **{config_source}**")
    intro.append(f"*DNT coverage:* **{dnt_coverage}**")
    intro.append(f"*Termbase coverage:* **{termbase_coverage}**")

    # Add termbase entry counts if available
    termbase_counts = rollup.get("termbase_entry_counts", {})
    if termbase_counts:
        count_details = [f"{lang}: {count}" for lang, count in termbase_counts.items()]
        intro.append(f"*Termbase entries:* {', '.join(count_details)}")

    out.insert(1, "\n\n".join(intro) + "\n")

    # Add consolidated punch list using new function
    out.append(render_consolidated_punchlist(langs, batch_root=batch_root))
    out.append("\n")

    # Roll-up table
    out.append("\n---\n")
    out.append(
        "## Language Roll-Up\n\n| Language | File | Ready? | Notes |\n|---|---|---|---|"
    )
    for lang, entry in langs.items():
        for f in entry.get("files", []):
            notes = []
            if f.get("issues", {}).get("untranslated_after_dnt"):
                notes.append(
                    f"untranslated:{len(f['issues']['untranslated_after_dnt'])}"
                )
            if f.get("issues", {}).get("missing_translation"):
                notes.append(f"missing:{len(f['issues']['missing_translation'])}")
            if f.get("issues", {}).get("timing_fail"):
                notes.append("timing")
            if not f.get("metrics", {}).get("parity_ok", True):
                notes.append("parity")
            out.append(
                f"| {lang} | {f.get('target_file')} | {_status_label(f)} | {', '.join(notes) or '—'} |"
            )

    # Add detailed issue sections using new function
    out.append("\n")
    out.append(render_issue_sections(langs, batch_root=batch_root))
    out.append("\n")

    # Per-language key metrics (brief)
    out.append("\n---\n## Per-Language Details (key metrics)")
    for lang, entry in langs.items():
        for f in entry.get("files", []):
            m = f.get("metrics", {})
            out.append(f"\n### {lang} — {f.get('target_file')}")
            out.append(
                f"- Cue parity: {'OK' if m.get('parity_ok', True) else 'Mismatch'}"
            )
            out.append(
                f"- Timing Δstart median/p95={m.get('med_ds_ms',0):.0f}/{m.get('p95_ds_ms',0):.0f}ms; Δend median/p95={m.get('med_de_ms',0):.0f}/{m.get('p95_de_ms',0):.0f}ms"
            )
            out.append(
                f"- CPS caps used: soft={m.get('cps_soft')} hard={m.get('cps_hard')}\n"
            )

    # Glossary
    out.append("\n---\n## Glossary")
    out.append("\n")
    out.append(
        "- **Cue (subtitle):** one numbered subtitle block with in/out times and text."
    )
    out.append('- **DNT:** "Do Not Translate" — protected names/codes to keep as-is.')
    out.append("- **Termbase:** approved glossary mapping original → target terms.")
    out.append(
        "- **Cue parity:** target must have the same number of cues as the original."
    )
    out.append(
        "- **Timing drift:** how far target cue times deviate from the original."
    )
    out.append(
        "- **CPS:** characters per second; readability guideline, not a hard fail unless rubric says so."
    )

    out_path = batch_root / "eval_report.md"
    out_path.write_text("\n".join(out) + "\n", encoding="utf-8")
    log.info("Wrote eval_report.md", extra={"path": str(out_path)})

    # Also write JSON report with coverage information
    try:
        _write_json_report(batch_root, rollup, logger)
    except Exception as e:
        log.warning(f"Failed to write JSON report: {e}")

    return out_path
