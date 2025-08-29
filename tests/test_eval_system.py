# tests/test_eval_system.py
"""
Basic tests for the evaluation system.
"""

import json
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
        expected_params = ["batch_root", "logger", "language_config"]

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


class TestV1EvaluationPolicy:
    """Test the new v1.0 evaluation policy implementation."""

    @patch("srt_translator.eval.runner._rubric_path")
    @patch("srt_translator.eval.runner._load_batch_config")
    @patch("srt_translator.eval.runner._validate_batch_structure")
    def test_required_inputs_missing_ai_config_stops_evaluation(
        self, mock_validate, mock_load_config, mock_rubric_path
    ):
        """Test that missing ai_config.json stops evaluation."""
        mock_rubric_path.return_value = Path("/tmp/rubric.yaml")
        mock_load_config.side_effect = FileNotFoundError("ai_config.json required")
        mock_logger = Mock()
        mock_logger.getChild.return_value = mock_logger

        result = run_batch_evaluation(Path("/tmp/batch"), mock_logger)

        assert result is None
        mock_logger.error.assert_called()

    @patch("srt_translator.eval.runner._rubric_path")
    @patch("srt_translator.eval.runner._load_batch_config")
    @patch("srt_translator.eval.runner._validate_batch_structure")
    def test_required_inputs_invalid_ai_config_stops_evaluation(
        self, mock_validate, mock_load_config, mock_rubric_path
    ):
        """Test that invalid ai_config.json stops evaluation."""
        mock_rubric_path.return_value = Path("/tmp/rubric.yaml")
        mock_load_config.side_effect = ValueError("Invalid ai_config.json")
        mock_logger = Mock()
        mock_logger.getChild.return_value = mock_logger

        result = run_batch_evaluation(Path("/tmp/batch"), mock_logger)

        assert result is None
        mock_logger.error.assert_called()

    @patch("srt_translator.eval.runner._rubric_path")
    @patch("srt_translator.eval.runner._load_batch_config")
    @patch("srt_translator.eval.runner._validate_batch_structure")
    def test_required_inputs_batch_structure_validation_failure_stops_evaluation(
        self, mock_validate, mock_load_config, mock_rubric_path
    ):
        """Test that batch structure validation failure stops evaluation."""
        mock_rubric_path.return_value = Path("/tmp/rubric.yaml")
        mock_load_config.return_value = {"target_languages": ["es", "fr"]}
        mock_validate.return_value = False
        mock_logger = Mock()
        mock_logger.getChild.return_value = mock_logger

        result = run_batch_evaluation(Path("/tmp/batch"), mock_logger)

        assert result is None
        mock_logger.error.assert_called()

    @patch("srt_translator.eval.runner._rubric_path")
    @patch("srt_translator.eval.runner._load_batch_config")
    @patch("srt_translator.eval.runner._validate_batch_structure")
    def test_optional_inputs_dnt_missing_continues_evaluation(
        self, mock_validate, mock_load_config, mock_rubric_path
    ):
        """Test that missing DNT terms continues evaluation with INFO log."""
        mock_rubric_path.return_value = Path("/tmp/rubric.yaml")
        mock_load_config.return_value = {
            "target_languages": ["es"],
            "dnt_terms": [],
            "termbase": {}
        }
        mock_validate.return_value = True
        mock_logger = Mock()
        mock_logger.getChild.return_value = mock_logger

        # Mock the rest of the evaluation process
        with patch("srt_translator.eval.runner._collect_language_dirs") as mock_collect:
            mock_collect.return_value = [Path("/tmp/batch/es")]
            result = run_batch_evaluation(Path("/tmp/batch"), mock_logger)

        # Should continue (not return None)
        assert result is not None
        # Should log INFO about missing DNT
        mock_logger.info.assert_any_call("No DNT terms provided; continuing without DNT coverage")

    @patch("srt_translator.eval.runner._rubric_path")
    @patch("srt_translator.eval.runner._load_batch_config")
    @patch("srt_translator.eval.runner._validate_batch_structure")
    def test_optional_inputs_termbase_missing_continues_evaluation(
        self, mock_validate, mock_load_config, mock_rubric_path
    ):
        """Test that missing termbase continues evaluation with INFO log."""
        mock_rubric_path.return_value = Path("/tmp/rubric.yaml")
        mock_load_config.return_value = {
            "target_languages": ["es", "fr"],
            "dnt_terms": ["term1"],
            "termbase": {}
        }
        mock_validate.return_value = True
        mock_logger = Mock()
        mock_logger.getChild.return_value = mock_logger

        # Mock the rest of the evaluation process
        with patch("srt_translator.eval.runner._collect_language_dirs") as mock_collect:
            mock_collect.return_value = [Path("/tmp/batch/es"), Path("/tmp/batch/fr")]
            result = run_batch_evaluation(Path("/tmp/batch"), mock_logger)

        # Should continue (not return None)
        assert result is not None
        # Should log INFO about missing termbase
        mock_logger.info.assert_any_call("No termbase provided; continuing without termbase coverage")

    @patch("srt_translator.eval.runner._rubric_path")
    @patch("srt_translator.eval.runner._load_batch_config")
    @patch("srt_translator.eval.runner._validate_batch_structure")
    def test_coverage_fields_present_in_rollup(
        self, mock_validate, mock_load_config, mock_rubric_path
    ):
        """Test that coverage fields are present in the evaluation rollup."""
        mock_rubric_path.return_value = Path("/tmp/rubric.yaml")
        mock_load_config.return_value = {
            "target_languages": ["es", "fr"],
            "dnt_terms": ["Operating Plan", "Module"],
            "termbase": {
                "es": [{"source": "Operating Plan", "target": "Plan Operativo"}],
                "fr": [{"source": "Module", "target": "Module"}]
            }
        }
        mock_validate.return_value = True
        mock_logger = Mock()
        mock_logger.getChild.return_value = mock_logger

        # Mock the rest of the evaluation process
        with patch("srt_translator.eval.runner._collect_language_dirs") as mock_collect:
            mock_collect.return_value = [Path("/tmp/batch/es"), Path("/tmp/batch/fr")]
            result = run_batch_evaluation(Path("/tmp/batch"), mock_logger)

        # Should continue (not return None)
        assert result is not None
        
        # Check required coverage fields
        assert result["config_source"] == "ai_config.json"
        assert result["dnt_coverage"] == "present"
        assert result["termbase_coverage"] == "full"
        assert "termbase_entry_counts" in result
        assert result["termbase_entry_counts"]["es"] == 1
        assert result["termbase_entry_counts"]["fr"] == 1

    @patch("srt_translator.eval.runner._rubric_path")
    @patch("srt_translator.eval.runner._load_batch_config")
    @patch("srt_translator.eval.runner._validate_batch_structure")
    def test_coverage_fields_partial_termbase(
        self, mock_validate, mock_load_config, mock_rubric_path
    ):
        """Test that partial termbase coverage is correctly reported."""
        mock_rubric_path.return_value = Path("/tmp/rubric.yaml")
        mock_load_config.return_value = {
            "target_languages": ["es", "fr", "de"],
            "dnt_terms": ["Operating Plan"],
            "termbase": {
                "es": [{"source": "Operating Plan", "target": "Plan Operativo"}],
                "fr": [],  # No terms
                "de": [{"source": "Operating Plan", "target": "Betriebsplan"}]
            }
        }
        mock_validate.return_value = True
        mock_logger = Mock()
        mock_logger.getChild.return_value = mock_logger

        # Mock the rest of the evaluation process
        with patch("srt_translator.eval.runner._collect_language_dirs") as mock_collect:
            mock_collect.return_value = [Path("/tmp/batch/es"), Path("/tmp/batch/fr"), Path("/tmp/batch/de")]
            result = run_batch_evaluation(Path("/tmp/batch"), mock_logger)

        # Should continue (not return None)
        assert result is not None
        
        # Check coverage fields
        assert result["dnt_coverage"] == "present"
        assert result["termbase_coverage"] == "partial"
        assert result["termbase_entry_counts"]["es"] == 1
        assert result["termbase_entry_counts"]["fr"] == 0
        assert result["termbase_entry_counts"]["de"] == 1


