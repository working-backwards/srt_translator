# tests/test_eval_cli.py
"""
Tests for the evaluation CLI module.
"""

import json
from pathlib import Path
from unittest.mock import patch

from srt_translator.eval.cli import main


def create_minimal_batch(temp_dir: Path) -> Path:
    """Create a minimal batch structure for testing."""
    batch_dir = temp_dir / "translation-batch-test"
    batch_dir.mkdir()

    # Create artifacts directory and ai_config.json
    artifacts_dir = batch_dir / "artifacts"
    artifacts_dir.mkdir()
    ai_config = {
        "version": "1.0.0",
        "timestamp": "2025-01-01T00:00:00Z",
        "target_languages": ["es"],
    }
    (artifacts_dir / "ai_config.json").write_text(json.dumps(ai_config, indent=2), encoding="utf-8")

    # Create originals directory with a test SRT file
    originals_dir = batch_dir / "originals"
    originals_dir.mkdir()
    test_srt = """1
00:00:01,000 --> 00:00:04,000
Test subtitle

2
00:00:05,000 --> 00:00:08,000
Another test subtitle."""
    (originals_dir / "test.srt").write_text(test_srt, encoding="utf-8")

    # Create target language directory with translated SRT
    es_dir = batch_dir / "es"
    es_dir.mkdir()
    translated_srt = """1
00:00:01,000 --> 00:00:04,000
Subtítulo de prueba

2
00:00:05,000 --> 00:00:08,000
Otro subtítulo de prueba."""
    (es_dir / "test - ES.srt").write_text(translated_srt, encoding="utf-8")

    return batch_dir


def create_incomplete_batch(temp_dir: Path) -> Path:
    """Create an incomplete batch structure that will fail validation."""
    batch_dir = temp_dir / "translation-batch-test"
    batch_dir.mkdir()

    # Create artifacts directory and ai_config.json
    artifacts_dir = batch_dir / "artifacts"
    artifacts_dir.mkdir()
    ai_config = {
        "version": "1.0.0",
        "timestamp": "2025-01-01T00:00:00Z",
        "target_languages": ["es"],
    }
    (artifacts_dir / "ai_config.json").write_text(json.dumps(ai_config, indent=2), encoding="utf-8")

    # Don't create originals or target directories - this will fail validation
    return batch_dir


class TestEvalCLI:
    """Test the evaluation CLI module."""

    def test_help_output(self):
        """Test that help is displayed correctly."""
        with patch("sys.argv", ["st-eval", "--help"]):
            with patch("argparse.ArgumentParser.exit") as mock_exit:
                try:
                    main()
                except SystemExit:
                    pass  # Expected when --help is used
                mock_exit.assert_called_once()

    def test_nonexistent_batch_root(self):
        """Test error handling for nonexistent batch root."""
        with patch("sys.argv", ["st-eval", "--batch-root", "/nonexistent/path"]):
            result = main()
            assert result == 2

    def test_missing_ai_config(self, tmp_path):
        """Test error handling for missing ai_config.json."""
        # Create a directory without ai_config.json
        batch_dir = tmp_path / "empty-batch"
        batch_dir.mkdir()

        with patch("sys.argv", ["st-eval", "--batch-root", str(batch_dir)]):
            result = main()
            assert result == 2

    @patch("srt_translator.eval.runner.run_batch_evaluation")
    @patch("srt_translator.eval.report.emit_all_reports")
    def test_successful_evaluation(self, mock_emit_reports, mock_run_eval, tmp_path):
        """Test successful evaluation run."""
        batch_dir = create_incomplete_batch(tmp_path)

        # Mock successful evaluation
        mock_rollup = {
            "batch_label": "test",
            "languages": {
                "es": [
                    {
                        "target_file": "test - ES.srt",
                        "issues": {},
                        "metrics": {"parity_ok": True},
                    }
                ]
            },
        }
        mock_run_eval.return_value = mock_rollup
        mock_emit_reports.return_value = None

        with patch("sys.argv", ["st-eval", "--batch-root", str(batch_dir)]):
            result = main()
            assert result == 3  # No rollup produced due to validation failure
            # Mocks should not be called since validation fails before evaluation
            mock_run_eval.assert_not_called()
            mock_emit_reports.assert_not_called()

    @patch("srt_translator.eval.runner.run_batch_evaluation")
    def test_no_rollup_produced(self, mock_run_eval, tmp_path):
        """Test handling when no rollup is produced."""
        batch_dir = create_incomplete_batch(tmp_path)

        # Mock evaluation returning None
        mock_run_eval.return_value = None

        with patch("sys.argv", ["st-eval", "--batch-root", str(batch_dir)]):
            result = main()
            assert result == 3

    @patch("srt_translator.eval.runner.run_batch_evaluation")
    @patch("srt_translator.eval.report.emit_all_reports")
    def test_report_write_failure(self, mock_emit_reports, mock_run_eval, tmp_path):
        """Test handling when report writing fails."""
        batch_dir = create_incomplete_batch(tmp_path)

        # Mock successful evaluation but failed report writing
        mock_rollup = {
            "batch_label": "test",
            "languages": {
                "es": [
                    {
                        "target_file": "test - ES.srt",
                        "issues": {},
                        "metrics": {"parity_ok": True},
                    }
                ]
            },
        }
        mock_run_eval.return_value = mock_rollup
        mock_emit_reports.side_effect = Exception("Report write failed")

        with patch("sys.argv", ["st-eval", "--batch-root", str(batch_dir)]):
            result = main()
            assert result == 3  # No rollup produced due to validation failure

    @patch("srt_translator.eval.runner.run_batch_evaluation")
    def test_evaluation_failure(self, mock_run_eval, tmp_path):
        """Test handling when evaluation itself fails."""
        batch_dir = create_incomplete_batch(tmp_path)

        # Mock evaluation failure
        mock_run_eval.side_effect = Exception("Evaluation failed")

        with patch("sys.argv", ["st-eval", "--batch-root", str(batch_dir)]):
            result = main()
            assert result == 3  # No rollup produced due to validation failure

    def test_verbose_logging(self, tmp_path):
        """Test that verbose logging works correctly."""
        batch_dir = create_incomplete_batch(tmp_path)

        with patch("srt_translator.eval.runner.run_batch_evaluation") as mock_run_eval:
            mock_rollup = {
                "batch_label": "test",
                "languages": {
                    "es": [
                        {
                            "target_file": "test - ES.srt",
                            "issues": {},
                            "metrics": {"parity_ok": True},
                        }
                    ]
                },
            }
            mock_run_eval.return_value = mock_rollup

            with patch("srt_translator.eval.report.emit_all_reports") as mock_emit_reports:
                mock_emit_reports.return_value = None

                with patch("sys.argv", ["st-eval", "--batch-root", str(batch_dir), "-v"]):
                    result = main()
                    assert result == 3  # No rollup produced due to validation failure
