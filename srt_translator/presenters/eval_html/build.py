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

        # Load and validate report_v1.json
        report_data = _load_json_or_raise(
            report_v1_path, ["decision", "totals", "kpis", "file_status", "lexicons"]
        )

        # Validate required structure
        if not isinstance(report_data.get("decision"), dict):
            raise ValueError("report_v1.json decision must be a dict")
        if not isinstance(report_data.get("totals"), dict):
            raise ValueError("report_v1.json totals must be a dict")
        if not isinstance(report_data.get("kpis"), dict):
            raise ValueError("report_v1.json kpis must be a dict")
        if not isinstance(report_data.get("file_status"), list):
            raise ValueError("report_v1.json file_status must be a list")

        # Extract data from compiled report
        decision = report_data["decision"]
        kpis = report_data["kpis"]
        file_status = report_data["file_status"]
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
{chr(10).join(f"            <li>{item}</li>" for item in what_to_do)}
        </ol>
    </div>

    <!-- KPIs -->
    <div class="kpi-section">
        <h2>KPIs</h2>
        <div class="kpi-grid">
            <div class="kpi-item">
                <span class="kpi-label">Files:</span>
                <span class="kpi-value">{kpis["Files"]}</span>
            </div>
            <div class="kpi-item">
                <span class="kpi-label">Languages:</span>
                <span class="kpi-value">{kpis["Languages"]}</span>
            </div>
            <div class="kpi-item">
                <span class="kpi-label">Errors:</span>
                <span class="kpi-value">{kpis["Errors"]}</span>
            </div>
            <div class="kpi-item">
                <span class="kpi-label">Warnings:</span>
                <span class="kpi-value">{kpis["Warnings"]}</span>
            </div>
            <div class="kpi-item">
                <span class="kpi-label">DNT coverage:</span>
                <span class="kpi-value">{kpis["DNT coverage"]}</span>
            </div>
            <div class="kpi-item">
                <span class="kpi-label">Termbase coverage:</span>
                <span class="kpi-value">{kpis["Termbase coverage"]}</span>
            </div>
            <div class="kpi-item">
                <span class="kpi-label">Parity:</span>
                <span class="kpi-value">{kpis["Parity"]}</span>
            </div>
        </div>
    </div>

    <!-- File Status -->
    <div class="file-status-section">
        <h2>File Status</h2>
        <div class="file-status-list">
            {_render_file_status(file_status)}
        </div>
    </div>

    <!-- Punch List -->
    {_render_punch_list(report_data.get("sections", {}))}

    <!-- DNT Terms -->
    {_render_dnt_terms(report_data.get("lexicons", {}).get("dnt_terms", []))}

    <!-- Termbase -->
    {_render_termbase(report_data.get("lexicons", {}).get("termbase", {}))}
</body>
</html>"""

        # Write HTML file
        out_path.write_text(html_content, encoding="utf-8")

        if logger:
            logger.info(f"Generated HTML report: {out_path}")

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
