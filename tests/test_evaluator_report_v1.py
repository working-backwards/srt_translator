"""Tests for the strict EvalReportV1 writer."""

import pytest

from srt_translator.eval.assemble import build_eval_report_v1


class TestEvalReportV1Writer:
    """Test cases for the strict EvalReportV1 writer."""

    def test_build_eval_report_v1_happy_path(self):
        """Test successful EvalReportV1 generation."""
        # Build a small per_language_file_counts
        per_language_file_counts = {
            "fr": {
                "Input1 - EN.srt": {
                    "missing_translation": 1,
                    "untranslated_after_dnt": 0,
                    "timing_fail": 0,
                }
            },
            "ja": {
                "Input1 - EN.srt": {
                    "missing_translation": 0,
                    "untranslated_after_dnt": 1,
                    "timing_fail": 2,
                }
            },
        }

        # Call build_eval_report_v1
        result = build_eval_report_v1(
            per_language_file_counts=per_language_file_counts,
            source_language="en",
        )

        # Assert keys exist and values are correct
        assert result["files_total"] == 1  # 1 unique file across all languages
        assert result["languages_total"] == 2  # fr, ja
        assert result["issues_total"] == 4  # 1 + 0 + 0 + 0 + 1 + 2
        assert result["source_language"] == "en"
        assert "languages" in result

        # Check languages structure
        languages = result["languages"]
        assert "fr" in languages
        assert "ja" in languages
        assert "files" in languages["fr"]
        assert "files" in languages["ja"]
        assert "Input1 - EN.srt" in languages["fr"]["files"]
        assert "Input1 - EN.srt" in languages["ja"]["files"]

        # Check issue counts
        fr_file = languages["fr"]["files"]["Input1 - EN.srt"]
        assert fr_file["missing_translation"] == 1
        assert fr_file["untranslated_after_dnt"] == 0
        assert fr_file["timing_fail"] == 0

        ja_file = languages["ja"]["files"]["Input1 - EN.srt"]
        assert ja_file["missing_translation"] == 0
        assert ja_file["untranslated_after_dnt"] == 1
        assert ja_file["timing_fail"] == 2

    def test_build_eval_report_v1_normalization(self):
        """Test that missing category keys default to 0."""
        # Provide a per-file dict missing one category key
        per_language_file_counts = {
            "fr": {
                "Input1 - EN.srt": {
                    "missing_translation": 1,
                    "untranslated_after_dnt": 0,
                    # missing timing_fail
                }
            }
        }

        # Should still work and default timing_fail to 0
        result = build_eval_report_v1(
            per_language_file_counts=per_language_file_counts,
            source_language="en",
        )

        # Check that timing_fail was defaulted to 0
        fr_file = result["languages"]["fr"]["files"]["Input1 - EN.srt"]
        assert fr_file["timing_fail"] == 0
        assert fr_file["missing_translation"] == 1
        assert fr_file["untranslated_after_dnt"] == 0

    def test_build_eval_report_v1_validation_error(self):
        """Test that malformed data raises ValueError."""
        # Provide malformed data (string where int expected)
        per_language_file_counts = {
            "fr": {
                "Input1 - EN.srt": {
                    "missing_translation": "not an int",  # Should be int
                    "untranslated_after_dnt": 0,
                    "timing_fail": 0,
                }
            }
        }

        # Should raise ValueError
        with pytest.raises(ValueError, match="must be integer"):
            build_eval_report_v1(
                per_language_file_counts=per_language_file_counts,
                source_language="en",
            )

    def test_build_eval_report_v1_source_language_none(self):
        """Test that None source_language is converted to empty string."""
        per_language_file_counts = {
            "fr": {
                "Input1 - EN.srt": {
                    "missing_translation": 0,
                    "untranslated_after_dnt": 0,
                    "timing_fail": 0,
                }
            }
        }

        result = build_eval_report_v1(
            per_language_file_counts=per_language_file_counts,
            source_language=None,
        )

        assert result["source_language"] == ""

    def test_build_eval_report_v1_multiple_files(self):
        """Test with multiple files across languages."""
        per_language_file_counts = {
            "fr": {
                "Input1 - EN.srt": {
                    "missing_translation": 1,
                    "untranslated_after_dnt": 0,
                    "timing_fail": 0,
                },
                "Input2 - EN.srt": {
                    "missing_translation": 0,
                    "untranslated_after_dnt": 1,
                    "timing_fail": 0,
                },
            },
            "ja": {
                "Input1 - EN.srt": {
                    "missing_translation": 0,
                    "untranslated_after_dnt": 0,
                    "timing_fail": 1,
                },
            },
        }

        result = build_eval_report_v1(
            per_language_file_counts=per_language_file_counts,
            source_language="en",
        )

        # Should count unique files across all languages
        assert result["files_total"] == 2  # Input1 - EN.srt, Input2 - EN.srt
        assert result["languages_total"] == 2  # fr, ja
        assert result["issues_total"] == 3  # 1 + 0 + 0 + 0 + 1 + 0 + 0 + 0 + 1
