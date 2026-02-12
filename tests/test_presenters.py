"""Tests for the presenters with unified report.json schema."""

import json

import pytest

from srt_translator.presenters.eval_html.build import build_eval_html
from srt_translator.presenters.eval_md.build import build_eval_md


def _ok_report():
    return {
        "decision": "pass",
        "one_liner": "Everything looks great. Your translated files are ready to use.",
        "punch_list": {"errors": [], "warnings": []},
        "file_status": {"es": {"test1.srt": "ready", "test2.srt": "ready"}},
        "kpis": {
            "files_total": 2,
            "languages_total": 1,
            "issues_total": 0,
            "by_type": {
                "missing_translation": 0,
                "timing_fail": 0,
                "placeholder_mismatch": 0,
                "parity_issue": 0,
            },
        },
        "lexicons": {
            "dnt": {"count": 3, "sample": ["API", "JSON", "HTTP"]},
            "termbase": {
                "es": {
                    "count": 2,
                    "sample": [
                        {"source": "hello", "target": "hola"},
                        {"source": "world", "target": "mundo"},
                    ],
                }
            },
        },
    }


def _mixed_report():
    return {
        "decision": "fail",
        "one_liner": "We found 1 errors that must be fixed before publishing.",
        "punch_list": {
            "errors": [
                {
                    "language": "es",
                    "file": "test1.srt",
                    "cue_index": 1,
                    "type": "timing_fail",
                    "desc": "Timing drift too high",
                    "suggested_fix": "Check subtitle timing.",
                    "context": {
                        "source": {"prev2": "", "prev1": "", "cur": "API endpoint", "next1": "", "next2": ""},
                        "target": {"prev2": "", "prev1": "", "cur": "Punto final API", "next1": "", "next2": ""},
                    },
                }
            ],
            "warnings": [
                {
                    "language": "es",
                    "file": "test2.srt",
                    "cue_index": 2,
                    "type": "missing_translation",
                    "desc": "Some subtitles look blank.",
                    "suggested_fix": "Check if the translation was cut off.",
                    "context": {
                        "source": {"prev2": "", "prev1": "", "cur": "Hello world", "next1": "", "next2": ""},
                        "target": {"prev2": "", "prev1": "", "cur": "", "next1": "", "next2": ""},
                    },
                }
            ],
        },
        "file_status": {"es": {"test1.srt": "blocked", "test2.srt": "review"}},
        "kpis": {
            "files_total": 2,
            "languages_total": 1,
            "issues_total": 2,
            "by_type": {
                "missing_translation": 1,
                "timing_fail": 1,
                "placeholder_mismatch": 0,
                "parity_issue": 0,
            },
        },
        "lexicons": {
            "dnt": {"count": 2, "sample": ["API", "JSON"]},
            "termbase": {
                "es": {
                    "count": 1,
                    "sample": [{"source": "hello", "target": "hola"}],
                }
            },
        },
    }


class TestPresenters:
    """Test presenters with unified report.json schema."""

    def test_html_presenter_ok(self, tmp_path):
        report_path = tmp_path / "report.json"
        report_path.write_text(json.dumps(_ok_report()))

        html_path = build_eval_html(report_path)
        assert html_path.exists()
        html_content = html_path.read_text(encoding="utf-8")

        assert "Everything looks great" in html_content
        assert "No Issues Found" in html_content
        assert "Do-Not-Translate Terms" in html_content
        assert "Termbases" in html_content
        assert "File Status by Language" in html_content
        assert "KPI Summary" in html_content

    def test_html_presenter_mixed(self, tmp_path):
        report_path = tmp_path / "report.json"
        report_path.write_text(json.dumps(_mixed_report()))

        html_path = build_eval_html(report_path)
        assert html_path.exists()
        html_content = html_path.read_text(encoding="utf-8")

        assert "❌" in html_content
        assert "Critical Issues" in html_content
        assert "Warnings" in html_content
        assert "timing_fail" in html_content
        assert "missing_translation" in html_content

    def test_md_presenter_ok(self, tmp_path):
        report_path = tmp_path / "report.json"
        report_path.write_text(json.dumps(_ok_report()))

        md_path = build_eval_md(report_path)
        assert md_path.exists()
        md_content = md_path.read_text(encoding="utf-8")

        assert "# ✅ Everything looks great" in md_content
        assert "## ✅ No Issues Found" in md_content
        assert "## 📁 File Status by Language" in md_content
        assert "## 📊 KPI Summary" in md_content
        assert "## 📚 Lexicons" in md_content
        assert "Do-Not-Translate Terms" in md_content
        assert "Termbases" in md_content

    def test_md_presenter_mixed(self, tmp_path):
        report_path = tmp_path / "report.json"
        report_path.write_text(json.dumps(_mixed_report()))

        md_path = build_eval_md(report_path)
        assert md_path.exists()
        md_content = md_path.read_text(encoding="utf-8")

        assert "# ❌" in md_content
        assert "## ❌ Critical Issues" in md_content
        assert "## ⚠️ Warnings" in md_content
        assert "missing_translation" in md_content
        assert "timing_fail" in md_content

    def test_presenters_missing_required_keys(self, tmp_path):
        report_data = {"decision": "pass"}
        report_path = tmp_path / "report.json"
        report_path.write_text(json.dumps(report_data))

        with pytest.raises(ValueError, match="missing required keys"):
            build_eval_html(report_path)

        with pytest.raises(ValueError, match="missing required keys"):
            build_eval_md(report_path)
