"""Report compiler that creates report_v1.json from v2 eval_report.json and ai_config.json."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List


def compile_report(artifacts_dir: Path) -> Path:
    """
    Compile report_v1.json from v2 eval_report.json and ai_config.json.

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

    # Validate v2 format
    if eval_data.get("version") != "2.0.0":
        raise ValueError(
            f"Expected eval_report.json version 2.0.0, got: {eval_data.get('version')}"
        )

    required_eval_keys = {"totals", "per_language"}
    missing_keys = required_eval_keys - set(eval_data.keys())
    if missing_keys:
        raise ValueError(
            f"eval_report.json missing required keys: {', '.join(sorted(missing_keys))}"
        )

    # Validate totals structure
    totals = eval_data.get("totals", {})
    required_totals_keys = {"files_total", "languages_total", "issues_total"}
    missing_totals_keys = required_totals_keys - set(totals.keys())
    if missing_totals_keys:
        raise ValueError(
            f"eval_report.json totals missing required keys: {', '.join(sorted(missing_totals_keys))}"
        )

    # Validate required fields in ai_data
    required_ai_keys = {"dnt_terms", "termbase"}
    missing_ai_keys = required_ai_keys - set(ai_data.keys())
    if missing_ai_keys:
        raise ValueError(
            f"ai_config.json missing required keys: {', '.join(sorted(missing_ai_keys))}"
        )

    # Compute totals and status from v2 data
    files_total = totals["files_total"]
    languages_total = totals["languages_total"]
    issues_total = totals["issues_total"]

    # Compute errors and warnings by reclassifying issues
    errors_total = 0
    warnings_total = 0

    # Count issues by type across all languages and files (v2 format)
    for _lang_code, lang_data in eval_data["per_language"].items():
        for _file_path, file_data in lang_data.get("files", {}).items():
            # Get issue counts from v2 structure
            issues_counts = file_data.get("issues_counts", {})
            issues_detail = file_data.get("issues_detail", {})

            # Validate counts match details (fail fast)
            for issue_type in [
                "missing_translation",
                "untranslated_after_dnt",
                "timing_fail",
                "placeholder_mismatch",
                "parity_issue",
            ]:
                count = issues_counts.get(issue_type, 0)
                detail_list = issues_detail.get(issue_type, [])
                if count > 0 and len(detail_list) == 0:
                    raise ValueError(
                        f"Count mismatch: {issue_type} count={count} but details empty in {_lang_code}/{_file_path}"
                    )
                if count != len(detail_list):
                    raise ValueError(
                        f"Count mismatch: {issue_type} count={count} but details length={len(detail_list)} in {_lang_code}/{_file_path}"
                    )

            # Reclassify: missing_translation is WARNING, not ERROR
            missing_count = issues_counts.get("missing_translation", 0)
            warnings_total += missing_count

            # untranslated_after_dnt, timing_fail, placeholder_mismatch are ERRORS
            untrans_dnt_count = issues_counts.get("untranslated_after_dnt", 0)
            timing_fail_count = issues_counts.get("timing_fail", 0)
            placeholder_count = issues_counts.get("placeholder_mismatch", 0)
            errors_total += untrans_dnt_count + timing_fail_count + placeholder_count

    # Determine overall status using exact specification
    if errors_total > 0:
        decision_level = "fail"
        one_liner = f"We found {errors_total} errors that must be fixed before publishing."
    elif warnings_total > 0:
        decision_level = "review"
        one_liner = f"We found {warnings_total} warnings. Fix the items in the Punch List below."
    else:
        decision_level = "pass"
        one_liner = "Everything looks great. Your translated files are ready to use."

    # Compute file status (per-file READY/REVIEW/BLOCKED)
    file_status = _compute_file_status(eval_data)

    # Extract lexicons
    lexicons = _extract_lexicons(ai_data)

    # Extract punch list (errors and warnings) - this populates sections
    punch_list = _extract_punch_list(eval_data)

    # Build the compiled report with exact schema
    report_v1 = {
        "decision": decision_level,
        "one_liner": one_liner,
        "punch_list": {
            "errors": punch_list["errors"],
            "warnings": punch_list["warnings"],
        },
        "file_status": file_status,
        "kpis": {
            "files_total": files_total,
            "languages_total": languages_total,
            "issues_total": issues_total,
            "by_type": _compute_per_type_counts(eval_data),
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
    """Compute per-file status (ready/review/blocked) in format {lang: {file: status}}."""
    file_status = {}

    for lang_code, lang_data in eval_data["per_language"].items():
        file_status[lang_code] = {}

        for file_path, file_data in lang_data.get("files", {}).items():
            # Count errors and warnings for this file using v2 structure
            errors = 0
            warnings = 0

            issues_counts = file_data.get("issues_counts", {})

            # Reclassify: missing_translation is WARNING
            missing_count = issues_counts.get("missing_translation", 0)
            warnings += missing_count

            # untranslated_after_dnt, timing_fail, placeholder_mismatch are ERRORS
            untrans_dnt_count = issues_counts.get("untranslated_after_dnt", 0)
            timing_fail_count = issues_counts.get("timing_fail", 0)
            placeholder_count = issues_counts.get("placeholder_mismatch", 0)
            errors += untrans_dnt_count + timing_fail_count + placeholder_count

            # Determine file status
            if errors > 0:
                file_state = "blocked"
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
        "placeholder_mismatch": 0,
        "parity_issue": 0,
    }

    for _lang_code, lang_data in eval_data["per_language"].items():
        for _file_path, file_data in lang_data.get("files", {}).items():
            issues_counts = file_data.get("issues_counts", {})
            per_type["missing_translation"] += issues_counts.get("missing_translation", 0)
            per_type["untranslated_after_dnt"] += issues_counts.get("untranslated_after_dnt", 0)
            per_type["timing_fail"] += issues_counts.get("timing_fail", 0)
            per_type["placeholder_mismatch"] += issues_counts.get("placeholder_mismatch", 0)
            per_type["parity_issue"] += issues_counts.get("parity_issue", 0)

    return per_type


def _extract_punch_list(eval_data: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """Extract punch list from v2 eval_report.json - transform real details, never fabricate."""
    errors = []
    warnings = []

    for lang_code, lang_data in eval_data["per_language"].items():
        for file_path, file_data in lang_data.get("files", {}).items():
            issues_detail = file_data.get("issues_detail", {})

            # Fail fast if issues_detail exists but lacks required structure
            if issues_detail and not isinstance(issues_detail, dict):
                raise ValueError(
                    f"issues_detail must be dict, got {type(issues_detail)} for {file_path}"
                )

            # Process each issue type from real details
            for issue_type, details in issues_detail.items():
                for detail in details:
                    punch_item = _create_punch_item(lang_code, file_path, issue_type, detail)

                    # Classify as error or warning
                    if issue_type in [
                        "untranslated_after_dnt",
                        "timing_fail",
                        "placeholder_mismatch",
                    ]:
                        errors.append(punch_item)
                    elif issue_type in ["missing_translation", "parity_issue"]:
                        warnings.append(punch_item)

    return {"errors": errors, "warnings": warnings}


def _create_punch_item(
    lang_code: str, file_path: str, issue_type: str, detail: Dict[str, Any]
) -> Dict[str, Any]:
    """Create a punch list item from real issue detail."""

    # Get cue index (handle both single cues and file-level issues)
    cue_index = detail.get("cue_index")
    if issue_type == "timing_fail" and detail.get("file_level"):
        cue_index = None

    # Get context (use real context from detail)
    context = detail.get("context", {})
    source_context = context.get("source", {})
    target_context = context.get("target", {})

    # Create standardized context structure
    standardized_context = {
        "source": {
            "prev2": source_context.get("prev2", ""),
            "prev1": source_context.get("prev1", ""),
            "cur": source_context.get("cur", ""),
            "next1": source_context.get("next1", ""),
            "next2": source_context.get("next2", ""),
        },
        "target": {
            "prev2": target_context.get("prev2", ""),
            "prev1": target_context.get("prev1", ""),
            "cur": target_context.get("cur", ""),
            "next1": target_context.get("next1", ""),
            "next2": target_context.get("next2", ""),
        },
    }

    # Create human-friendly descriptions
    descriptions = {
        "missing_translation": "This cue has no translation.",
        "untranslated_after_dnt": "This term should not be translated according to your DNT list.",
        "timing_fail": "Timing drift too high (median or p95)",
        "placeholder_mismatch": "Placeholder mismatch between source and target.",
        "parity_issue": "Cue count mismatch between source and target files.",
    }

    suggested_fixes = {
        "missing_translation": "Translate the source text to the target language.",
        "untranslated_after_dnt": "Keep the original term untranslated or add it to your DNT list.",
        "timing_fail": "Check subtitle timing synchronization.",
        "placeholder_mismatch": "Ensure placeholders match between source and target.",
        "parity_issue": "Check that both files have the same number of cues.",
    }

    return {
        "language": lang_code,
        "file": file_path,
        "cue_index": cue_index,
        "type": issue_type,
        "desc": descriptions.get(issue_type, "Unknown issue type"),
        "suggested_fix": suggested_fixes.get(issue_type, "Please review this issue."),
        "context": standardized_context,
    }


def _extract_lexicons(ai_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract lexicon data from ai_config.json."""
    dnt_terms = ai_data.get("dnt_terms", [])
    termbase = ai_data.get("termbase", {})

    # Build DNT lexicon
    dnt_lexicon = {
        "count": len(dnt_terms),
        "sample": dnt_terms[:5] if dnt_terms else [],  # Show first 5 as sample
    }

    # Build termbase lexicon
    termbase_lexicon = {}
    for lang_code, terms in termbase.items():
        if isinstance(terms, dict):
            # Convert dict to list of {source, target} pairs
            term_list = [{"source": k, "target": v} for k, v in terms.items()]
            termbase_lexicon[lang_code] = {
                "count": len(term_list),
                "sample": term_list[:5] if term_list else [],  # Show first 5 as sample
            }
        else:
            termbase_lexicon[lang_code] = {"count": 0, "sample": []}

    return {
        "dnt": dnt_lexicon,
        "termbase": termbase_lexicon,
    }


def _enforce_invariants(report_v1: Dict[str, Any]) -> None:
    """Enforce invariants and fail fast if violated."""
    kpis = report_v1["kpis"]
    punch_list = report_v1["punch_list"]
    file_status = report_v1["file_status"]

    # Invariant 1: issues_total == sum of by_type counts
    by_type = kpis["by_type"]
    computed_total = sum(by_type.values())
    if kpis["issues_total"] != computed_total:
        raise ValueError(
            f"Invariant violated: issues_total ({kpis['issues_total']}) != "
            f"sum of by_type counts ({computed_total})"
        )

    # Invariant 2: If errors/warnings > 0, punch_list must not be empty
    errors_total = len(punch_list["errors"])
    warnings_total = len(punch_list["warnings"])

    if errors_total > 0 and len(punch_list["errors"]) == 0:
        raise ValueError(
            f"Invariant violated: errors_total ({errors_total}) > 0 but punch_list.errors is empty"
        )

    if warnings_total > 0 and len(punch_list["warnings"]) == 0:
        raise ValueError(
            f"Invariant violated: warnings_total ({warnings_total}) > 0 but punch_list.warnings is empty"
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
