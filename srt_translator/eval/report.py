# srt_translator/eval/report.py
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

from srt_translator.core.config.language_config import LanguageConfig

# v1.0: reporter is JSON-only. No SRT parsing/imports here.


def _load_ai_config_from_artifacts(batch_root: Path) -> dict:
    """Load ai_config.json from artifacts directory with strict validation."""
    ai_config_path = batch_root / "artifacts" / "ai_config.json"
    if not ai_config_path.exists():
        raise ValueError(
            f"ai_config.json must be located alongside eval_report.json; not found at: {ai_config_path}"
        )

    try:
        return json.loads(ai_config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {ai_config_path}: {e}") from e


def _compute_status_from_rollup(rollup: Dict[str, Any]) -> str:
    """Compute status based on evaluation results: critical, warning, or ready."""
    # Check for critical issues
    languages = rollup.get("languages", {})

    for _lang_code, lang_data in languages.items():
        if not isinstance(lang_data, dict):
            continue

        for file_data in lang_data.get("files", []):
            if not isinstance(file_data, dict):
                continue

            issues = file_data.get("issues", {})
            if not isinstance(issues, dict):
                continue

            # Critical: DNT violations, termbase violations, missing translations, timing fails
            if (
                len(issues.get("untranslated_after_dnt", [])) > 0
                or len(issues.get("missing_translation", [])) > 0
                or issues.get("timing_fail", False)
            ):
                return "critical"

    # Check for warnings (soft CPS overage, timing drift)
    # For now, assume no warnings if no critical issues
    # TODO: Implement warning detection based on soft thresholds
    return "ready"


def _compute_warnings_from_rollup(rollup: Dict[str, Any]) -> int:
    """Compute total warning count from evaluation results."""
    # For now, return 0 - warnings will be implemented in future iterations
    # This maintains the interface while keeping the change minimal
    return 0


def _kpis_from_rollup(rollup: Dict[str, Any], ai_config: dict) -> dict:
    """Compute KPI values for display from rollup and ai_config."""
    # Get target languages from ai_config
    target_languages = ai_config.get("target_languages", {})
    if not target_languages:
        # Fallback to target_language_codes if available
        target_codes = ai_config.get("target_language_codes", [])
        target_languages = {code: code for code in target_codes}

    # Compute termbase coverage
    termbase = ai_config.get("termbase", {})
    languages_with_termbase = len([lang for lang, entries in termbase.items() if entries])
    total_languages = len(target_languages)

    if total_languages == 0:
        termbase_coverage = "0/0 languages"
    else:
        termbase_coverage = f"{languages_with_termbase}/{total_languages} languages"

    # Compute DNT coverage
    dnt_terms = ai_config.get("dnt_terms", [])
    dnt_coverage = "present" if len(dnt_terms) > 0 else "missing"

    # Get source language
    source_language = rollup.get("original_language", {}).get("detected", "")
    if not source_language:
        # Try to get from ai_config
        source_lang_info = ai_config.get("source_language", {})
        if isinstance(source_lang_info, dict):
            source_language = source_lang_info.get("normalized_name") or source_lang_info.get(
                "name", ""
            )

    # Count total files and languages
    languages = rollup.get("languages", {})
    files_total = sum(len(lang_data.get("files", [])) for lang_data in languages.values())
    languages_total = len(languages)

    # Count total issues
    issues_total = 0
    for lang_data in languages.values():
        for file_data in lang_data.get("files", []):
            issues = file_data.get("issues", {})
            issues_total += len(issues.get("untranslated_after_dnt", []))
            issues_total += len(issues.get("missing_translation", []))
            if issues.get("timing_fail"):
                issues_total += 1

    return {
        "files_total": files_total,
        "languages_total": languages_total,
        "issues_total": issues_total,
        "warnings_total": _compute_warnings_from_rollup(rollup),
        "source_language": source_language or "Unknown",
        "dnt_coverage": dnt_coverage,
        "termbase_coverage": termbase_coverage,
    }


def _what_to_do_next_from_status(status: str) -> list[str]:
    """Generate what to do next steps based on status."""
    if status == "ready":
        return [
            "Spot-check a few captions for tone and brand terms.",
            "Publish when satisfied.",
        ]
    elif status == "warning":
        return [
            "Scan warnings (timing drift, high CPS) and tweak a few problem captions.",
            "Re-export and spot-check brand terms.",
            "Publish when satisfied.",
        ]
    else:  # critical
        return [
            "Resolve DNT or termbase violations in the listed files.",
            "Fix cue parity mismatches or missing translations.",
            "Re-run evaluation and confirm 'Ready to publish'.",
        ]


# Display blanks as real empty lines; avoid glyphs like "(none)" that look odd to users.
EMPTY_CUE_PLACEHOLDER = ""


def _render_context_pairs(pairs: list[tuple[int, str]]) -> str:
    """
    Given [(index, text), ...] pairs from the evaluator, build a fenced code block.
    """
    if not pairs:
        return "```\n(context unavailable)\n```"
    lines = []
    for idx, txt in pairs:
        lines.append(f"{idx}: {txt or EMPTY_CUE_PLACEHOLDER}")
    return "```\n" + "\n".join(lines) + "\n```"


def _context_blocks_for_issue(
    batch_root: Path, lang: str, file_entry: dict, issue: dict, source_lang_name: str
) -> tuple[str, str, str]:
    """
    Returns (target_block, source_block, notice) using *embedded* context from the evaluator.
    Reporter does not read SRT files in v1.0.
    """
    ctx = issue.get("context") or {}
    tgt_pairs = ctx.get("target") or []
    src_pairs = ctx.get("source") or []
    if not (tgt_pairs or src_pairs):
        return (
            "```\n(context unavailable)\n```",
            "```\n(context unavailable)\n```",
            "Context unavailable (no embedded context).",
        )
    return _render_context_pairs(tgt_pairs), _render_context_pairs(src_pairs), ""


def _source_language_name(batch_root: Path) -> str:
    """
    Resolve a friendly source language name from ai_config.json; fallback to 'English'.
    Uses _lang_label(code) if available, then strips trailing ' (xx)'.
    """
    cfg_path = Path(batch_root) / "ai_config.json"
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    except Exception:
        cfg = {}
    # explicit friendly name wins
    for key in ("source_language_name", "source_lang_name"):
        v = cfg.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    # else try codes we commonly store
    code = (
        cfg.get("source_language_code")
        or cfg.get("source_lang")
        or (cfg.get("original_language") or {}).get("code")
        or "en"
    )
    try:
        label = _lang_label(code)  # e.g., 'English (en)'
        name = re.sub(r"\s*\([^)]+\)\s*$", "", label).strip() or "English"
        return name
    except Exception:
        return "English"


# This function is no longer needed since we use eval_parse_srt directly


# This function is no longer needed since we directly iterate over the languages structure


def render_consolidated_punchlist(
    languages: Dict, *, batch_root: Path, source_lang_name: str
) -> str:
    """
    Top-of-report consolidated list of ERROR issues across all files.
    Includes a contextual "Suggested check" (prev2/current/next2) block.
    """
    error_issues: List[dict] = []
    for lang, entry in languages.items():
        files = entry.get("files", [])
        for f in files:
            issues = f.get("issues", {}) or {}
            missing = issues.get("missing_translation", []) or []
            un = issues.get("untranslated_after_dnt", []) or []
            errs = missing + un
            if not errs:
                continue
            src_rel = f.get("source_rel", "")
            tgt_rel = f.get("target_rel", "")
            file_name = f.get("target_file", f.get("file_name", ""))
            for issue in errs:
                # Inline copy with language & resolvable paths
                i = dict(issue)
                i["_lang"] = lang
                i["_file"] = file_name
                i["source_rel"] = src_rel
                i["target_rel"] = tgt_rel
                error_issues.append(i)

    if not error_issues:
        return "Everything looks great. Your translated files are **ready for use**."

    total = len(error_issues)
    out: List[str] = []
    out.append(
        f"Some files need attention. Below is a consolidated punch list of **{total}** issue(s). "
        "For each cue, we show the original and the translation with a contextual suggested check.\n"
    )
    for issue in error_issues:
        lang = issue["_lang"]
        file_name = issue["_file"]
        cue = issue.get("cue") or issue.get("idx")
        orig = issue.get("original") or issue.get("src") or ""
        tgt = issue.get("target") or issue.get("tgt") or ""
        out.append(f"### {_lang_label(lang)}\n")
        out.append(f"#### {file_name}")
        out.append(f"- cue {cue}:\n  `Original: {orig}`\n  `{_lang_label(lang)}: {tgt}`\n")

        # Context window (prev2/current/next2), boundary-safe
        try:
            tgt_block, src_block, notice = _context_blocks_for_issue(
                batch_root=batch_root,
                lang=lang,
                file_entry=f,
                issue=issue,
                source_lang_name=source_lang_name,
            )
            if tgt_block and src_block:
                # Friendly source language name is already shown at top; keep this simple
                out.append(
                    "\n_Suggested check:_ Copy the **Target context** below into your AI assistant "
                    "and ask for a translation into **the source language**, then compare it to the **Source context**.\n"
                )
                out.append("**Target context (prev 2 / current / next 2):**")
                out.append("```")
                out.append(tgt_block)
                out.append("```")
                out.append("**Source context (prev 2 / current / next 2):**")
                out.append("```")
                out.append(src_block)
                out.append("```")
        except Exception as e:
            # Never let context rendering break the report
            out.append(f"[Warning: Failed to render context blocks: {e}]")

        out.append("")  # spacing
    return "\n".join(out)


def render_issue_sections(languages: Dict, *, batch_root: Path, source_lang_name: str) -> str:
    """
    Render ERROR issues grouped by language/file with contextual "Suggested check".
    INFO/WARN are intentionally omitted from Markdown.
    """
    out: List[str] = []
    for lang, entry in languages.items():
        out.append(f"## {_lang_label(lang)}\n")
        files = entry.get("files", [])
        for f in files:
            issues = f.get("issues", {}) or {}
            missing = issues.get("missing_translation", []) or []
            un = issues.get("untranslated_after_dnt", []) or []
            errs = missing + un
            if not errs:
                continue
            file_name = f.get("target_file", f.get("file_name", "—"))
            out.append(f"### {file_name}")
            out.append("**Blocking issues**\n")
            for issue in errs:
                cue = issue.get("cue") or issue.get("idx")
                orig = issue.get("original") or issue.get("src") or ""
                tgt = issue.get("target") or issue.get("tgt") or ""
                out.append(f"- cue {cue}:\n  `Original: {orig}`\n  `{_lang_label(lang)}: {tgt}`\n")
                try:
                    tgt_block, src_block, notice = _context_blocks_for_issue(
                        batch_root=batch_root,
                        lang=lang,
                        file_entry=f,
                        issue=issue,
                        source_lang_name=source_lang_name,
                    )
                    if tgt_block and src_block:
                        out.append(
                            "\n_Suggested check:_ Copy the **Target context** below into your AI assistant "
                            "and ask for a translation into **the source language**, then compare it to the **Source context**.\n"
                        )
                        out.append("**Target context (prev 2 / current / next 2):**")
                        out.append("```")
                        out.append(tgt_block)
                        out.append("```")
                        out.append("**Source context (prev 2 / current / next 2):**")
                        out.append("```")
                        out.append(src_block)
                        out.append("```")
                except Exception as e:
                    out.append(f"[Warning: Failed to render context blocks: {e}]")
            out.append("")  # spacing
    return "\n".join(out)


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
    except Exception as e:
        # Fallback to code if language lookup fails
        print(f"Warning: Failed to load language info for {code}: {e}")  # noqa: T201
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
    except Exception as e:
        # Fallback to code if language lookup fails
        print(f"Warning: Failed to load language name for {code}: {e}")  # noqa: T201
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
    Write eval_report.json with strict EvalReportV1 format.

    Args:
        batch_root: Path to the batch directory
        rollup: Evaluation rollup data
        logger: Logger instance

    Returns:
        Path to the written JSON report
    """
    log = logger.getChild("report.json")

    # Extract per-language file counts from rollup
    per_language_file_counts = {}
    languages = rollup.get("languages", {})

    for lang_code, lang_data in languages.items():
        per_language_file_counts[lang_code] = {}
        for file_data in lang_data.get("files", []):
            file_path = file_data.get("target_file", "")
            issues = file_data.get("issues", {})

            # Extract issue counts
            missing_count = len(issues.get("missing_translation", []))
            untrans_dnt_count = len(issues.get("untranslated_after_dnt", []))
            timing_fail_count = 1 if issues.get("timing_fail") else 0

            per_language_file_counts[lang_code][file_path] = {
                "missing_translation": missing_count,
                "untranslated_after_dnt": untrans_dnt_count,
                "timing_fail": timing_fail_count,
            }

    # Get source language
    source_language = rollup.get("original_language", {}).get("detected", "")

    # Build strict EvalReportV1
    from srt_translator.eval.assemble import build_eval_report_v1

    try:
        json_report = build_eval_report_v1(
            per_language_file_counts=per_language_file_counts,
            source_language=source_language,
        )

        # Write to artifacts directory
        artifacts_dir = batch_root / "artifacts"
        artifacts_dir.mkdir(exist_ok=True)

        json_path = artifacts_dir / "eval_report.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_report, f, ensure_ascii=False, indent=2)

        log.info(
            "Wrote strict eval_report.json (v1): files=%d, langs=%d, issues=%d",
            json_report["files_total"],
            json_report["languages_total"],
            json_report["issues_total"],
        )
        return json_path

    except Exception as e:
        log.error(f"Failed to build strict eval_report.json: {e}")
        raise


def write_batch_report(batch_root: Path, rollup: Dict[str, Any], logger) -> Path:
    """
    Write eval_report.md with unified top sections: banner, next steps, and KPIs.
    """
    log = logger.getChild("report")
    batch_root = Path(batch_root)
    langs = rollup.get("languages", {})

    out = []

    # Load ai_config.json from artifacts directory
    try:
        ai_config = _load_ai_config_from_artifacts(batch_root)
    except ValueError as e:
        log.error(f"Failed to load ai_config.json: {e}")
        raise

    # Compute status and KPIs
    status = _compute_status_from_rollup(rollup)
    kpis = _kpis_from_rollup(rollup, ai_config)
    what_to_do = _what_to_do_next_from_status(status)

    # Generate banner text based on status
    if status == "ready":
        banner_emoji = "✅"
        banner_text = "Everything looks great. Your translated files are ready to use."
    elif status == "warning":
        banner_emoji = "⚠️"
        banner_text = (
            "Looks good overall. Address the items below to improve quality before publishing."
        )
    else:  # critical
        banner_emoji = "❌"
        banner_text = (
            "We found issues that will degrade quality. Fix the items below before publishing."
        )

    # Render header
    out.append("# Evaluation Report\n")

    # Publish readiness banner
    out.append(f"## {banner_emoji} {banner_text}\n")

    # What to do next
    out.append("## What to do next\n")
    for i, item in enumerate(what_to_do, 1):
        out.append(f"{i}. {item}")
    out.append("")

    # KPIs
    out.append("## KPIs\n")
    out.append(f"- **Files total:** {kpis['files_total']}")
    out.append(f"- **Languages:** {kpis['languages_total']}")
    out.append(f"- **Issues (critical):** {kpis['issues_total']}")
    out.append(f"- **Warnings (non-critical):** {kpis['warnings_total']}")
    out.append(f"- **Detected source language:** {kpis['source_language']}")
    out.append(f"- **DNT coverage:** {kpis['dnt_coverage']}")
    out.append(f"- **Termbase coverage:** {kpis['termbase_coverage']}")
    out.append("")

    # Add consolidated punch list using new function
    src_label = _resolve_source_label(batch_root, rollup)
    out.append(
        render_consolidated_punchlist(langs, batch_root=batch_root, source_lang_name=src_label)
    )
    out.append("\n")

    # Roll-up table
    out.append("\n---\n")
    out.append("## Language Roll-Up\n\n| Language | File | Ready? | Notes |\n|---|---|---|---|")
    for lang, entry in langs.items():
        for f in entry.get("files", []):
            notes = []
            if f.get("issues", {}).get("untranslated_after_dnt"):
                notes.append(f"untranslated:{len(f['issues']['untranslated_after_dnt'])}")
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
    out.append(render_issue_sections(langs, batch_root=batch_root, source_lang_name=src_label))
    out.append("\n")

    # Per-language key metrics (brief)
    out.append("\n---\n## Per-Language Details (key metrics)")
    for lang, entry in langs.items():
        for f in entry.get("files", []):
            m = f.get("metrics", {})
            out.append(f"\n### {lang} — {f.get('target_file')}")
            out.append(f"- Cue parity: {'OK' if m.get('parity_ok', True) else 'Mismatch'}")
            out.append(
                f"- Timing Δstart median/p95={m.get('med_ds_ms', 0):.0f}/{m.get('p95_ds_ms', 0):.0f}ms; Δend median/p95={m.get('med_de_ms', 0):.0f}/{m.get('p95_de_ms', 0):.0f}ms"
            )
            out.append(f"- CPS caps used: soft={m.get('cps_soft')} hard={m.get('cps_hard')}\n")

    # Glossary
    out.append("\n---\n## Glossary")
    out.append("\n")
    out.append("- **Cue (subtitle):** one numbered subtitle block with in/out times and text.")
    out.append('- **DNT:** "Do Not Translate" — protected names/codes to keep as-is.')
    out.append("- **Termbase:** approved glossary mapping original → target terms.")
    out.append("- **Cue parity:** target must have the same number of cues as the original.")
    out.append("- **Timing drift:** how far target cue times deviate from the original.")
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
