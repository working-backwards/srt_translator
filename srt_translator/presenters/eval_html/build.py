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


def build_eval_html(json_path: Path, out_path: Path | None = None) -> Path:
    """Generate HTML report with unified top sections: banner, next steps, and KPIs.

    Reads eval_report.json and ai_config.json with strict validation.
    Fails fast on missing/invalid inputs.
    """
    # Set up logging if available
    logger = logging.getLogger(__name__)

    # Default output path
    if out_path is None:
        out_path = json_path.with_suffix(".html")

    try:
        # Load CSS resource
        css_text = (
            importlib.resources.files("srt_translator.presenters.eval_html.assets")
            .joinpath("eval.css")
            .read_text(encoding="utf-8")
        )

        # Load and validate eval_report.json
        eval_data = _load_json_or_raise(
            json_path, ["files_total", "languages_total", "issues_total"]
        )

        # Load and validate ai_config.json (must be in same directory)
        ai_config_path = json_path.parent / "ai_config.json"
        ai_config_data = _load_json_or_raise(ai_config_path, ["dnt_terms", "termbase"])

        # Validate field types
        if not isinstance(eval_data["files_total"], int):
            raise ValueError("eval_report.json files_total must be an integer")
        if not isinstance(eval_data["languages_total"], int):
            raise ValueError("eval_report.json languages_total must be an integer")
        if not isinstance(eval_data["issues_total"], int):
            raise ValueError("eval_report.json issues_total must be an integer")
        if not isinstance(ai_config_data["dnt_terms"], list):
            raise ValueError("ai_config.json dnt_terms must be a list")
        if not isinstance(ai_config_data["termbase"], dict):
            raise ValueError("ai_config.json termbase must be a dict")

        # Compute status and KPIs
        status = _compute_status(eval_data)
        kpis = _kpis(eval_data, ai_config_data)
        what_to_do = _what_to_do_next(status)

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
                <span class="kpi-label">Files total:</span>
                <span class="kpi-value">{kpis["files_total"]}</span>
            </div>
            <div class="kpi-item">
                <span class="kpi-label">Languages:</span>
                <span class="kpi-value">{kpis["languages_total"]}</span>
            </div>
            <div class="kpi-item">
                <span class="kpi-label">Issues (critical):</span>
                <span class="kpi-value">{kpis["issues_total"]}</span>
            </div>
            <div class="kpi-item">
                <span class="kpi-label">Warnings (non-critical):</span>
                <span class="kpi-value">{kpis["warnings_total"]}</span>
            </div>
            <div class="kpi-item">
                <span class="kpi-label">Detected source language:</span>
                <span class="kpi-value">{kpis["source_language"]}</span>
            </div>
            <div class="kpi-item">
                <span class="kpi-label">DNT coverage:</span>
                <span class="kpi-value">{kpis["dnt_coverage"]}</span>
            </div>
            <div class="kpi-item">
                <span class="kpi-label">Termbase coverage:</span>
                <span class="kpi-value">{kpis["termbase_coverage"]}</span>
            </div>
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
        error_msg = f"Invalid JSON in {json_path}: {e}"
        if logger:
            logger.error(error_msg)
        raise ValueError(error_msg) from e
    except Exception as e:
        error_msg = f"Failed to generate HTML report: {e}"
        if logger:
            logger.error(error_msg)
        raise ValueError(error_msg) from e
