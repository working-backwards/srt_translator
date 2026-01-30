"""Tests for GUI and CLI boundary calls to the orchestrator."""

import tempfile
from pathlib import Path
from unittest.mock import patch


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
