"""Tests for the orchestrator with unified pipeline."""

import json
from pathlib import Path

import pytest

from srt_translator.eval.report import emit_all_reports


def _setup_artifacts(tmp_path, eval_fixture, ai_fixture):
    """Write eval_report.json and ai_config.json into artifacts dir and return it."""
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    eval_data = json.loads(Path(eval_fixture).read_text(encoding="utf-8"))
    ai_data = json.loads(Path(ai_fixture).read_text(encoding="utf-8"))
    (artifacts_dir / "eval_report.json").write_text(json.dumps(eval_data), encoding="utf-8")
    (artifacts_dir / "ai_config.json").write_text(json.dumps(ai_data), encoding="utf-8")
    return artifacts_dir


class TestOrchestrator:
    """Test the orchestrator with unified pipeline."""

    def test_emit_all_reports_ok(self, tmp_path):
        """Test orchestrator with OK fixture produces all outputs."""
        artifacts_dir = _setup_artifacts(
            tmp_path,
            "tests/fixtures/eval_report_ok.json",
            "tests/fixtures/ai_config_ok.json",
        )

        rollup = {
            "languages": {
                "es": {
                    "files": [
                        {
                            "target_rel": "test1.srt",
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
                        },
                        {
                            "target_rel": "test2.srt",
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
                        },
                    ]
                }
            },
        }

        paths = emit_all_reports(artifacts_dir, rollup)

        # Verify all outputs exist
        assert "eval_report_json" in paths
        assert "report_json" in paths
        assert "eval_report_md" in paths
        assert "eval_report_html" in paths

        for name, path in paths.items():
            assert Path(path).exists(), f"{name} should exist at {path}"

        # Verify report.json has correct schema
        report_data = json.loads(Path(paths["report_json"]).read_text())
        assert report_data["decision"] == "pass"
        assert "ready to use" in report_data["one_liner"].lower()
        assert "punch_list" in report_data
        assert "kpis" in report_data
        assert "file_status" in report_data
        assert "lexicons" in report_data

        # Verify file statuses are "ready"
        for lang_files in report_data["file_status"].values():
            for status in lang_files.values():
                assert status == "ready"

    def test_emit_all_reports_mixed(self, tmp_path):
        """Test orchestrator with mixed fixture produces all outputs."""
        artifacts_dir = _setup_artifacts(
            tmp_path,
            "tests/fixtures/eval_report_mixed.json",
            "tests/fixtures/ai_config_mixed.json",
        )

        rollup = {
            "languages": {
                "es": {
                    "files": [
                        {
                            "target_rel": "test1.srt",
                            "issues_counts": {
                                "missing_translation": 1,
                                "timing_fail": 0,
                                "placeholder_mismatch": 0,
                                "parity_issue": 0,
                            },
                            "issues_detail": {
                                "missing_translation": [
                                    {
                                        "cue_index": 1,
                                        "source_text": "Hello",
                                        "target_text": "",
                                        "context": {"source": {}, "target": {}},
                                    }
                                ],
                                "timing_fail": [],
                                "placeholder_mismatch": [],
                                "parity_issue": [],
                            },
                        },
                        {
                            "target_rel": "test2.srt",
                            "issues_counts": {
                                "missing_translation": 1,
                                "timing_fail": 1,
                                "placeholder_mismatch": 0,
                                "parity_issue": 0,
                            },
                            "issues_detail": {
                                "missing_translation": [
                                    {
                                        "cue_index": 3,
                                        "source_text": "World",
                                        "target_text": "",
                                        "context": {"source": {}, "target": {}},
                                    }
                                ],
                                "timing_fail": [
                                    {
                                        "file_level": True,
                                        "median_start_ms": 250,
                                        "median_end_ms": 240,
                                        "p95_start_ms": 550,
                                        "p95_end_ms": 560,
                                    }
                                ],
                                "placeholder_mismatch": [],
                                "parity_issue": [],
                            },
                        },
                    ]
                }
            },
        }

        paths = emit_all_reports(artifacts_dir, rollup)

        for name, path in paths.items():
            assert Path(path).exists(), f"{name} should exist at {path}"

        # Verify report.json
        report_data = json.loads(Path(paths["report_json"]).read_text())
        assert report_data["decision"] == "fail"

        # Verify HTML and MD contain expected markers
        html_content = Path(paths["eval_report_html"]).read_text(encoding="utf-8")
        assert "❌" in html_content
        assert "Critical Issues" in html_content

        md_content = Path(paths["eval_report_md"]).read_text(encoding="utf-8")
        assert "# ❌" in md_content
        assert "## ❌ Critical Issues" in md_content

    def test_emit_all_reports_missing_ai_config(self, tmp_path):
        """Test orchestrator fails fast on missing ai_config.json."""
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()
        eval_data = json.loads(Path("tests/fixtures/eval_report_ok.json").read_text(encoding="utf-8"))
        (artifacts_dir / "eval_report.json").write_text(json.dumps(eval_data))

        rollup = {"languages": {}}

        with pytest.raises(ValueError, match="ai_config.json not found"):
            emit_all_reports(artifacts_dir, rollup)
