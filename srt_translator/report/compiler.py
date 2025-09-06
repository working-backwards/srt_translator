"""Report compiler that creates report_v1.json from eval_report.json and ai_config.json."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

# LanguageConfig not used in this module


def compile_report(artifacts_dir: Path) -> Path:
    """
    Compile report_v1.json from eval_report.json and ai_config.json.

    Args:
        artifacts_dir: Path to the artifacts directory containing eval_report.json and ai_config.json

    Returns:
        Path to the generated report_v1.json

    Raises:
        ValueError: If required files are missing or malformed
    """
    logger = logging.getLogger("srt_translator.report.compiler")

    # Resolve input paths
    eval_path = artifacts_dir / "eval_report.json"
    ai_path = artifacts_dir / "ai_config.json"

    # Fail fast if either missing
    if not eval_path.exists():
        raise ValueError(f"eval_report.json not found at: {eval_path}")
    if not ai_path.exists():
        raise ValueError(f"ai_config.json not found at: {ai_path}")

    # Load and validate inputs
    try:
        with open(eval_path, "r", encoding="utf-8") as f:
            eval_data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {eval_path}: {e}") from e

    try:
        with open(ai_path, "r", encoding="utf-8") as f:
            ai_data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {ai_path}: {e}") from e

    # Validate required fields in eval_data
    required_eval_keys = {"files_total", "languages_total", "issues_total", "languages"}
    missing_keys = required_eval_keys - set(eval_data.keys())
    if missing_keys:
        raise ValueError(
            f"eval_report.json missing required keys: {', '.join(sorted(missing_keys))}"
        )

    # Validate required fields in ai_data
    required_ai_keys = {"dnt_terms", "termbase"}
    missing_ai_keys = required_ai_keys - set(ai_data.keys())
    if missing_ai_keys:
        raise ValueError(
            f"ai_config.json missing required keys: {', '.join(sorted(missing_ai_keys))}"
        )

    # Compute totals and status
    files_total = eval_data["files_total"]
    languages_total = eval_data["languages_total"]

    # Compute errors and warnings by reclassifying issues
    errors_total = 0
    warnings_total = 0

    # Count issues by type across all languages and files
    for _lang_code, lang_data in eval_data["languages"].items():
        for _file_path, file_data in lang_data.get("files", {}).items():
            # Reclassify: missing_translation is now WARNING, not ERROR
            missing_count = file_data.get("missing_translation", 0)
            warnings_total += missing_count

            # untranslated_after_dnt and timing_fail are ERRORS
            untrans_dnt_count = file_data.get("untranslated_after_dnt", 0)
            timing_fail_count = file_data.get("timing_fail", 0)
            errors_total += untrans_dnt_count + timing_fail_count

    # Determine overall status
    if errors_total > 0:
        decision_state = "FIX"
    elif warnings_total > 0:
        decision_state = "REVIEW"
    else:
        decision_state = "READY"

    # Generate one-liner
    one_liner = _generate_banner_and_steps(decision_state, errors_total, warnings_total)

    # KPIs are computed directly in the report structure

    # Compute file status (per-file READY/REVIEW/FIX)
    file_status = _compute_file_status(eval_data)

    # Extract lexicons
    lexicons = _extract_lexicons(ai_data)

    # Extract punch list (errors and warnings)
    punch_list = _extract_punch_list(eval_data)

    # Build the compiled report with exact schema
    report_v1 = {
        "version": "1.0",
        "meta": {
            "batch_id": eval_data.get("batch_label", ""),
            "created_at": eval_data.get("timestamp", ""),
            "source_language": eval_data.get("source_language", "en"),
        },
        "decision": {
            "level": decision_state.lower(),  # pass, review, fix
            "one_liner": one_liner,
        },
        "kpis": {
            "files_total": files_total,
            "languages_total": languages_total,
            "issues_total": errors_total + warnings_total,
            "errors_total": errors_total,
            "warnings_total": warnings_total,
            "dnt_terms_count": len(lexicons.get("dnt_terms", [])),
            "termbase_languages_count": len(lexicons.get("termbase", {})),
        },
        "file_status": _convert_file_status_to_dict(file_status),
        "sections": {
            "errors": punch_list["errors"],
            "warnings": punch_list["warnings"],
        },
        "lexicons": lexicons,
    }

    # Write the compiled report
    output_path = artifacts_dir / "report_v1.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report_v1, f, ensure_ascii=False, indent=2)

    logger.info("Compiled report_v1.json → %s", output_path)
    return output_path


def _generate_banner_and_steps(
    state: str, errors_total: int, warnings_total: int
) -> tuple[str, str]:
    """Generate banner text and one-liner based on status."""
    if state == "READY":
        one_liner = "Everything looks great. Your translated files are ready to use."
    elif state == "REVIEW":
        one_liner = f"Review recommended: {warnings_total} warning(s) found."
    else:  # FIX
        one_liner = f"Fix required: {errors_total} error(s), {warnings_total} warning(s) found."

    return one_liner


def _compute_file_status(eval_data: Dict[str, Any]) -> List[Dict[str, str]]:
    """Compute per-file status (READY/REVIEW/FIX) sorted by file_path."""
    file_statuses = []

    for _lang_code, lang_data in eval_data["languages"].items():
        for file_path, file_data in lang_data.get("files", {}).items():
            # Count errors and warnings for this file
            errors = 0
            warnings = 0

            # Reclassify: missing_translation is WARNING
            missing_count = file_data.get("missing_translation", 0)
            warnings += missing_count

            # untranslated_after_dnt and timing_fail are ERRORS
            untrans_dnt_count = file_data.get("untranslated_after_dnt", 0)
            timing_fail_count = file_data.get("timing_fail", 0)
            errors += untrans_dnt_count + timing_fail_count

            # Determine file status
            if errors > 0:
                file_state = "FIX"
            elif warnings > 0:
                file_state = "REVIEW"
            else:
                file_state = "READY"

            file_statuses.append({"file_path": file_path, "status": file_state})

    # Sort by file_path for deterministic ordering
    file_statuses.sort(key=lambda x: x["file_path"])
    return file_statuses


def _convert_file_status_to_dict(
    file_status_list: List[Dict[str, str]],
) -> Dict[str, Dict[str, str]]:
    """Convert file status list to dict of dicts format: {lang: {file: status}}."""
    file_status_dict = {}

    for file_info in file_status_list:
        file_path = file_info.get("file_path", "")
        status = file_info.get("status", "unknown")

        # Extract language from file path or use a default
        # For now, we'll use a simple approach - this might need refinement
        # based on how the evaluator structures the data
        lang = "unknown"  # This should be extracted from the evaluator data

        if lang not in file_status_dict:
            file_status_dict[lang] = {}

        # Map status to new format
        if status == "READY":
            new_status = "ok"
        elif status == "REVIEW":
            new_status = "warning"
        elif status == "FIX":
            new_status = "error"
        else:
            new_status = "unknown"

        file_status_dict[lang][file_path] = new_status

    return file_status_dict


def _extract_punch_list(eval_data: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """Extract errors and warnings from evaluation data for punch list using new schema."""
    errors = []
    warnings = []

    for lang_code, lang_data in eval_data["languages"].items():
        for file_path, file_data in lang_data.get("files", {}).items():
            issues = file_data.get("issues", {})

            # Extract missing translation issues (WARNINGS)
            missing_issues = issues.get("missing_translation", [])
            # Handle case where missing_translation is a count instead of a list
            if isinstance(missing_issues, int):
                missing_issues = [
                    {"src": f"Missing translation {i + 1}", "tgt": "", "context": {}}
                    for i in range(missing_issues)
                ]
            for issue in missing_issues:
                warnings.append(
                    {
                        "lang": lang_code,
                        "file": file_path,
                        "subtitle": issue.get("cue", issue.get("idx")),
                        "type": "missing_translation",
                        "message": "This subtitle may be incomplete or missing context.",
                        "suggest_fix": "Check if the translation was cut off or if context was lost.",
                        "context": {
                            "target_window": issue.get("context", {}).get("target", []),
                            "source_window": issue.get("context", {}).get("source", []),
                        },
                    }
                )

            # Extract DNT violations (ERRORS)
            untrans_dnt_issues = issues.get("untranslated_after_dnt", [])
            # Handle case where untranslated_after_dnt is a count instead of a list
            if isinstance(untrans_dnt_issues, int):
                untrans_dnt_issues = [
                    {"src": f"DNT violation {i + 1}", "tgt": "", "context": {}}
                    for i in range(untrans_dnt_issues)
                ]
            for issue in untrans_dnt_issues:
                errors.append(
                    {
                        "lang": lang_code,
                        "file": file_path,
                        "subtitle": issue.get("cue", issue.get("idx")),
                        "type": "untranslated_after_dnt",
                        "message": "This term should not be translated according to your DNT list.",
                        "suggest_fix": "Keep the original term untranslated or add it to your DNT list.",
                        "context": {
                            "target_window": issue.get("context", {}).get("target", []),
                            "source_window": issue.get("context", {}).get("source", []),
                        },
                    }
                )

            # Extract timing failures (ERRORS)
            if issues.get("timing_fail", False):
                errors.append(
                    {
                        "lang": lang_code,
                        "file": file_path,
                        "subtitle": None,
                        "type": "timing_misaligned",
                        "message": "The subtitle timing doesn't match the source file.",
                        "suggest_fix": "Check subtitle timing and duration settings.",
                        "context": {"target_window": [], "source_window": []},
                    }
                )

    return {
        "errors": errors,
        "warnings": warnings,
    }


def _extract_lexicons(ai_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract DNT terms and termbase from ai_config.json."""
    dnt_terms = ai_data.get("dnt_terms", [])

    # Convert termbase to the expected format: {lang: [{source, preferred}]}
    termbase: Dict[str, List[Dict[str, str]]] = {}
    raw_termbase = ai_data.get("termbase", {})

    for lang_name, lang_termbase in raw_termbase.items():
        termbase[lang_name] = []
        for source, preferred in lang_termbase.items():
            termbase[lang_name].append({"source": source, "preferred": preferred})
        # Sort by source for deterministic ordering
        termbase[lang_name].sort(key=lambda x: x["source"])

    return {
        "dnt_terms": sorted(dnt_terms),  # Sort for deterministic ordering
        "termbase": termbase,
    }
