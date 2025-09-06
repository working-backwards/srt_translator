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
            report_v1_path, ["decision", "totals", "kpis", "file_status", "punch_list", "lexicons"]
        )

        # Validate required structure
        if not isinstance(report_data.get("decision"), dict):
            raise ValueError("report_v1.json decision must be a dict")
        if not isinstance(report_data.get("totals"), dict):
            raise ValueError("report_v1.json totals must be a dict")
        if not isinstance(report_data.get("kpis"), dict):
            raise ValueError("report_v1.json kpis must be a dict")
        if not isinstance(report_data.get("file_status"), dict):
            raise ValueError("report_v1.json file_status must be a dict")
        if not isinstance(report_data.get("punch_list"), dict):
            raise ValueError("report_v1.json punch_list must be a dict")
        if not isinstance(report_data.get("lexicons"), dict):
            raise ValueError("report_v1.json lexicons must be a dict")

        # Extract data from compiled report
        decision = report_data["decision"]
        totals = report_data["totals"]
        kpis = report_data["kpis"]
        file_status = report_data["file_status"]
        punch_list = report_data["punch_list"]
        lexicons = report_data["lexicons"]

        # Extract decision level and one-liner
        decision_level = decision.get("level", "review")
        one_liner = decision.get("one_liner", "")

        # Map decision level to emoji - use exact one_liner from decision
        if decision_level == "pass":
            banner_emoji = "✅"
        elif decision_level == "review":
            banner_emoji = "⚠️"
        else:  # fix
            banner_emoji = "❌"

        # Generate HTML content in fixed order
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

    <!-- 1. Decision Banner + One-liner -->
    <div class="decision-banner">
        <h2>{banner_emoji} {one_liner}</h2>
    </div>

    <!-- 2. Punch List -->
    {_render_punch_list_new(punch_list)}

    <!-- 3. File Status by Language -->
    <div class="file-status-section">
        <h2>File Status by Language</h2>
        {_render_file_status_by_language(file_status)}
    </div>

    <!-- 4. KPI Summary -->
    <div class="kpi-section">
        <h2>KPI Summary</h2>
        <div class="kpi-grid">
            <div class="kpi-item">
                <span class="kpi-label">Files:</span>
                <span class="kpi-value">{totals.get("files_total", 0)}</span>
            </div>
            <div class="kpi-item">
                <span class="kpi-label">Languages:</span>
                <span class="kpi-value">{totals.get("languages_total", 0)}</span>
            </div>
            <div class="kpi-item">
                <span class="kpi-label">Issues:</span>
                <span class="kpi-value">{totals.get("issues_total", 0)}</span>
            </div>
            <div class="kpi-item">
                <span class="kpi-label">Errors:</span>
                <span class="kpi-value">{kpis.get("errors_total", 0)}</span>
            </div>
            <div class="kpi-item">
                <span class="kpi-label">Warnings:</span>
                <span class="kpi-value">{kpis.get("warnings_total", 0)}</span>
            </div>
        </div>
        {_render_per_type_counts(kpis.get("per_type", {}))}
    </div>

    <!-- 5. Lexicons -->
    {_render_lexicons(lexicons)}
