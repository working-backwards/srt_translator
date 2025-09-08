"""Tests for GUI and CLI boundary calls to the orchestrator."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from srt_translator.eval.cli import main as cli_main


class TestGUIOrchestratorCalls:
    """Test that GUI calls the orchestrator correctly."""

    @patch("srt_translator.eval.report.emit_all_reports")
    def test_gui_calls_orchestrator_once(self, mock_emit_reports):
        """Test that GUI calls emit_all_reports once and doesn't call presenters directly."""
        # Create a mock app instance
        from srt_translator.gui.main_window import SRTTranslatorMainWindow

        app = SRTTranslatorMainWindow()

        # Mock the evaluation completion hook
        with tempfile.TemporaryDirectory() as temp_dir:
            artifacts_dir = Path(temp_dir) / "artifacts"
            artifacts_dir.mkdir()

            # Create a mock rollup
            mock_rollup = {
                "config_source": "ai_config.json",
                "dnt_coverage": "present",
                "termbase_coverage": "full",
                "termbase_entry_counts": {"fr": 1},
                "languages": {
                    "fr": {
                        "files": [
                            {
                                "target_file": "test - FR.srt",
                                "issues": {
                                    "missing_translation": [],
                                    "timing_fail": False,
                                },
                            }
                        ]
                    }
                },
                "original_language": {"detected": "en"},
            }

            # Mock the evaluation runner to return our rollup
            with patch("srt_translator.eval.runner.run_batch_evaluation") as mock_run_eval:
                mock_run_eval.return_value = mock_rollup

                # Mock the batch evaluation completion
                # This would typically be called when evaluation completes
                app.on_evaluation_completed(artifacts_dir, mock_rollup)

                # Verify emit_all_reports was called once
                mock_emit_reports.assert_called_once_with(artifacts_dir, mock_rollup)

    @patch("srt_translator.presenters.eval_md.build.build_eval_md")
    @patch("srt_translator.presenters.eval_html.build.build_eval_html")
    def test_gui_no_direct_presenter_calls(self, mock_html, mock_md):
        """Test that GUI doesn't call presenters directly."""
        from srt_translator.gui.main_window import SRTTranslatorMainWindow

        app = SRTTranslatorMainWindow()

        with tempfile.TemporaryDirectory() as temp_dir:
            artifacts_dir = Path(temp_dir) / "artifacts"
            artifacts_dir.mkdir()

            mock_rollup = {
                "config_source": "ai_config.json",
                "dnt_coverage": "present",
                "termbase_coverage": "full",
                "termbase_entry_counts": {"fr": 1},
                "languages": {
                    "fr": {
                        "files": [
                            {
                                "target_file": "test - FR.srt",
                                "issues": {
                                    "missing_translation": [],
                                    "timing_fail": False,
                                },
                            }
                        ]
                    }
                },
                "original_language": {"detected": "en"},
            }

            # Mock the evaluation runner
            with patch("srt_translator.eval.runner.run_batch_evaluation") as mock_run_eval:
                mock_run_eval.return_value = mock_rollup

                # Mock emit_all_reports to avoid actual file creation
                with patch("srt_translator.eval.report.emit_all_reports") as mock_emit:
                    mock_emit.return_value = None

                    # Call the evaluation completion hook
                    app.on_evaluation_completed(artifacts_dir, mock_rollup)

                    # Verify presenters were not called directly
                    mock_html.assert_not_called()
                    mock_md.assert_not_called()


class TestCLIOrchestratorCalls:
    """Test that CLI calls the orchestrator correctly."""

    @patch("srt_translator.eval.report.emit_all_reports")
    def test_cli_calls_orchestrator_once(self, mock_emit_reports):
        """Test that CLI calls emit_all_reports once and doesn't call presenters directly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            batch_dir = temp_dir / "test-batch"
            batch_dir.mkdir()
            artifacts_dir = batch_dir / "artifacts"
            artifacts_dir.mkdir()

            # Create minimal ai_config.json
            import json

            ai_config = {
                "version": "1.0.0",
                "timestamp": "2025-01-01T00:00:00Z",
                "target_languages": ["fr"],
                "dnt_terms": ["test"],
                "termbase": {"fr": {"test": "test"}},
            }
            (artifacts_dir / "ai_config.json").write_text(
                json.dumps(ai_config, indent=2), encoding="utf-8"
            )

            # Create originals directory
            originals_dir = batch_dir / "originals"
            originals_dir.mkdir()
            test_srt = """1
00:00:01,000 --> 00:00:04,000
Test subtitle"""
            (originals_dir / "test.srt").write_text(test_srt, encoding="utf-8")

            # Create target directory
            fr_dir = batch_dir / "fr"
            fr_dir.mkdir()
            translated_srt = """1
