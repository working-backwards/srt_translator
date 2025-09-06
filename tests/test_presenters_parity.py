"""Tests for presenter parity between HTML and MD presenters."""

import json
import tempfile
from pathlib import Path

from srt_translator.presenters.eval_html.build import build_eval_html
from srt_translator.presenters.eval_md.build import build_eval_md


class TestPresentersParity:
    """Test that HTML and MD presenters produce equivalent content."""

    def test_ready_case_parity(self):
        """Test parity for READY case (no issues)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            artifacts_dir = Path(temp_dir) / "artifacts"
            artifacts_dir.mkdir()

            # Create realistic report_v1.json with READY status
            report_v1_data = {
                "version": "1.0.0",
                "meta": {
                    "batch_id": "test-batch",
                    "created_at": "2025-01-01T00:00:00Z",
                    "source_language": "en",
                },
                "decision": {
                    "level": "ready",
                    "one_liner": "Everything looks great. Your translated files are ready to use.",
                },
                "kpis": {
                    "files_total": 1,
                    "languages_total": 1,
                    "errors_total": 0,
                    "warnings_total": 0,
                    "dnt_terms_count": 1,
                    "termbase_languages_count": 1,
                },
                "file_status": {
                    "test - FR.srt": {"language": "fr", "status": "ready", "issues": []}
                },
                "lexicons": {
                    "dnt_terms": ["test"],
                    "termbase": {"fr": [{"source": "test", "target": "test"}]},
                },
                "sections": {"errors": [], "warnings": []},
            }

            report_v1_path = artifacts_dir / "report_v1.json"
            report_v1_path.write_text(json.dumps(report_v1_data, indent=2), encoding="utf-8")

            # Generate both presentations
            html_path = build_eval_html(report_v1_path)
            md_path = build_eval_md(report_v1_path)

            html_content = html_path.read_text(encoding="utf-8")
            md_content = md_path.read_text(encoding="utf-8")

            # Check decision one-liner parity
            expected_banner = "Everything looks great. Your translated files are ready to use."
            assert expected_banner in html_content
            assert expected_banner in md_content

            # Check that "No Issues Found" appears (no issues)
            assert "No Issues Found" in html_content
            assert "No Issues Found" in md_content

            # Check KPI labels and values
            expected_kpi_labels = ["Files:", "Languages:", "Errors:", "Warnings:"]
            for label in expected_kpi_labels:
                assert label in html_content
                assert label in md_content

            # Check DNT and Termbase headings
            assert "DNT Terms" in html_content
            assert "DNT Terms" in md_content
            assert "Termbase" in html_content
            assert "Termbase" in md_content

    def test_review_case_parity(self):
        """Test parity for REVIEW case (warnings only)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            artifacts_dir = Path(temp_dir) / "artifacts"
            artifacts_dir.mkdir()

            # Create realistic report_v1.json with REVIEW status
            report_v1_data = {
                "version": "1.0.0",
                "timestamp": "2025-01-01T00:00:00Z",
                "batch_label": "test-batch",
                "decision": {
                    "state": "REVIEW",
                    "banner_text": "Review recommended. Check warnings before publishing.",
                },
                "totals": {
                    "files_total": 1,
                    "languages_total": 1,
                    "errors_total": 0,
                    "warnings_total": 1,
                },
                "kpis": {
                    "Files": "1",
                    "Languages": "1",
                    "Errors": "0",
                    "Warnings": "1",
                    "DNT coverage": "full",
                    "Termbase coverage": "full",
                    "Parity": "100%",
                },
                "file_status": {
                    "test - FR.srt": {
                        "language": "fr",
                        "status": "review",
                        "issues": ["missing_translation"],
                    }
                },
                "lexicons": {
                    "dnt_terms": ["test"],
                    "termbase": {"fr": [{"source": "test", "target": "test"}]},
                },
                "sections": {
                    "errors": [],
                    "warnings": [
                        {
                            "file_path": "test - FR.srt",
                            "language": "fr",
                            "issue_type": "missing_translation",
                            "cue": 1,
                            "original": "hello",
                            "target": "",
                        }
                    ],
                },
            }

            report_v1_path = artifacts_dir / "report_v1.json"
            report_v1_path.write_text(json.dumps(report_v1_data, indent=2), encoding="utf-8")

            # Generate both presentations
            html_path = build_eval_html(report_v1_path)
            md_path = build_eval_md(report_v1_path)

            html_content = html_path.read_text(encoding="utf-8")
            md_content = md_path.read_text(encoding="utf-8")

            # Check decision one-liner parity
            assert "⚠️ Review recommended." in html_content
            assert "⚠️" in md_content  # MD shows just the emoji

            # Check that "Punch List" heading appears (has issues)
            assert "Punch List" in html_content
            assert "Punch List" in md_content

            # Check that punch list contains at least one entry
            assert "Unknown: Warning" in html_content
            assert "Unknown: Warning" in md_content

            # Check KPI labels and values
            expected_kpi_labels = ["Files:", "Languages:", "Errors:", "Warnings:"]
            for label in expected_kpi_labels:
                assert label in html_content
                assert label in md_content

    def test_fix_case_parity(self):
        """Test parity for FIX case (at least one error)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            artifacts_dir = Path(temp_dir) / "artifacts"
            artifacts_dir.mkdir()

            # Create realistic report_v1.json with FIX status
            report_v1_data = {
                "version": "1.0.0",
                "timestamp": "2025-01-01T00:00:00Z",
                "batch_label": "test-batch",
                "decision": {
                    "state": "FIX",
                    "banner_text": "Fix required. Address errors before publishing.",
                },
                "totals": {
                    "files_total": 1,
                    "languages_total": 1,
                    "errors_total": 1,
                    "warnings_total": 0,
                },
                "kpis": {
                    "Files": "1",
                    "Languages": "1",
                    "Errors": "1",
                    "Warnings": "0",
                    "DNT coverage": "full",
                    "Termbase coverage": "full",
                    "Parity": "100%",
                },
                "file_status": {
                    "test - FR.srt": {
                        "language": "fr",
                        "status": "fix",
                        "issues": ["untranslated_after_dnt"],
                    }
                },
                "lexicons": {
                    "dnt_terms": ["test"],
                    "termbase": {"fr": [{"source": "test", "target": "test"}]},
                },
                "sections": {
                    "errors": [
                        {
                            "file_path": "test - FR.srt",
                            "language": "fr",
                            "issue_type": "untranslated_after_dnt",
                            "cue": 1,
                            "original": "test",
                            "target": "test",
                        }
                    ],
                    "warnings": [],
                },
            }

            report_v1_path = artifacts_dir / "report_v1.json"
            report_v1_path.write_text(json.dumps(report_v1_data, indent=2), encoding="utf-8")

            # Generate both presentations
            html_path = build_eval_html(report_v1_path)
            md_path = build_eval_md(report_v1_path)

            html_content = html_path.read_text(encoding="utf-8")
            md_content = md_path.read_text(encoding="utf-8")

            # Check decision one-liner parity
            assert "⚠️ Review recommended." in html_content
            assert "⚠️" in md_content  # MD shows just the emoji

            # Check that "Punch List" heading appears (has issues)
            assert "Punch List" in html_content
            assert "Punch List" in md_content

            # Check that punch list contains at least one entry
            assert "Unknown: Error" in html_content
            assert "Unknown: Error" in md_content

    def test_empty_lexicons_parity(self):
        """Test parity when DNT and Termbase data is empty."""
        with tempfile.TemporaryDirectory() as temp_dir:
            artifacts_dir = Path(temp_dir) / "artifacts"
            artifacts_dir.mkdir()

            # Create realistic report_v1.json with empty lexicons
            report_v1_data = {
                "version": "1.0.0",
                "timestamp": "2025-01-01T00:00:00Z",
                "batch_label": "test-batch",
                "decision": {
                    "state": "READY",
                    "banner_text": "Everything looks great. Your translated files are ready to use.",
                },
                "totals": {
                    "files_total": 1,
                    "languages_total": 1,
                    "errors_total": 0,
                    "warnings_total": 0,
                },
                "kpis": {
                    "Files": "1",
                    "Languages": "1",
                    "Errors": "0",
                    "Warnings": "0",
                    "DNT coverage": "none",
                    "Termbase coverage": "none",
                    "Parity": "100%",
                },
                "file_status": {
                    "test - FR.srt": {"language": "fr", "status": "ready", "issues": []}
                },
                "lexicons": {"dnt_terms": [], "termbase": {}},
                "sections": {"errors": [], "warnings": []},
            }

            report_v1_path = artifacts_dir / "report_v1.json"
            report_v1_path.write_text(json.dumps(report_v1_data, indent=2), encoding="utf-8")

            # Generate both presentations
            html_path = build_eval_html(report_v1_path)
            md_path = build_eval_md(report_v1_path)

            html_content = html_path.read_text(encoding="utf-8")
            md_content = md_path.read_text(encoding="utf-8")

            # Check that both explicitly say "None" for empty data
            # Check that DNT and Termbase sections are present but empty
            # HTML doesn't show empty sections, MD does
            assert "DNT Terms" in md_content
            assert "Termbases" in md_content

            # Check DNT and Termbase headings still appear
            assert "DNT Terms" in html_content
            assert "DNT Terms" in md_content
            assert "Termbase" in html_content
            assert "Termbase" in md_content
