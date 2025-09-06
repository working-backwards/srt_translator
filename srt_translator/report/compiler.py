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

    # Determine overall status using exact specification
    if errors_total == 0 and warnings_total == 0:
        decision_level = "pass"
        one_liner = "Everything looks great. Your translated files are ready to use."
    elif errors_total > 0:
        decision_level = "fix"
        one_liner = f"We found {errors_total} errors that must be fixed before publishing."
    else:  # only warnings
        decision_level = "review"
        one_liner = f"We found {warnings_total} warnings. Fix the items in the Punch List below."

    # Compute file status (per-file READY/REVIEW/FIX)
    file_status = _compute_file_status(eval_data)

    # Extract lexicons
    lexicons = _extract_lexicons(ai_data)

    # Extract punch list (errors and warnings) - this populates sections
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
            "level": decision_level,
            "one_liner": one_liner,
        },
        "totals": {
            "files_total": files_total,
            "languages_total": languages_total,
            "issues_total": errors_total + warnings_total,
        },
        "kpis": {
            "errors_total": errors_total,
            "warnings_total": warnings_total,
            "per_type": _compute_per_type_counts(eval_data),
        },
        "file_status": file_status,
        "punch_list": {
            "errors": punch_list["errors"],
            "warnings": punch_list["warnings"],
        },
        "lexicons": lexicons,
    }

    # Enforce invariants (fail fast)
    _enforce_invariants(report_v1)

    # Write the compiled report
    output_path = artifacts_dir / "report_v1.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report_v1, f, ensure_ascii=False, indent=2)

    logger.info("Compiled report_v1.json → %s", output_path)
    return output_path


