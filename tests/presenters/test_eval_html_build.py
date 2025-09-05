"""Tests for the HTML presenter build module."""

import shutil
from pathlib import Path

import pytest

from srt_translator.presenters.eval_html.build import build_eval_html


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

        # Run the function
        output_path = tmp_path / "eval_report.html"
        result_path = build_eval_html(eval_report_dst, output_path)

        # Assertions
        assert result_path == output_path
        assert output_path.exists()

        # Read the generated HTML
        html_content = output_path.read_text(encoding="utf-8")

        # Check decision banner
        assert (
            "❌ We found issues that will degrade quality. Fix the items below before publishing."
            in html_content
        )

        # Check what to do next
        assert "What to do next" in html_content
        assert "Resolve DNT or termbase violations in the listed files." in html_content
        assert "Fix cue parity mismatches or missing translations." in html_content
        assert "Re-run evaluation and confirm 'Ready to publish'." in html_content

        # Check KPIs - the HTML has label and value in separate spans
        assert "Files total:" in html_content
        assert "Languages:" in html_content
        assert "Issues (critical):" in html_content
        assert "Warnings (non-critical):" in html_content
        assert "Detected source language:" in html_content
        assert "DNT coverage:" in html_content
        assert "Termbase coverage:" in html_content
        # Check the actual values
        assert '<span class="kpi-value">3</span>' in html_content
        assert '<span class="kpi-value">2</span>' in html_content
        assert '<span class="kpi-value">4</span>' in html_content
        assert '<span class="kpi-value">0</span>' in html_content  # warnings
        assert '<span class="kpi-value">en</span>' in html_content
        assert '<span class="kpi-value">present</span>' in html_content
        assert '<span class="kpi-value">0/0 languages</span>' in html_content

        # Verify it's valid HTML structure
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

        # Run without specifying output path
        result_path = build_eval_html(eval_report_dst)

        # Should create HTML file next to JSON file
        expected_path = eval_report_dst.with_suffix(".html")
        assert result_path == expected_path
        assert expected_path.exists()

    def test_build_eval_html_missing_ai_config(self, tmp_path):
        """Test fail-fast when ai_config.json is missing."""
        # Copy only eval_report to temp directory (no ai_config.json)
        fixtures_dir = Path(__file__).parent.parent / "fixtures"
        eval_report_src = fixtures_dir / "eval_report_strict.json"
        eval_report_dst = tmp_path / "eval_report.json"

        shutil.copy2(eval_report_src, eval_report_dst)

        # Should raise ValueError
        with pytest.raises(ValueError, match="Required file not found"):
            build_eval_html(eval_report_dst)

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

        # Should raise ValueError
        with pytest.raises(
            ValueError,
            match="eval_report.json missing required keys: issues_total",
        ):
            build_eval_html(eval_report_dst)

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

        # Should raise ValueError
        with pytest.raises(ValueError, match="ai_config.json missing required keys: termbase"):
            build_eval_html(eval_report_dst)

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
