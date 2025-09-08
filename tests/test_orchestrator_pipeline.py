"""Tests for orchestrator pipeline and no-double-build functionality."""

import json
from unittest.mock import patch

import pytest

from srt_translator.eval.report import emit_all_reports


class TestOrchestratorPipeline:
    """Test cases for orchestrator pipeline functionality."""

    def test_emit_all_reports_returns_all_paths(self, tmp_path):
        """Test that emit_all_reports returns all 4 required paths."""
        # Create mock rollup data
        rollup = {
            "issues_total": 0,
            "source_language": "en",
            "languages": {
                "ja": {
                    "files": [
                        {
                            "target_rel": "file1.srt",
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
                        }
                    ]
                }
            },
        }

        # Create ai_config.json
        ai_config_data = {
            "dnt_terms": ["API"],
            "termbase": {
                "ja": {
                    "hello": "こんにちは",
                }
            },
        }

        # Write ai_config.json in artifacts_dir (not parent)
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()
        ai_config_path = artifacts_dir / "ai_config.json"
        with open(ai_config_path, "w", encoding="utf-8") as f:
            json.dump(ai_config_data, f)

        # Run emit_all_reports
        paths = emit_all_reports(artifacts_dir, rollup)

        # Verify all 4 paths are returned
        expected_keys = {"eval_report_json", "report_v1_json", "eval_report_md", "eval_report_html"}
        assert set(paths.keys()) == expected_keys

        # Verify all paths exist
        for name, path in paths.items():
            assert path.exists(), f"{name} file not found at {path}"

    def test_emit_all_reports_single_html_generation(self, tmp_path):
        """Test that HTML is generated only once (no double-build)."""
        # Create mock rollup data
        rollup = {
            "issues_total": 0,
            "source_language": "en",
            "languages": {
                "ja": {
                    "files": [
                        {
                            "target_rel": "file1.srt",
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
                        }
                    ]
                }
            },
        }

        # Create ai_config.json
        ai_config_data = {
            "dnt_terms": [],
            "termbase": {},
        }

        # Write ai_config.json in artifacts_dir (not parent)
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()
        ai_config_path = artifacts_dir / "ai_config.json"
        with open(ai_config_path, "w", encoding="utf-8") as f:
            json.dump(ai_config_data, f)

        # Mock the HTML builder to track calls
        with patch("srt_translator.presenters.eval_html.build.build_eval_html") as mock_html:
            with patch("srt_translator.presenters.eval_md.build.build_eval_md") as mock_md:
                # Run emit_all_reports
                paths = emit_all_reports(artifacts_dir, rollup)

                # Verify HTML builder was called exactly once
                assert mock_html.call_count == 1
                assert mock_md.call_count == 1

                # Verify the call was made with correct arguments
                html_call_args = mock_html.call_args
                assert html_call_args[0][0] == paths["report_v1_json"]  # report_v1_path
                assert html_call_args[0][1] == artifacts_dir / "eval_report.html"  # out_path

    def test_emit_all_reports_logs_single_generation(self, tmp_path, caplog):
        """Test that logs show single HTML generation event."""
        # Create mock rollup data
        rollup = {
            "issues_total": 0,
            "source_language": "en",
            "languages": {
                "ja": {
                    "files": [
                        {
                            "target_rel": "file1.srt",
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
                        }
                    ]
                }
            },
        }

        # Create ai_config.json
        ai_config_data = {
            "dnt_terms": [],
            "termbase": {},
        }

        # Write ai_config.json in artifacts_dir (not parent)
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()
        ai_config_path = artifacts_dir / "ai_config.json"
        with open(ai_config_path, "w", encoding="utf-8") as f:
            json.dump(ai_config_data, f)

        # Run emit_all_reports
        with caplog.at_level("INFO"):
            paths = emit_all_reports(artifacts_dir, rollup)

        # Verify paths were returned
        assert len(paths) == 4

        # Check that HTML generation is logged only once
        html_logs = [
            record.message for record in caplog.records if "eval_report.html" in record.message
        ]
        assert len(html_logs) == 1, (
            f"Expected 1 HTML generation log, got {len(html_logs)}: {html_logs}"
        )

        # Check that MD generation is logged only once
        md_logs = [
            record.message for record in caplog.records if "eval_report.md" in record.message
        ]
        assert len(md_logs) == 1, f"Expected 1 MD generation log, got {len(md_logs)}: {md_logs}"

    def test_emit_all_reports_fails_fast_on_missing_ai_config(self, tmp_path):
        """Test that emit_all_reports fails fast when ai_config.json is missing."""
        # Create mock rollup data
        rollup = {
            "issues_total": 0,
            "source_language": "en",
            "languages": {
                "ja": {
                    "files": [
                        {
                            "target_rel": "file1.srt",
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
                        }
                    ]
                }
            },
        }

        # Don't create ai_config.json

        # Run emit_all_reports - should raise ValueError
        with pytest.raises(ValueError, match="ai_config.json not found"):
            emit_all_reports(tmp_path, rollup)

    def test_emit_all_reports_compiles_report_v1_correctly(self, tmp_path):
        """Test that report_v1.json is compiled correctly by the orchestrator."""
        # Create mock rollup data with issues
        rollup = {
            "issues_total": 2,
            "source_language": "en",
            "languages": {
                "ja": {
                    "files": [
                        {
                            "target_rel": "file1.srt",
                            "issues_counts": {
                                "missing_translation": 1,  # warning
                                "timing_fail": 0,
                                "placeholder_mismatch": 0,
                                "parity_issue": 0,
                            },
                            "issues_detail": {
                                "missing_translation": [
                                    {
                                        "cue_index": 1,
                                        "source_text": "test",
                                        "target_text": "",
                                        "context": {"source": {}, "target": {}},
                                    }
                                ],
                                "timing_fail": [],
                                "placeholder_mismatch": [],
                                "parity_issue": [],
                            },
                        },
                        {
                            "target_rel": "file2.srt",
                            "issues_counts": {
                                "missing_translation": 0,
                                "timing_fail": 1,  # error
                                "placeholder_mismatch": 0,
                                "parity_issue": 0,
                            },
                            "issues_detail": {
                                "missing_translation": [],
                                "timing_fail": [
                                    {
                                        "cue_index": 1,
                                        "source_text": "API",
                                        "target_text": "API",
                                        "context": {"source": {}, "target": {}},
                                    }
                                ],
                                "placeholder_mismatch": [],
                                "parity_issue": [],
                            },
                        },
                    ]
                }
            },
        }

        # Create ai_config.json
        ai_config_data = {
            "dnt_terms": ["API", "JSON"],
            "termbase": {
                "ja": {
                    "hello": "こんにちは",
                    "world": "世界",
                }
            },
        }

        # Write ai_config.json in artifacts_dir (not parent)
        artifacts_dir = tmp_path / "artifacts"
        artifacts_dir.mkdir()
        ai_config_path = artifacts_dir / "ai_config.json"
        with open(ai_config_path, "w", encoding="utf-8") as f:
            json.dump(ai_config_data, f)

        # Run emit_all_reports
        paths = emit_all_reports(artifacts_dir, rollup)

        # Load and verify report_v1.json
        with open(paths["report_v1_json"], "r", encoding="utf-8") as f:
            report_v1 = json.load(f)

        # Test structure (according to rulebook)
        assert "decision" in report_v1
        assert "one_liner" in report_v1
        assert "kpis" in report_v1
        assert "file_status" in report_v1
        assert "punch_list" in report_v1
        assert "lexicons" in report_v1

        # Test decision
        assert report_v1["decision"] == "fail"
        assert "errors that must be fixed" in report_v1["one_liner"]

        # Test KPIs
        assert report_v1["kpis"]["files_total"] == 2
        assert report_v1["kpis"]["languages_total"] == 1
        assert report_v1["kpis"]["issues_total"] == 2
        assert report_v1["kpis"]["by_type"]["missing_translation"] == 1
        assert report_v1["kpis"]["by_type"]["timing_fail"] == 1

        # Test file status
        assert "ja" in report_v1["file_status"]
        assert report_v1["file_status"]["ja"]["file1.srt"] == "review"
        assert report_v1["file_status"]["ja"]["file2.srt"] == "blocked"

        # Test punch_list
        assert len(report_v1["punch_list"]["errors"]) == 1
        assert len(report_v1["punch_list"]["warnings"]) == 1

        # Test lexicons
        assert report_v1["lexicons"]["dnt"]["count"] == 2
        assert "ja" in report_v1["lexicons"]["termbase"]
        assert report_v1["lexicons"]["termbase"]["ja"]["count"] == 2
