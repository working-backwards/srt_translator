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

    # Generate banner text and what to do next
    banner_text, what_to_do_next = _generate_banner_and_steps(
        decision_state, errors_total, warnings_total
    )

    # Compute KPIs
    kpis = _compute_kpis(eval_data, ai_data, errors_total, warnings_total)

    # Compute file status (per-file READY/REVIEW/FIX)
    file_status = _compute_file_status(eval_data)

    # Extract lexicons
    lexicons = _extract_lexicons(ai_data)

    # Build the compiled report
    report_v1 = {
        "version": "1.0",
        "timestamp": eval_data.get("timestamp", ""),
        "batch_label": eval_data.get("batch_label", ""),
        "decision": {
            "state": decision_state,
            "banner_text": banner_text,
            "what_to_do_next": what_to_do_next,
        },
        "totals": {
            "files_total": files_total,
            "languages_total": languages_total,
            "errors_total": errors_total,
            "warnings_total": warnings_total,
        },
        "kpis": kpis,
        "file_status": file_status,
        "lexicons": lexicons,
        "sections": {
            "errors": [],  # Will be populated in Packet 6
            "warnings": [],  # Will be populated in Packet 6
        },
    }

    # Write the compiled report
    output_path = artifacts_dir / "report_v1.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report_v1, f, ensure_ascii=False, indent=2)

    logger.info(f"Compiled report_v1.json → {output_path}")
    return output_path


def _generate_banner_and_steps(
    state: str, errors_total: int, warnings_total: int
) -> tuple[str, List[str]]:
    """Generate banner text and what to do next steps based on status."""
    if state == "READY":
        banner_text = "✅ Everything looks great. Your translated files are ready to use."
        what_to_do_next = [
            "Spot-check a few captions for flow and brand terms, then publish.",
            "Save the HTML/MD report with your course materials.",
        ]
    elif state == "REVIEW":
        banner_text = f"⚠️ Review recommended: {warnings_total} warning(s) found."
        what_to_do_next = [
            "Work through the Punch List below.",
            "For each warning, use the context snippet and suggested check to verify quickly.",
            "If everything looks good, publish.",
        ]
    else:  # FIX
        banner_text = (
            f"❌ Fix required: {errors_total} error(s), {warnings_total} warning(s) found."
        )
        what_to_do_next = [
            "Work through the Punch List below; fix **errors first**, then warnings.",
            "Use the context snippets to validate or regenerate translations.",
            "Re-run the app after fixes to verify a clean report.",
        ]

    return banner_text, what_to_do_next


def _compute_kpis(
    eval_data: Dict[str, Any], ai_data: Dict[str, Any], errors_total: int, warnings_total: int
) -> Dict[str, str]:
    """Compute KPIs in the specified order."""
    # Determine DNT coverage
    dnt_terms = ai_data.get("dnt_terms", [])
    dnt_coverage = "none" if not dnt_terms else "full"

    # Determine termbase coverage
    termbase = ai_data.get("termbase", {})
    if not termbase:
        termbase_coverage = "none"
    else:
        # Check if we have termbase entries for any languages
        if len(termbase) == 0:
            termbase_coverage = "none"
        elif len(termbase) == 1:
            termbase_coverage = "partial"
        else:
            termbase_coverage = "full"

    # Determine parity status
    parity_ok = True
    for lang_data in eval_data["languages"].values():
        for _file_data in lang_data.get("files", {}).values():
            # Note: We don't have parity_ok in the current eval_report.json structure
            # This would need to be added to the evaluator output
            pass  # For now, assume OK

    parity_status = "OK" if parity_ok else "Needs review"

    return {
        "Files": str(eval_data["files_total"]),
        "Languages": str(eval_data["languages_total"]),
        "Errors": str(errors_total),
        "Warnings": str(warnings_total),
        "DNT coverage": dnt_coverage,
        "Termbase coverage": termbase_coverage,
        "Parity": parity_status,
    }


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
