from __future__ import annotations

import importlib.resources
import json
import logging
from pathlib import Path
from typing import Any


def _format_number(value: int | float) -> str:
    """Format numeric values consistently, avoiding locale dependence."""
    if isinstance(value, float):
        # Format floating point numbers to 1 decimal place
        return f"{value:.1f}"
    else:
        # Format integers as-is
        return str(value)


def _load_eval_css() -> str:
    """Load CSS from package data; fail soft so HTML still renders if missing."""
    try:
        return (importlib.resources.files("srt_translator.presenters.eval_html.assets") / "eval.css").read_text(
            encoding="utf-8"
        )
    except Exception as e:
        logging.warning("eval_html: missing CSS asset (eval.css); continuing without CSS: %s", e)
        return ""


def _validate_punch_list_context(punch_list: dict) -> None:
    """Validate that punch list items have proper context structure."""
    for category in ["errors", "warnings"]:
        for item in punch_list.get(category, []):
            context = item.get("context", {})
            if context:
                source_context = context.get("source", {})
                target_context = context.get("target", {})
                if not source_context.get("cur") and not target_context.get("cur"):
                    logging.warning("Punch list item missing context.cur: %s", item.get("issue_type", "unknown"))


def _load_json_or_raise(file_path: Path, required_keys: list[str]) -> dict[str, Any]:
    """Load JSON file with strict validation, fail fast on missing keys."""
    if not file_path.exists():
        raise ValueError(f"Required file not found: {file_path}")

    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {file_path}: {e}") from e

    missing_keys = [key for key in required_keys if key not in data]
    if missing_keys:
        raise ValueError(f"{file_path.name} missing required keys: {', '.join(missing_keys)}")

    return data  # type: ignore[no-any-return]


def build_eval_html(report_path: Path, out_path: Path | None = None) -> Path:
    """Generate HTML report from compiled report.json.

    Reads report.json with strict validation.
    Fails fast on missing/invalid inputs.
    """
    # Set up logging if available
    logger = logging.getLogger(__name__)

    # Default output path
    if out_path is None:
        out_path = report_path.with_suffix(".html")

    try:
        # Load CSS resource
        css_text = _load_eval_css()

        # Load and validate report.json with strict schema
        report_data = _load_json_or_raise(
            report_path,
            ["decision", "one_liner", "punch_list", "file_status", "kpis", "lexicons"],
        )

        # Validate required structure
        if not isinstance(report_data.get("decision"), str):
            raise ValueError("report.json decision must be a string")
        if not isinstance(report_data.get("one_liner"), str):
            raise ValueError("report.json one_liner must be a string")
        if not isinstance(report_data.get("punch_list"), dict):
            raise ValueError("report.json punch_list must be a dict")
        if not isinstance(report_data.get("file_status"), dict):
            raise ValueError("report.json file_status must be a dict")

        # Validate context structure in punch list items
        _validate_punch_list_context(report_data["punch_list"])
        if not isinstance(report_data.get("kpis"), dict):
            raise ValueError("report.json kpis must be a dict")
        if not isinstance(report_data.get("lexicons"), dict):
            raise ValueError("report.json lexicons must be a dict")

        # Extract data
        decision = report_data["decision"]
        one_liner = report_data["one_liner"]
        punch_list = report_data["punch_list"]
        file_status = report_data["file_status"]
        kpis = report_data["kpis"]
        lexicons = report_data["lexicons"]

        # Map decision level to emoji
        icon = {"pass": "✅", "review": "⚠️", "fail": "❌"}.get(decision, "⚠️")  # nosec B105

        # Generate HTML
        html_content = _generate_html(icon, one_liner, punch_list, file_status, kpis, lexicons, css_text)

        # Write the file
        out_path.write_text(html_content, encoding="utf-8")

        return out_path

    except Exception as e:
        logger.error("Failed to generate HTML report: %s", e)
        raise


