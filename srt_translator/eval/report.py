# srt_translator/eval/report.py
from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, Tuple
import json
from srt_translator.core.config.language_config import LanguageConfig


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
    st = (per_file.get("status") or "").upper()
    if st.startswith("PASS"):
        return "✅ Ready"
    if "WARN" in st or st.startswith("READY WITH"):
        return "⚠️ Ready w/ warnings"
    return "❌ Not ready"


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
        "version": rollup.get("version", "unknown")
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
    total_items = 0

    # Render header
    out.append("# Evaluation Report\n")

    # Punch list per language/file (only sections that have issues)
    for lang, entry in langs.items():
        for f in entry.get("files", []):
            issues = f.get("issues", {})
            show = bool(
                issues.get("untranslated_after_dnt")
                or issues.get("missing_translation")
                or not f.get("metrics", {}).get("parity_ok", True)
                or issues.get("timing_fail")
            )
            if not show:
                continue
            out.append(f"## {_lang_label(lang)} ({lang})\n")
            out.append(f"### {f.get('target_file')}")

            # Untranslated
            untranslated_issues = issues.get("untranslated_after_dnt", [])
            if untranslated_issues:
                out.append(
                    "**Untranslated after DNT removal** — identical to the original language once protected terms are removed."
                )
                for untranslated_issue in untranslated_issues:  # FULL list, no cap
                    out.append(
                        f"- cue {untranslated_issue['cue']}:\n  `Original: {untranslated_issue['original']}`\n  `{_lang_label(lang)}: {untranslated_issue['target']}`"
                    )
                out.append(
                    "_Suggested fix:_ translate the sentence fully while preserving protected terms (DNT). Add missing items to DNT/Termbase if needed.\n"
                )
                total_items += len(untranslated_issues)

            # Missing translation
            missing_translation_issues = issues.get("missing_translation", [])
            if missing_translation_issues:
                out.append(
                    "**Missing translation** — this subtitle has no translated text.\n"
                )
                for missing_issue in missing_translation_issues:
                    out.append(
                        f"- cue {missing_issue['idx']}:\n  `Original: {missing_issue['src']}`\n  `{_lang_label(lang)}: `\n"
                    )
                out.append(
                    "_Suggested fix:_ translate this subtitle. You can copy the original into your AI assistant and ask for a translation into the target language, then paste it back into the SRT.\n"
                )
                total_items += len(missing_translation_issues)

            # Parity
            if not f.get("metrics", {}).get("parity_ok", True):
                out.append(
                    "**Cue parity** — counts differ between original and translation."
                )
                out.append(
                    "_Suggested fix:_ align cue splits/merges to match counts.\n"
                )
            # Timing drift section (only if there are drift findings or rubric says to always show)
            drift = f.get("metrics", {})
            if issues.get("timing_fail"):
                out.append(
                    f"**Timing drift** — review per-cue timing deltas in artifacts if requested by reviewers.\n"
                )

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
    
    if total_items == 0:
        intro.append(
            "Everything looks great. Your translated files are **ready for use**."
        )
    else:
        intro.append(
            f"Some files need attention. Below is a consolidated punch list of **{total_items}** issue(s). For each cue, we show the original and the translation with a suggested fix."
        )
    out.insert(1, "\n\n".join(intro) + "\n")

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
            if f.get("issues", {}).get("timing_fail"):
                notes.append("timing")
            if not f.get("metrics", {}).get("parity_ok", True):
                notes.append("parity")
            out.append(
                f"| {lang} | {f.get('target_file')} | {_status_label(f)} | {', '.join(notes) or '—'} |"
            )

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