def _compute_file_status(eval_data: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    """Compute per-file status (ready/review/error) in format {lang: {file: status}}."""
    file_status = {}

    for lang_code, lang_data in eval_data["languages"].items():
        file_status[lang_code] = {}

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
                file_state = "error"
            elif warnings > 0:
                file_state = "review"
            else:
                file_state = "ready"

            file_status[lang_code][file_path] = file_state

    return file_status


def _compute_per_type_counts(eval_data: Dict[str, Any]) -> Dict[str, int]:
    """Compute per-type issue counts across all languages and files."""
    per_type = {
        "missing_translation": 0,
        "untranslated_after_dnt": 0,
        "timing_fail": 0,
    }

    for _lang_code, lang_data in eval_data["languages"].items():
        for _file_path, file_data in lang_data.get("files", {}).items():
            per_type["missing_translation"] += file_data.get("missing_translation", 0)
            per_type["untranslated_after_dnt"] += file_data.get("untranslated_after_dnt", 0)
            per_type["timing_fail"] += file_data.get("timing_fail", 0)

    return per_type


def _enforce_invariants(report_v1: Dict[str, Any]) -> None:
    """Enforce invariants and fail fast if violated."""
    totals = report_v1["totals"]
    kpis = report_v1["kpis"]
    punch_list = report_v1["punch_list"]
    file_status = report_v1["file_status"]

    # Invariant 1: issues_total == errors_total + warnings_total
    if totals["issues_total"] != kpis["errors_total"] + kpis["warnings_total"]:
        raise ValueError(
            f"Invariant violated: issues_total ({totals['issues_total']}) != "
            f"errors_total ({kpis['errors_total']}) + warnings_total ({kpis['warnings_total']})"
        )

    # Invariant 2: If errors/warnings > 0, punch_list must not be empty
    if kpis["errors_total"] > 0 and len(punch_list["errors"]) == 0:
        raise ValueError(
            f"Invariant violated: errors_total ({kpis['errors_total']}) > 0 but punch_list.errors is empty"
        )

    if kpis["warnings_total"] > 0 and len(punch_list["warnings"]) == 0:
        raise ValueError(
            f"Invariant violated: warnings_total ({kpis['warnings_total']}) > 0 but punch_list.warnings is empty"
        )

    # Invariant 3: No "unknown" keys in file_status
    for lang_code, files in file_status.items():
        if lang_code == "unknown":
            raise ValueError("Invariant violated: file_status contains 'unknown' language key")
        for file_path, status in files.items():
            if status == "unknown":
                raise ValueError(
                    f"Invariant violated: file_status contains 'unknown' status for {lang_code}/{file_path}"
                )


def _extract_punch_list(eval_data: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """Extract errors and warnings from evaluation data for punch list using new schema."""
    errors = []
    warnings = []

    for lang_code, lang_data in eval_data["languages"].items():
        for file_path, file_data in lang_data.get("files", {}).items():
            # Extract missing translation issues (WARNINGS)
            missing_count = file_data.get("missing_translation", 0)
            for i in range(missing_count):
                warnings.append(
                    {
                        "language": lang_code,
                        "file": file_path,
                        "cue_index": i + 1,
                        "type": "missing_translation",
                        "human_summary": "This subtitle may be incomplete or missing context.",
                        "suggested_fix": "Copy ±2 target lines, back-translate to verify completeness, then regenerate if needed.",
                        "context": {
                            "source": {
                                "prev2": "",
                                "prev1": "",
                                "cur": "",
                                "next1": "",
                                "next2": "",
                            },
                            "target": {
                                "prev2": "",
                                "prev1": "",
                                "cur": "",
                                "next1": "",
                                "next2": "",
                            },
                        },
                    }
                )

            # Extract DNT violations (ERRORS)
            untrans_dnt_count = file_data.get("untranslated_after_dnt", 0)
            for i in range(untrans_dnt_count):
                errors.append(
                    {
                        "language": lang_code,
                        "file": file_path,
                        "cue_index": i + 1,
                        "type": "untranslated_after_dnt",
                        "human_summary": "This term should not be translated according to your DNT list.",
                        "suggested_fix": "Keep the original term untranslated or add it to your DNT list.",
                        "context": {
                            "source": {
                                "prev2": "",
                                "prev1": "",
                                "cur": "",
                                "next1": "",
                                "next2": "",
                            },
                            "target": {
                                "prev2": "",
                                "prev1": "",
                                "cur": "",
                                "next1": "",
                                "next2": "",
                            },
                        },
                    }
                )

            # Extract timing failures (ERRORS)
            timing_fail_count = file_data.get("timing_fail", 0)
            if timing_fail_count > 0:
                errors.append(
                    {
                        "language": lang_code,
                        "file": file_path,
                        "cue_index": None,
                        "type": "timing_fail",
                        "human_summary": "The subtitle timing doesn't match the source file.",
                        "suggested_fix": "Check subtitle timing and duration settings.",
                        "context": {
                            "source": {
                                "prev2": "",
                                "prev1": "",
                                "cur": "",
                                "next1": "",
                                "next2": "",
                            },
                            "target": {
                                "prev2": "",
                                "prev1": "",
                                "cur": "",
                                "next1": "",
                                "next2": "",
                            },
                        },
                    }
                )

    return {
        "errors": errors,
        "warnings": warnings,
    }


def _extract_lexicons(ai_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract DNT terms and termbase from ai_config.json."""
    dnt_terms = ai_data.get("dnt_terms", [])

    # Convert termbase to the expected format: {lang: {count, sample: [...]}}
    termbase: Dict[str, Dict[str, Any]] = {}
    raw_termbase = ai_data.get("termbase", {})

    for lang_name, lang_termbase in raw_termbase.items():
        entries = []
        for source, preferred in lang_termbase.items():
            entries.append({"source": source, "target": preferred})
        # Sort by source for deterministic ordering
        entries.sort(key=lambda x: x["source"])

        termbase[lang_name] = {
            "count": len(entries),
            "sample": entries[:5] if len(entries) > 5 else entries,  # Show up to 5 examples
        }

    return {
        "dnt": {
            "count": len(dnt_terms),
            "sample": sorted(dnt_terms)[:5] if len(dnt_terms) > 5 else sorted(dnt_terms),
        },
        "termbases": termbase,
    }
