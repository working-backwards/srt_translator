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


# Old helper functions removed - now using compiled report_v1.json data


def build_eval_html(report_v1_path: Path, out_path: Path | None = None) -> Path:
    """Generate HTML report with unified top sections: banner, next steps, and KPIs.

    Reads report_v1.json with strict validation.
    Fails fast on missing/invalid inputs.
    """
    # Set up logging if available
    logger = logging.getLogger(__name__)

    # Default output path
    if out_path is None:
        out_path = report_v1_path.with_suffix(".html")

    try:
        # Load CSS resource
        css_text = (
            importlib.resources.files("srt_translator.presenters.eval_html.assets")
            .joinpath("eval.css")
            .read_text(encoding="utf-8")
        )

        # Load and validate report_v1.json with strict schema
        report_data = _load_json_or_raise(
            report_v1_path, ["decision", "kpis", "file_status", "sections", "lexicons"]
        )

        # Validate required structure
        if not isinstance(report_data.get("decision"), dict):
            raise ValueError("report_v1.json decision must be a dict")
        if not isinstance(report_data.get("kpis"), dict):
            raise ValueError("report_v1.json kpis must be a dict")
        if not isinstance(report_data.get("file_status"), dict):
            raise ValueError("report_v1.json file_status must be a dict")
        if not isinstance(report_data.get("sections"), dict):
            raise ValueError("report_v1.json sections must be a dict")
        if not isinstance(report_data.get("lexicons"), dict):
            raise ValueError("report_v1.json lexicons must be a dict")

        # Extract data from compiled report
        decision = report_data["decision"]
        kpis = report_data["kpis"]
        file_status = report_data["file_status"]
        sections = report_data["sections"]
        lexicons = report_data["lexicons"]

        # Extract decision level and one-liner
        decision_level = decision.get("level", "review")
        one_liner = decision.get("one_liner", "")

        # Map decision level to emoji and banner text
        if decision_level == "pass":
            banner_emoji = "✅"
            banner_text = (
                one_liner or "Everything looks great. Your translated files are ready to use."
            )
        elif decision_level == "review":
            banner_emoji = "⚠️"
            banner_text = one_liner or "Review recommended."
        else:  # fix
            banner_emoji = "❌"
            banner_text = one_liner or "Fix required."

        # Generate HTML content
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Eval Report</title>
    <style>
{css_text}
    </style>
</head>
<body>
    <h1>Eval Report</h1>

    <!-- Publish readiness banner -->
    <div class="decision-banner">
        <h2>{banner_emoji} {banner_text}</h2>
    </div>

    <!-- What to do next -->
    <div class="what-to-do-next">
        <h2>What to do next</h2>
        <ol>
{chr(10).join(f"            <li>{item}</li>" for item in _get_what_to_do_steps(decision_level, kpis))}
        </ol>
    </div>

    <!-- KPIs -->
    <div class="kpi-section">
        <h2>KPIs</h2>
        <div class="kpi-grid">
            <div class="kpi-item">
                <span class="kpi-label">Files:</span>
                <span class="kpi-value">{kpis.get("files_total", 0)}</span>
            </div>
            <div class="kpi-item">
                <span class="kpi-label">Languages:</span>
                <span class="kpi-value">{kpis.get("languages_total", 0)}</span>
            </div>
            <div class="kpi-item">
                <span class="kpi-label">Errors:</span>
                <span class="kpi-value">{kpis.get("errors_total", 0)}</span>
            </div>
            <div class="kpi-item">
                <span class="kpi-label">Warnings:</span>
                <span class="kpi-value">{kpis.get("warnings_total", 0)}</span>
            </div>
            <div class="kpi-item">
                <span class="kpi-label">DNT terms:</span>
                <span class="kpi-value">{kpis.get("dnt_terms_count", 0)}</span>
            </div>
            <div class="kpi-item">
                <span class="kpi-label">Termbase languages:</span>
                <span class="kpi-value">{kpis.get("termbase_languages_count", 0)}</span>
            </div>
        </div>
    </div>

    <!-- File Status -->
    <div class="file-status-section">
        <h2>File Status</h2>
        <div class="file-status-list">
            {_render_file_status_dict(file_status)}
        </div>
    </div>

    <!-- Punch List -->
    {_render_punch_list_new(sections)}

    <!-- DNT Terms -->
    {_render_dnt_terms(lexicons.get("dnt_terms", []))}

    <!-- Termbase -->
    {_render_termbase(lexicons.get("termbase", {}))}
