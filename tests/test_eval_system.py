# tests/test_eval_system.py
"""
Basic tests for the evaluation system.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from srt_translator.eval.tools import generate_eval, evaluate_pair
from srt_translator.eval.runner import run_batch_evaluation
from srt_translator.eval.report import write_batch_report


class TestEvaluationTools:
    """Test the evaluation tools module."""

    def test_generate_eval_import(self):
        """Test that generate_eval can be imported and called."""
        assert callable(generate_eval)
        assert callable(evaluate_pair)

    def test_generate_eval_signature(self):
        """Test that generate_eval has the expected signature."""
        import inspect

        sig = inspect.signature(generate_eval)
        expected_params = [
            "en_path",
            "tgt_path",
            "lang",
            "batch_label",
            "out_dir",
            "dnt_path",
            "tb_path",
            "cps_soft",
            "cps_hard",
        ]

        for param in expected_params:
            assert param in sig.parameters


class TestEvaluationRunner:
    """Test the evaluation runner module."""

    def test_run_batch_evaluation_import(self):
        """Test that run_batch_evaluation can be imported and called."""
        assert callable(run_batch_evaluation)

    def test_run_batch_evaluation_signature(self):
        """Test that run_batch_evaluation has the expected signature."""
        import inspect

        sig = inspect.signature(run_batch_evaluation)
        expected_params = ["batch_root", "logger"]

        for param in expected_params:
            assert param in sig.parameters


class TestEvaluationReport:
    """Test the evaluation report module."""

    def test_write_batch_report_import(self):
        """Test that write_batch_report can be imported and called."""
        assert callable(write_batch_report)

    def test_write_batch_report_signature(self):
        """Test that write_batch_report has the expected signature."""
        import inspect

        sig = inspect.signature(write_batch_report)
        expected_params = ["batch_root", "rollup", "logger"]

        for param in expected_params:
            assert param in sig.parameters


class TestEvaluationIntegration:
    """Test basic integration of the evaluation system."""

    @patch("srt_translator.eval.runner._rubric_path")
    def test_evaluation_skipped_when_no_rubric(self, mock_rubric_path):
        """Test that evaluation is skipped when rubric file doesn't exist."""
        mock_rubric_path.return_value = Path("/nonexistent/rubric.yaml")
        mock_logger = Mock()

        result = run_batch_evaluation(Path("/tmp/batch"), mock_logger)

        assert result is None
        mock_logger.getChild.assert_called_once_with("runner")
        mock_logger.getChild().info.assert_called_once()

    def test_evaluation_package_structure(self):
        """Test that the evaluation package has the expected structure."""
        eval_dir = Path("srt_translator/eval")

        assert eval_dir.exists()
        assert (eval_dir / "__init__.py").exists()
        assert (eval_dir / "tools.py").exists()
        assert (eval_dir / "runner.py").exists()
        assert (eval_dir / "report.py").exists()
        # Note: run_summaries.py was deleted as part of removing backwards compatibility

    def test_rubric_config_exists(self):
        """Test that the translation rubric configuration exists."""
        rubric_path = Path("config/translation_rubric.yaml")
        assert rubric_path.exists()

        # Basic validation that it's valid YAML
        import yaml

        with open(rubric_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        assert "caps" in data
        assert "timing" in data
        assert "terminology" in data
        assert "rules" in data
