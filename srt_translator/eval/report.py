# srt_translator/eval/report.py
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict

# v1.0: reporter is JSON-only. No SRT parsing/imports here.


def _load_ai_config_from_artifacts(batch_root: Path) -> dict:
    """Load ai_config.json from artifacts directory with strict validation."""
    ai_config_path = batch_root / "artifacts" / "ai_config.json"
    if not ai_config_path.exists():
        raise ValueError(
            f"ai_config.json must be located alongside eval_report.json; not found at: {ai_config_path}"
        )

    try:
        return json.loads(ai_config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {ai_config_path}: {e}") from e


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


def _write_json_report(batch_root: Path, rollup: Dict[str, Any], logger) -> Path:
    """
    Write eval_report.json with strict EvalReportV1 format.

    Args:
        batch_root: Path to the batch directory
        rollup: Evaluation rollup data
        logger: Logger instance

    Returns:
        Path to the written JSON report
    """
    log = logger.getChild("report.json")

    # Extract per-language file counts from rollup
    per_language_file_counts = {}
    languages = rollup.get("languages", {})

    for lang_code, lang_data in languages.items():
        per_language_file_counts[lang_code] = {}
        files = lang_data.get("files", {})

        # Handle both list and dict formats
        if isinstance(files, list):
            # Full rollup format with files as list
            for file_data in files:
                file_path = file_data.get("target_file", "")
                issues = file_data.get("issues", {})

                # Extract issue counts
                missing_count = len(issues.get("missing_translation", []))
                untrans_dnt_count = len(issues.get("untranslated_after_dnt", []))
                timing_fail_count = 1 if issues.get("timing_fail") else 0

                per_language_file_counts[lang_code][file_path] = {
                    "missing_translation": missing_count,
                    "untranslated_after_dnt": untrans_dnt_count,
                    "timing_fail": timing_fail_count,
                }
        else:
            # Simplified format with files as dict
            for file_path, file_data in files.items():
                per_language_file_counts[lang_code][file_path] = {
                    "missing_translation": file_data.get("missing_translation", 0),
                    "untranslated_after_dnt": file_data.get("untranslated_after_dnt", 0),
                    "timing_fail": file_data.get("timing_fail", 0),
                }

    # Get source language
    source_language = rollup.get("original_language", {}).get("detected", "")

    # Build strict EvalReportV1
    from srt_translator.eval.assemble import build_eval_report_v1

    try:
        json_report = build_eval_report_v1(
            per_language_file_counts=per_language_file_counts,
            source_language=source_language,
        )

        # Write to artifacts directory
        artifacts_dir = batch_root / "artifacts"
        artifacts_dir.mkdir(exist_ok=True)

        json_path = artifacts_dir / "eval_report.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_report, f, ensure_ascii=False, indent=2)

        log.info(
            "Wrote strict eval_report.json (v1): files=%d, langs=%d, issues=%d",
            json_report["files_total"],
            json_report["languages_total"],
            json_report["issues_total"],
        )
        return json_path

    except Exception as e:
        log.error(f"Failed to build strict eval_report.json: {e}")
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
    """Orchestrator: write eval_report.json, compile report_v1.json, render MD/HTML."""
    logger = logging.getLogger(__name__)

    # Ensure artifacts directory exists
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Write eval_report.json
    eval_json_path = write_evaluator_json(artifacts_dir, rollup)

    # Step 2: Verify ai_config.json exists in artifacts directory
    ai_config_path = artifacts_dir / "ai_config.json"
    if not ai_config_path.exists():
        raise ValueError(f"ai_config.json not found in artifacts directory: {ai_config_path}")

    # Step 3: Compile report_v1.json
    from srt_translator.report import compile_report

    report_v1_path = compile_report(artifacts_dir)
    logger.info("Compiled report_v1.json: %s", report_v1_path)

    # Step 4: Render markdown and HTML
    from srt_translator.presenters.eval_html.build import build_eval_html
    from srt_translator.presenters.eval_md.build import build_eval_md

    md_path = build_eval_md(report_v1_path, artifacts_dir / "eval_report.md")
    html_path = build_eval_html(report_v1_path, artifacts_dir / "eval_report.html")

    # Log all generated files
    logger.info("Wrote eval_report.json: %s", eval_json_path)
    logger.info("Compiled report_v1.json: %s", report_v1_path)
    logger.info("Wrote eval_report.md: %s", md_path)
    logger.info("Wrote eval_report.html: %s", html_path)

    return {
        "eval_report_json": eval_json_path,
        "report_v1_json": report_v1_path,
        "eval_report_md": md_path,
        "eval_report_html": html_path,
    }
