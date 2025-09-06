"""Tests for the presenters with unified report_v1.json schema."""

import json

import pytest

from srt_translator.presenters.eval_html.build import build_eval_html
from srt_translator.presenters.eval_md.build import build_eval_md


class TestPresentersV1:
    """Test presenters with unified report_v1.json schema."""

    def test_html_presenter_ok(self, tmp_path):
        """Test HTML presenter with OK report."""
        # Create report_v1.json with OK data
        report_data = {
            "version": "1.0",
            "meta": {
                "batch_id": "test-batch",
                "created_at": "2024-01-01T00:00:00Z",
                "source_language": "en",
            },
            "decision": {
                "level": "pass",
                "one_liner": "Everything looks great. Your translated files are ready to use.",
            },
            "kpis": {
                "files_total": 2,
                "languages_total": 1,
                "issues_total": 0,
                "errors_total": 0,
                "warnings_total": 0,
                "dnt_terms_count": 3,
                "termbase_languages_count": 1,
            },
            "file_status": {"es": {"test1.srt": "ok", "test2.srt": "ok"}},
            "sections": {"errors": [], "warnings": []},
            "lexicons": {
                "dnt_terms": ["API", "JSON", "HTTP"],
                "termbase": {
                    "es": [
                        {"source": "hello", "preferred": "hola"},
                        {"source": "world", "preferred": "mundo"},
                    ]
                },
            },
        }

        report_path = tmp_path / "report_v1.json"
        report_path.write_text(json.dumps(report_data))

        # Generate HTML
        html_path = build_eval_html(report_path)

        # Verify
        assert html_path.exists()
        html_content = html_path.read_text()

        # Check for key sections
        assert "✅ Everything looks great" in html_content
        assert "What to do next" in html_content
        assert "KPIs" in html_content
        assert "File Status" in html_content
        assert "No Issues Found" in html_content
        assert "Do-Not-Translate Terms" in html_content
        assert "Termbase" in html_content

        # Check KPIs
        assert "Files: 2" in html_content
        assert "Languages: 1" in html_content
        assert "Errors: 0" in html_content
        assert "Warnings: 0" in html_content

    def test_html_presenter_mixed(self, tmp_path):
        """Test HTML presenter with mixed report."""
        # Create report_v1.json with mixed data
        report_data = {
            "version": "1.0",
            "meta": {
                "batch_id": "test-batch",
                "created_at": "2024-01-01T00:00:00Z",
                "source_language": "en",
            },
            "decision": {
                "level": "fix",
                "one_liner": "Fix required: 2 error(s), 1 warning(s) found.",
            },
            "kpis": {
                "files_total": 2,
                "languages_total": 1,
                "issues_total": 3,
                "errors_total": 2,
                "warnings_total": 1,
                "dnt_terms_count": 2,
                "termbase_languages_count": 1,
            },
            "file_status": {"es": {"test1.srt": "error", "test2.srt": "warning"}},
            "sections": {
                "errors": [
                    {
                        "lang": "es",
                        "file": "test1.srt",
                        "subtitle": 1,
                        "type": "untranslated_after_dnt",
                        "message": "This term should not be translated.",
                        "suggest_fix": "Keep the original term untranslated.",
                        "context": {
                            "target_window": ["1: API endpoint"],
                            "source_window": ["1: Punto final API"],
                        },
                    }
                ],
                "warnings": [
                    {
                        "lang": "es",
                        "file": "test2.srt",
                        "subtitle": 2,
                        "type": "missing_translation",
                        "message": "This subtitle may be incomplete.",
                        "suggest_fix": "Check if the translation was cut off.",
                        "context": {
                            "target_window": ["2: Hello world"],
                            "source_window": ["2: Hola mundo"],
                        },
                    }
                ],
            },
            "lexicons": {
                "dnt_terms": ["API", "JSON"],
                "termbase": {"es": [{"source": "hello", "preferred": "hola"}]},
            },
        }

        report_path = tmp_path / "report_v1.json"
        report_path.write_text(json.dumps(report_data))

        # Generate HTML
        html_path = build_eval_html(report_path)

        # Verify
        assert html_path.exists()
        html_content = html_path.read_text()

        # Check for key sections
        assert "❌ Fix required" in html_content
        assert "Critical Issues" in html_content
        assert "Warnings" in html_content
        assert "untranslated_after_dnt" in html_content
        assert "missing_translation" in html_content

        # Check KPIs
        assert "Errors: 2" in html_content
        assert "Warnings: 1" in html_content

    def test_md_presenter_ok(self, tmp_path):
        """Test MD presenter with OK report."""
        # Create report_v1.json with OK data
        report_data = {
            "version": "1.0",
            "meta": {
                "batch_id": "test-batch",
                "created_at": "2024-01-01T00:00:00Z",
                "source_language": "en",
            },
            "decision": {
                "level": "pass",
                "one_liner": "Everything looks great. Your translated files are ready to use.",
            },
            "kpis": {
                "files_total": 2,
                "languages_total": 1,
                "issues_total": 0,
                "errors_total": 0,
                "warnings_total": 0,
                "dnt_terms_count": 3,
                "termbase_languages_count": 1,
            },
            "file_status": {"es": {"test1.srt": "ok", "test2.srt": "ok"}},
            "sections": {"errors": [], "warnings": []},
            "lexicons": {
                "dnt_terms": ["API", "JSON", "HTTP"],
                "termbase": {
                    "es": [
                        {"source": "hello", "preferred": "hola"},
                        {"source": "world", "preferred": "mundo"},
                    ]
                },
            },
        }

        report_path = tmp_path / "report_v1.json"
        report_path.write_text(json.dumps(report_data))

        # Generate MD
        md_path = build_eval_md(report_path)

        # Verify
        assert md_path.exists()
        md_content = md_path.read_text()

        # Check for key sections
        assert "# ✅ Everything looks great" in md_content
        assert "## What to do next" in md_content
        assert "## KPIs" in md_content
        assert "## File Status" in md_content
        assert "## ✅ No Issues Found" in md_content
        assert "## Lexicons" in md_content
        assert "### DNT Terms" in md_content
        assert "### Termbases" in md_content

        # Check KPIs
        assert "**Files:** 2" in md_content
        assert "**Languages:** 1" in md_content
        assert "**Errors:** 0" in md_content
        assert "**Warnings:** 0" in md_content

    def test_md_presenter_mixed(self, tmp_path):
        """Test MD presenter with mixed report."""
        # Create report_v1.json with mixed data
        report_data = {
            "version": "1.0",
            "meta": {
                "batch_id": "test-batch",
                "created_at": "2024-01-01T00:00:00Z",
                "source_language": "en",
            },
            "decision": {"level": "review", "one_liner": "Review recommended: 1 warning(s) found."},
            "kpis": {
                "files_total": 1,
                "languages_total": 1,
                "issues_total": 1,
                "errors_total": 0,
                "warnings_total": 1,
                "dnt_terms_count": 2,
                "termbase_languages_count": 1,
            },
            "file_status": {"es": {"test1.srt": "warning"}},
            "sections": {
                "errors": [],
                "warnings": [
                    {
                        "lang": "es",
                        "file": "test1.srt",
                        "subtitle": 1,
                        "type": "missing_translation",
                        "message": "This subtitle may be incomplete.",
                        "suggest_fix": "Check if the translation was cut off.",
                        "context": {
                            "target_window": ["1: Hello world"],
                            "source_window": ["1: Hola mundo"],
                        },
                    }
                ],
            },
            "lexicons": {
                "dnt_terms": ["API", "JSON"],
                "termbase": {"es": [{"source": "hello", "preferred": "hola"}]},
            },
        }

        report_path = tmp_path / "report_v1.json"
        report_path.write_text(json.dumps(report_data))

        # Generate MD
        md_path = build_eval_md(report_path)

        # Verify
        assert md_path.exists()
        md_content = md_path.read_text()

        # Check for key sections
        assert "# ⚠️ Review recommended" in md_content
        assert "## ⚠️ Warnings" in md_content
        assert "missing_translation" in md_content

        # Check KPIs
        assert "**Warnings:** 1" in md_content

    def test_presenters_missing_required_keys(self, tmp_path):
        """Test presenters fail fast on missing required keys."""
        # Create incomplete report
        report_data = {
            "version": "1.0",
            "decision": {"level": "pass"},
            # Missing required keys
        }

        report_path = tmp_path / "report_v1.json"
        report_path.write_text(json.dumps(report_data))

        # HTML presenter should fail
        with pytest.raises(ValueError, match="missing required keys"):
            build_eval_html(report_path)

        # MD presenter should fail
        with pytest.raises(ValueError, match="missing required keys"):
            build_eval_md(report_path)
