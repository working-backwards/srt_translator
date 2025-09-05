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


def _compute_status(eval_json: dict[str, Any]) -> str:
    """Compute status based on evaluation results: critical, warning, or ready."""
    # Check for critical issues
    languages = eval_json.get("languages", {})

    for _lang_code, lang_data in languages.items():
        if not isinstance(lang_data, dict):
            continue

        files_data = lang_data.get("files", {})
        if isinstance(files_data, list):
            # Handle old format: files is a list, issues are lists
            for file_data in files_data:
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
        else:
            # Handle new format: files is a dict, issues are integers
            for file_data in files_data.values():
                if not isinstance(file_data, dict):
                    continue

                issues = file_data.get("issues", {})
                if not isinstance(issues, dict):
                    continue

                # Critical: DNT violations, termbase violations, missing translations, timing fails
                # In new format, these are integers, not lists
                if (
                    issues.get("untranslated_after_dnt", 0) > 0
                    or issues.get("missing_translation", 0) > 0
                    or issues.get("timing_fail", 0) > 0
                ):
                    return "critical"

    # Check for warnings (soft CPS overage, timing drift)
    # For now, assume no warnings if no critical issues
    # TODO: Implement warning detection based on soft thresholds
    return "ready"


def _compute_warnings(eval_json: dict[str, Any]) -> int:
    """Compute total warning count from evaluation results."""
    # For now, return 0 - warnings will be implemented in future iterations
    # This maintains the interface while keeping the change minimal
    return 0


def _kpis(eval_json: dict[str, Any], ai_config: dict[str, Any]) -> dict[str, Any]:
    """Compute KPI values for display."""
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
    source_language = eval_json.get("source_language", "")
    if not source_language:
        # Try to get from ai_config
        source_lang_info = ai_config.get("source_language", {})
        if isinstance(source_lang_info, dict):
            source_language = source_lang_info.get("normalized_name") or source_lang_info.get(
                "name", ""
            )

    return {
        "files_total": eval_json["files_total"],
        "languages_total": eval_json["languages_total"],
        "issues_total": eval_json["issues_total"],
        "warnings_total": _compute_warnings(eval_json),
        "source_language": source_language or "Unknown",
        "dnt_coverage": dnt_coverage,
        "termbase_coverage": termbase_coverage,
    }


def _what_to_do_next(status: str) -> list[str]:
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
