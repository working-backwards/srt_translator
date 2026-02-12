"""Tests for the emit_all_reports orchestrator function."""

import json
from unittest.mock import patch

import pytest

from srt_translator.eval.report import emit_all_reports


def _minimal_rollup():
    """Return a minimal rollup dict that emit_all_reports can process."""
    return {
        "languages": {
            "fr": {
                "files": [
                    {
                        "target_rel": "test - FR.srt",
                        "issues_counts": {
                            "missing_translation": 0,
                            "timing_fail": 0,
                            "placeholder_mismatch": 0,
                            "parity_issue": 0,
                        },
                        "issues_detail": {
                            "missing_translation": [],
                            "timing_fail": [],
                            "placeholder_mismatch": [],
                            "parity_issue": [],
                        },
                    }
                ]
            }
        },
    }


def _minimal_ai_config():
    return {
        "version": "1.0.0",
        "timestamp": "2025-01-01T00:00:00Z",
        "target_languages": ["fr"],
        "dnt_terms": ["test"],
        "termbase": {"fr": {"test": "test"}},
    }


class TestEmitAllReports:
    """Test the emit_all_reports orchestrator function."""

    def test_emit_all_reports_creates_four_files(self, tmp_path):
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()
        (artifacts_dir / "ai_config.json").write_text(json.dumps(_minimal_ai_config(), indent=2), encoding="utf-8")

        emit_all_reports(artifacts_dir, _minimal_rollup())

        for filename in ["eval_report.json", "report.json", "eval_report.md", "eval_report.html"]:
            assert (artifacts_dir / filename).exists(), f"Expected file {filename} not found"

    def test_emit_all_reports_uses_report_for_presenters(self, tmp_path):
        """Test that presenters are fed report.json, not eval_report.json."""
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()
        (artifacts_dir / "ai_config.json").write_text(json.dumps(_minimal_ai_config(), indent=2), encoding="utf-8")

        emit_all_reports(artifacts_dir, _minimal_rollup())

        report_path = artifacts_dir / "report.json"
        assert report_path.exists()

        report_data = json.loads(report_path.read_text(encoding="utf-8"))
        assert "decision" in report_data
        assert "kpis" in report_data
        assert "file_status" in report_data
        assert "lexicons" in report_data
        assert "punch_list" in report_data

    def test_emit_all_reports_no_direct_presenter_calls(self, tmp_path):
        """Test that presenters receive report.json path."""
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()
        (artifacts_dir / "ai_config.json").write_text(json.dumps(_minimal_ai_config(), indent=2), encoding="utf-8")

        with (
            patch("srt_translator.presenters.eval_md.build.build_eval_md") as mock_md,
            patch("srt_translator.presenters.eval_html.build.build_eval_html") as mock_html,
        ):
            mock_md.return_value = artifacts_dir / "eval_report.md"
            mock_html.return_value = artifacts_dir / "eval_report.html"

            emit_all_reports(artifacts_dir, _minimal_rollup())

            mock_md.assert_called_once()
            mock_html.assert_called_once()

            assert mock_md.call_args[0][0].name == "report.json"
            assert mock_html.call_args[0][0].name == "report.json"

    def test_emit_all_reports_missing_ai_config_raises_error(self, tmp_path):
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()

        with pytest.raises(ValueError, match="ai_config.json not found"):
            emit_all_reports(artifacts_dir, _minimal_rollup())

    def test_emit_all_reports_handles_compilation_error(self, tmp_path):
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()
        (artifacts_dir / "ai_config.json").write_text(json.dumps({"version": "1.0.0"}), encoding="utf-8")

        with pytest.raises(ValueError):
            emit_all_reports(artifacts_dir, _minimal_rollup())
