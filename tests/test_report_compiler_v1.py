"""Tests for the report compiler v1 invariants and functionality."""

import json

from srt_translator.report import compile_report


class TestReportCompilerV1:
    """Test cases for the report compiler v1 functionality."""

    def test_compiler_invariants_clean_batch(self, tmp_path):
        """Test compiler invariants with a clean batch (no issues)."""
        # Create eval_report.json with no issues
        eval_data = {
            "files_total": 2,
            "languages_total": 1,
            "issues_total": 0,
            "source_language": "en",
            "languages": {
                "ja": {
                    "files": {
                        "file1.srt": {
                            "missing_translation": 0,
                            "timing_fail": 0,
                        },
                        "file2.srt": {
                            "missing_translation": 0,
                            "timing_fail": 0,
                        },
                    }
                }
            },
        }

        # Create ai_config.json
        ai_data = {
            "dnt_terms": ["API", "JSON"],
            "termbase": {
                "ja": {
                    "hello": "こんにちは",
                    "world": "世界",
                }
            },
        }

        # Write test files
        eval_path = tmp_path / "eval_report.json"
        ai_path = tmp_path / "ai_config.json"

        with open(eval_path, "w", encoding="utf-8") as f:
            json.dump(eval_data, f)

        with open(ai_path, "w", encoding="utf-8") as f:
            json.dump(ai_data, f)

        # Run compiler
        result_path = compile_report(tmp_path)

        # Load and verify result
        with open(result_path, "r", encoding="utf-8") as f:
            result = json.load(f)

        # Test invariants
        assert (
            result["totals"]["issues_total"]
            == result["kpis"]["errors_total"] + result["kpis"]["warnings_total"]
        )
        assert result["kpis"]["errors_total"] == 0
        assert result["kpis"]["warnings_total"] == 0
        assert len(result["punch_list"]["errors"]) == 0
        assert len(result["punch_list"]["warnings"]) == 0
        assert result["decision"]["level"] == "pass"
        assert "ready to use" in result["decision"]["one_liner"]

        # Test file_status structure
        assert "ja" in result["file_status"]
        assert "file1.srt" in result["file_status"]["ja"]
        assert "file2.srt" in result["file_status"]["ja"]
        assert result["file_status"]["ja"]["file1.srt"] == "ready"
        assert result["file_status"]["ja"]["file2.srt"] == "ready"

        # Test no "unknown" keys
        assert "unknown" not in result["file_status"]
        for lang_files in result["file_status"].values():
            for status in lang_files.values():
                assert status != "unknown"

    def test_compiler_invariants_with_issues(self, tmp_path):
        """Test compiler invariants with issues (errors and warnings)."""
        # Create eval_report.json with issues
        eval_data = {
            "files_total": 2,
            "languages_total": 1,
            "issues_total": 3,  # 1 error + 2 warnings
            "source_language": "en",
            "languages": {
                "ja": {
                    "files": {
                        "file1.srt": {
                            "missing_translation": 2,  # warnings
                            "timing_fail": 0,
                        },
                        "file2.srt": {
                            "missing_translation": 0,
                            "timing_fail": 1,  # error
                        },
                    }
                }
            },
        }

        # Create ai_config.json
        ai_data = {
            "dnt_terms": ["API"],
            "termbase": {
                "ja": {
                    "hello": "こんにちは",
                }
            },
        }

        # Write test files
        eval_path = tmp_path / "eval_report.json"
        ai_path = tmp_path / "ai_config.json"

        with open(eval_path, "w", encoding="utf-8") as f:
            json.dump(eval_data, f)

        with open(ai_path, "w", encoding="utf-8") as f:
            json.dump(ai_data, f)

        # Run compiler
        result_path = compile_report(tmp_path)

        # Load and verify result
        with open(result_path, "r", encoding="utf-8") as f:
            result = json.load(f)

        # Test invariants
        assert (
            result["totals"]["issues_total"]
            == result["kpis"]["errors_total"] + result["kpis"]["warnings_total"]
        )
        assert result["kpis"]["errors_total"] == 1
        assert result["kpis"]["warnings_total"] == 2
        assert len(result["punch_list"]["errors"]) == 1
        assert len(result["punch_list"]["warnings"]) == 2
        assert result["decision"]["level"] == "fix"
        assert "errors that must be fixed" in result["decision"]["one_liner"]

        # Test file_status structure
        assert "ja" in result["file_status"]
        assert result["file_status"]["ja"]["file1.srt"] == "review"  # warnings only
        assert result["file_status"]["ja"]["file2.srt"] == "error"  # has error

        # Test punch list items have correct structure
        error = result["punch_list"]["errors"][0]
        assert "language" in error
        assert "file" in error
        assert "cue_index" in error
        assert "type" in error
        assert "human_summary" in error
        assert "suggested_fix" in error
        assert "context" in error
        assert error["type"] == "timing_fail"

        warning = result["punch_list"]["warnings"][0]
        assert warning["type"] == "missing_translation"

    def test_compiler_lexicons_structure(self, tmp_path):
        """Test that lexicons are structured correctly."""
        # Create eval_report.json
        eval_data = {
            "files_total": 1,
            "languages_total": 1,
            "issues_total": 0,
            "source_language": "en",
            "languages": {
                "ja": {
                    "files": {
                        "file1.srt": {
                            "missing_translation": 0,
                            "timing_fail": 0,
                        },
                    }
                }
            },
        }

        # Create ai_config.json with DNT and termbase
        ai_data = {
            "dnt_terms": ["API", "JSON", "HTTP", "REST", "XML", "YAML"],  # 6 terms
            "termbase": {
                "ja": {
                    "hello": "こんにちは",
                    "world": "世界",
                    "test": "テスト",
                },
                "es": {
                    "hello": "hola",
                    "world": "mundo",
                },
            },
        }

        # Write test files
        eval_path = tmp_path / "eval_report.json"
        ai_path = tmp_path / "ai_config.json"

        with open(eval_path, "w", encoding="utf-8") as f:
            json.dump(eval_data, f)

        with open(ai_path, "w", encoding="utf-8") as f:
            json.dump(ai_data, f)

        # Run compiler
        result_path = compile_report(tmp_path)

        # Load and verify result
        with open(result_path, "r", encoding="utf-8") as f:
            result = json.load(f)

        # Test lexicons structure
        lexicons = result["lexicons"]
        assert "dnt" in lexicons
        assert "termbases" in lexicons

        # Test DNT structure
        dnt = lexicons["dnt"]
        assert dnt["count"] == 6
        assert len(dnt["sample"]) == 5  # Should be limited to 5 samples
        assert "API" in dnt["sample"]

        # Test termbases structure
        termbases = lexicons["termbases"]
        assert "ja" in termbases
        assert "es" in termbases

        ja_tb = termbases["ja"]
        assert ja_tb["count"] == 3
        assert len(ja_tb["sample"]) == 3  # All 3 entries since <= 5

        es_tb = termbases["es"]
        assert es_tb["count"] == 2
        assert len(es_tb["sample"]) == 2  # All 2 entries since <= 5

        # Test sample entries have correct structure
        for entry in ja_tb["sample"]:
            assert "source" in entry
            assert "target" in entry
