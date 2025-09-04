from __future__ import annotations

import importlib.resources
import json
import logging
from pathlib import Path


def _format_number(value: int | float) -> str:
    """Format numeric values consistently, avoiding locale dependence."""
    if isinstance(value, float):
        # Format floating point numbers to 1 decimal place
        return f"{value:.1f}"
    else:
        # Format integers as-is
        return str(value)


def build_eval_html(json_path: Path, out_path: Path | None = None) -> Path:
    """Generate HTML report with decision banner, what to do next, and KPIs.

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

        # Read and validate eval_report.json
        if not json_path.exists():
            error_msg = f"eval_report.json not found: {json_path}"
            if logger:
                logger.error(error_msg)
            raise ValueError(error_msg)

        eval_data = json.loads(json_path.read_text(encoding="utf-8"))

        # Validate required fields in eval_report.json
        required_eval_fields = ["files_total", "languages_total", "issues_total"]
        missing_eval_fields = [field for field in required_eval_fields if field not in eval_data]
        if missing_eval_fields:
            error_msg = f"eval_report.json missing required keys: {', '.join(missing_eval_fields)}"
            if logger:
                logger.error(error_msg)
            raise ValueError(error_msg)

        # Validate field types
        if not isinstance(eval_data["files_total"], int):
            raise ValueError("eval_report.json files_total must be an integer")
        if not isinstance(eval_data["languages_total"], int):
            raise ValueError("eval_report.json languages_total must be an integer")
        if not isinstance(eval_data["issues_total"], int):
            raise ValueError("eval_report.json issues_total must be an integer")

        # Read and validate ai_config.json (must be in same directory)
        ai_config_path = json_path.parent / "ai_config.json"
        if not ai_config_path.exists():
            error_msg = f"ai_config.json must be located alongside eval_report.json; not found at: {ai_config_path}"
            if logger:
                logger.error(error_msg)
            raise ValueError(error_msg)

        ai_config_data = json.loads(ai_config_path.read_text(encoding="utf-8"))

        # Validate required fields in ai_config.json
        if "dnt_terms" not in ai_config_data:
            raise ValueError("ai_config.json missing required key: dnt_terms")
        if "termbase" not in ai_config_data:
            raise ValueError("ai_config.json missing required key: termbase")

        if not isinstance(ai_config_data["dnt_terms"], list):
            raise ValueError("ai_config.json dnt_terms must be a list")
        if not isinstance(ai_config_data["termbase"], dict):
            raise ValueError("ai_config.json termbase must be a dict")

        # Extract values from eval_report.json
        files_total = eval_data["files_total"]
        languages_total = eval_data["languages_total"]
        issues_total = eval_data["issues_total"]
        source_language = eval_data.get("source_language", "")

        # Handle source language display
        source_display = source_language if source_language else "Unknown"

        # Extract language structure to compute affected languages
        languages = eval_data.get("languages", {})
        if not isinstance(languages, dict):
            raise ValueError("eval_report.json must contain languages dict")

        # Compute affected languages (languages with any issues)
        affected_languages = []
        for lang_code, lang_data in languages.items():
            if not isinstance(lang_data, dict):
                continue

            # Sum issue counts for this language
            lang_issues = 0
            for file_data in lang_data.get("files", []):
                if not isinstance(file_data, dict):
                    continue

                issues = file_data.get("issues", {})
                if not isinstance(issues, dict):
                    continue

                lang_issues += len(issues.get("missing_translation", []))
                lang_issues += len(issues.get("untranslated_after_dnt", []))
                lang_issues += 1 if issues.get("timing_fail") else 0

            if lang_issues > 0:
                affected_languages.append(lang_code)

        # Sort affected languages for deterministic display
        affected_languages.sort()
        affected_count = len(affected_languages)

        # Extract values from ai_config.json
        dnt_terms = ai_config_data["dnt_terms"]
        termbase = ai_config_data["termbase"]

        # Compute DNT coverage
        dnt_coverage = "Present" if len(dnt_terms) > 0 else "Absent"

        # Compute termbase coverage
        target_languages = list(languages.keys())
        target_languages.sort()  # Deterministic ordering

        termbase_entries_by_lang = {}
        languages_with_entries = 0

        for lang_code in target_languages:
            entries = termbase.get(lang_code, [])
            if not isinstance(entries, list):
                entries = []
            count = len(entries)
            termbase_entries_by_lang[lang_code] = count
            if count > 0:
                languages_with_entries += 1

        # Determine termbase coverage
        if languages_with_entries == 0:
            termbase_coverage = "None"
        elif languages_with_entries == len(target_languages):
            termbase_coverage = "Full"
        else:
            termbase_coverage = "Partial"

        # Generate termbase entries display
        termbase_entries_display = []
        for lang_code in target_languages:
            count = termbase_entries_by_lang[lang_code]
            if count > 0:
                termbase_entries_display.append(f"{lang_code}: {count}")

        if termbase_entries_display:
            termbase_entries_text = ", ".join(termbase_entries_display)
        else:
            termbase_entries_text = "None"

        # Generate decision banner
        if issues_total == 0:
            banner_text = "✅ Publish readiness: Ready to publish"
            summary_text = "No issues detected."
        else:
            banner_text = "❌ Publish readiness: Needs fixes"
            affected_codes_str = ", ".join(affected_languages)
            summary_text = f"{issues_total} items to fix across {affected_count} languages ({affected_codes_str})."

        # Generate what to do next
        if issues_total > 0:
            what_to_do_next = [
                f"Fix {issues_total} issues (see drill-downs below for exact captions).",
                "Re-run Evaluate.",
                "If all clear, export and publish.",
            ]
        else:
            what_to_do_next = ["Spot-check a few captions for flow and brand terms, then publish."]

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

    <!-- Decision Banner -->
    <div class="decision-banner">
        <h2>{banner_text}</h2>
        <p>{summary_text}</p>
    </div>

    <!-- What to do next -->
    <div class="what-to-do-next">
        <h2>What to do next</h2>
        <ol>
{chr(10).join(f"            <li>{item}</li>" for item in what_to_do_next)}
        </ol>
    </div>

    <!-- KPIs -->
    <div class="kpi-section">
        <h2>KPIs</h2>
        <div class="kpi-grid">
            <div class="kpi-item">
                <span class="kpi-label">Files total:</span>
                <span class="kpi-value">{files_total}</span>
            </div>
            <div class="kpi-item">
                <span class="kpi-label">Languages:</span>
                <span class="kpi-value">{languages_total}</span>
            </div>
            <div class="kpi-item">
                <span class="kpi-label">Issues total:</span>
                <span class="kpi-value">{issues_total}</span>
            </div>
            <div class="kpi-item">
                <span class="kpi-label">Source language:</span>
                <span class="kpi-value">{source_display}</span>
            </div>
            <div class="kpi-item">
                <span class="kpi-label">DNT coverage:</span>
                <span class="kpi-value">{dnt_coverage}</span>
            </div>
            <div class="kpi-item">
                <span class="kpi-label">Termbase coverage:</span>
                <span class="kpi-value">{termbase_coverage}</span>
            </div>
            <div class="kpi-item">
                <span class="kpi-label">Termbase entries:</span>
                <span class="kpi-value">{termbase_entries_text}</span>
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
