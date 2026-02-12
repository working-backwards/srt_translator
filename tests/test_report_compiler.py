"""Tests for the report compiler."""

import json

import pytest

from srt_translator.report.compiler import compile_report


def _make_eval_report(*, per_language, issues_total=None):
    """Build an eval_report.json dict with correct version and totals."""
    files_total = sum(len(lang_data.get("files", {})) for lang_data in per_language.values())
    languages_total = len(per_language)
    if issues_total is None:
        issues_total = sum(
            sum(file_data.get("issues_counts", {}).values())
            for lang_data in per_language.values()
            for file_data in lang_data.get("files", {}).values()
        )
    return {
        "version": "1.0",
        "totals": {
            "files_total": files_total,
            "languages_total": languages_total,
            "issues_total": issues_total,
        },
        "per_language": per_language,
    }


def _make_ai_config(*, dnt_terms=None, termbase=None):
    """Build an ai_config.json dict."""
    return {
        "dnt_terms": dnt_terms or [],
        "termbase": termbase or {},
    }


def _write_fixtures(tmp_path, eval_report, ai_config):
    """Write eval_report.json and ai_config.json into tmp_path."""
    (tmp_path / "eval_report.json").write_text(json.dumps(eval_report), encoding="utf-8")
    (tmp_path / "ai_config.json").write_text(json.dumps(ai_config), encoding="utf-8")


def _compile_and_load(tmp_path):
    """Run compile_report and return the loaded JSON dict."""
    result_path = compile_report(tmp_path)
    return json.loads(result_path.read_text(encoding="utf-8")), result_path


# ---------------------------------------------------------------------------
# Fixtures shared by multiple tests
# ---------------------------------------------------------------------------

PASS_PER_LANGUAGE = {
    "es": {
        "files": {
            "test1.srt": {
                "issues_counts": {
                    "missing_translation": 0,
                    "timing_fail": 0,
                    "placeholder_mismatch": 0,
                    "parity_issue": 0,
                },
                "issues_detail": {
                    "missing_translation": [],
                    "timing_fail": [],
                    "placeholder_mismatch": [],
                    "parity_issue": [],
                },
            },
            "test2.srt": {
                "issues_counts": {
                    "missing_translation": 0,
                    "timing_fail": 0,
                    "placeholder_mismatch": 0,
                    "parity_issue": 0,
                },
                "issues_detail": {
                    "missing_translation": [],
                    "timing_fail": [],
                    "placeholder_mismatch": [],
                    "parity_issue": [],
                },
            },
        }
    }
}

REVIEW_PER_LANGUAGE = {
    "fr": {
        "files": {
            "intro - FR.srt": {
                "issues_counts": {
                    "missing_translation": 2,
                    "timing_fail": 0,
                    "placeholder_mismatch": 0,
                    "parity_issue": 0,
                },
                "issues_detail": {
                    "missing_translation": [
                        {
                            "cue_index": 5,
                            "source_text": "Hello world",
                            "target_text": "",
                            "context": {
                                "source": {"prev2": "", "prev1": "", "cur": "Hello world", "next1": "", "next2": ""},
                                "target": {"prev2": "", "prev1": "", "cur": "", "next1": "", "next2": ""},
                            },
                        },
                        {
                            "cue_index": 10,
                            "source_text": "Goodbye",
                            "target_text": "",
                            "context": {
                                "source": {"prev2": "", "prev1": "", "cur": "Goodbye", "next1": "", "next2": ""},
                                "target": {"prev2": "", "prev1": "", "cur": "", "next1": "", "next2": ""},
                            },
                        },
                    ],
                    "timing_fail": [],
                    "placeholder_mismatch": [],
                    "parity_issue": [],
                },
            },
        }
    }
}

