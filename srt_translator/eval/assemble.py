"""Assembler to build strict EvalReportV1 from per-language/file counts."""

from typing import Dict

from srt_translator.eval.schema import (
    MISSING,
    TIMING,
    UNTRANS_DNT,
    validate_eval_report_v1,
)


def build_eval_report_v1(
    *,
    per_language_file_counts: Dict[str, Dict[str, Dict[str, int]]],
    source_language: str | None,
) -> Dict:
    """
    Returns a dict matching EvalReportV1.

    Args:
        per_language_file_counts: languages -> files -> {missing_translation, untranslated_after_dnt, timing_fail}
        source_language: string or None (convert None to "")

    Returns:
        Dict matching EvalReportV1 schema

    Raises:
        ValueError: if the assembled data doesn't validate
    """
    # Deep copy and ensure all three keys exist per file with default 0 if missing
    languages = {}
    for lang_code, files_data in per_language_file_counts.items():
        languages[lang_code] = {}
        for file_path, file_counts in files_data.items():
            # Ensure all required categories exist with default 0
            normalized_counts = {
                MISSING: file_counts.get(MISSING, 0),
                UNTRANS_DNT: file_counts.get(UNTRANS_DNT, 0),
                TIMING: file_counts.get(TIMING, 0),
            }
            # Validate types
            for category, count in normalized_counts.items():
                if not isinstance(count, int):
                    raise ValueError(
                        f"Category '{category}' count must be integer, got {type(count).__name__}"
                    )
            languages[lang_code][file_path] = normalized_counts

    # Compute totals
    files_total = 0
    issues_total = 0

    # Count unique files across all languages
    all_files = set()
    for lang_files in languages.values():
        all_files.update(lang_files.keys())
    files_total = len(all_files)

    # Count total issues across all languages/files
    for lang_files in languages.values():
        for file_counts in lang_files.values():
            for count in file_counts.values():
                issues_total += count

    # Language count
    languages_total = len(languages)

    # Handle source language
    source_lang_str = source_language if source_language is not None else ""
    if not isinstance(source_lang_str, str):
        raise ValueError("source_language must be string or None")

    # Assemble the report
    report = {
        "files_total": files_total,
        "languages_total": languages_total,
        "issues_total": issues_total,
        "source_language": source_lang_str,
        "languages": languages,
    }

    # Validate before returning
    validate_eval_report_v1(report)

    return report
