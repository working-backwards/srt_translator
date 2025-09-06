"""Tests for the HTML presenter build module."""

import shutil
from pathlib import Path

import pytest

from srt_translator.presenters.eval_html.build import build_eval_html
from srt_translator.report.compiler import compile_report


class TestEvalHtmlBuild:
    """Test cases for the HTML presenter build functionality."""

    def test_build_eval_html_success_strict(self, tmp_path):
        """Test successful HTML generation with strict fixtures."""
        # Copy strict fixtures to temp directory
        fixtures_dir = Path(__file__).parent.parent / "fixtures"

        eval_report_src = fixtures_dir / "eval_report_strict.json"
        ai_config_src = fixtures_dir / "ai_config_strict.json"

        eval_report_dst = tmp_path / "eval_report.json"
        ai_config_dst = tmp_path / "ai_config.json"

        shutil.copy2(eval_report_src, eval_report_dst)
        shutil.copy2(ai_config_src, ai_config_dst)

        # First compile report_v1.json
        report_v1_path = compile_report(tmp_path)

        # Run the function
        output_path = tmp_path / "eval_report.html"
        result_path = build_eval_html(report_v1_path, output_path)

        # Assertions
        assert result_path == output_path
        assert output_path.exists()

        # Read the generated HTML
        html_content = output_path.read_text(encoding="utf-8")

        # Check decision banner
        assert "❌ Fix required: 3 error(s), 1 warning(s) found." in html_content

        # Check what to do next
        assert "What to do next" in html_content
        assert (
            "Work through the Punch List below; fix **errors first**, then warnings."
            in html_content
        )
        assert "Use the context snippets to validate or regenerate translations." in html_content

        # Check that HTML was generated successfully
        assert "Eval Report" in html_content
        assert "<!DOCTYPE html>" in html_content
        assert "<html" in html_content
        assert "</html>" in html_content

    def test_build_eval_html_default_output_path(self, tmp_path):
        """Test that default output path is used when not specified."""
        # Copy strict fixtures to temp directory
        fixtures_dir = Path(__file__).parent.parent / "fixtures"

        eval_report_src = fixtures_dir / "eval_report_strict.json"
        ai_config_src = fixtures_dir / "ai_config_strict.json"

        eval_report_dst = tmp_path / "eval_report.json"
        ai_config_dst = tmp_path / "ai_config.json"

        shutil.copy2(eval_report_src, eval_report_dst)
        shutil.copy2(ai_config_src, ai_config_dst)

        # First compile report_v1.json
        report_v1_path = compile_report(tmp_path)

        # Run without specifying output path
        result_path = build_eval_html(report_v1_path)

        # Should create HTML file next to JSON file
        expected_path = report_v1_path.with_suffix(".html")
        assert result_path == expected_path
        assert expected_path.exists()

    def test_build_eval_html_missing_ai_config(self, tmp_path):
        """Test fail-fast when ai_config.json is missing."""
        # Copy only eval_report to temp directory (no ai_config.json)
        fixtures_dir = Path(__file__).parent.parent / "fixtures"
        eval_report_src = fixtures_dir / "eval_report_strict.json"
        eval_report_dst = tmp_path / "eval_report.json"

        shutil.copy2(eval_report_src, eval_report_dst)

        # Should raise ValueError when compiling
        with pytest.raises(ValueError, match="ai_config.json not found"):
            compile_report(tmp_path)

    def test_build_eval_html_missing_eval_fields(self, tmp_path):
        """Test fail-fast when required eval_report.json fields are missing."""
        # Copy fixtures with missing fields
        fixtures_dir = Path(__file__).parent.parent / "fixtures"

        eval_report_src = fixtures_dir / "eval_report_missing_fields.json"
        ai_config_src = fixtures_dir / "ai_config_strict.json"

        eval_report_dst = tmp_path / "eval_report.json"
        ai_config_dst = tmp_path / "ai_config.json"

        shutil.copy2(eval_report_src, eval_report_dst)
        shutil.copy2(ai_config_src, ai_config_dst)

        # Should raise ValueError when compiling
        with pytest.raises(
            ValueError,
            match="eval_report.json missing required keys:",
        ):
            compile_report(tmp_path)

    def test_build_eval_html_missing_ai_config_keys(self, tmp_path):
        """Test fail-fast when required ai_config.json keys are missing."""
        # Copy fixtures with missing keys
        fixtures_dir = Path(__file__).parent.parent / "fixtures"

        eval_report_src = fixtures_dir / "eval_report_strict.json"
        ai_config_src = fixtures_dir / "ai_config_missing_keys.json"

        eval_report_dst = tmp_path / "eval_report.json"
        ai_config_dst = tmp_path / "ai_config.json"

        shutil.copy2(eval_report_src, eval_report_dst)
        shutil.copy2(ai_config_src, ai_config_dst)

        # Should raise ValueError when compiling
        with pytest.raises(ValueError, match="ai_config.json missing required keys: termbase"):
            compile_report(tmp_path)

    def test_build_eval_html_invalid_json(self, tmp_path):
        """Test error handling for invalid JSON."""
        # Create invalid JSON file
        invalid_json = tmp_path / "invalid.json"
        invalid_json.write_text("{ invalid json }", encoding="utf-8")

        # Should raise ValueError
        with pytest.raises(ValueError, match="Invalid JSON"):
            build_eval_html(invalid_json)

    def test_build_eval_html_missing_file(self, tmp_path):
        """Test error handling for missing input file."""
        missing_file = tmp_path / "missing.json"

        # Should raise ValueError
        with pytest.raises(ValueError, match="Required file not found"):
            build_eval_html(missing_file)
