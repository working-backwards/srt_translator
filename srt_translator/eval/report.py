# srt_translator/eval/report.py
from __future__ import annotations

import json
import logging
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
    cfg_path = Path(batch_root) / "artifacts" / "ai_config.json"
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

    This function now reads from report_v1.json instead of separate files.
    """
    log = logger.getChild("report")
    batch_root = Path(batch_root)

    out = []

    # Load report_v1.json from artifacts directory
    report_v1_path = batch_root / "artifacts" / "report_v1.json"
    if not report_v1_path.exists():
        log.error(f"report_v1.json not found at: {report_v1_path}")
        raise FileNotFoundError(f"report_v1.json not found at: {report_v1_path}")

    try:
        report_data = json.loads(report_v1_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        log.error(f"Invalid JSON in {report_v1_path}: {e}")
        raise ValueError(f"Invalid JSON in {report_v1_path}: {e}") from e

    # Extract data from compiled report
    decision = report_data.get("decision", {})
    kpis = report_data.get("kpis", {})
    file_status = report_data.get("file_status", [])
    what_to_do = decision.get("what_to_do_next", [])

    # Extract banner from compiled report
    banner_text = decision.get("banner_text", "")
    # Extract emoji from banner text
    if banner_text.startswith("✅"):
        banner_emoji = "✅"
        banner_text = banner_text[2:].strip()
    elif banner_text.startswith("⚠️"):
        banner_emoji = "⚠️"
        banner_text = banner_text[2:].strip()
    elif banner_text.startswith("❌"):
        banner_emoji = "❌"
        banner_text = banner_text[2:].strip()
    else:
        banner_emoji = "❓"

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
    out.append(f"- **Files:** {kpis.get('Files', 'N/A')}")
    out.append(f"- **Languages:** {kpis.get('Languages', 'N/A')}")
    out.append(f"- **Errors:** {kpis.get('Errors', 'N/A')}")
    out.append(f"- **Warnings:** {kpis.get('Warnings', 'N/A')}")
    out.append(f"- **DNT coverage:** {kpis.get('DNT coverage', 'N/A')}")
    out.append(f"- **Termbase coverage:** {kpis.get('Termbase coverage', 'N/A')}")
    out.append(f"- **Parity:** {kpis.get('Parity', 'N/A')}")
    out.append("")

    # File Status
    out.append("## File Status\n")
    if file_status:
        for file_info in file_status:
            file_path = file_info.get("file_path", "Unknown")
            status = file_info.get("status", "UNKNOWN")

            # Map status to emoji
            if status == "READY":
                emoji = "✅"
            elif status == "REVIEW":
                emoji = "⚠️"
            elif status == "FIX":
                emoji = "❌"
            else:
                emoji = "❓"

            out.append(f"- {emoji} **{file_path}** ({status})")
        out.append("")
    else:
        out.append("No files processed.\n")

    # Punch List
    sections = report_data.get("sections", {})
    errors = sections.get("errors", [])
    warnings = sections.get("warnings", [])

    if errors:
        out.append("## ❌ Critical Issues\n")
        for error in errors:
            out.append(f"### {error.get('filename', 'Unknown')}: {error.get('title', 'Error')}")
            out.append(f"**Why it matters:** {error.get('why_it_matters', '')}")
            out.append(f"**Suggested fix:** {error.get('suggested_fix', '')}")
            out.append(f"**Ask an AI:** {error.get('ask_ai_prompt', '')}")
            out.append("")

    if warnings:
        out.append("## ⚠️ Warnings\n")
        for warning in warnings:
            out.append(
                f"### {warning.get('filename', 'Unknown')}: {warning.get('title', 'Warning')}"
            )
            out.append(f"**Why it matters:** {warning.get('why_it_matters', '')}")
            out.append(f"**Suggested fix:** {warning.get('suggested_fix', '')}")
            out.append(f"**Ask an AI:** {warning.get('ask_ai_prompt', '')}")
            out.append("")

    if not errors and not warnings:
        out.append("## ✅ No Issues Found\n")
        out.append("All files passed evaluation with no errors or warnings.\n")

    # DNT Terms
    dnt_terms = report_data.get("lexicons", {}).get("dnt_terms", [])
    if dnt_terms:
        out.append("## Do-Not-Translate Terms\n")
        for term in dnt_terms:
            out.append(f"- `{term}`")
        out.append("")

    # Termbase
    termbase = report_data.get("lexicons", {}).get("termbase", {})
    if termbase:
        out.append("## Termbase\n")
        for lang_name, terms in termbase.items():
            if terms:
                out.append(f"### {lang_name}\n")
                for term in terms:
                    source = term.get("source", "")
                    preferred = term.get("preferred", "")
                    out.append(f"- `{source}` → `{preferred}`")
                out.append("")

    # TODO: Language Roll-Up will be added in Packet 6
    # out.append("\n---\n")
    # out.append("## Language Roll-Up\n\n| Language | File | Ready? | Notes |\n|---|---|---|---|")
    # for lang, entry in langs.items():
    #     for f in entry.get("files", []):
    #         notes = []
    #         if f.get("issues", {}).get("untranslated_after_dnt"):
    #             notes.append(f"untranslated:{len(f['issues']['untranslated_after_dnt'])}")
    #         if f.get("issues", {}).get("missing_translation"):
    #             notes.append(f"missing:{len(f['issues']['missing_translation'])}")
    #         if f.get("issues", {}).get("timing_fail"):
    #             notes.append("timing")
    #         if not f.get("metrics", {}).get("parity_ok", True):
    #             notes.append("parity")
    #         out.append(
    #             f"| {lang} | {f.get('target_file')} | {_status_label(f)} | {', '.join(notes) or '—'} |"
    #         )

    # # Add detailed issue sections using new function
    # out.append("\n")
    # out.append(render_issue_sections(langs, batch_root=batch_root, source_lang_name=src_label))
    # out.append("\n")

    # # Per-language key metrics (brief)
    # out.append("\n---\n## Per-Language Details (key metrics)")
    # for lang, entry in langs.items():
    #     for f in entry.get("files", []):
    #         m = f.get("metrics", {})
    #         out.append(f"\n### {lang} — {f.get('target_file')}")
    #         out.append(f"- Cue parity: {'OK' if m.get('parity_ok', True) else 'Mismatch'}")
    #         out.append(
    #             f"- Timing Δstart median/p95={m.get('med_ds_ms', 0):.0f}/{m.get('p95_ds_ms', 0):.0f}ms; Δend median/p95={m.get('med_de_ms', 0):.0f}/{m.get('p95_de_ms', 0):.0f}ms"
    #         )
    #         out.append(f"- CPS caps used: soft={m.get('cps_soft')} hard={m.get('cps_hard')}\n")

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


def write_evaluator_json(artifacts_dir: Path, rollup: dict) -> Path:
    """Write eval_report.json to artifacts directory."""
    logger = logging.getLogger(__name__)

    # Ensure artifacts directory exists
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    # Write eval_report.json using existing function
    json_path = _write_json_report(artifacts_dir.parent, rollup, logger)

    logger.info(f"Wrote eval_report.json: {json_path}")
    return json_path


def render_markdown(artifacts_dir: Path, report_json: Path) -> Path:
    """Render markdown report from report_v1.json."""
    logger = logging.getLogger(__name__)

    # Load report_v1.json
    try:
        with open(report_json, "r", encoding="utf-8") as f:
            report_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        raise ValueError(f"Failed to load report_v1.json: {e}") from e

    # Generate markdown content
    out = []

    # Extract data from compiled report
    decision = report_data.get("decision", {})
    kpis = report_data.get("kpis", {})
    file_status = report_data.get("file_status", [])
    what_to_do = decision.get("what_to_do_next", [])

    # Extract banner from compiled report
    banner_text = decision.get("banner_text", "")
    # Extract emoji from banner text
    if banner_text.startswith("✅"):
        banner_emoji = "✅"
        banner_text = banner_text[2:].strip()
    elif banner_text.startswith("⚠️"):
        banner_emoji = "⚠️"
        banner_text = banner_text[2:].strip()
    elif banner_text.startswith("❌"):
        banner_emoji = "❌"
        banner_text = banner_text[2:].strip()
    else:
        banner_emoji = "❓"

    # Render header
    out.append("# Evaluation Report\n")

    # Publish readiness banner
    out.append(f"## {banner_emoji} {banner_text}\n")

    # What to do next
    if what_to_do:
        out.append("## What to do next\n")
        for i, item in enumerate(what_to_do, 1):
            out.append(f"{i}. {item}")
        out.append("")

    # KPIs
    out.append("## KPIs\n")
    for key, value in kpis.items():
        out.append(f"- **{key}:** {value}")
    out.append("")

    # File Status
    out.append("## File Status\n")
    if file_status:
        for file_info in file_status:
            file_path = file_info.get("file_path", "Unknown")
            status = file_info.get("status", "UNKNOWN")

            # Map status to emoji
            if status == "READY":
                emoji = "✅"
            elif status == "REVIEW":
                emoji = "⚠️"
            elif status == "FIX":
                emoji = "❌"
            else:
                emoji = "❓"

            out.append(f"- {emoji} **{file_path}** ({status})")
        out.append("")
    else:
        out.append("No files processed.\n")

    # Punch List
    sections = report_data.get("sections", {})
    errors = sections.get("errors", [])
    warnings = sections.get("warnings", [])

    if errors:
        out.append("## ❌ Critical Issues\n")
        for error in errors:
            out.append(f"### {error.get('filename', 'Unknown')}: {error.get('title', 'Error')}")
            out.append(f"**Why it matters:** {error.get('why_it_matters', '')}")
            out.append(f"**Suggested fix:** {error.get('suggested_fix', '')}")
            out.append(f"**Ask an AI:** {error.get('ask_ai_prompt', '')}")
            out.append("")

    if warnings:
        out.append("## ⚠️ Warnings\n")
        for warning in warnings:
            out.append(
                f"### {warning.get('filename', 'Unknown')}: {warning.get('title', 'Warning')}"
            )
            out.append(f"**Why it matters:** {warning.get('why_it_matters', '')}")
            out.append(f"**Suggested fix:** {warning.get('suggested_fix', '')}")
            out.append(f"**Ask an AI:** {warning.get('ask_ai_prompt', '')}")
            out.append("")

    if not errors and not warnings:
        out.append("## ✅ No Issues Found\n")
        out.append("All files passed evaluation with no errors or warnings.\n")

    # DNT Terms
    dnt_terms = report_data.get("lexicons", {}).get("dnt_terms", [])
    if dnt_terms:
        out.append("## Do-Not-Translate Terms\n")
        for term in dnt_terms:
            out.append(f"- `{term}`")
        out.append("")

    # Termbase
    termbase = report_data.get("lexicons", {}).get("termbase", {})
    if termbase:
        out.append("## Termbase\n")
        for lang_name, terms in termbase.items():
            if terms:
                out.append(f"### {lang_name}\n")
                for term in terms:
                    source = term.get("source", "")
                    preferred = term.get("preferred", "")
                    out.append(f"- `{source}` → `{preferred}`")
                out.append("")

    # Write markdown file
    md_path = artifacts_dir / "eval_report.md"
    md_path.write_text("\n".join(out) + "\n", encoding="utf-8")
    logger.info(f"Wrote eval_report.md: {md_path}")

    return md_path


def render_html(artifacts_dir: Path, report_json: Path) -> Path:
    """Render HTML report from report_v1.json."""
    from srt_translator.presenters.eval_html.build import build_eval_html

    logger = logging.getLogger(__name__)

    # Use existing HTML builder
    html_path = build_eval_html(report_json, artifacts_dir / "eval_report.html")
    logger.info(f"Wrote eval_report.html: {html_path}")

    return html_path


def emit_all_reports(artifacts_dir: Path, rollup: dict) -> dict[str, Path]:
    """Orchestrator: write eval_report.json, compile report_v1.json, render MD/HTML."""
    logger = logging.getLogger(__name__)

    # Ensure artifacts directory exists
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Write eval_report.json
    eval_json_path = write_evaluator_json(artifacts_dir, rollup)

    # Step 2: Verify ai_config.json exists
    ai_config_path = artifacts_dir / "ai_config.json"
    if not ai_config_path.exists():
        raise ValueError(f"ai_config.json not found in artifacts directory: {ai_config_path}")

    # Step 3: Compile report_v1.json
    from srt_translator.report.compiler import compile_report

    report_v1_path = compile_report(artifacts_dir)
    logger.info(f"Compiled report_v1.json: {report_v1_path}")

    # Step 4: Render markdown and HTML
    md_path = render_markdown(artifacts_dir, report_v1_path)
    html_path = render_html(artifacts_dir, report_v1_path)

    return {
        "eval_report_json": eval_json_path,
        "report_v1_json": report_v1_path,
        "eval_report_md": md_path,
        "eval_report_html": html_path,
    }
