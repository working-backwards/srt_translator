"""Tests for presenter parity between HTML and Markdown."""

import json

from srt_translator.presenters.eval_html.build import build_eval_html
from srt_translator.presenters.eval_md.build import build_eval_md


class TestPresentersParity:
    """Test cases for presenter parity between HTML and Markdown."""

    def test_presenters_section_order(self, tmp_path):
        """Test that both presenters render sections in the same order."""
        # Create a test report_v1.json
        report_data = {
            "version": "1.0",
            "meta": {
                "batch_id": "test-batch",
                "created_at": "2024-01-01T00:00:00Z",
                "source_language": "en",
            },
            "decision": {
                "level": "review",
                "one_liner": "We found 2 warnings. Fix the items in the Punch List below.",
            },
            "totals": {
                "files_total": 2,
                "languages_total": 1,
                "issues_total": 2,
            },
            "kpis": {
                "errors_total": 0,
                "warnings_total": 2,
                "per_type": {
                    "missing_translation": 2,
                    "timing_fail": 0,
                },
            },
            "file_status": {
                "ja": {
                    "file1.srt": "review",
                    "file2.srt": "ready",
                }
            },
            "punch_list": {
                "errors": [],
                "warnings": [
                    {
                        "language": "ja",
                        "file": "file1.srt",
                        "cue_index": 5,
                        "type": "missing_translation",
                        "human_summary": "This subtitle may be incomplete.",
                        "suggested_fix": "Copy ±2 target lines, back-translate to verify completeness.",
                        "context": {
                            "source": {"cur": "Hello world", "next1": "How are you?"},
                            "target": {"cur": "こんにちは", "next1": "お元気ですか？"},
                        },
                    },
                    {
                        "language": "ja",
                        "file": "file1.srt",
                        "cue_index": 10,
                        "type": "missing_translation",
                        "human_summary": "This subtitle may be incomplete.",
                        "suggested_fix": "Copy ±2 target lines, back-translate to verify completeness.",
                        "context": {
                            "source": {"cur": "Good morning", "next1": "Have a nice day"},
                            "target": {"cur": "おはよう", "next1": "良い一日を"},
                        },
                    },
                ],
            },
            "lexicons": {
                "dnt": {
                    "count": 2,
                    "sample": ["API", "JSON"],
                },
                "termbases": {
                    "ja": {
                        "count": 2,
                        "sample": [
                            {"source": "hello", "target": "こんにちは"},
                            {"source": "world", "target": "世界"},
                        ],
                    }
                },
            },
        }

        # Write test file
        report_path = tmp_path / "report_v1.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f)

        # Generate both reports
        html_path = build_eval_html(report_path, tmp_path / "test.html")
        md_path = build_eval_md(report_path, tmp_path / "test.md")

        # Read both outputs
        html_content = html_path.read_text(encoding="utf-8")
        md_content = md_path.read_text(encoding="utf-8")

        # Test that both contain the same decision banner
        assert "⚠️ We found 2 warnings" in html_content
        assert "⚠️ We found 2 warnings" in md_content

        # Test that both contain punch list sections
        assert "❌ Critical Issues" in html_content
        assert "❌ Critical Issues" in md_content
        assert "⚠️ Warnings" in html_content
        assert "⚠️ Warnings" in md_content

        # Test that both contain file status sections
        assert "File Status by Language" in html_content
        assert "File Status by Language" in md_content

        # Test that both contain KPI sections
        assert "KPI Summary" in html_content
        assert "KPI Summary" in md_content

        # Test that both contain lexicons sections
        assert "Lexicons" in html_content
        assert "Lexicons" in md_content

    def test_presenters_banner_consistency(self, tmp_path):
        """Test that banner icon and text are consistent between presenters."""
        test_cases = [
            ("pass", "✅", "Everything looks great. Your translated files are ready to use."),
            ("review", "⚠️", "We found 1 warnings. Fix the items in the Punch List below."),
            ("fix", "❌", "We found 1 errors that must be fixed before publishing."),
        ]

        for decision_level, expected_icon, expected_text in test_cases:
            # Create test report
            report_data = {
                "version": "1.0",
                "meta": {
                    "batch_id": "test",
                    "created_at": "2024-01-01T00:00:00Z",
                    "source_language": "en",
                },
                "decision": {"level": decision_level, "one_liner": expected_text},
                "totals": {
                    "files_total": 1,
                    "languages_total": 1,
                    "issues_total": 0 if decision_level == "pass" else 1,
                },
                "kpis": {
                    "errors_total": 1 if decision_level == "fix" else 0,
                    "warnings_total": 1 if decision_level == "review" else 0,
                    "per_type": {},
                },
                "file_status": {"ja": {"file1.srt": "ready"}},
                "punch_list": {"errors": [], "warnings": []},
                "lexicons": {"dnt": {"count": 0, "sample": []}, "termbases": {}},
            }

            # Write test file
            report_path = tmp_path / f"report_{decision_level}.json"
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report_data, f)

            # Generate both reports
            html_path = build_eval_html(report_path, tmp_path / f"test_{decision_level}.html")
            md_path = build_eval_md(report_path, tmp_path / f"test_{decision_level}.md")

            # Read both outputs
            html_content = html_path.read_text(encoding="utf-8")
            md_content = md_path.read_text(encoding="utf-8")

            # Test icon consistency
            assert f"{expected_icon} {expected_text}" in html_content
            assert f"{expected_icon} {expected_text}" in md_content

    def test_presenters_no_issues_found_consistency(self, tmp_path):
        """Test that 'No Issues Found' appears only when totals are zero."""
        # Test case 1: No issues
        report_data_no_issues = {
            "version": "1.0",
            "meta": {
                "batch_id": "test",
                "created_at": "2024-01-01T00:00:00Z",
                "source_language": "en",
            },
            "decision": {
                "level": "pass",
                "one_liner": "Everything looks great. Your translated files are ready to use.",
            },
            "totals": {"files_total": 1, "languages_total": 1, "issues_total": 0},
            "kpis": {"errors_total": 0, "warnings_total": 0, "per_type": {}},
            "file_status": {"ja": {"file1.srt": "ready"}},
            "punch_list": {"errors": [], "warnings": []},
            "lexicons": {"dnt": {"count": 0, "sample": []}, "termbases": {}},
        }

        # Test case 2: With issues
        report_data_with_issues = {
            "version": "1.0",
            "meta": {
                "batch_id": "test",
                "created_at": "2024-01-01T00:00:00Z",
                "source_language": "en",
            },
            "decision": {
                "level": "review",
                "one_liner": "We found 1 warnings. Fix the items in the Punch List below.",
            },
            "totals": {"files_total": 1, "languages_total": 1, "issues_total": 1},
            "kpis": {
                "errors_total": 0,
                "warnings_total": 1,
                "per_type": {"missing_translation": 1},
            },
            "file_status": {"ja": {"file1.srt": "review"}},
            "punch_list": {
                "errors": [],
                "warnings": [
                    {
                        "language": "ja",
                        "file": "file1.srt",
                        "cue_index": 5,
                        "type": "missing_translation",
                        "human_summary": "This subtitle may be incomplete.",
                        "suggested_fix": "Copy ±2 target lines, back-translate to verify completeness.",
                        "context": {"source": {}, "target": {}},
                    }
                ],
            },
            "lexicons": {"dnt": {"count": 0, "sample": []}, "termbases": {}},
        }

        for test_name, report_data in [
            ("no_issues", report_data_no_issues),
            ("with_issues", report_data_with_issues),
        ]:
            # Write test file
            report_path = tmp_path / f"report_{test_name}.json"
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report_data, f)

            # Generate both reports
            html_path = build_eval_html(report_path, tmp_path / f"test_{test_name}.html")
            md_path = build_eval_md(report_path, tmp_path / f"test_{test_name}.md")

            # Read both outputs
            html_content = html_path.read_text(encoding="utf-8")
            md_content = md_path.read_text(encoding="utf-8")

            if test_name == "no_issues":
                # Should show "No Issues Found"
                assert "No Issues Found" in html_content
                assert "No Issues Found" in md_content
            else:
                # Should NOT show "No Issues Found"
                assert "No Issues Found" not in html_content
                assert "No Issues Found" not in md_content

    def test_presenters_punch_list_structure(self, tmp_path):
        """Test that punch list items have consistent structure between presenters."""
        # Create test report with punch list items
        report_data = {
            "version": "1.0",
            "meta": {
                "batch_id": "test",
                "created_at": "2024-01-01T00:00:00Z",
                "source_language": "en",
            },
            "decision": {
                "level": "fix",
                "one_liner": "We found 1 errors that must be fixed before publishing.",
            },
            "totals": {"files_total": 1, "languages_total": 1, "issues_total": 1},
            "kpis": {
                "errors_total": 1,
                "warnings_total": 0,
                "per_type": {"timing_fail": 1},
            },
            "file_status": {"ja": {"file1.srt": "error"}},
            "punch_list": {
                "errors": [
                    {
                        "language": "ja",
                        "file": "file1.srt",
                        "cue_index": 3,
                        "type": "timing_fail",
                        "human_summary": "This term should not be translated according to your DNT list.",
                        "suggested_fix": "Keep the original term untranslated or add it to your DNT list.",
                        "context": {
                            "source": {"cur": "API call", "next1": "Response received"},
                            "target": {"cur": "API呼び出し", "next1": "レスポンス受信"},
                        },
                    }
                ],
                "warnings": [],
            },
            "lexicons": {"dnt": {"count": 0, "sample": []}, "termbases": {}},
        }

        # Write test file
        report_path = tmp_path / "report_punch_list.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f)

        # Generate both reports
        html_path = build_eval_html(report_path, tmp_path / "test_punch_list.html")
        md_path = build_eval_md(report_path, tmp_path / "test_punch_list.md")

        # Read both outputs
        html_content = html_path.read_text(encoding="utf-8")
        md_content = md_path.read_text(encoding="utf-8")

        # Test that both contain the punch list item details
        assert "file1.srt" in html_content
        assert "file1.srt" in md_content
        # Test content presence (not specific markup)
        assert "ja" in html_content  # Language code should be present
        assert "ja" in md_content
        assert "3" in html_content  # Cue index should be present
        assert "3" in md_content
        assert "This term should not be translated" in html_content
        assert "This term should not be translated" in md_content
        assert "Keep the original term untranslated" in html_content
        assert "Keep the original term untranslated" in md_content

        # Test context rendering
        assert "Source context:" in html_content
        assert "Source context:" in md_content
        assert "Target context:" in html_content
        assert "Target context:" in md_content
