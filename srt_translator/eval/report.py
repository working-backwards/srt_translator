# srt_translator/eval/report.py
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

# v1.0: reporter is JSON-only. No SRT parsing/imports here.


# Display blanks as real empty lines; avoid glyphs like "(none)" that look odd to users.
EMPTY_CUE_PLACEHOLDER = ""


def _render_context_pairs(pairs: list[tuple[int, str]]) -> str:
    """
    Given [(index, text), ...] pairs from the evaluator, build a fenced code block.
    """
    if not pairs:
        return "```\n(context unavailable)\n```"
    lines = []
    for idx, txt in pairs:
        lines.append(f"{idx}: {txt or EMPTY_CUE_PLACEHOLDER}")
    return "```\n" + "\n".join(lines) + "\n```"


# This function is no longer needed since we use eval_parse_srt directly


# This function is no longer needed since we directly iterate over the languages structure


def _write_json_report(batch_root: Path, rollup: dict[str, Any], logger) -> Path:
    """
    Write eval_report.json with strict v2 format.

    Args:
        batch_root: Path to the batch directory
        rollup: Evaluation rollup data
        logger: Logger instance

    Returns:
        Path to the written JSON report
    """
    log = logger.getChild("report.json")

    # Extract per-language data from rollup
    per_language = {}
    languages = rollup.get("languages", {})

    for lang_code, lang_data in languages.items():
        per_language[lang_code] = {"files": {}}

        files = lang_data.get("files", [])

        # Process each file
        for file_data in files:
            file_path = file_data.get("target_rel", file_data.get("target_file", ""))

            # Extract v2 issues structure
            issues_counts = file_data.get("issues_counts", {})
            issues_detail = file_data.get("issues_detail", {})

            per_language[lang_code]["files"][file_path] = {
                "issues_counts": issues_counts,
                "issues_detail": issues_detail,
            }

    # Calculate totals
    files_total = sum(len(files) for lang_data in per_language.values() for files in [lang_data["files"]])
    languages_total = len(per_language)

    # Calculate total issues across all files and languages
    issues_total = 0
    for lang_data in per_language.values():
        for file_data in lang_data["files"].values():
            issues_counts = file_data.get("issues_counts", {})
            issues_total += sum(issues_counts.values())

    # Get lexicons from rollup
    lexicons = rollup.get("lexicons", {"dnt": {"count": 0, "sample": []}, "termbase": {}})

    # Build the v2 report according to rulebook structure
    json_report = {
        "version": "1.0",
        "totals": {
            "files_total": files_total,
            "languages_total": languages_total,
            "issues_total": issues_total,
        },
        "per_language": per_language,
        "lexicons": lexicons,
    }

    # Write to artifacts directory
    artifacts_dir = batch_root / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    json_path = artifacts_dir / "eval_report.json"

    try:
        with json_path.open("w", encoding="utf-8") as f:
            json.dump(json_report, f, ensure_ascii=False, indent=2)

        log.info(
            "Wrote eval_report.json: files=%d, langs=%d, issues=%d",
            json_report["totals"]["files_total"],
            json_report["totals"]["languages_total"],
            json_report["totals"]["issues_total"],
        )
        return json_path

    except Exception as e:
        log.error("Failed to build eval_report.json: %s", e)
        raise


def write_evaluator_json(artifacts_dir: Path, rollup: dict) -> Path:
    """Write eval_report.json to artifacts directory."""
    logger = logging.getLogger(__name__)

    # Ensure artifacts directory exists
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    # Write eval_report.json using existing function
    # Note: _write_json_report expects batch_root and writes to batch_root/artifacts/
    # Since we want to write directly to artifacts_dir, pass artifacts_dir.parent
    json_path = _write_json_report(artifacts_dir.parent, rollup, logger)

    logger.info("Wrote eval_report.json: %s", json_path)
    return json_path


def emit_all_reports(artifacts_dir: Path, rollup: dict) -> dict[str, Path]:
    """Orchestrator: write eval_report.json, compile report.json, render MD/HTML."""
    logger = logging.getLogger(__name__)

    # Ensure artifacts directory exists
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Write eval_report.json
    eval_json_path = write_evaluator_json(artifacts_dir, rollup)

    # Step 2: Verify ai_config.json exists in artifacts directory
    ai_config_path = artifacts_dir / "ai_config.json"
    if not ai_config_path.exists():
        raise ValueError(f"ai_config.json not found in artifacts directory: {ai_config_path}")

    # Step 3: Compile report.json
    from srt_translator.report import compile_report

    report_path = compile_report(artifacts_dir)
    logger.info("Compiled report.json: %s", report_path)

    # Step 4: Render markdown and HTML
    from srt_translator.presenters.eval_html.build import build_eval_html
    from srt_translator.presenters.eval_md.build import build_eval_md

    md_path = build_eval_md(report_path, artifacts_dir / "eval_report.md")
    html_path = build_eval_html(report_path, artifacts_dir / "eval_report.html")

    # Log all generated files
    logger.info("Wrote eval_report.json: %s", eval_json_path)
    logger.info("Compiled report.json: %s", report_path)
    logger.info("Wrote eval_report.md: %s", md_path)
    logger.info("Wrote eval_report.html: %s", html_path)

    return {
        "eval_report_json": eval_json_path,
        "report_json": report_path,
        "eval_report_md": md_path,
        "eval_report_html": html_path,
    }
