from __future__ import annotations

import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)

_REQUIRED = {"decision", "kpis", "file_status", "sections", "lexicons"}


def _get_what_to_do_steps(decision_level: str, kpis: dict) -> list[str]:
    """Generate what to do next steps based on decision level and KPIs."""
    # kpis parameter kept for future use but not currently needed
    _ = kpis  # Suppress unused parameter warning

    if decision_level == "pass":
        return [
            "Spot-check a few captions for flow and brand terms, then publish.",
            "Save the HTML/MD report with your course materials.",
        ]
    elif decision_level == "review":
        return [
            "Work through the Punch List below.",
            "For each warning, use the context snippet and suggested check to verify quickly.",
            "If everything looks good, publish.",
        ]
    else:  # fix
        return [
            "Work through the Punch List below; fix **errors first**, then warnings.",
            "Use the context snippets to validate or regenerate translations.",
            "Re-run the app after fixes to verify a clean report.",
        ]


def _load(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"{path.name} not found at: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    missing = sorted(_REQUIRED - data.keys())
    if missing:
        raise ValueError(f"{path.name} missing required keys: {', '.join(missing)}")
    return data


def build_eval_md(report_v1_path: Path, out_path: Path | None = None) -> Path:
    """Render Markdown report from compiled report_v1.json."""
    data = _load(report_v1_path)
    if out_path is None:
        out_path = report_v1_path.with_name("eval_report.md")

    decision = data["decision"]
    kpis = data["kpis"]
    file_status = data["file_status"]
    sections = data["sections"]
    lexicons = data["lexicons"]

    # Extract decision level and one-liner
    decision_level = decision.get("level", "review")
    one_liner = decision.get("one_liner", "")

    # Map decision level to emoji
    icon = {"pass": "✅", "review": "⚠️", "fix": "❌"}.get(decision_level, "⚠️")

    lines: list[str] = []
    # Banner
    lines.append(f"# {icon} {one_liner}".rstrip())
    lines.append("")
    lines.append("## What to do next")
    steps = _get_what_to_do_steps(decision_level, kpis)
    for step in steps:
        lines.append(f"- {step}")
    lines.append("")

    # KPI strip
    lines.append("## KPIs")
    lines.append(f"- **Files:** {kpis.get('files_total', 0)}")
    lines.append(f"- **Languages:** {kpis.get('languages_total', 0)}")
    lines.append(f"- **Errors:** {kpis.get('errors_total', 0)}")
    lines.append(f"- **Warnings:** {kpis.get('warnings_total', 0)}")
    lines.append(f"- **DNT terms:** {kpis.get('dnt_terms_count', 0)}")
    lines.append(f"- **Termbase languages:** {kpis.get('termbase_languages_count', 0)}")
    lines.append("")

    # Per-file status
    lines.append("## File Status")
    if file_status:
        for lang in sorted(file_status.keys()):
            lang_files = file_status[lang]
            for file_path in sorted(lang_files.keys()):
                status = lang_files[file_path]
                # Map status to emoji
                if status == "ok":
                    emoji = "✅"
                elif status == "warning":
                    emoji = "⚠️"
                elif status == "error":
                    emoji = "❌"
                else:
                    emoji = "❓"
                lines.append(f"- {emoji} **{lang}/{file_path}** ({status})")
    else:
        lines.append("No files processed.")
    lines.append("")

    # Punch List
    errors = sections.get("errors", [])
    warnings = sections.get("warnings", [])

    if errors:
        lines.append("## ❌ Critical Issues")
        for error in errors:
            lines.append(f"### {error.get('file', 'Unknown')}: {error.get('type', 'Error')}")
            lines.append(f"**Message:** {error.get('message', '')}")
            lines.append(f"**Suggested fix:** {error.get('suggest_fix', '')}")
            # Render context if available
            context = error.get("context", {})
            if context:
                target_window = context.get("target_window", [])
                source_window = context.get("source_window", [])
                if target_window or source_window:
                    lines.append("**Context:**")
                    if target_window:
                        lines.append("**Target context:**")
                        lines.append("```")
                        lines.extend(target_window)
                        lines.append("```")
                    if source_window:
                        lines.append("**Source context:**")
                        lines.append("```")
                        lines.extend(source_window)
                        lines.append("```")
            lines.append("")

    if warnings:
        lines.append("## ⚠️ Warnings")
        for warning in warnings:
            lines.append(f"### {warning.get('file', 'Unknown')}: {warning.get('type', 'Warning')}")
            lines.append(f"**Message:** {warning.get('message', '')}")
            lines.append(f"**Suggested fix:** {warning.get('suggest_fix', '')}")
            # Render context if available
            context = warning.get("context", {})
            if context:
                target_window = context.get("target_window", [])
                source_window = context.get("source_window", [])
                if target_window or source_window:
                    lines.append("**Context:**")
                    if target_window:
                        lines.append("**Target context:**")
                        lines.append("```")
                        lines.extend(target_window)
                        lines.append("```")
                    if source_window:
                        lines.append("**Source context:**")
                        lines.append("```")
                        lines.extend(source_window)
                        lines.append("```")
            lines.append("")

    if not errors and not warnings:
        lines.append("## ✅ No Issues Found")
        lines.append("All files passed evaluation with no errors or warnings.")
        lines.append("")

    # DNT + Termbase
    lines.append("## Lexicons")
    dnt_terms = lexicons.get("dnt_terms", [])
    termbase = lexicons.get("termbase", {})

    lines.append("### DNT Terms")
    if dnt_terms:
        for term in dnt_terms:
            lines.append(f"- `{term}`")
    else:
        lines.append("_None_")
    lines.append("")

    lines.append("### Termbases")
    if termbase:
        for lang in sorted(termbase.keys()):
            terms = termbase[lang]
            lines.append(f"#### {lang}")
            for term in terms:
                source = term.get("source", "")
                preferred = term.get("preferred", "")
                lines.append(f"- `{source}` → `{preferred}`")
            lines.append("")
    else:
        lines.append("_None_")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log.info("Wrote eval_report.md: %s", out_path)
    return out_path
