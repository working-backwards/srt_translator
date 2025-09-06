"""Tests for the report compiler v1."""

import json
from pathlib import Path

import pytest

from srt_translator.report.compiler import compile_report


class TestCompilerV1:
    """Test the report compiler with strict schema."""

    def test_compile_report_ok(self, tmp_path):
        """Test compiler with OK fixture produces pass decision."""
        # Setup fixtures
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()

        # Copy fixtures
        eval_data = json.loads(
            Path("tests/fixtures/eval_report_strict_ok.json").read_text(encoding="utf-8")
        )
        ai_data = json.loads(Path("tests/fixtures/ai_config_ok.json").read_text(encoding="utf-8"))

        (artifacts_dir / "eval_report.json").write_text(json.dumps(eval_data))
        (artifacts_dir / "ai_config.json").write_text(json.dumps(ai_data))

        # Compile
        result_path = compile_report(artifacts_dir)

        # Verify
        assert result_path.exists()
        result_data = json.loads(result_path.read_text())

        # Check schema
        assert result_data["version"] == "1.0"
        assert "meta" in result_data
        assert "decision" in result_data
        assert "kpis" in result_data
        assert "file_status" in result_data
        assert "sections" in result_data
        assert "lexicons" in result_data

        # Check decision
        assert result_data["decision"]["level"] == "pass"
        assert "ready to use" in result_data["decision"]["one_liner"].lower()

        # Check KPIs
        kpis = result_data["kpis"]
        assert kpis["files_total"] == 2
        assert kpis["languages_total"] == 1
        assert kpis["errors_total"] == 0
        assert kpis["warnings_total"] == 0
        assert kpis["dnt_terms_count"] == 3
        assert kpis["termbase_languages_count"] == 1

        # Check file status
        file_status = result_data["file_status"]
        assert "unknown" in file_status  # Language key
        assert "test1.srt" in file_status["unknown"]
        assert "test2.srt" in file_status["unknown"]
        assert file_status["unknown"]["test1.srt"] == "ok"
        assert file_status["unknown"]["test2.srt"] == "ok"

        # Check sections
        sections = result_data["sections"]
        assert sections["errors"] == []
        assert sections["warnings"] == []

        # Check lexicons
        lexicons = result_data["lexicons"]
        assert lexicons["dnt_terms"] == ["API", "JSON", "HTTP"]
        assert "es" in lexicons["termbase"]
        assert len(lexicons["termbase"]["es"]) == 2

    def test_compile_report_mixed(self, tmp_path):
        """Test compiler with mixed fixture produces review/fix decision."""
        # Setup fixtures
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()

        # Copy fixtures
        eval_data = json.loads(
            Path("tests/fixtures/eval_report_strict_mixed.json").read_text(encoding="utf-8")
        )
        ai_data = json.loads(
            Path("tests/fixtures/ai_config_mixed.json").read_text(encoding="utf-8")
        )

        (artifacts_dir / "eval_report.json").write_text(json.dumps(eval_data))
        (artifacts_dir / "ai_config.json").write_text(json.dumps(ai_data))

        # Compile
        result_path = compile_report(artifacts_dir)

        # Verify
        assert result_path.exists()
        result_data = json.loads(result_path.read_text())

        # Check decision
        assert result_data["decision"]["level"] == "fix"  # Has errors
        assert "fix required" in result_data["decision"]["one_liner"].lower()

        # Check KPIs
        kpis = result_data["kpis"]
        assert kpis["files_total"] == 2
        assert kpis["languages_total"] == 1
        assert kpis["errors_total"] == 2  # 1 untranslated_after_dnt + 1 timing_fail
        assert kpis["warnings_total"] == 2  # 2 missing_translation
        assert kpis["dnt_terms_count"] == 2
        assert kpis["termbase_languages_count"] == 1

        # Check file status
        file_status = result_data["file_status"]
        assert "unknown" in file_status
        assert file_status["unknown"]["test1.srt"] == "error"  # Has errors
        assert file_status["unknown"]["test2.srt"] == "error"  # Has errors

        # Check sections
        sections = result_data["sections"]
        assert len(sections["errors"]) == 2  # untranslated_after_dnt + timing_fail
        assert len(sections["warnings"]) == 2  # missing_translation

        # Check error types
        error_types = [e["type"] for e in sections["errors"]]
        assert "untranslated_after_dnt" in error_types
        assert "timing_misaligned" in error_types

        # Check warning types
        warning_types = [w["type"] for w in sections["warnings"]]
        assert all(t == "missing_translation" for t in warning_types)

        # Check lexicons
        lexicons = result_data["lexicons"]
        assert lexicons["dnt_terms"] == ["API", "JSON"]
        assert "es" in lexicons["termbase"]
        assert len(lexicons["termbase"]["es"]) == 3

    def test_compile_report_missing_files(self, tmp_path):
        """Test compiler fails fast on missing files."""
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()

        # Missing eval_report.json
        with pytest.raises(ValueError, match="eval_report.json not found"):
            compile_report(artifacts_dir)

        # Missing ai_config.json
        (artifacts_dir / "eval_report.json").write_text("{}")
        with pytest.raises(ValueError, match="ai_config.json not found"):
            compile_report(artifacts_dir)

    def test_compile_report_invalid_json(self, tmp_path):
        """Test compiler fails fast on invalid JSON."""
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()

        # Invalid JSON
        (artifacts_dir / "eval_report.json").write_text("{ invalid json")
        (artifacts_dir / "ai_config.json").write_text("{}")

        with pytest.raises(ValueError, match="Invalid JSON"):
            compile_report(artifacts_dir)
