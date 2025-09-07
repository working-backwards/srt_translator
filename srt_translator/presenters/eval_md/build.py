from __future__ import annotations

import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)

_REQUIRED = {"decision", "one_liner", "punch_list", "file_status", "kpis", "lexicons"}


def _validate_punch_list_context(punch_list: dict) -> None:
    """Validate that punch list items have proper context structure."""
    for category in ["errors", "warnings"]:
        for item in punch_list.get(category, []):
            context = item.get("context", {})
            if context:
                source_context = context.get("source", {})
                target_context = context.get("target", {})
                if not source_context.get("cur") and not target_context.get("cur"):
                    log.warning(
                        "Punch list item missing context.cur: %s", item.get("issue_type", "unknown")
                    )


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

    # Validate context structure in punch list items
    _validate_punch_list_context(data["punch_list"])

    decision = data["decision"]
    one_liner = data["one_liner"]
    punch_list = data["punch_list"]
    file_status = data["file_status"]
    kpis = data["kpis"]
    lexicons = data["lexicons"]

    # Map decision level to emoji
    icon = {"pass": "✅", "review": "⚠️", "fail": "❌"}.get(decision, "⚠️")

    lines: list[str] = []

    # 1. Decision Banner + One-liner
    lines.append(f"# {icon} {one_liner}".rstrip())
    lines.append("")

    # 2. Punch List (Errors first, then Warnings)
    errors = punch_list.get("errors", [])
    warnings = punch_list.get("warnings", [])

    if errors or warnings:
        # Show Errors section
        lines.append("## ❌ Critical Issues")
        if errors:
            for error in errors:
                lines.append(f"### {error.get('file', 'Unknown')}: {error.get('type', 'Error')}")
                lines.append(f"**Language:** {error.get('language', 'Unknown')}")
                if error.get("cue_index") is not None:
                    lines.append(f"**Cue Index:** {error.get('cue_index')}")
                lines.append(f"**Summary:** {error.get('desc', '')}")
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

        # Show Warnings section
        lines.append("## ⚠️ Warnings")
        if warnings:
            for warning in warnings:
                lines.append(
                    f"### {warning.get('file', 'Unknown')}: {warning.get('type', 'Warning')}"
                )
                lines.append(f"**Language:** {warning.get('language', 'Unknown')}")
                if warning.get("cue_index") is not None:
                    lines.append(f"**Cue Index:** {warning.get('cue_index')}")
                lines.append(f"**Summary:** {warning.get('desc', '')}")
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
    else:
        # No issues found
        lines.append("## ✅ No Issues Found")
        lines.append("")
        lines.append("Everything looks great! Your translated files are ready to use.")
        lines.append("")

    # 3. File Status by Language
    lines.append("## 📁 File Status by Language")
    lines.append("")

    for lang_code in sorted(file_status.keys()):
        files = file_status[lang_code]
        ready_count = sum(1 for status in files.values() if status == "ready")
        review_count = sum(1 for status in files.values() if status == "review")
        blocked_count = sum(1 for status in files.values() if status == "blocked")

        lines.append(f"### {lang_code}")
        lines.append(f"- ✅ Ready: {ready_count}")
        lines.append(f"- ⚠️ Review: {review_count}")
        lines.append(f"- ❌ Blocked: {blocked_count}")
        lines.append("")

        # Show individual files
        for file_path, status in sorted(files.items()):
            status_icon = {"ready": "✅", "review": "⚠️", "blocked": "❌"}.get(status, "❓")
            lines.append(f"  {status_icon} {file_path}")
        lines.append("")

    # 4. KPI Summary
    lines.append("## 📊 KPI Summary")
    lines.append("")
    lines.append(f"- **Files Total:** {kpis.get('files_total', 0)}")
    lines.append(f"- **Languages Total:** {kpis.get('languages_total', 0)}")
    lines.append(f"- **Issues Total:** {kpis.get('issues_total', 0)}")
    lines.append("")

    # Per-type breakdown
    by_type = kpis.get("by_type", {})
    if by_type:
        lines.append("**Issues by Type:**")
        for issue_type, count in sorted(by_type.items()):
            if count > 0:
                lines.append(f"- {issue_type}: {count}")
        lines.append("")

    # 5. Lexicons
    lines.append("## 📚 Lexicons")
    lines.append("")

    # DNT terms
    dnt = lexicons.get("dnt", {})
    dnt_count = dnt.get("count", 0)
    dnt_sample = dnt.get("sample", [])
    lines.append(f"### Do-Not-Translate Terms ({dnt_count} total)")
    if dnt_sample:
        lines.append("Sample terms:")
        for term in dnt_sample:
            lines.append(f"- {term}")
    else:
        lines.append("No DNT terms configured.")
    lines.append("")

    # Termbases
    termbase = lexicons.get("termbase", {})
    if termbase:
        lines.append("### Termbases")
        for lang_code, terms in sorted(termbase.items()):
            term_count = terms.get("count", 0)
            term_sample = terms.get("sample", [])
            lines.append(f"**{lang_code}** ({term_count} terms)")
            if term_sample:
                lines.append("Sample translations:")
                for term in term_sample:
                    source = term.get("source", "")
                    target = term.get("target", "")
                    lines.append(f"- {source} → {target}")
            else:
                lines.append("No termbase entries.")
            lines.append("")
    else:
        lines.append("### Termbases")
        lines.append("No termbases configured.")
        lines.append("")

    # Write the file
    content = "\n".join(lines)
    out_path.write_text(content, encoding="utf-8")

    return out_path