</body>
</html>"""

        # Write HTML file
        out_path.write_text(html_content, encoding="utf-8")

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


def _render_punch_list_new(punch_list: dict[str, list]) -> str:
    """Render punch list (errors and warnings) as HTML using new schema."""
    errors = punch_list.get("errors", [])
    warnings = punch_list.get("warnings", [])

    html = []

    # Always show Critical Issues section
    html.append('<div class="punch-list-section">')
    html.append("<h2>❌ Critical Issues</h2>")
    html.append('<div class="punch-list">')
    if errors:
        for error in errors:
            html.append('<div class="punch-item error">')
            html.append(f"  <h3>{error.get('file', 'Unknown')}: {error.get('type', 'Error')}</h3>")
            html.append(f"  <p><strong>Language:</strong> {error.get('language', 'Unknown')}</p>")
            if error.get("cue_index") is not None:
                html.append(f"  <p><strong>Cue Index:</strong> {error.get('cue_index')}</p>")
            html.append(f"  <p><strong>Summary:</strong> {error.get('human_summary', '')}</p>")
            html.append(
                f"  <p><strong>Suggested fix:</strong> {error.get('suggested_fix', '')}</p>"
            )
            # Render context if available
            context = error.get("context", {})
            if context:
                source = context.get("source", {})
                target = context.get("target", {})
                if source or target:
                    html.append("  <p><strong>Context:</strong></p>")
                    if source:
                        html.append("  <p><strong>Source context:</strong></p>")
                        html.append(
                            "  <pre>"
                            + "\n".join([f"{k}: {v}" for k, v in source.items() if v])
                            + "</pre>"
                        )
                    if target:
                        html.append("  <p><strong>Target context:</strong></p>")
                        html.append(
                            "  <pre>"
                            + "\n".join([f"{k}: {v}" for k, v in target.items() if v])
                            + "</pre>"
                        )
            html.append("</div>")
    else:
        html.append("<p>No critical issues found.</p>")
    html.append("</div>")
    html.append("</div>")

    # Always show Warnings section
    html.append('<div class="punch-list-section">')
    html.append("<h2>⚠️ Warnings</h2>")
    html.append('<div class="punch-list">')
    if warnings:
        for warning in warnings:
            html.append('<div class="punch-item warning">')
            html.append(
                f"  <h3>{warning.get('file', 'Unknown')}: {warning.get('type', 'Warning')}</h3>"
            )
            html.append(f"  <p><strong>Language:</strong> {warning.get('language', 'Unknown')}</p>")
            if warning.get("cue_index") is not None:
                html.append(f"  <p><strong>Cue Index:</strong> {warning.get('cue_index')}</p>")
            html.append(f"  <p><strong>Summary:</strong> {warning.get('human_summary', '')}</p>")
            html.append(
                f"  <p><strong>Suggested fix:</strong> {warning.get('suggested_fix', '')}</p>"
            )
            # Render context if available
            context = warning.get("context", {})
            if context:
                source = context.get("source", {})
                target = context.get("target", {})
                if source or target:
                    html.append("  <p><strong>Context:</strong></p>")
                    if source:
                        html.append("  <p><strong>Source context:</strong></p>")
                        html.append(
                            "  <pre>"
                            + "\n".join([f"{k}: {v}" for k, v in source.items() if v])
                            + "</pre>"
                        )
                    if target:
                        html.append("  <p><strong>Target context:</strong></p>")
                        html.append(
                            "  <pre>"
                            + "\n".join([f"{k}: {v}" for k, v in target.items() if v])
                            + "</pre>"
                        )
            html.append("</div>")
    else:
        html.append("<p>No warnings found.</p>")
    html.append("</div>")
    html.append("</div>")

    if not errors and not warnings:
        html.append('<div class="punch-list-section">')
        html.append("<h2>✅ No Issues Found</h2>")
        html.append("<p>All files passed evaluation with no errors or warnings.</p>")
        html.append("</div>")

    return "\n".join(html)


def _render_file_status_by_language(file_status: dict[str, dict[str, str]]) -> str:
    """Render file status by language as HTML table."""
    html = []

    for lang_code in sorted(file_status.keys()):
        files = file_status[lang_code]
        ready_count = sum(1 for status in files.values() if status == "ready")
        review_count = sum(1 for status in files.values() if status == "review")
        error_count = sum(1 for status in files.values() if status == "error")

        html.append('<div class="language-status">')
        html.append(f"  <h3>{lang_code.upper()}</h3>")
        html.append('  <div class="status-summary">')
        html.append(f'    <span class="status-ready">✅ Ready: {ready_count}</span>')
        html.append(f'    <span class="status-review">⚠️ Review: {review_count}</span>')
        html.append(f'    <span class="status-error">❌ Error: {error_count}</span>')
        html.append("  </div>")
        html.append('  <div class="file-list">')

        for file_path in sorted(files.keys()):
            status = files[file_path]
            if status == "ready":
                emoji = "✅"
                css_class = "status-ready"
            elif status == "review":
                emoji = "⚠️"
                css_class = "status-review"
            elif status == "error":
                emoji = "❌"
                css_class = "status-error"
            else:
                emoji = "❓"
                css_class = "status-unknown"

            html.append(f'    <div class="file-item {css_class}">')
            html.append(f'      <span class="file-emoji">{emoji}</span>')
            html.append(f'      <span class="file-name">{file_path}</span>')
            html.append("    </div>")

        html.append("  </div>")
        html.append("</div>")

    return "\n".join(html)


def _render_per_type_counts(per_type: dict[str, int]) -> str:
    """Render per-type issue counts as HTML."""
    if not per_type:
        return ""

    html = []
    html.append('<div class="per-type-counts">')
    html.append("  <h3>Issues by Type</h3>")
    html.append('  <div class="type-grid">')

    for issue_type, count in per_type.items():
        if count > 0:
            html.append('    <div class="type-item">')
            html.append(
                f'      <span class="type-name">{issue_type.replace("_", " ").title()}</span>'
            )
            html.append(f'      <span class="type-count">{count}</span>')
            html.append("    </div>")

    html.append("  </div>")
    html.append("</div>")

    return "\n".join(html)


def _render_lexicons(lexicons: dict[str, any]) -> str:
    """Render DNT and termbases as HTML."""
    html = []
    html.append('<div class="lexicons-section">')
    html.append("  <h2>Lexicons</h2>")

    # DNT Terms
    dnt = lexicons.get("dnt", {})
    html.append('  <div class="dnt-section">')
    html.append("    <h3>DNT Terms</h3>")
    if dnt.get("count", 0) > 0:
        html.append(f"    <p><strong>Count:</strong> {dnt.get('count', 0)}</p>")
        html.append('    <div class="dnt-sample">')
        html.append("      <p><strong>Sample:</strong></p>")
        html.append("      <ul>")
        for term in dnt.get("sample", []):
            html.append(f"        <li><code>{term}</code></li>")
        html.append("      </ul>")
        html.append("    </div>")
    else:
        html.append("    <p><em>None</em></p>")
    html.append("  </div>")

    # Termbases
    termbases = lexicons.get("termbases", {})
    html.append('  <div class="termbases-section">')
    html.append("    <h3>Termbases</h3>")
    if termbases:
        for lang_code in sorted(termbases.keys()):
            tb = termbases[lang_code]
            html.append('    <div class="termbase-lang">')
            html.append(f"      <h4>{lang_code.upper()}</h4>")
            html.append(f"      <p><strong>Count:</strong> {tb.get('count', 0)}</p>")
            if tb.get("sample"):
                html.append('      <div class="termbase-sample">')
                html.append("        <p><strong>Sample:</strong></p>")
                html.append("        <ul>")
                for entry in tb.get("sample", []):
                    source = entry.get("source", "")
                    target = entry.get("target", "")
                    html.append(f"          <li><code>{source}</code> → <code>{target}</code></li>")
                html.append("        </ul>")
                html.append("      </div>")
            html.append("    </div>")
    else:
        html.append("    <p><em>None</em></p>")
    html.append("  </div>")

    html.append("</div>")
    return "\n".join(html)


def _render_punch_list(punch_list: dict[str, list]) -> str:
    """Render punch list (errors and warnings) as HTML."""
    errors = punch_list.get("errors", [])
    warnings = punch_list.get("warnings", [])

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