FAIL_PER_LANGUAGE = {
    "ja": {
        "files": {
            "file1.srt": {
                "issues_counts": {
                    "missing_translation": 1,
                    "timing_fail": 1,
                    "placeholder_mismatch": 0,
                    "parity_issue": 0,
                },
                "issues_detail": {
                    "missing_translation": [
                        {
                            "cue_index": 3,
                            "source_text": "Test",
                            "target_text": "",
                            "context": {
                                "source": {"prev2": "", "prev1": "", "cur": "Test", "next1": "", "next2": ""},
                                "target": {"prev2": "", "prev1": "", "cur": "", "next1": "", "next2": ""},
                            },
                        }
                    ],
                    "timing_fail": [
                        {
                            "file_level": True,
                            "median_start_ms": 250,
                            "median_end_ms": 240,
                            "p95_start_ms": 550,
                            "p95_end_ms": 560,
                        }
                    ],
                    "placeholder_mismatch": [],
                    "parity_issue": [],
                },
            },
        }
    }
}


class TestCompileReport:
    """Test the report compiler."""

    def test_compile_report_pass(self, tmp_path):
        """No issues → decision 'pass', all files 'ready'."""
        eval_report = _make_eval_report(per_language=PASS_PER_LANGUAGE)
        ai_config = _make_ai_config(dnt_terms=["API"], termbase={"es": {"hello": "hola"}})
        _write_fixtures(tmp_path, eval_report, ai_config)

        data, path = _compile_and_load(tmp_path)

        assert path.name == "report.json"
        assert data["decision"] == "pass"
        assert "ready to use" in data["one_liner"].lower()
        assert data["file_status"]["es"]["test1.srt"] == "ready"
        assert data["file_status"]["es"]["test2.srt"] == "ready"
        assert data["punch_list"]["errors"] == []
        assert data["punch_list"]["warnings"] == []

    def test_compile_report_review(self, tmp_path):
        """Warnings only → decision 'review', files 'review'."""
        eval_report = _make_eval_report(per_language=REVIEW_PER_LANGUAGE)
        ai_config = _make_ai_config(dnt_terms=["API"])
        _write_fixtures(tmp_path, eval_report, ai_config)

        data, _ = _compile_and_load(tmp_path)

        assert data["decision"] == "review"
        assert "warnings" in data["one_liner"].lower()
        assert data["file_status"]["fr"]["intro - FR.srt"] == "review"
        assert len(data["punch_list"]["warnings"]) == 2
        assert len(data["punch_list"]["errors"]) == 0

    def test_compile_report_fail(self, tmp_path):
        """Errors present → decision 'fail', files 'blocked'."""
        eval_report = _make_eval_report(per_language=FAIL_PER_LANGUAGE)
        ai_config = _make_ai_config(dnt_terms=["API"])
        _write_fixtures(tmp_path, eval_report, ai_config)

        data, _ = _compile_and_load(tmp_path)

        assert data["decision"] == "fail"
        assert "errors" in data["one_liner"].lower()
        assert data["file_status"]["ja"]["file1.srt"] == "blocked"

    def test_compile_report_kpi_totals(self, tmp_path):
        """issues_total == sum(by_type) and per-type counts are correct."""
        eval_report = _make_eval_report(per_language=FAIL_PER_LANGUAGE)
        ai_config = _make_ai_config()
        _write_fixtures(tmp_path, eval_report, ai_config)

        data, _ = _compile_and_load(tmp_path)

        kpis = data["kpis"]
        by_type = kpis["by_type"]
        assert kpis["issues_total"] == sum(by_type.values())
        assert by_type["missing_translation"] == 1
        assert by_type["timing_fail"] == 1
        assert by_type["placeholder_mismatch"] == 0
        assert by_type["parity_issue"] == 0
        assert kpis["files_total"] == 1
        assert kpis["languages_total"] == 1

    def test_compile_report_punch_list_structure(self, tmp_path):
        """Punch list items have correct fields."""
        eval_report = _make_eval_report(per_language=FAIL_PER_LANGUAGE)
        ai_config = _make_ai_config()
        _write_fixtures(tmp_path, eval_report, ai_config)

        data, _ = _compile_and_load(tmp_path)

        required_fields = {"language", "file", "type", "desc", "suggested_fix", "context"}
        for item in data["punch_list"]["errors"]:
            assert required_fields <= set(item.keys())
        for item in data["punch_list"]["warnings"]:
            assert required_fields <= set(item.keys())

    def test_compile_report_lexicons(self, tmp_path):
        """DNT count/sample and termbase per-language count/sample."""
        eval_report = _make_eval_report(per_language=PASS_PER_LANGUAGE)
        ai_config = _make_ai_config(
            dnt_terms=["API", "JSON", "HTTP"],
            termbase={"es": {"hello": "hola", "world": "mundo"}},
        )
        _write_fixtures(tmp_path, eval_report, ai_config)

        data, _ = _compile_and_load(tmp_path)

        lexicons = data["lexicons"]
        assert lexicons["dnt"]["count"] == 3
        assert "API" in lexicons["dnt"]["sample"]
        assert "es" in lexicons["termbase"]
        assert lexicons["termbase"]["es"]["count"] == 2
        assert {"source": "hello", "target": "hola"} in lexicons["termbase"]["es"]["sample"]

    def test_compile_report_fail_fast_count_mismatch(self, tmp_path):
        """Count > 0 but empty details → ValueError."""
        per_language = {
            "es": {
                "files": {
                    "test.srt": {
                        "issues_counts": {
                            "missing_translation": 0,
                            "timing_fail": 1,
                            "placeholder_mismatch": 0,
                            "parity_issue": 0,
                        },
                        "issues_detail": {
                            "missing_translation": [],
                            "timing_fail": [],
                            "placeholder_mismatch": [],
                            "parity_issue": [],
                        },
                    }
                }
            }
        }
        eval_report = _make_eval_report(per_language=per_language, issues_total=1)
        ai_config = _make_ai_config()
        _write_fixtures(tmp_path, eval_report, ai_config)

        with pytest.raises(ValueError, match="Count mismatch"):
            compile_report(tmp_path)

    def test_compile_report_fail_fast_wrong_version(self, tmp_path):
        """Wrong version string → ValueError."""
        eval_report = {
            "version": "9.9.9",
            "totals": {"files_total": 0, "languages_total": 0, "issues_total": 0},
            "per_language": {},
        }
        ai_config = _make_ai_config()
        _write_fixtures(tmp_path, eval_report, ai_config)

        with pytest.raises(ValueError, match="Expected eval_report.json version 1.0"):
            compile_report(tmp_path)

    def test_compile_report_missing_required_keys(self, tmp_path):
        """eval_report.json missing totals/per_language → ValueError."""
        eval_report = {"version": "1.0"}
        ai_config = _make_ai_config()
        _write_fixtures(tmp_path, eval_report, ai_config)

        with pytest.raises(ValueError, match="missing required keys"):
            compile_report(tmp_path)

    def test_compile_report_missing_eval_file(self, tmp_path):
        """Missing eval_report.json → ValueError."""
        (tmp_path / "ai_config.json").write_text("{}")
        with pytest.raises(ValueError, match="eval_report.json not found"):
            compile_report(tmp_path)

    def test_compile_report_missing_ai_config(self, tmp_path):
        """Missing ai_config.json → ValueError."""
        (tmp_path / "eval_report.json").write_text("{}")
        with pytest.raises(ValueError, match="ai_config.json not found"):
            compile_report(tmp_path)

    def test_compile_report_invalid_json(self, tmp_path):
        """Malformed JSON → ValueError."""
        (tmp_path / "eval_report.json").write_text("{ invalid")
        (tmp_path / "ai_config.json").write_text("{}")
        with pytest.raises(ValueError, match="Invalid JSON"):
            compile_report(tmp_path)
