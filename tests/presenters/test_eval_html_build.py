"""Tests for the HTML presenter build module."""

import json
from pathlib import Path

import pytest

from srt_translator.presenters.eval_html.build import build_eval_html


class TestEvalHtmlBuild:
    """Test cases for the HTML presenter build functionality."""

    def test_build_eval_html_smoke(self, tmp_path):
        """Smoke test for build_eval_html function."""
        # Load the fixture
        fixture_path = Path(__file__).parent.parent / "fixtures" / "eval_report_min.json"
        assert fixture_path.exists(), f"Fixture not found: {fixture_path}"

        # Read the fixture to get expected values
        with open(fixture_path, encoding="utf-8") as f:
            fixture_data = json.load(f)

        # Calculate expected KPI values
        languages = fixture_data.get("languages", {})
        expected_files_total = sum(
            len(lang_data.get("files", [])) for lang_data in languages.values()
        )
        expected_languages_total = len(languages)

        # Count total issues
        expected_issues_total = 0
        for lang_data in languages.values():
            for file_data in lang_data.get("files", []):
                issues = file_data.get("issues", {})
                expected_issues_total += len(issues.get("missing_translation", []))
                expected_issues_total += len(issues.get("untranslated_after_dnt", []))
                if issues.get("timing_fail"):
                    expected_issues_total += 1
                if not file_data.get("metrics", {}).get("parity_ok", True):
                    expected_issues_total += 1

        # Run the function
        output_path = tmp_path / "out.html"
        result_path = build_eval_html(fixture_path, output_path)

        # Assertions
        assert result_path == output_path
        assert output_path.exists()

        # Read the generated HTML
        html_content = output_path.read_text(encoding="utf-8")

        # Check for required content
        assert "Eval Report" in html_content
        assert f'<span class="kpi-value">{expected_files_total}</span>' in html_content
        assert f'<span class="kpi-value">{expected_languages_total}</span>' in html_content
        assert f'<span class="kpi-value">{expected_issues_total}</span>' in html_content

        # Check for language sections
        assert "Languages" in html_content
        assert "es" in html_content
        assert "fr" in html_content

        # Check for DNT and termbase sections
        assert "DNT Terms" in html_content
        assert "Termbase Violations" in html_content

        # Verify it's valid HTML structure
        assert "<!DOCTYPE html>" in html_content
        assert "<html" in html_content
        assert "</html>" in html_content
        assert "<head>" in html_content
        assert "<body>" in html_content
        assert "</body>" in html_content

    def test_build_eval_html_default_output_path(self, tmp_path):
        """Test that default output path is used when not specified."""
        fixture_path = Path(__file__).parent.parent / "fixtures" / "eval_report_min.json"

        # Run without specifying output path
        result_path = build_eval_html(fixture_path)

        # Should create HTML file next to JSON file
        expected_path = fixture_path.with_suffix(".html")
        assert result_path == expected_path
        assert expected_path.exists()

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
        with pytest.raises(ValueError, match="Required resource not found"):
            build_eval_html(missing_file)