00:00:01,000 --> 00:00:04,000
Sous-titre de test"""
            (fr_dir / "test - FR.srt").write_text(translated_srt, encoding="utf-8")

            # Mock the evaluation runner
            mock_rollup = {
                "config_source": "ai_config.json",
                "dnt_coverage": "present",
                "termbase_coverage": "full",
                "termbase_entry_counts": {"fr": 1},
                "languages": {
                    "fr": {
                        "files": [
                            {
                                "target_file": "test - FR.srt",
                                "issues": {
                                    "missing_translation": [],
                                    "timing_fail": False,
                                },
                            }
                        ]
                    }
                },
                "original_language": {"detected": "en"},
            }

            with patch("srt_translator.eval.runner.run_batch_evaluation") as mock_run_eval:
                mock_run_eval.return_value = mock_rollup

                # Mock sys.argv for CLI
                with patch("sys.argv", ["st-eval", "--batch-root", str(batch_dir)]):
                    cli_main()

                    # Verify emit_all_reports was called once
                    mock_emit_reports.assert_called_once_with(artifacts_dir, mock_rollup)

    @patch("srt_translator.presenters.eval_md.build.build_eval_md")
    @patch("srt_translator.presenters.eval_html.build.build_eval_html")
    def test_cli_no_direct_presenter_calls(self, mock_html, mock_md):
        """Test that CLI doesn't call presenters directly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            batch_dir = temp_dir / "test-batch"
            batch_dir.mkdir()
            artifacts_dir = batch_dir / "artifacts"
            artifacts_dir.mkdir()

            # Create minimal ai_config.json
            import json

            ai_config = {
                "version": "1.0.0",
                "timestamp": "2025-01-01T00:00:00Z",
                "target_languages": ["fr"],
                "dnt_terms": ["test"],
                "termbase": {"fr": {"test": "test"}},
            }
            (artifacts_dir / "ai_config.json").write_text(
                json.dumps(ai_config, indent=2), encoding="utf-8"
            )

            # Create originals directory
            originals_dir = batch_dir / "originals"
            originals_dir.mkdir()
            test_srt = """1
00:00:01,000 --> 00:00:04,000
Test subtitle"""
            (originals_dir / "test.srt").write_text(test_srt, encoding="utf-8")

            # Create target directory
            fr_dir = batch_dir / "fr"
            fr_dir.mkdir()
            translated_srt = """1
00:00:01,000 --> 00:00:04,000
Sous-titre de test"""
            (fr_dir / "test - FR.srt").write_text(translated_srt, encoding="utf-8")

            # Mock the evaluation runner
            mock_rollup = {
                "config_source": "ai_config.json",
                "dnt_coverage": "present",
                "termbase_coverage": "full",
                "termbase_entry_counts": {"fr": 1},
                "languages": {
                    "fr": {
                        "files": [
                            {
                                "target_file": "test - FR.srt",
                                "issues": {
                                    "missing_translation": [],
                                    "timing_fail": False,
                                },
                            }
                        ]
                    }
                },
                "original_language": {"detected": "en"},
            }

            with patch("srt_translator.eval.runner.run_batch_evaluation") as mock_run_eval:
                mock_run_eval.return_value = mock_rollup

                # Mock emit_all_reports to avoid actual file creation
                with patch("srt_translator.eval.report.emit_all_reports") as mock_emit:
                    mock_emit.return_value = None

                    # Mock sys.argv for CLI
                    with patch("sys.argv", ["st-eval", "--batch-root", str(batch_dir)]):
                        cli_main()

                        # Verify presenters were not called directly
                        mock_html.assert_not_called()
                        mock_md.assert_not_called()

    def test_cli_handles_no_rollup_gracefully(self):
        """Test that CLI handles cases where no rollup is produced."""
        with tempfile.TemporaryDirectory() as temp_dir:
            batch_dir = temp_dir / "test-batch"
            batch_dir.mkdir()
            artifacts_dir = batch_dir / "artifacts"
            artifacts_dir.mkdir()

            # Create minimal ai_config.json
            import json

            ai_config = {
                "version": "1.0.0",
                "timestamp": "2025-01-01T00:00:00Z",
                "target_languages": ["fr"],
                "dnt_terms": ["test"],
                "termbase": {"fr": {"test": "test"}},
            }
            (artifacts_dir / "ai_config.json").write_text(
                json.dumps(ai_config, indent=2), encoding="utf-8"
            )

            # Mock the evaluation runner to return None (no rollup)
            with patch("srt_translator.eval.runner.run_batch_evaluation") as mock_run_eval:
                mock_run_eval.return_value = None

                # Mock sys.argv for CLI
                with patch("sys.argv", ["st-eval", "--batch-root", str(batch_dir)]):
                    result = cli_main()

                    # Should return error code when no rollup is produced
                    assert result == 3
