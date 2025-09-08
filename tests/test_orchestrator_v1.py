"""Tests for the orchestrator with unified pipeline."""

import json
from pathlib import Path

import pytest

from srt_translator.eval.report import emit_all_reports


class TestOrchestratorV1:
    """Test the orchestrator with unified pipeline."""

    def test_emit_all_reports_ok(self, tmp_path):
        """Test orchestrator with OK fixture produces all outputs."""
        # Setup artifacts directory
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()

        # Create eval_report.json
        eval_data = json.loads(Path("tests/fixtures/eval_report_strict_ok.json").read_text())
        (artifacts_dir / "eval_report.json").write_text(json.dumps(eval_data))

        # Create ai_config.json
        ai_data = json.loads(Path("tests/fixtures/ai_config_ok.json").read_text())
        (artifacts_dir / "ai_config.json").write_text(json.dumps(ai_data))

        # Create mock rollup data
        rollup = {
            "languages": {
                "es": {
                    "files": [
                        {"target_file": "test1.srt", "issues": {}},
                        {"target_file": "test2.srt", "issues": {}},
                    ]
                }
            },
            "original_language": {"detected": "en"},
        }

        # Run orchestrator
        paths = emit_all_reports(artifacts_dir, rollup)

        # Verify all outputs exist
        assert "eval_report_json" in paths
        assert "report_v1_json" in paths
        assert "eval_report_md" in paths
        assert "eval_report_html" in paths

        for name, path in paths.items():
            assert Path(path).exists(), f"{name} should exist at {path}"

        # Verify report_v1.json has correct schema
        report_v1_data = json.loads(Path(paths["report_v1_json"]).read_text())
        assert report_v1_data["version"] == "1.0"
        assert "meta" in report_v1_data
        assert "decision" in report_v1_data
        assert "kpis" in report_v1_data
        assert "file_status" in report_v1_data
        assert "sections" in report_v1_data
        assert "lexicons" in report_v1_data

        # Verify decision is pass
        assert report_v1_data["decision"]["level"] == "pass"

        # Verify HTML and MD contain expected content
        html_content = Path(paths["eval_report_html"]).read_text()
        assert "✅" in html_content
        assert "What to do next" in html_content
        assert "KPIs" in html_content

        md_content = Path(paths["eval_report_md"]).read_text()
        assert "# ✅" in md_content
        assert "## What to do next" in md_content
        assert "## KPIs" in md_content

    def test_emit_all_reports_mixed(self, tmp_path):
        """Test orchestrator with mixed fixture produces all outputs."""
        # Setup artifacts directory
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()

        # Create eval_report.json
        eval_data = json.loads(Path("tests/fixtures/eval_report_strict_mixed.json").read_text())
        (artifacts_dir / "eval_report.json").write_text(json.dumps(eval_data))

        # Create ai_config.json
        ai_data = json.loads(Path("tests/fixtures/ai_config_mixed.json").read_text())
        (artifacts_dir / "ai_config.json").write_text(json.dumps(ai_data))

        # Create mock rollup data
        rollup = {
            "languages": {
                "es": {
                    "files": [
                        {
                            "target_file": "test1.srt",
                            "issues": {
                                "missing_translation": [{"idx": 1, "src": "Hello", "tgt": ""}],
                                "timing_fail": [{"idx": 2, "src": "API", "tgt": "API"}],
                            },
                        },
                        {
                            "target_file": "test2.srt",
                            "issues": {
                                "missing_translation": [{"idx": 3, "src": "World", "tgt": ""}]
                            },
                        },
                    ]
                }
            },
            "original_language": {"detected": "en"},
        }

        # Run orchestrator
        paths = emit_all_reports(artifacts_dir, rollup)

        # Verify all outputs exist
        for name, path in paths.items():
            assert Path(path).exists(), f"{name} should exist at {path}"

        # Verify report_v1.json has correct schema
        report_v1_data = json.loads(Path(paths["report_v1_json"]).read_text())
        assert report_v1_data["decision"]["level"] == "fix"  # Has errors

        # Verify HTML and MD contain punch list
        html_content = Path(paths["eval_report_html"]).read_text()
        assert "❌" in html_content
        assert "Critical Issues" in html_content
        assert "Warnings" in html_content

        md_content = Path(paths["eval_report_md"]).read_text()
        assert "# ❌" in md_content
        assert "## ❌ Critical Issues" in md_content
        assert "## ⚠️ Warnings" in md_content

    def test_emit_all_reports_missing_ai_config(self, tmp_path):
        """Test orchestrator fails fast on missing ai_config.json."""
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()

        # Create eval_report.json but no ai_config.json
        eval_data = json.loads(Path("tests/fixtures/eval_report_strict_ok.json").read_text())
        (artifacts_dir / "eval_report.json").write_text(json.dumps(eval_data))

        rollup = {"languages": {}, "original_language": {"detected": "en"}}

        with pytest.raises(ValueError, match="ai_config.json not found"):
            emit_all_reports(artifacts_dir, rollup)
