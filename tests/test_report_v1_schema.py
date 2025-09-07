"""Tests for report_v1.json schema validation."""

import json
import tempfile
from pathlib import Path

from srt_translator.report.compiler import compile_report


class TestReportV1Schema:
    """Test that report_v1.json conforms to expected schema."""

    def test_report_v1_required_keys(self):
        """Test that report_v1.json contains all required keys."""
        with tempfile.TemporaryDirectory() as tmpdir:
            artifacts_dir = Path(tmpdir)

            # Create test data
            eval_data = {
                "files_total": 1,
                "languages_total": 1,
                "issues_total": 0,
                "source_language": "en",
                "languages": {
                    "fr": {
                        "files": {
                            "test - FR.srt": {
                                "missing_translation": 0,
                                "untranslated_after_dnt": 0,
                                "timing_fail": 0,
                            }
                        }
                    }
                },
            }

            ai_data = {
                "version": "1.0.0",
                "timestamp": "2025-01-01T00:00:00Z",
                "target_languages": ["fr"],
                "dnt_terms": ["test"],
                "termbase": {"fr": {"test": "test"}},
            }

            (artifacts_dir / "eval_report.json").write_text(json.dumps(eval_data))
            (artifacts_dir / "ai_config.json").write_text(json.dumps(ai_data))

            # Compile report
            result_path = compile_report(artifacts_dir)
            report_data = json.loads(result_path.read_text(encoding="utf-8"))

            # Check required top-level keys
            required_keys = {
                "version",
                "meta",
                "decision",
                "kpis",
                "file_status",
                "lexicons",
                "sections",
            }
            assert set(report_data.keys()) == required_keys

    def test_decision_schema(self):
        """Test that decision object has correct schema."""
        with tempfile.TemporaryDirectory() as tmpdir:
            artifacts_dir = Path(tmpdir)

            eval_data = {
                "files_total": 1,
                "languages_total": 1,
                "issues_total": 0,
                "source_language": "en",
                "languages": {
                    "fr": {
                        "files": {
                            "test - FR.srt": {
                                "missing_translation": 0,
                                "untranslated_after_dnt": 0,
                                "timing_fail": 0,
                            }
                        }
                    }
                },
            }

            ai_data = {
                "version": "1.0.0",
                "timestamp": "2025-01-01T00:00:00Z",
                "target_languages": ["fr"],
                "dnt_terms": ["test"],
                "termbase": {"fr": {"test": "test"}},
            }

            (artifacts_dir / "eval_report.json").write_text(json.dumps(eval_data))
            (artifacts_dir / "ai_config.json").write_text(json.dumps(ai_data))

            result_path = compile_report(artifacts_dir)
            report_data = json.loads(result_path.read_text(encoding="utf-8"))

            decision = report_data["decision"]

            # Check required keys
            assert "level" in decision
            assert "one_liner" in decision

            # Check level is one of expected values
            assert decision["level"] in ["ready", "review", "fix"]

            # Check types
            assert isinstance(decision["level"], str)
            assert isinstance(decision["one_liner"], str)

    def test_totals_schema(self):
        """Test that totals object has correct schema."""
        with tempfile.TemporaryDirectory() as tmpdir:
            artifacts_dir = Path(tmpdir)

            eval_data = {
                "files_total": 1,
                "languages_total": 1,
                "issues_total": 0,
                "source_language": "en",
                "languages": {
                    "fr": {
                        "files": {
                            "test - FR.srt": {
                                "missing_translation": 0,
                                "untranslated_after_dnt": 0,
                                "timing_fail": 0,
                            }
                        }
                    }
                },
            }

            ai_data = {
                "version": "1.0.0",
                "timestamp": "2025-01-01T00:00:00Z",
                "target_languages": ["fr"],
                "dnt_terms": ["test"],
                "termbase": {"fr": {"test": "test"}},
            }

            (artifacts_dir / "eval_report.json").write_text(json.dumps(eval_data))
            (artifacts_dir / "ai_config.json").write_text(json.dumps(ai_data))

            result_path = compile_report(artifacts_dir)
            report_data = json.loads(result_path.read_text(encoding="utf-8"))

            totals = report_data["totals"]

            # Check required keys
            required_keys = {
                "files_total",
                "languages_total",
                "errors_total",
                "warnings_total",
            }
            assert set(totals.keys()) == required_keys

            # Check types
            for key in required_keys:
                assert isinstance(totals[key], int)
                assert totals[key] >= 0

    def test_kpis_schema(self):
        """Test that kpis object has correct schema."""
        with tempfile.TemporaryDirectory() as tmpdir:
            artifacts_dir = Path(tmpdir)

            eval_data = {
                "files_total": 1,
                "languages_total": 1,
                "issues_total": 0,
                "source_language": "en",
                "languages": {
                    "fr": {
                        "files": {
                            "test - FR.srt": {
                                "missing_translation": 0,
                                "untranslated_after_dnt": 0,
                                "timing_fail": 0,
                            }
                        }
                    }
                },
            }

            ai_data = {
                "version": "1.0.0",
                "timestamp": "2025-01-01T00:00:00Z",
                "target_languages": ["fr"],
                "dnt_terms": ["test"],
                "termbase": {"fr": {"test": "test"}},
            }

            (artifacts_dir / "eval_report.json").write_text(json.dumps(eval_data))
            (artifacts_dir / "ai_config.json").write_text(json.dumps(ai_data))

            result_path = compile_report(artifacts_dir)
            report_data = json.loads(result_path.read_text(encoding="utf-8"))

            kpis = report_data["kpis"]

            # Check required keys
            required_keys = {
                "Files",
                "Languages",
                "Errors",
                "Warnings",
                "DNT coverage",
                "Termbase coverage",
                "Parity",
            }
            assert set(kpis.keys()) == required_keys

            # Check types
            for _key, value in kpis.items():
                assert isinstance(value, str)
                assert value.strip() != ""

    def test_file_status_schema(self):
        """Test that file_status array has correct schema."""
        with tempfile.TemporaryDirectory() as tmpdir:
            artifacts_dir = Path(tmpdir)

            eval_data = {
                "files_total": 1,
                "languages_total": 1,
                "issues_total": 0,
                "source_language": "en",
                "languages": {
                    "fr": {
                        "files": {
                            "test - FR.srt": {
                                "missing_translation": 0,
                                "untranslated_after_dnt": 0,
                                "timing_fail": 0,
                            }
                        }
                    }
                },
            }

            ai_data = {
                "version": "1.0.0",
                "timestamp": "2025-01-01T00:00:00Z",
                "target_languages": ["fr"],
                "dnt_terms": ["test"],
                "termbase": {"fr": {"test": "test"}},
            }

            (artifacts_dir / "eval_report.json").write_text(json.dumps(eval_data))
            (artifacts_dir / "ai_config.json").write_text(json.dumps(ai_data))

            result_path = compile_report(artifacts_dir)
            report_data = json.loads(result_path.read_text(encoding="utf-8"))

            file_status = report_data["file_status"]

            # Check it's a list
            assert isinstance(file_status, list)

            # Check each item has required keys
            for item in file_status:
                required_keys = {
                    "file_path",
                    "language",
                    "status",
                    "issues",
                }
                assert set(item.keys()) == required_keys

                # Check types
                assert isinstance(item["file_path"], str)
                assert isinstance(item["language"], str)
                assert isinstance(item["status"], str)
                assert isinstance(item["issues"], list)

                # Check status is one of expected values
                assert item["status"] in ["READY", "REVIEW", "FIX"]

    def test_lexicons_schema(self):
        """Test that lexicons object has correct schema."""
        with tempfile.TemporaryDirectory() as tmpdir:
            artifacts_dir = Path(tmpdir)

            eval_data = {
                "files_total": 1,
                "languages_total": 1,
                "issues_total": 0,
                "source_language": "en",
                "languages": {
                    "fr": {
                        "files": {
                            "test - FR.srt": {
                                "missing_translation": 0,
                                "untranslated_after_dnt": 0,
                                "timing_fail": 0,
                            }
                        }
                    }
                },
            }

            ai_data = {
                "version": "1.0.0",
                "timestamp": "2025-01-01T00:00:00Z",
                "target_languages": ["fr"],
                "dnt_terms": ["test"],
                "termbase": {"fr": {"test": "test"}},
            }

            (artifacts_dir / "eval_report.json").write_text(json.dumps(eval_data))
            (artifacts_dir / "ai_config.json").write_text(json.dumps(ai_data))

            result_path = compile_report(artifacts_dir)
            report_data = json.loads(result_path.read_text(encoding="utf-8"))

            lexicons = report_data["lexicons"]

            # Check required keys
            assert "dnt_terms" in lexicons
            assert "termbase" in lexicons

            # Check types
            assert isinstance(lexicons["dnt_terms"], list)
            assert isinstance(lexicons["termbase"], dict)

            # Check dnt_terms items are strings
            for term in lexicons["dnt_terms"]:
                assert isinstance(term, str)

            # Check termbase structure
            for lang, terms in lexicons["termbase"].items():
                assert isinstance(lang, str)
                assert isinstance(terms, list)
                for term in terms:
                    assert isinstance(term, dict)
                    assert "source" in term
                    assert "target" in term
                    assert isinstance(term["source"], str)
                    assert isinstance(term["target"], str)

    def test_sections_schema(self):
        """Test that sections object has correct schema."""
        with tempfile.TemporaryDirectory() as tmpdir:
            artifacts_dir = Path(tmpdir)

            eval_data = {
                "files_total": 1,
                "languages_total": 1,
                "issues_total": 0,
                "source_language": "en",
                "languages": {
                    "fr": {
                        "files": {
                            "test - FR.srt": {
                                "missing_translation": 0,
                                "untranslated_after_dnt": 0,
                                "timing_fail": 0,
                            }
                        }
                    }
                },
            }

            ai_data = {
                "version": "1.0.0",
                "timestamp": "2025-01-01T00:00:00Z",
                "target_languages": ["fr"],
                "dnt_terms": ["test"],
                "termbase": {"fr": {"test": "test"}},
            }

            (artifacts_dir / "eval_report.json").write_text(json.dumps(eval_data))
            (artifacts_dir / "ai_config.json").write_text(json.dumps(ai_data))

            result_path = compile_report(artifacts_dir)
            report_data = json.loads(result_path.read_text(encoding="utf-8"))

            sections = report_data["sections"]

            # Check required keys
            assert "errors" in sections
            assert "warnings" in sections

            # Check types
            assert isinstance(sections["errors"], list)
            assert isinstance(sections["warnings"], list)

            # Check each error/warning item has required keys
            for item in sections["errors"] + sections["warnings"]:
                required_keys = {
                    "file_path",
                    "language",
                    "issue_type",
                    "idx",
                    "src",
                    "tgt",
                }
                assert set(item.keys()) == required_keys

                # Check types
                assert isinstance(item["file_path"], str)
                assert isinstance(item["language"], str)
                assert isinstance(item["issue_type"], str)
                assert isinstance(item["idx"], int)
                assert isinstance(item["src"], str)
                assert isinstance(item["tgt"], str)

    def test_version_and_timestamp_types(self):
        """Test that version and timestamp have correct types."""
        with tempfile.TemporaryDirectory() as tmpdir:
            artifacts_dir = Path(tmpdir)

            eval_data = {
                "files_total": 1,
                "languages_total": 1,
                "issues_total": 0,
                "source_language": "en",
                "languages": {
                    "fr": {
                        "files": {
                            "test - FR.srt": {
                                "missing_translation": 0,
                                "untranslated_after_dnt": 0,
                                "timing_fail": 0,
                            }
                        }
                    }
                },
            }

            ai_data = {
                "version": "1.0.0",
                "timestamp": "2025-01-01T00:00:00Z",
                "target_languages": ["fr"],
                "dnt_terms": ["test"],
                "termbase": {"fr": {"test": "test"}},
            }

            (artifacts_dir / "eval_report.json").write_text(json.dumps(eval_data))
            (artifacts_dir / "ai_config.json").write_text(json.dumps(ai_data))

            result_path = compile_report(artifacts_dir)
            report_data = json.loads(result_path.read_text(encoding="utf-8"))

            # Check types
            assert isinstance(report_data["version"], str)
            assert isinstance(report_data["timestamp"], str)
            assert isinstance(report_data["batch_label"], str)

            # Check they're not empty
            assert report_data["version"].strip() != ""
            assert report_data["timestamp"].strip() != ""
            assert report_data["batch_label"].strip() != ""