</body>
</html>"""

        # Write HTML file
        out_path.write_text(html_content, encoding="utf-8")

        if logger:
            logger.info("Generated HTML report: %s", out_path)

        return out_path

    except FileNotFoundError as e:
        error_msg = f"Required resource not found: {e}"
        if logger:
            logger.error(error_msg)
        raise ValueError(error_msg) from e
    except json.JSONDecodeError as e:
        error_msg = f"Invalid JSON in {report_v1_path}: {e}"
        if logger:
            logger.error(error_msg)
        raise ValueError(error_msg) from e
    except Exception as e:
        error_msg = f"Failed to generate HTML report: {e}"
        if logger:
            logger.error(error_msg)
        raise ValueError(error_msg) from e


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


def _render_file_status_dict(file_status: dict[str, dict[str, str]]) -> str:
    """Render file status dict as HTML."""
    if not file_status:
        return "<p>No files processed.</p>"

    html = []
    # Sort languages and files for deterministic output
    for lang in sorted(file_status.keys()):
        lang_files = file_status[lang]
        for file_path in sorted(lang_files.keys()):
            status = lang_files[file_path]

            # Map status to emoji and CSS class
            if status == "ok":
                emoji = "✅"
                css_class = "status-ready"
            elif status == "warning":
                emoji = "⚠️"
                css_class = "status-review"
            elif status == "error":
                emoji = "❌"
                css_class = "status-fix"
            else:
                emoji = "❓"
                css_class = "status-unknown"

            html.append(f'<div class="file-status-item {css_class}">')
            html.append(f'  <span class="file-status-emoji">{emoji}</span>')
            html.append(f'  <span class="file-status-path">{lang}/{file_path}</span>')
            html.append("</div>")

    return "\n".join(html)


def _render_file_status(file_status: list[dict[str, str]]) -> str:
    """Render file status list as HTML."""
    if not file_status:
        return "<p>No files processed.</p>"

    html = []
    for file_info in file_status:
        file_path = file_info.get("file_path", "Unknown")
        status = file_info.get("status", "UNKNOWN")

        # Map status to emoji and CSS class
        if status == "READY":
            emoji = "✅"
            css_class = "status-ready"
        elif status == "REVIEW":
            emoji = "⚠️"
            css_class = "status-review"
        elif status == "FIX":
            emoji = "❌"
            css_class = "status-fix"
        else:
            emoji = "❓"
            css_class = "status-unknown"

        html.append(f'<div class="file-status-item {css_class}">')
        html.append(f'  <span class="file-status-emoji">{emoji}</span>')
        html.append(f'  <span class="file-status-path">{file_path}</span>')
        html.append("</div>")

    return "\n".join(html)


def _render_punch_list_new(sections: dict[str, list]) -> str:
    """Render punch list (errors and warnings) as HTML using new schema."""
    errors = sections.get("errors", [])
    warnings = sections.get("warnings", [])

    html = []

    if errors:
        html.append('<div class="punch-list-section">')
        html.append("<h2>❌ Critical Issues</h2>")
        html.append('<div class="punch-list">')
        for error in errors:
            html.append('<div class="punch-item error">')
            html.append(f"  <h3>{error.get('file', 'Unknown')}: {error.get('type', 'Error')}</h3>")
            html.append(f"  <p><strong>Message:</strong> {error.get('message', '')}</p>")
            html.append(f"  <p><strong>Suggested fix:</strong> {error.get('suggest_fix', '')}</p>")
            # Render context if available
            context = error.get("context", {})
            if context:
                target_window = context.get("target_window", [])
                source_window = context.get("source_window", [])
                if target_window or source_window:
                    html.append("  <p><strong>Context:</strong></p>")
                    if target_window:
                        html.append("  <p><strong>Target context:</strong></p>")
                        html.append("  <pre>" + "\n".join(target_window) + "</pre>")
                    if source_window:
                        html.append("  <p><strong>Source context:</strong></p>")
                        html.append("  <pre>" + "\n".join(source_window) + "</pre>")
            html.append("</div>")
        html.append("</div>")
        html.append("</div>")

    if warnings:
        html.append('<div class="punch-list-section">')
        html.append("<h2>⚠️ Warnings</h2>")
        html.append('<div class="punch-list">')
        for warning in warnings:
            html.append('<div class="punch-item warning">')
            html.append(
                f"  <h3>{warning.get('file', 'Unknown')}: {warning.get('type', 'Warning')}</h3>"
            )
            html.append(f"  <p><strong>Message:</strong> {warning.get('message', '')}</p>")
            html.append(
                f"  <p><strong>Suggested fix:</strong> {warning.get('suggest_fix', '')}</p>"
            )
            # Render context if available
            context = warning.get("context", {})
            if context:
                target_window = context.get("target_window", [])
                source_window = context.get("source_window", [])
                if target_window or source_window:
                    html.append("  <p><strong>Context:</strong></p>")
                    if target_window:
                        html.append("  <p><strong>Target context:</strong></p>")
                        html.append("  <pre>" + "\n".join(target_window) + "</pre>")
                    if source_window:
                        html.append("  <p><strong>Source context:</strong></p>")
                        html.append("  <pre>" + "\n".join(source_window) + "</pre>")
            html.append("</div>")
        html.append("</div>")
        html.append("</div>")

    if not errors and not warnings:
        html.append('<div class="punch-list-section">')
        html.append("<h2>✅ No Issues Found</h2>")
        html.append("<p>All files passed evaluation with no errors or warnings.</p>")
        html.append("</div>")

    return "\n".join(html)


def _render_punch_list(sections: dict[str, list]) -> str:
    """Render punch list (errors and warnings) as HTML."""
    errors = sections.get("errors", [])
    warnings = sections.get("warnings", [])

    html = []

    if errors:
        html.append('<div class="punch-list-section">')
        html.append("<h2>❌ Critical Issues</h2>")
        html.append('<div class="punch-list">')
        for error in errors:
            html.append('<div class="punch-item error">')
            html.append(
                f"  <h3>{error.get('filename', 'Unknown')}: {error.get('title', 'Error')}</h3>"
            )
            html.append(
                f"  <p><strong>Why it matters:</strong> {error.get('why_it_matters', '')}</p>"
            )
            html.append(
                f"  <p><strong>Suggested fix:</strong> {error.get('suggested_fix', '')}</p>"
            )
            html.append(f"  <p><strong>Ask an AI:</strong> {error.get('ask_ai_prompt', '')}</p>")
            html.append("</div>")
        html.append("</div>")
        html.append("</div>")

    if warnings:
        html.append('<div class="punch-list-section">')
        html.append("<h2>⚠️ Warnings</h2>")
        html.append('<div class="punch-list">')
        for warning in warnings:
            html.append('<div class="punch-item warning">')
            html.append(
                f"  <h3>{warning.get('filename', 'Unknown')}: {warning.get('title', 'Warning')}</h3>"
            )
            html.append(
                f"  <p><strong>Why it matters:</strong> {warning.get('why_it_matters', '')}</p>"
            )
            html.append(
                f"  <p><strong>Suggested fix:</strong> {warning.get('suggested_fix', '')}</p>"
            )
            html.append(f"  <p><strong>Ask an AI:</strong> {warning.get('ask_ai_prompt', '')}</p>")
            html.append("</div>")
        html.append("</div>")
        html.append("</div>")

    if not errors and not warnings:
        html.append('<div class="punch-list-section">')
        html.append("<h2>✅ No Issues Found</h2>")
        html.append("<p>All files passed evaluation with no errors or warnings.</p>")
        html.append("</div>")

    return "\n".join(html)


def _render_dnt_terms(dnt_terms: list[str]) -> str:
    """Render DNT terms as HTML."""
    if not dnt_terms:
        return ""

    html = []
    html.append('<div class="dnt-section">')
    html.append("<h2>Do-Not-Translate Terms</h2>")
    html.append('<div class="dnt-list">')
    for term in dnt_terms:
        html.append(f'<span class="dnt-term">{term}</span>')
    html.append("</div>")
    html.append("</div>")

    return "\n".join(html)


def _render_termbase(termbase: dict[str, list[dict[str, str]]]) -> str:
    """Render termbase as HTML."""
    if not termbase:
        return ""

    html = []
    html.append('<div class="termbase-section">')
    html.append("<h2>Termbase</h2>")

    for lang_name, terms in termbase.items():
        if not terms:
            continue
        html.append('<div class="termbase-language">')
        html.append(f"  <h3>{lang_name}</h3>")
        html.append('  <div class="termbase-terms">')
        for term in terms:
            source = term.get("source", "")
            preferred = term.get("preferred", "")
            html.append('    <div class="termbase-item">')
            html.append(
                f'      <span class="term-source">{source}</span> → <span class="term-preferred">{preferred}</span>'
            )
            html.append("    </div>")
        html.append("  </div>")
        html.append("</div>")

    html.append("</div>")

    return "\n".join(html)