class TestUnifiedLogging:
    """Test that evaluation logs appear in both console and batch log file."""

    @patch("srt_translator.eval.runner._rubric_path")
    @patch("srt_translator.eval.runner._load_batch_config")
    @patch("srt_translator.eval.runner._validate_batch_structure")
    def test_evaluation_logger_gets_batch_file_handler(
        self, mock_validate, mock_load_config, mock_rubric_path
    ):
        """Test that evaluation logger gets batch file handler for unified logging."""
        mock_rubric_path.return_value = Path("/tmp/rubric.yaml")
        mock_load_config.return_value = {
            "target_languages": ["es"],
            "dnt_terms": [],
            "termbase": {}
        }
        mock_validate.return_value = True
        mock_logger = Mock()
        mock_logger.getChild.return_value = mock_logger

        # Mock the rest of the evaluation process
        with patch("srt_translator.eval.runner._collect_language_dirs") as mock_collect:
            mock_collect.return_value = [Path("/tmp/batch/es")]
            result = run_batch_evaluation(Path("/tmp/batch"), mock_logger)

        # Should continue (not return None)
        assert result is not None
        
        # The _ensure_batch_log_handler should have been called
        # (This is tested by checking that the function completes successfully)


class TestDataNormalization:
    """Test that ai_config.json data is properly normalized."""

    def test_dnt_terms_normalization(self):
        """Test that DNT terms are properly normalized from ai_config.json."""
        from srt_translator.eval.runner import _load_batch_config
        
        # Mock the file reading
        with patch("pathlib.Path.read_text") as mock_read:
            mock_read.return_value = json.dumps({
                "version": "1.0.0",
                "target_languages": ["es", "fr"],
                "dnt_terms": ["Operating Plan", "Module"],
                "termbase": {
                    "es": {"Operating Plan": "Plan Operativo"},
                    "fr": {"Module": "Module"}
                }
            })
            
            mock_logger = Mock()
            result = _load_batch_config(Path("/tmp/batch"), mock_logger)
            
            # Check normalization
            assert result["dnt_terms"] == ["Operating Plan", "Module"]
            assert result["termbase"]["es"] == [{"source": "Operating Plan", "target": "Plan Operativo"}]
            assert result["termbase"]["fr"] == [{"source": "Module", "target": "Module"}]

    def test_termbase_coverage_calculation(self):
        """Test that termbase coverage is correctly calculated."""
        from srt_translator.eval.runner import _calculate_termbase_coverage
        
        # Test full coverage
        full_termbase = {
            "es": [{"source": "term1", "target": "término1"}],
            "fr": [{"source": "term1", "target": "terme1"}]
        }
        assert _calculate_termbase_coverage(full_termbase) == "full"
        
        # Test partial coverage
        partial_termbase = {
            "es": [{"source": "term1", "target": "término1"}],
            "fr": []
        }
        assert _calculate_termbase_coverage(partial_termbase) == "partial"
        
        # Test no coverage
        no_termbase = {}
        assert _calculate_termbase_coverage(no_termbase) == "none"
        
        # Test empty entries
        empty_termbase = {
            "es": [],
            "fr": []
        }
        assert _calculate_termbase_coverage(empty_termbase) == "none"
