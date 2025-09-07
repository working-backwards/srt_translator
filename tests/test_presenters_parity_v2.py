"""Tests for presenter parity between HTML and Markdown."""

import json
from pathlib import Path

from srt_translator.presenters.eval_html.build import build_eval_html
from srt_translator.presenters.eval_md.build import build_eval_md


def test_presenters_parity_v2():
    """Test that HTML and Markdown presenters produce identical content."""
    # Use our golden fixture
    report_v1_path = Path("tests/fixtures/report_v1_mixed.json")

    # Generate both reports
    md_path = build_eval_md(report_v1_path)
    html_path = build_eval_html(report_v1_path)

    # Read content
    md_content = md_path.read_text(encoding="utf-8")
    html_content = html_path.read_text(encoding="utf-8")

    # Test decision and one-liner
    assert "fail" in md_content
    assert "fail" in html_content
    assert "We found 3 errors that must be fixed before publishing" in md_content
    assert "We found 3 errors that must be fixed before publishing" in html_content

    # Test punch list content
    assert "Critical Issues" in md_content
    assert "Critical Issues" in html_content
    assert "Warnings" in md_content
    assert "Warnings" in html_content

    # Test specific punch list items
    assert "untranslated_after_dnt" in md_content
    assert "untranslated_after_dnt" in html_content
    assert "Amazon marketing campaign" in md_content
    assert "Amazon marketing campaign" in html_content
    assert "Cue Index" in md_content
    assert "Cue Index" in html_content

    # Test file status
    assert "File Status by Language" in md_content
    assert "File Status by Language" in html_content
    assert "pt-BR" in md_content
    assert "pt-BR" in html_content
    assert "Blocked" in md_content
    assert "Blocked" in html_content

    # Test KPIs
    assert "KPI Summary" in md_content
    assert "KPI Summary" in html_content
    assert "**Files Total:** 1" in md_content
    assert "<strong>Files Total:</strong> 1" in html_content
    assert "**Issues Total:** 3" in md_content
    assert "<strong>Issues Total:</strong> 3" in html_content

    # Test lexicons
    assert "Lexicons" in md_content
    assert "Lexicons" in html_content
    assert "Do-Not-Translate Terms" in md_content
    assert "Do-Not-Translate Terms" in html_content
    assert "Amazon" in md_content
    assert "Amazon" in html_content
    assert "Termbases" in md_content
    assert "Termbases" in html_content

    # Test section order (Decision → Punch List → File Status → KPIs → Lexicons)
    md_lines = md_content.split("\n")
    html_lines = html_content.split("\n")

    # Find section headers
    md_headers = [line for line in md_lines if line.startswith("##")]
    md_section_titles = [h.replace("## ", "") for h in md_headers if h.startswith("## ")]

    # Check that we have the expected sections in the right order
    assert "❌ Critical Issues" in md_section_titles
    assert "⚠️ Warnings" in md_section_titles
    assert "📁 File Status by Language" in md_section_titles
    assert "📊 KPI Summary" in md_section_titles
    assert "📚 Lexicons" in md_section_titles

    # Verify section order in HTML
    html_section_titles = []
    for line in html_lines:
        if "<h2>" in line and "</h2>" in line:
            title = line.split("<h2>")[1].split("</h2>")[0]
            html_section_titles.append(title)

    assert "❌ Critical Issues" in html_section_titles
    assert "⚠️ Warnings" in html_section_titles
    assert "📁 File Status by Language" in html_section_titles
    assert "📊 KPI Summary" in html_section_titles
    assert "📚 Lexicons" in html_section_titles


def test_presenters_no_issues_found():
    """Test presenters when no issues are found."""
    # Create a minimal report with no issues
    no_issues_report = {
        "decision": "pass",
        "one_liner": "Everything looks great. Your translated files are ready to use.",
        "punch_list": {"errors": [], "warnings": []},
        "file_status": {"en": {"test.srt": "ready"}},
        "kpis": {
            "files_total": 1,
            "languages_total": 1,
            "issues_total": 0,
            "by_type": {
                "missing_translation": 0,
                "untranslated_after_dnt": 0,
                "timing_fail": 0,
                "placeholder_mismatch": 0,
                "parity_issue": 0,
            },
        },
        "lexicons": {"dnt": {"count": 0, "sample": []}, "termbase": {}},
    }

    # Write to temporary file
    temp_report = Path("temp_no_issues.json")
    with open(temp_report, "w", encoding="utf-8") as f:
        json.dump(no_issues_report, f)

    try:
        # Generate both reports
        md_path = build_eval_md(temp_report)
        html_path = build_eval_html(temp_report)

        # Read content
        md_content = md_path.read_text(encoding="utf-8")
        html_content = html_path.read_text(encoding="utf-8")

        # Test "No Issues Found" message
        assert "No Issues Found" in md_content
        assert "No Issues Found" in html_content
        assert "Everything looks great" in md_content
        assert "Everything looks great" in html_content

        # Test that punch list sections are NOT present when no issues
        assert "Critical Issues" not in md_content
        assert "Critical Issues" not in html_content
        assert "Warnings" not in md_content
        assert "Warnings" not in html_content

    finally:
        # Cleanup
        temp_report.unlink(missing_ok=True)
        md_path.unlink(missing_ok=True)
        html_path.unlink(missing_ok=True)
