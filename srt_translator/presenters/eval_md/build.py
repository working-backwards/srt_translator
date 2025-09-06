from __future__ import annotations

import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)

_REQUIRED = {"decision", "totals", "kpis", "file_status", "punch_list", "lexicons"}


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
    totals = data["totals"]
    kpis = data["kpis"]
    file_status = data["file_status"]
    punch_list = data["punch_list"]
    lexicons = data["lexicons"]

    # Extract decision level and one-liner
    decision_level = decision.get("level", "review")
    one_liner = decision.get("one_liner", "")

    # Map decision level to emoji
    icon = {"pass": "✅", "review": "⚠️", "fix": "❌"}.get(decision_level, "⚠️")

    lines: list[str] = []

    # 1. Decision Banner + One-liner
    lines.append(f"# {icon} {one_liner}".rstrip())
    lines.append("")

    # 2. Punch List
    errors = punch_list.get("errors", [])
    warnings = punch_list.get("warnings", [])

    # Always show Critical Issues section
    lines.append("## ❌ Critical Issues")
    if errors:
        for error in errors:
            lines.append(f"### {error.get('file', 'Unknown')}: {error.get('type', 'Error')}")
            lines.append(f"**Language:** {error.get('language', 'Unknown')}")
            if error.get("cue_index") is not None:
                lines.append(f"**Cue Index:** {error.get('cue_index')}")
            lines.append(f"**Summary:** {error.get('human_summary', '')}")
            lines.append(f"**Suggested fix:** {error.get('suggested_fix', '')}")
            # Render context if available
            context = error.get("context", {})
            if context:
                source = context.get("source", {})
                target = context.get("target", {})
                if source or target:
                    lines.append("**Context:**")
                    if source:
                        lines.append("**Source context:**")
                        lines.append("```")
                        for k, v in source.items():
                            if v:
                                lines.append(f"{k}: {v}")
                        lines.append("```")
                    if target:
                        lines.append("**Target context:**")
                        lines.append("```")
                        for k, v in target.items():
                            if v:
                                lines.append(f"{k}: {v}")
                        lines.append("```")
            lines.append("")
    else:
        lines.append("No critical issues found.")
        lines.append("")

    # Always show Warnings section
    lines.append("## ⚠️ Warnings")
    if warnings:
        for warning in warnings:
            lines.append(f"### {warning.get('file', 'Unknown')}: {warning.get('type', 'Warning')}")
            lines.append(f"**Language:** {warning.get('language', 'Unknown')}")
            if warning.get("cue_index") is not None:
                lines.append(f"**Cue Index:** {warning.get('cue_index')}")
            lines.append(f"**Summary:** {warning.get('human_summary', '')}")
            lines.append(f"**Suggested fix:** {warning.get('suggested_fix', '')}")
            # Render context if available
            context = warning.get("context", {})
            if context:
                source = context.get("source", {})
                target = context.get("target", {})
                if source or target:
                    lines.append("**Context:**")
                    if source:
                        lines.append("**Source context:**")
                        lines.append("```")
                        for k, v in source.items():
                            if v:
                                lines.append(f"{k}: {v}")
                        lines.append("```")
                    if target:
                        lines.append("**Target context:**")
                        lines.append("```")
                        for k, v in target.items():
                            if v:
                                lines.append(f"{k}: {v}")
                        lines.append("```")
            lines.append("")
    else:
        lines.append("No warnings found.")
        lines.append("")

    if not errors and not warnings:
        lines.append("## ✅ No Issues Found")
        lines.append("All files passed evaluation with no errors or warnings.")
        lines.append("")

    # 3. File Status by Language
    lines.append("## File Status by Language")
    if file_status:
        for lang in sorted(file_status.keys()):
            lang_files = file_status[lang]
            ready_count = sum(1 for status in lang_files.values() if status == "ready")
            review_count = sum(1 for status in lang_files.values() if status == "review")
            error_count = sum(1 for status in lang_files.values() if status == "error")

            lines.append(f"### {lang.upper()}")
            lines.append(f"- ✅ Ready: {ready_count}")
            lines.append(f"- ⚠️ Review: {review_count}")
            lines.append(f"- ❌ Error: {error_count}")
            lines.append("")

            for file_path in sorted(lang_files.keys()):
                status = lang_files[file_path]
                # Map status to emoji
                if status == "ready":
                    emoji = "✅"
                elif status == "review":
                    emoji = "⚠️"
                elif status == "error":
                    emoji = "❌"
                else:
                    emoji = "❓"
                lines.append(f"  - {emoji} **{file_path}** ({status})")
            lines.append("")
    else:
        lines.append("No files processed.")
        lines.append("")

    # 4. KPI Summary
    lines.append("## KPI Summary")
    lines.append(f"- **Files:** {totals.get('files_total', 0)}")
    lines.append(f"- **Languages:** {totals.get('languages_total', 0)}")
    lines.append(f"- **Issues:** {totals.get('issues_total', 0)}")
    lines.append(f"- **Errors:** {kpis.get('errors_total', 0)}")
    lines.append(f"- **Warnings:** {kpis.get('warnings_total', 0)}")

    # Per-type counts
    per_type = kpis.get("per_type", {})
    if per_type:
        lines.append("")
        lines.append("### Issues by Type")
        for issue_type, count in per_type.items():
            if count > 0:
                lines.append(f"- **{issue_type.replace('_', ' ').title()}:** {count}")
    lines.append("")

    # 5. Lexicons
    lines.append("## Lexicons")

    # DNT Terms
    dnt = lexicons.get("dnt", {})
    lines.append("### DNT Terms")
    if dnt.get("count", 0) > 0:
        lines.append(f"**Count:** {dnt.get('count', 0)}")
        lines.append("**Sample:**")
        for term in dnt.get("sample", []):
            lines.append(f"- `{term}`")
    else:
        lines.append("_None_")
    lines.append("")

    # Termbases
    termbases = lexicons.get("termbases", {})
    lines.append("### Termbases")
    if termbases:
        for lang in sorted(termbases.keys()):
            tb = termbases[lang]
            lines.append(f"#### {lang.upper()}")
            lines.append(f"**Count:** {tb.get('count', 0)}")
            if tb.get("sample"):
                lines.append("**Sample:**")
                for entry in tb.get("sample", []):
                    source = entry.get("source", "")
                    target = entry.get("target", "")
                    lines.append(f"- `{source}` → `{target}`")
            lines.append("")
    else:
        lines.append("_None_")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path
