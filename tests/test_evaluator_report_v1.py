"""Tests for the strict EvalReportV1 writer and presenter parity."""

import json
import tempfile
from pathlib import Path

import pytest

from srt_translator.eval.assemble import build_eval_report_v1
from srt_translator.eval.report import write_batch_report
from srt_translator.presenters.eval_html.build import build_eval_html


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


class TestPresenterParity:
    """Test cases for HTML/MD presenter parity."""

    def test_banner_text_parity(self):
        """Test that HTML and MD presenters show identical banner text."""
        with tempfile.TemporaryDirectory() as temp_dir:
            batch_root = Path(temp_dir)
            artifacts_dir = batch_root / "artifacts"
            artifacts_dir.mkdir()

            # Create test eval_report.json
            eval_report = {
                "files_total": 1,
                "languages_total": 1,
                "issues_total": 0,
                "source_language": "en",
                "languages": {
                    "fr": {
                        "files": {
                            "test.srt": {
                                "missing_translation": 0,
                                "untranslated_after_dnt": 0,
                                "timing_fail": 0,
                            }
                        }
                    }
                },
            }

            eval_report_path = artifacts_dir / "eval_report.json"
            with open(eval_report_path, "w", encoding="utf-8") as f:
                json.dump(eval_report, f, ensure_ascii=False, indent=2)

            # Create test ai_config.json
            ai_config = {
                "dnt_terms": ["DNT1", "DNT2"],
                "termbase": {"fr": [{"source": "hello", "target": "bonjour"}]},
                "target_languages": {"French": "fr"},
            }

            ai_config_path = artifacts_dir / "ai_config.json"
            with open(ai_config_path, "w", encoding="utf-8") as f:
                json.dump(ai_config, f, ensure_ascii=False, indent=2)

            # Generate HTML report
            html_path = build_eval_html(eval_report_path)
            html_content = html_path.read_text(encoding="utf-8")

            # Generate MD report
            rollup = {
                "languages": {
                    "fr": {
                        "files": [
                            {
                                "target_file": "test.srt",
                                "issues": {
                                    "missing_translation": [],
                                    "untranslated_after_dnt": [],
                                    "timing_fail": False,
                                },
                            }
                        ]
                    }
                },
                "original_language": {"detected": "en"},
            }

            import logging

            logger = logging.getLogger("test")
            md_path = write_batch_report(batch_root, rollup, logger)
            md_content = md_path.read_text(encoding="utf-8")

            # Check that both contain the same banner text
            expected_banner = "Everything looks great. Your translated files are ready to use."
            assert expected_banner in html_content
            assert expected_banner in md_content

    def test_kpi_labels_parity(self):
        """Test that HTML and MD presenters show identical KPI labels and order."""
        with tempfile.TemporaryDirectory() as temp_dir:
            batch_root = Path(temp_dir)
            artifacts_dir = batch_root / "artifacts"
            artifacts_dir.mkdir()

            # Create test eval_report.json
            eval_report = {
                "files_total": 2,
                "languages_total": 2,
                "issues_total": 1,
                "source_language": "en",
                "languages": {
                    "fr": {
                        "files": {
                            "test1.srt": {
                                "missing_translation": 1,
                                "untranslated_after_dnt": 0,
                                "timing_fail": 0,
                            }
                        }
                    },
                    "ja": {
                        "files": {
                            "test2.srt": {
                                "missing_translation": 0,
                                "untranslated_after_dnt": 0,
                                "timing_fail": 0,
                            }
                        }
                    },
                },
            }

            eval_report_path = artifacts_dir / "eval_report.json"
            with open(eval_report_path, "w", encoding="utf-8") as f:
                json.dump(eval_report, f, ensure_ascii=False, indent=2)

            # Create test ai_config.json
            ai_config = {
                "dnt_terms": ["DNT1"],
                "termbase": {"fr": [{"source": "hello", "target": "bonjour"}]},
                "target_languages": {"French": "fr", "Japanese": "ja"},
            }

            ai_config_path = artifacts_dir / "ai_config.json"
            with open(ai_config_path, "w", encoding="utf-8") as f:
                json.dump(ai_config, f, ensure_ascii=False, indent=2)

            # Generate HTML report
            html_path = build_eval_html(eval_report_path)
            html_content = html_path.read_text(encoding="utf-8")

            # Generate MD report
            rollup = {
                "languages": {
                    "fr": {
                        "files": [
                            {
                                "target_file": "test1.srt",
                                "issues": {
                                    "missing_translation": [
                                        {"cue": 1, "original": "hello", "target": ""}
                                    ],
                                    "untranslated_after_dnt": [],
                                    "timing_fail": False,
                                },
                            }
                        ]
                    },
                    "ja": {
                        "files": [
                            {
                                "target_file": "test2.srt",
                                "issues": {
                                    "missing_translation": [],
                                    "untranslated_after_dnt": [],
                                    "timing_fail": False,
                                },
                            }
                        ]
                    },
                },
                "original_language": {"detected": "en"},
            }

            import logging

            logger = logging.getLogger("test")
            md_path = write_batch_report(batch_root, rollup, logger)
            md_content = md_path.read_text(encoding="utf-8")

            # Check that both contain the same KPI labels in the same order
            expected_kpi_labels = [
                "Files total:",
                "Languages:",
                "Issues (critical):",
                "Warnings (non-critical):",
                "Detected source language:",
                "DNT coverage:",
                "Termbase coverage:",
            ]

            for label in expected_kpi_labels:
                assert label in html_content
                assert label in md_content

    def test_critical_status_parity(self):
        """Test that both presenters show critical status with identical wording."""
        with tempfile.TemporaryDirectory() as temp_dir:
            batch_root = Path(temp_dir)
            artifacts_dir = batch_root / "artifacts"
            artifacts_dir.mkdir()

            # Create test eval_report.json with critical issues
            eval_report = {
                "files_total": 1,
                "languages_total": 1,
                "issues_total": 1,
                "source_language": "en",
                "languages": {
                    "fr": {
                        "files": {
                            "test.srt": {
                                "issues": {
                                    "missing_translation": 1,
                                    "untranslated_after_dnt": 0,
                                    "timing_fail": 0,
                                }
                            }
                        }
                    }
                },
            }

            eval_report_path = artifacts_dir / "eval_report.json"
            with open(eval_report_path, "w", encoding="utf-8") as f:
                json.dump(eval_report, f, ensure_ascii=False, indent=2)

            # Create test ai_config.json
            ai_config = {
                "dnt_terms": [],
                "termbase": {},
                "target_languages": {"French": "fr"},
            }

            ai_config_path = artifacts_dir / "ai_config.json"
            with open(ai_config_path, "w", encoding="utf-8") as f:
                json.dump(ai_config, f, ensure_ascii=False, indent=2)

            # Generate HTML report
            html_path = build_eval_html(eval_report_path)
            html_content = html_path.read_text(encoding="utf-8")

            # Generate MD report
            rollup = {
                "languages": {
                    "fr": {
                        "files": [
                            {
                                "target_file": "test.srt",
                                "issues": {
                                    "missing_translation": [
                                        {"cue": 1, "original": "hello", "target": ""}
                                    ],
                                    "untranslated_after_dnt": [],
                                    "timing_fail": False,
                                },
                            }
                        ]
                    }
                },
                "original_language": {"detected": "en"},
            }

            import logging

            logger = logging.getLogger("test")
            md_path = write_batch_report(batch_root, rollup, logger)
            md_content = md_path.read_text(encoding="utf-8")

            # Check that both contain the critical status banner
            expected_critical_banner = (
                "We found issues that will degrade quality. Fix the items below before publishing."
            )
            assert expected_critical_banner in html_content
            assert expected_critical_banner in md_content

            # Check that both contain the critical what-to-do steps
            expected_steps = [
                "Resolve DNT or termbase violations in the listed files.",
                "Fix cue parity mismatches or missing translations.",
                "Re-run evaluation and confirm 'Ready to publish'.",
            ]

            for step in expected_steps:
                assert step in html_content
                assert step in md_content
