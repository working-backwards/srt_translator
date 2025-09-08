"""Tests for v2 report compiler."""

import json
from pathlib import Path

import pytest

from srt_translator.report.compiler import compile_report


def test_compiler_v2_happy_path():
    """Test compiler with valid v2 eval_report.json."""
    # Create test artifacts directory
    artifacts_dir = Path("test_artifacts_compiler")
    artifacts_dir.mkdir(exist_ok=True)

    # Copy our v2 fixture
    import shutil

    shutil.copy(
        "tests/fixtures/eval_report_v2_with_details.json", artifacts_dir / "eval_report.json"
    )

    # Create minimal ai_config.json
    ai_config = {
        "dnt_terms": ["Amazon", "Google", "Microsoft"],
        "termbase": {"pt-BR": {"marketing": "marketing", "campaign": "campanha"}},
    }
    with open(artifacts_dir / "ai_config.json", "w") as f:
        json.dump(ai_config, f)

    try:
        # Test the compiler
        result_path = compile_report(artifacts_dir)

        # Verify output exists
        assert result_path.exists()

        # Load and validate result
        with open(result_path, "r") as f:
            result = json.load(f)

        # Check required keys
        required_keys = {"decision", "one_liner", "punch_list", "file_status", "kpis", "lexicons"}
        assert set(result.keys()) == required_keys

        # Check decision
        assert result["decision"] == "fail"
        assert "2 errors" in result["one_liner"]

        # Check punch list structure
        punch_list = result["punch_list"]
        assert "errors" in punch_list
        assert "warnings" in punch_list
        assert len(punch_list["errors"]) == 1  # timing_fail
        assert len(punch_list["warnings"]) == 1  # missing_translation

        # Check that punch list items have real data (not synthetic)
        for error in punch_list["errors"]:
            assert "language" in error
            assert "file" in error
            assert "type" in error
            assert "desc" in error
            assert "suggested_fix" in error
            assert "context" in error

            # Verify context has real data for timing_fail
            if error["type"] == "timing_fail":
                assert error["cue_index"] == 168
                assert "Amazon marketing campaign" in error["context"]["source"]["cur"]
                assert "Amazon marketing campaign" in error["context"]["target"]["cur"]

        # Check file status
        file_status = result["file_status"]
        assert "pt-BR" in file_status
        assert "targets/pt-BR/InputMetrics10 - EN.srt" in file_status["pt-BR"]
        assert file_status["pt-BR"]["targets/pt-BR/InputMetrics10 - EN.srt"] == "blocked"

        # Check KPIs
        kpis = result["kpis"]
        assert kpis["files_total"] == 1
        assert kpis["languages_total"] == 1
        assert kpis["issues_total"] == 3

        by_type = kpis["by_type"]
        assert by_type["missing_translation"] == 1
        assert by_type["timing_fail"] == 1
        assert by_type["placeholder_mismatch"] == 0
        assert by_type["parity_issue"] == 0

        # Check lexicons
        lexicons = result["lexicons"]
        assert "dnt" in lexicons
        assert "termbase" in lexicons

        dnt = lexicons["dnt"]
        assert dnt["count"] == 3
        assert "Amazon" in dnt["sample"]

        termbase = lexicons["termbase"]
        assert "pt-BR" in termbase
        assert termbase["pt-BR"]["count"] == 2
        assert {"source": "marketing", "target": "marketing"} in termbase["pt-BR"]["sample"]

    finally:
        # Cleanup
        import shutil

        shutil.rmtree(artifacts_dir, ignore_errors=True)


def test_compiler_v2_fail_fast_on_missing_details():
    """Test compiler fails fast when counts > 0 but details empty."""
    # Create test artifacts directory
    artifacts_dir = Path("test_artifacts_compiler_fail")
    artifacts_dir.mkdir(exist_ok=True)

    # Create invalid eval_report.json (count > 0 but empty details)
    invalid_eval_report = {
        "version": "2.0.0",
        "totals": {"files_total": 1, "languages_total": 1, "issues_total": 1},
        "per_language": {
            "pt-BR": {
                "files": {
                    "test.srt": {
                        "issues_counts": {
                            "timing_fail": 1,
                            "missing_translation": 0,
                            "placeholder_mismatch": 0,
                            "parity_issue": 0,
                        },
                        "issues_detail": {
                            "timing_fail": [],  # Empty details!
                            "missing_translation": [],
                            "placeholder_mismatch": [],
                            "parity_issue": [],
                        },
                    }
                }
            }
        },
        "lexicons": {"dnt": {"count": 0, "sample": []}, "termbase": {}},
    }

    with open(artifacts_dir / "eval_report.json", "w") as f:
        json.dump(invalid_eval_report, f)

    # Create minimal ai_config.json
    ai_config = {"dnt_terms": [], "termbase": {}}
    with open(artifacts_dir / "ai_config.json", "w") as f:
        json.dump(ai_config, f)

    try:
        # Test that compiler fails fast
        with pytest.raises(ValueError, match="Count mismatch.*timing_fail.*count=1.*details empty"):
            compile_report(artifacts_dir)

    finally:
        # Cleanup
        import shutil

        shutil.rmtree(artifacts_dir, ignore_errors=True)


def test_compiler_v2_fail_fast_on_wrong_version():
    """Test compiler fails fast on wrong version."""
    # Create test artifacts directory
    artifacts_dir = Path("test_artifacts_compiler_version")
    artifacts_dir.mkdir(exist_ok=True)

    # Create eval_report.json with wrong version
    invalid_eval_report = {
        "version": "1.0.0",  # Wrong version!
        "files_total": 0,
        "languages_total": 0,
        "issues_total": 0,
        "per_language": {},
        "lexicons": {"dnt": {"count": 0, "sample": []}, "termbase": {}},
    }

    with open(artifacts_dir / "eval_report.json", "w") as f:
        json.dump(invalid_eval_report, f)

    # Create minimal ai_config.json
    ai_config = {"dnt_terms": [], "termbase": {}}
    with open(artifacts_dir / "ai_config.json", "w") as f:
        json.dump(ai_config, f)

    try:
        # Test that compiler fails fast
        with pytest.raises(ValueError, match="Expected eval_report.json version 2.0.0, got: 1.0.0"):
            compile_report(artifacts_dir)

    finally:
        # Cleanup
        import shutil

        shutil.rmtree(artifacts_dir, ignore_errors=True)
