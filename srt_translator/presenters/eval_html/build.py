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
                    languages_section.append(f"<td>{_format_number(total_issues)}</td>")
                    languages_section.append(f"<td>{_format_number(missing_translation)}</td>")
                    languages_section.append(f"<td>{_format_number(untranslated_after_dnt)}</td>")
                    languages_section.append(f"<td>{_format_number(timing_fail)}</td>")
                    languages_section.append(f"<td>{_format_number(parity_issue)}</td>")
                    languages_section.append("</tr>")

                languages_section.append("</tbody>")
                languages_section.append("</table>")

            languages_section.append("</div>")

        languages_section.append("</div>")
        languages_html = "\n".join(languages_section)

        # Generate DNT drill-down section
        dnt_section = []
        dnt_section.append('<div class="dnt-section">')
        dnt_section.append("<h2>DNT Terms</h2>")

        # Collect DNT terms and their occurrences
        dnt_terms: dict[str, list[dict[str, str | dict[str, Any]]]] = {}
        for lang_code in sorted_languages:
            lang_data = languages[lang_code]
            for file_data in lang_data.get("files", []):
                issues = file_data.get("issues", {})
                untranslated_after_dnt = issues.get("untranslated_after_dnt", [])
                for issue in untranslated_after_dnt:
                    term = issue.get("original", issue.get("src", ""))
                    if term:
                        if term not in dnt_terms:
                            dnt_terms[term] = []
                        dnt_terms[term].append(
                            {
                                "language": lang_code,
                                "file": file_data.get(
                                    "target_file", file_data.get("file_name", "")
                                ),
                                "context": issue.get("context", {}),
                            }
                        )

        if not dnt_terms:
            dnt_section.append('<p class="no-issues">No DNT issues</p>')
        else:
            # Sort terms for deterministic display
            sorted_dnt_terms = sorted(dnt_terms.keys())
            dnt_section.append('<table class="dnt-table">')
            dnt_section.append("<thead>")
            dnt_section.append("<tr>")
            dnt_section.append("<th>DNT Term</th>")
            dnt_section.append("<th>Total Occurrences</th>")
            dnt_section.append("</tr>")
            dnt_section.append("</thead>")
            dnt_section.append("<tbody>")

            for term in sorted_dnt_terms:
                occurrences = dnt_terms[term]
                dnt_section.append("<tr>")
                dnt_section.append(f"<td>{term}</td>")
                dnt_section.append(f"<td>{_format_number(len(occurrences))}</td>")
                dnt_section.append("</tr>")

            dnt_section.append("</tbody>")
            dnt_section.append("</table>")

            # Add drill-down details for each term
            for term in sorted_dnt_terms:
                occurrences = dnt_terms[term]
                # Sort occurrences by language, then by file for deterministic display
                sorted_occurrences = sorted(occurrences, key=lambda x: (x["language"], x["file"]))
                dnt_section.append('<details class="dnt-details">')
                dnt_section.append(
                    f'<summary>Details for "{term}" ({_format_number(len(occurrences))} occurrences)</summary>'
                )
                dnt_section.append('<div class="dnt-occurrences">')

                for occurrence in sorted_occurrences:
                    dnt_section.append('<div class="dnt-occurrence">')
                    dnt_section.append(f"<strong>Language:</strong> {occurrence['language']}<br>")
                    dnt_section.append(f"<strong>File:</strong> {occurrence['file']}<br>")

                    # Add context if available
                    context = occurrence.get("context", {})
                    if isinstance(context, dict):
                        target_context = context.get("target", [])
                        if isinstance(target_context, list) and target_context:
                            dnt_section.append("<strong>Context:</strong><br>")
                            for item in target_context[:3]:  # Show first 3 context lines
                                if isinstance(item, (list, tuple)) and len(item) >= 2:
                                    idx, text = item[0], item[1]
                                    dnt_section.append(f"  {idx}: {text}<br>")

                    dnt_section.append("</div>")

                dnt_section.append("</div>")
                dnt_section.append("</details>")

        dnt_section.append("</div>")
        dnt_html = "\n".join(dnt_section)

        # Generate termbase violations drill-down section
        termbase_section = []
        termbase_section.append('<div class="termbase-section">')
        termbase_section.append("<h2>Termbase Violations</h2>")

        # Collect termbase violations per language
        termbase_violations: dict[str, list[dict[str, str | dict[str, Any]]]] = {}
        for lang_code in sorted_languages:
            lang_data = languages[lang_code]
            violations = []
            for file_data in lang_data.get("files", []):
                issues = file_data.get("issues", {})
                missing_translation = issues.get("missing_translation", [])
                for issue in missing_translation:
                    violations.append(
                        {
                            "file": file_data.get("target_file", file_data.get("file_name", "")),
                            "original": issue.get("original", issue.get("src", "")),
                            "target": issue.get("target", issue.get("tgt", "")),
                            "context": issue.get("context", {}),
                        }
                    )

            if violations:
                termbase_violations[lang_code] = violations

        if not termbase_violations:
            termbase_section.append('<p class="no-issues">No termbase issues</p>')
        else:
            for lang_code in sorted(termbase_violations.keys()):
                violations = termbase_violations[lang_code]
                # Sort violations by file, then by original text for deterministic display
                sorted_violations = sorted(violations, key=lambda x: (x["file"], x["original"]))
                termbase_section.append('<details class="termbase-details">')
                termbase_section.append(
                    f"<summary>{lang_code} ({_format_number(len(violations))} violations)</summary>"
                )
                termbase_section.append('<div class="termbase-violations">')

                for violation in sorted_violations:
                    termbase_section.append('<div class="termbase-violation">')
                    termbase_section.append(f"<strong>File:</strong> {violation['file']}<br>")
                    termbase_section.append(
                        f"<strong>Original:</strong> {violation['original']}<br>"
                    )
                    termbase_section.append(f"<strong>Target:</strong> {violation['target']}<br>")

                    # Add context if available
                    context = violation.get("context", {})
                    if isinstance(context, dict):
                        target_context = context.get("target", [])
                        if isinstance(target_context, list) and target_context:
                            termbase_section.append("<strong>Context:</strong><br>")
                            for item in target_context[:3]:  # Show first 3 context lines
                                if isinstance(item, (list, tuple)) and len(item) >= 2:
                                    idx, text = item[0], item[1]
                                    termbase_section.append(f"  {idx}: {text}<br>")

                    termbase_section.append("</div>")

                termbase_section.append("</div>")
                termbase_section.append("</details>")

        termbase_section.append("</div>")
        termbase_html = "\n".join(termbase_section)

        # Generate HTML with KPI header, languages section, and drill-downs
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
                <span class="kpi-value">{_format_number(files_total)}</span>
            </div>
            <div class="kpi-item">
                <span class="kpi-label">Languages Total:</span>
                <span class="kpi-value">{_format_number(languages_total)}</span>
            </div>
            <div class="kpi-item">
                <span class="kpi-label">Issues Total:</span>
                <span class="kpi-value">{_format_number(issues_total)}</span>
            </div>
        </div>
        <div class="languages-list">
            <span class="kpi-label">Target Languages:</span>
            <span class="kpi-value">{", ".join(sorted_languages)}</span>
        </div>
    </div>

    {languages_html}

    {dnt_html}

    {termbase_html}
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
