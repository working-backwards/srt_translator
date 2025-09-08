"""Strict schema for EvalReportV1 JSON output."""

from typing import TypedDict


class EvalReportV1(TypedDict):
    """Strict schema for evaluation report JSON (v1)."""

    files_total: int
    languages_total: int
    issues_total: int
    source_language: str
    languages: dict[str, dict[str, dict[str, int]]]


# Constants for issue category keys
MISSING = "missing_translation"
TIMING = "timing_fail"

# All required issue categories
REQUIRED_CATEGORIES = {MISSING, TIMING}


def validate_eval_report_v1(obj: dict) -> None:
    """Validate that obj matches EvalReportV1 schema.

    Raises ValueError with clear message on any violation.
    """
    # Check top-level required keys
    required_top_keys = {
        "files_total",
        "languages_total",
        "issues_total",
        "source_language",
        "languages",
    }
    missing_top_keys = required_top_keys - set(obj.keys())
    if missing_top_keys:
        raise ValueError(
            f"eval_report.json missing required keys: {', '.join(sorted(missing_top_keys))}"
        )

    # Validate top-level types
    if not isinstance(obj["files_total"], int):
        raise ValueError("eval_report.json files_total must be an integer")
    if not isinstance(obj["languages_total"], int):
        raise ValueError("eval_report.json languages_total must be an integer")
    if not isinstance(obj["issues_total"], int):
        raise ValueError("eval_report.json issues_total must be an integer")
    if not isinstance(obj["source_language"], str):
        raise ValueError("eval_report.json source_language must be a string")
    if not isinstance(obj["languages"], dict):
        raise ValueError("eval_report.json languages must be a dictionary")

    # Validate languages structure
    languages = obj["languages"]
    for lang_code, lang_data in languages.items():
        if not isinstance(lang_code, str):
            raise ValueError(f"Language code must be string, got {type(lang_code).__name__}")
        if not isinstance(lang_data, dict):
            raise ValueError(
                f"Language data for '{lang_code}' must be dictionary, got {type(lang_data).__name__}"
            )

        # Check if lang_data has "files" key
        if "files" not in lang_data:
            raise ValueError(f"Language '{lang_code}' missing required 'files' key")

        files = lang_data["files"]
        if not isinstance(files, dict):
            raise ValueError(
                f"Files data for language '{lang_code}' must be dictionary, got {type(files).__name__}"
            )

        # Validate each file's issue counts
        for file_path, file_data in files.items():
            if not isinstance(file_path, str):
                raise ValueError(f"File path must be string, got {type(file_path).__name__}")
            if not isinstance(file_data, dict):
                raise ValueError(
                    f"File data for '{file_path}' must be dictionary, got {type(file_data).__name__}"
                )

            # Check that all required categories exist and are integers
            missing_categories = REQUIRED_CATEGORIES - set(file_data.keys())
            if missing_categories:
                raise ValueError(
                    f"File '{file_path}' in language '{lang_code}' missing required categories: {', '.join(sorted(missing_categories))}"
                )

            for category in REQUIRED_CATEGORIES:
                if not isinstance(file_data[category], int):
                    raise ValueError(
                        f"Category '{category}' in file '{file_path}' language '{lang_code}' must be integer, got {type(file_data[category]).__name__}"
                    )
