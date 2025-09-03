from __future__ import annotations

import importlib.resources
import json
import logging
from pathlib import Path


def build_eval_html(json_path: Path, out_path: Path | None = None) -> Path:
    """Minimal HTML presenter implementation.

    Reads eval_report.json and generates HTML with inline CSS.
    Fails fast on missing/invalid inputs.
    """
    # Set up logging if available
    logger = logging.getLogger(__name__)

    # Default output path
    if out_path is None:
        out_path = json_path.with_suffix(".html")

    try:
        # Load resources using importlib.resources
        css_text = (
            importlib.resources.files("srt_translator.presenters.eval_html.assets")
            .joinpath("eval.css")
            .read_text(encoding="utf-8")
        )

        # Read and parse JSON (validate it exists and is valid)
        json_data = json.loads(json_path.read_text(encoding="utf-8"))

        # Extract KPIs from JSON data
        languages = json_data.get("languages", {})

        # Calculate totals
        files_total = sum(len(lang_data.get("files", [])) for lang_data in languages.values())
        languages_total = len(languages)

        # Count total issues across all files
        issues_total = 0
        for lang_data in languages.values():
            for file_data in lang_data.get("files", []):
                issues = file_data.get("issues", {})
                issues_total += len(issues.get("missing_translation", []))
                issues_total += len(issues.get("untranslated_after_dnt", []))
                if issues.get("timing_fail"):
                    issues_total += 1
                if not file_data.get("metrics", {}).get("parity_ok", True):
                    issues_total += 1

        # Sort target languages by code for deterministic display
        sorted_languages = sorted(languages.keys())

        # Generate per-language tables
        languages_section = []
        languages_section.append('<div class="languages-section">')
        languages_section.append("<h2>Languages</h2>")

        for lang_code in sorted_languages:
            lang_data = languages[lang_code]
            files = lang_data.get("files", [])

            languages_section.append('<div class="language-section">')
            languages_section.append(f"<h3>{lang_code}</h3>")

            if not files:
                languages_section.append('<p class="no-files">No files</p>')
            else:
                # Sort files by path for determinism
                sorted_files = sorted(
                    files, key=lambda f: f.get("target_file", f.get("file_name", ""))
                )

                languages_section.append('<table class="files-table">')
                languages_section.append("<thead>")
                languages_section.append("<tr>")
                languages_section.append("<th>File Path</th>")
                languages_section.append("<th>Total Issues</th>")
                languages_section.append("<th>Missing Translation</th>")
                languages_section.append("<th>Untranslated After DNT</th>")
                languages_section.append("<th>Timing Fail</th>")
                languages_section.append("<th>Parity Issue</th>")
                languages_section.append("</tr>")
                languages_section.append("</thead>")
                languages_section.append("<tbody>")

                for file_data in sorted_files:
                    file_path = file_data.get("target_file", file_data.get("file_name", ""))
                    issues = file_data.get("issues", {})

                    # Count issues by type
                    missing_translation = len(issues.get("missing_translation", []))
                    untranslated_after_dnt = len(issues.get("untranslated_after_dnt", []))
                    timing_fail = 1 if issues.get("timing_fail") else 0
                    parity_issue = (
                        1 if not file_data.get("metrics", {}).get("parity_ok", True) else 0
                    )
                    total_issues = (
                        missing_translation + untranslated_after_dnt + timing_fail + parity_issue
                    )

                    languages_section.append("<tr>")
                    languages_section.append(f"<td>{file_path}</td>")
                    languages_section.append(f"<td>{total_issues}</td>")
                    languages_section.append(f"<td>{missing_translation}</td>")
                    languages_section.append(f"<td>{untranslated_after_dnt}</td>")
                    languages_section.append(f"<td>{timing_fail}</td>")
                    languages_section.append(f"<td>{parity_issue}</td>")
                    languages_section.append("</tr>")

                languages_section.append("</tbody>")
                languages_section.append("</table>")

            languages_section.append("</div>")

        languages_section.append("</div>")
        languages_html = "\n".join(languages_section)

        # Generate HTML with KPI header and languages section
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

    <div class="kpi-header">
        <h2>Summary</h2>
        <div class="kpi-grid">
            <div class="kpi-item">
                <span class="kpi-label">Files Total:</span>
                <span class="kpi-value">{files_total}</span>
            </div>
            <div class="kpi-item">
                <span class="kpi-label">Languages Total:</span>
                <span class="kpi-value">{languages_total}</span>
            </div>
            <div class="kpi-item">
                <span class="kpi-label">Issues Total:</span>
                <span class="kpi-value">{issues_total}</span>
            </div>
        </div>
        <div class="languages-list">
            <span class="kpi-label">Target Languages:</span>
            <span class="kpi-value">{", ".join(sorted_languages)}</span>
        </div>
    </div>

    {languages_html}
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
