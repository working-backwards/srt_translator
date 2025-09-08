"""Tests for the emit_all_reports orchestrator function."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from srt_translator.eval.report import emit_all_reports


class TestEmitAllReports:
    """Test the emit_all_reports orchestrator function."""

    def test_emit_all_reports_creates_four_files(self):
        """Test that emit_all_reports creates all four required files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            artifacts_dir = Path(temp_dir) / "artifacts"
            artifacts_dir.mkdir()

            # Create minimal rollup fixture
            rollup = {
                "config_source": "ai_config.json",
                "dnt_coverage": "present",
                "termbase_coverage": "full",
                "termbase_entry_counts": {"fr": 1},
                "languages": {
                    "fr": {
                        "files": [
                            {
                                "target_file": "test - FR.srt",
                                "issues": {
                                    "missing_translation": [],
                                    "timing_fail": False,
                                },
                            }
                        ]
                    }
                },
                "original_language": {"detected": "en"},
            }

            # Create valid ai_config.json
            ai_config = {
                "version": "1.0.0",
                "timestamp": "2025-01-01T00:00:00Z",
                "target_languages": ["fr"],
                "dnt_terms": ["test"],
                "termbase": {"fr": {"test": "test"}},
            }
            (artifacts_dir / "ai_config.json").write_text(
                json.dumps(ai_config, indent=2), encoding="utf-8"
            )

            # Call emit_all_reports
            emit_all_reports(artifacts_dir, rollup)

            # Verify all four files exist
            expected_files = [
                "eval_report.json",
                "report_v1.json",
                "eval_report.md",
                "eval_report.html",
            ]

            for filename in expected_files:
                file_path = artifacts_dir / filename
                assert file_path.exists(), f"Expected file {filename} not found"

    def test_emit_all_reports_uses_report_v1_for_presenters(self):
        """Test that presenters are fed report_v1.json, not eval_report.json."""
        with tempfile.TemporaryDirectory() as temp_dir:
            artifacts_dir = Path(temp_dir) / "artifacts"
            artifacts_dir.mkdir()

            # Create minimal rollup fixture
            rollup = {
                "config_source": "ai_config.json",
                "dnt_coverage": "present",
                "termbase_coverage": "full",
                "termbase_entry_counts": {"fr": 1},
                "languages": {
                    "fr": {
                        "files": [
                            {
                                "target_file": "test - FR.srt",
                                "issues": {
                                    "missing_translation": [],
                                    "timing_fail": False,
                                },
                            }
                        ]
                    }
                },
                "original_language": {"detected": "en"},
            }

            # Create valid ai_config.json
            ai_config = {
                "version": "1.0.0",
                "timestamp": "2025-01-01T00:00:00Z",
                "target_languages": ["fr"],
                "dnt_terms": ["test"],
                "termbase": {"fr": {"test": "test"}},
            }
            (artifacts_dir / "ai_config.json").write_text(
                json.dumps(ai_config, indent=2), encoding="utf-8"
            )

            # Call emit_all_reports
            emit_all_reports(artifacts_dir, rollup)

            # Verify that report_v1.json was created and contains presenter-specific content
            report_v1_path = artifacts_dir / "report_v1.json"
            assert report_v1_path.exists()

            report_v1_data = json.loads(report_v1_path.read_text(encoding="utf-8"))

            # Check for presenter-specific content that wouldn't be in eval_report.json
            assert "decision" in report_v1_data
            assert "kpis" in report_v1_data
            assert "file_status" in report_v1_data
            assert "lexicons" in report_v1_data
            assert "sections" in report_v1_data

            # Verify that presenters were called with report_v1.json
            # by checking for content that's only injected by presenters
            md_path = artifacts_dir / "eval_report.md"
            html_path = artifacts_dir / "eval_report.html"

            assert md_path.exists()
            assert html_path.exists()

            # Check for presenter-specific content in outputs
            md_content = md_path.read_text(encoding="utf-8")
            html_content = html_path.read_text(encoding="utf-8")

            # These strings should only appear if presenters processed report_v1.json
            assert "Files:" in md_content
            assert "Languages:" in md_content
            assert "Files:" in html_content
            assert "Languages:" in html_content

    def test_emit_all_reports_no_direct_presenter_calls(self):
        """Test that emit_all_reports doesn't call presenters directly with eval_report.json."""
        with tempfile.TemporaryDirectory() as temp_dir:
            artifacts_dir = Path(temp_dir) / "artifacts"
            artifacts_dir.mkdir()

            # Create minimal rollup fixture
            rollup = {
                "config_source": "ai_config.json",
                "dnt_coverage": "present",
                "termbase_coverage": "full",
                "termbase_entry_counts": {"fr": 1},
                "languages": {
                    "fr": {
                        "files": [
                            {
                                "target_file": "test - FR.srt",
                                "issues": {
                                    "missing_translation": [],
                                    "timing_fail": False,
                                },
                            }
                        ]
                    }
                },
                "original_language": {"detected": "en"},
            }

            # Create valid ai_config.json
            ai_config = {
                "version": "1.0.0",
                "timestamp": "2025-01-01T00:00:00Z",
                "target_languages": ["fr"],
                "dnt_terms": ["test"],
                "termbase": {"fr": {"test": "test"}},
            }
            (artifacts_dir / "ai_config.json").write_text(
                json.dumps(ai_config, indent=2), encoding="utf-8"
            )

            # Mock the presenters to verify they're called with report_v1.json
            with (
                patch("srt_translator.presenters.eval_md.build.build_eval_md") as mock_md,
                patch("srt_translator.presenters.eval_html.build.build_eval_html") as mock_html,
            ):
                mock_md.return_value = artifacts_dir / "eval_report.md"
                mock_html.return_value = artifacts_dir / "eval_report.html"

                # Call emit_all_reports
                emit_all_reports(artifacts_dir, rollup)

                # Verify presenters were called with report_v1.json path
                mock_md.assert_called_once()
                mock_html.assert_called_once()

                # Get the path that was passed to the presenters
                md_call_args = mock_md.call_args[0]
                html_call_args = mock_html.call_args[0]

                # Verify they were called with report_v1.json, not eval_report.json
                assert md_call_args[0].name == "report_v1.json"
                assert html_call_args[0].name == "report_v1.json"

    def test_emit_all_reports_missing_ai_config_raises_error(self):
        """Test that missing ai_config.json raises an error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            artifacts_dir = Path(temp_dir) / "artifacts"
            artifacts_dir.mkdir()

            # Create minimal rollup fixture
            rollup = {
                "config_source": "ai_config.json",
                "dnt_coverage": "present",
                "termbase_coverage": "full",
                "termbase_entry_counts": {"fr": 1},
                "languages": {
                    "fr": {
                        "files": [
                            {
                                "target_file": "test - FR.srt",
                                "issues": {
                                    "missing_translation": [],
                                    "timing_fail": False,
                                },
                            }
                        ]
                    }
                },
                "original_language": {"detected": "en"},
            }

            # Don't create ai_config.json - this should cause an error
            with pytest.raises(ValueError, match="ai_config.json not found"):
                emit_all_reports(artifacts_dir, rollup)

    def test_emit_all_reports_handles_compilation_error(self):
        """Test that compilation errors are handled gracefully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            artifacts_dir = Path(temp_dir) / "artifacts"
            artifacts_dir.mkdir()

            # Create minimal rollup fixture
            rollup = {
                "config_source": "ai_config.json",
                "dnt_coverage": "present",
                "termbase_coverage": "full",
                "termbase_entry_counts": {"fr": 1},
                "languages": {
                    "fr": {
                        "files": [
                            {
                                "target_file": "test - FR.srt",
                                "issues": {
                                    "missing_translation": [],
                                    "timing_fail": False,
                                },
                            }
                        ]
                    }
                },
                "original_language": {"detected": "en"},
            }

            # Create invalid ai_config.json (missing required fields)
            ai_config = {"version": "1.0.0"}  # Missing required fields
            (artifacts_dir / "ai_config.json").write_text(
                json.dumps(ai_config, indent=2), encoding="utf-8"
            )

            # This should raise an error during compilation
            with pytest.raises(ValueError):
                emit_all_reports(artifacts_dir, rollup)