def _generate_html(
    icon: str,
    one_liner: str,
    punch_list: dict,
    file_status: dict,
    kpis: dict,
    lexicons: dict,
    css_text: str,
) -> str:
    """Generate the complete HTML content."""
    html = []

    # HTML header
    html.append("<!DOCTYPE html>")
    html.append('<html lang="en">')
    html.append("<head>")
    html.append('<meta charset="utf-8">')
    html.append('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
    html.append("<title>Translation Evaluation Report</title>")
    html.append("<style>")
    html.append(css_text)
    html.append("</style>")
    html.append("</head>")
    html.append("<body>")

    # 1. Decision Banner + One-liner
    html.append('<div class="decision-banner">')
    html.append(f"<h1>{icon} {one_liner}</h1>")
    html.append("</div>")

    # 2. Punch List (Errors first, then Warnings)
    errors = punch_list.get("errors", [])
    warnings = punch_list.get("warnings", [])

    if errors or warnings:
        html.append('<div class="punch-list-section">')
        html.append("<h2>❌ Critical Issues</h2>")
        html.append('<div class="punch-list">')
        if errors:
            for error in errors:
                html.append('<div class="punch-item error">')
                html.append(f"<h3>{error.get('file', 'Unknown')}: {error.get('type', 'Error')}</h3>")
                html.append(f"<p><strong>Language:</strong> {error.get('language', 'Unknown')}</p>")
                if error.get("cue_index") is not None:
                    html.append(f"<p><strong>Cue Index:</strong> {error.get('cue_index')}</p>")
                html.append(f"<p><strong>Summary:</strong> {error.get('desc', '')}</p>")
                html.append(f"<p><strong>Suggested fix:</strong> {error.get('suggested_fix', '')}</p>")
                # Render context if available
                context = error.get("context", {})
                if context:
                    source = context.get("source", {})
                    target = context.get("target", {})
                    if source or target:
                        html.append("<p><strong>Context:</strong></p>")
                        if source:
                            html.append("<p><strong>Source context:</strong></p>")
                            html.append("<pre>")
                            html.append("\n".join([f"{k}: {v}" for k, v in source.items() if v]))
                            html.append("</pre>")
                        if target:
                            html.append("<p><strong>Target context:</strong></p>")
                            html.append("<pre>")
                            html.append("\n".join([f"{k}: {v}" for k, v in target.items() if v]))
                            html.append("</pre>")
                html.append("</div>")
        else:
            html.append("<p>No critical issues found.</p>")
        html.append("</div>")
        html.append("</div>")

        # Warnings section
        html.append('<div class="punch-list-section">')
        html.append("<h2>⚠️ Warnings</h2>")
        html.append('<div class="punch-list">')
        if warnings:
            for warning in warnings:
                html.append('<div class="punch-item warning">')
                html.append(f"<h3>{warning.get('file', 'Unknown')}: {warning.get('type', 'Warning')}</h3>")
                html.append(f"<p><strong>Language:</strong> {warning.get('language', 'Unknown')}</p>")
                if warning.get("cue_index") is not None:
                    html.append(f"<p><strong>Cue Index:</strong> {warning.get('cue_index')}</p>")
                html.append(f"<p><strong>Summary:</strong> {warning.get('desc', '')}</p>")
                html.append(f"<p><strong>Suggested fix:</strong> {warning.get('suggested_fix', '')}</p>")
                # Render context if available
                context = warning.get("context", {})
                if context:
                    source = context.get("source", {})
                    target = context.get("target", {})
                    if source or target:
                        html.append("<p><strong>Context:</strong></p>")
                        if source:
                            html.append("<p><strong>Source context:</strong></p>")
                            html.append("<pre>")
                            html.append("\n".join([f"{k}: {v}" for k, v in source.items() if v]))
                            html.append("</pre>")
                        if target:
                            html.append("<p><strong>Target context:</strong></p>")
                            html.append("<pre>")
                            html.append("\n".join([f"{k}: {v}" for k, v in target.items() if v]))
                            html.append("</pre>")
                html.append("</div>")
        else:
            html.append("<p>No warnings found.</p>")
        html.append("</div>")
        html.append("</div>")
    else:
        # No issues found
        html.append('<div class="punch-list-section">')
        html.append("<h2>✅ No Issues Found</h2>")
        html.append("<p>Everything looks great! Your translated files are ready to use.</p>")
        html.append("</div>")

    # 3. File Status by Language
    html.append('<div class="file-status-section">')
    html.append("<h2>📁 File Status by Language</h2>")

    for lang_code in sorted(file_status.keys()):
        files = file_status[lang_code]
        ready_count = sum(1 for status in files.values() if status == "ready")
        review_count = sum(1 for status in files.values() if status == "review")
        blocked_count = sum(1 for status in files.values() if status == "blocked")

        html.append(f"<h3>{lang_code}</h3>")
        html.append("<ul>")
        html.append(f"<li>✅ Ready: {ready_count}</li>")
        html.append(f"<li>⚠️ Review: {review_count}</li>")
        html.append(f"<li>❌ Blocked: {blocked_count}</li>")
        html.append("</ul>")

        # Show individual files
        html.append("<ul>")
        for file_path, status in sorted(files.items()):
            status_icon = {"ready": "✅", "review": "⚠️", "blocked": "❌"}.get(status, "❓")
            html.append(f"<li>{status_icon} {file_path}</li>")
        html.append("</ul>")

    html.append("</div>")

    # 4. KPI Summary
    html.append('<div class="kpi-section">')
    html.append("<h2>📊 KPI Summary</h2>")
    html.append("<ul>")
    html.append(f"<li><strong>Files Total:</strong> {kpis.get('files_total', 0)}</li>")
    html.append(f"<li><strong>Languages Total:</strong> {kpis.get('languages_total', 0)}</li>")
    html.append(f"<li><strong>Issues Total:</strong> {kpis.get('issues_total', 0)}</li>")
    html.append("</ul>")

    # Per-type breakdown
    by_type = kpis.get("by_type", {})
    if by_type:
        html.append("<h3>Issues by Type</h3>")
        html.append("<ul>")
        for issue_type, count in sorted(by_type.items()):
            if count > 0:
                html.append(f"<li>{issue_type}: {count}</li>")
        html.append("</ul>")

    html.append("</div>")

    # 5. Lexicons
    html.append('<div class="lexicon-section">')
    html.append("<h2>📚 Lexicons</h2>")

    # DNT terms
    dnt = lexicons.get("dnt", {})
    dnt_count = dnt.get("count", 0)
    dnt_sample = dnt.get("sample", [])
    html.append(f"<h3>Do-Not-Translate Terms ({dnt_count} total)</h3>")
    if dnt_sample:
        html.append("<ul>")
        for term in dnt_sample:
            html.append(f"<li>{term}</li>")
        html.append("</ul>")
    else:
        html.append("<p>No DNT terms configured.</p>")

    # Termbases
    termbase = lexicons.get("termbase", {})
    if termbase:
        html.append("<h3>Termbases</h3>")
        for lang_code, terms in sorted(termbase.items()):
            term_count = terms.get("count", 0)
            term_sample = terms.get("sample", [])
            html.append(f"<h4>{lang_code} ({term_count} terms)</h4>")
            if term_sample:
                html.append("<ul>")
                for term in term_sample:
                    source = term.get("source", "")
                    target = term.get("target", "")
                    html.append(f"<li>{source} → {target}</li>")
                html.append("</ul>")
            else:
                html.append("<p>No termbase entries.</p>")
    else:
        html.append("<h3>Termbases</h3>")
        html.append("<p>No termbases configured.</p>")

    html.append("</div>")

    # HTML footer
    html.append("</body>")
    html.append("</html>")

    return "\n".join(html)
