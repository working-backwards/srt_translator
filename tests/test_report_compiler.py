"""Tests for the report compiler."""

import json
import tempfile
from pathlib import Path

import pytest

from srt_translator.report.compiler import compile_report


class TestReportCompiler:
    """Test the report compiler functionality."""

    def test_compile_report_success(self):
        """Test successful compilation of report_v1.json."""
        with tempfile.TemporaryDirectory() as tmpdir:
            artifacts_dir = Path(tmpdir)

            # Copy test fixtures
            fixtures_dir = Path(__file__).parent / "fixtures" / "report_v1"
            eval_data = json.loads((fixtures_dir / "eval_report.json").read_text())
            ai_data = json.loads((fixtures_dir / "ai_config.json").read_text())

            # Write test data
            (artifacts_dir / "eval_report.json").write_text(json.dumps(eval_data))
            (artifacts_dir / "ai_config.json").write_text(json.dumps(ai_data))

            # Compile report
            result_path = compile_report(artifacts_dir)

            # Verify output exists
            assert result_path.exists()
            assert result_path.name == "report_v1.json"

            # Load and verify structure
            report_data = json.loads(result_path.read_text(encoding="utf-8"))

            # Check required top-level keys
            required_keys = {
                "version",
                "timestamp",
                "batch_label",
                "decision",
                "totals",
                "kpis",
                "file_status",
                "lexicons",
                "sections",
            }
            assert set(report_data.keys()) == required_keys

            # Check decision state (should be FIX due to errors)
            assert report_data["decision"]["state"] == "FIX"
            assert "error(s)" in report_data["decision"]["banner_text"]

            # Check totals
            totals = report_data["totals"]
            assert totals["files_total"] == 2
            assert totals["languages_total"] == 2
            assert totals["errors_total"] == 2  # 1 untranslated_after_dnt + 1 timing_fail
            assert totals["warnings_total"] == 2  # 2 missing_translation (reclassified)

            # Check KPIs
            kpis = report_data["kpis"]
            assert kpis["Files"] == "2"
            assert kpis["Languages"] == "2"
            assert kpis["Errors"] == "2"
            assert kpis["Warnings"] == "2"
            assert kpis["DNT coverage"] == "full"
            assert kpis["Termbase coverage"] == "full"

            # Check file status (should be sorted by file_path)
            file_status = report_data["file_status"]
            assert len(file_status) == 4  # 2 files × 2 languages

            # Verify sorting
            file_paths = [fs["file_path"] for fs in file_status]
            assert file_paths == sorted(file_paths)

            # Check lexicons
            lexicons = report_data["lexicons"]
            assert "dnt_terms" in lexicons
            assert "termbase" in lexicons
            assert len(lexicons["dnt_terms"]) == 3
            assert "French" in lexicons["termbase"]
            assert "Japanese" in lexicons["termbase"]

    def test_compile_report_missing_eval_file(self):
        """Test error when eval_report.json is missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            artifacts_dir = Path(tmpdir)

            with pytest.raises(ValueError, match="eval_report.json not found"):
                compile_report(artifacts_dir)

    def test_compile_report_missing_ai_config(self):
        """Test error when ai_config.json is missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            artifacts_dir = Path(tmpdir)

            # Create eval_report.json but not ai_config.json
            eval_data = {"files_total": 1, "languages_total": 1, "issues_total": 0, "languages": {}}
            (artifacts_dir / "eval_report.json").write_text(json.dumps(eval_data))

            with pytest.raises(ValueError, match="ai_config.json not found"):
                compile_report(artifacts_dir)

    def test_compile_report_invalid_json(self):
        """Test error when JSON files are malformed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            artifacts_dir = Path(tmpdir)

            # Write invalid JSON
            (artifacts_dir / "eval_report.json").write_text("invalid json")
            (artifacts_dir / "ai_config.json").write_text("invalid json")

            with pytest.raises(ValueError, match="Invalid JSON"):
                compile_report(artifacts_dir)

    def test_compile_report_missing_required_keys(self):
        """Test error when required keys are missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            artifacts_dir = Path(tmpdir)

            # Write incomplete data
            incomplete_eval = {"files_total": 1}  # Missing required keys
            incomplete_ai = {"dnt_terms": []}  # Missing required keys

            (artifacts_dir / "eval_report.json").write_text(json.dumps(incomplete_eval))
            (artifacts_dir / "ai_config.json").write_text(json.dumps(incomplete_ai))

            with pytest.raises(ValueError, match="missing required keys"):
                compile_report(artifacts_dir)

    def test_compile_report_ready_status(self):
        """Test compilation with READY status (no errors or warnings)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            artifacts_dir = Path(tmpdir)

            # Create data with no issues
            eval_data = {
                "files_total": 1,
                "languages_total": 1,
                "issues_total": 0,
                "languages": {
                    "fr": {
                        "files": {
                            "test - FR.srt": {
                                "missing_translation": 0,
                                "untranslated_after_dnt": 0,
                                "timing_fail": 0,
                            }
                        }
                    }
                },
            }

            ai_data = {"dnt_terms": ["test"], "termbase": {"French": {"test": "test"}}}

            (artifacts_dir / "eval_report.json").write_text(json.dumps(eval_data))
            (artifacts_dir / "ai_config.json").write_text(json.dumps(ai_data))

            result_path = compile_report(artifacts_dir)
            report_data = json.loads(result_path.read_text(encoding="utf-8"))

            assert report_data["decision"]["state"] == "READY"
            assert "Everything looks great" in report_data["decision"]["banner_text"]
            assert report_data["totals"]["errors_total"] == 0
            assert report_data["totals"]["warnings_total"] == 0

    def test_compile_report_review_status(self):
        """Test compilation with REVIEW status (warnings only)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            artifacts_dir = Path(tmpdir)

            # Create data with warnings only
            eval_data = {
                "files_total": 1,
                "languages_total": 1,
                "issues_total": 1,
                "languages": {
                    "fr": {
                        "files": {
                            "test - FR.srt": {
                                "missing_translation": 1,  # Warning
                                "untranslated_after_dnt": 0,
                                "timing_fail": 0,
                            }
                        }
                    }
                },
            }

            ai_data = {"dnt_terms": ["test"], "termbase": {"French": {"test": "test"}}}

            (artifacts_dir / "eval_report.json").write_text(json.dumps(eval_data))
            (artifacts_dir / "ai_config.json").write_text(json.dumps(ai_data))

            result_path = compile_report(artifacts_dir)
            report_data = json.loads(result_path.read_text(encoding="utf-8"))

            assert report_data["decision"]["state"] == "REVIEW"
            assert "Review recommended" in report_data["decision"]["banner_text"]
            assert report_data["totals"]["errors_total"] == 0
            assert report_data["totals"]["warnings_total"] == 1
