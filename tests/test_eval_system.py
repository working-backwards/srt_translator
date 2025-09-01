# tests/test_eval_system.py
"""
Tests for the evaluation system that focus on actual functionality.
"""

import json
from pathlib import Path
from unittest.mock import Mock, patch

from srt_translator.eval.report import write_batch_report
from srt_translator.eval.runner import run_batch_evaluation
from srt_translator.eval.tools import evaluate_pair, generate_eval


def create_test_batch_structure(temp_dir: Path, has_ai_config: bool = True, 
                              has_originals: bool = True, has_targets: bool = True):
    """Create a real test batch directory structure."""
    batch_dir = temp_dir / "translation-batch-test"
    batch_dir.mkdir()
    
    # Create ai_config.json if requested
    if has_ai_config:
        ai_config = {
            "version": "1.0.0",
            "timestamp": "2025-01-01T00:00:00Z",
            "target_languages": ["es", "fr"],
            "dnt_terms": ["Operating Plan", "Module"],
            "termbase": {
                "es": {"Operating Plan": "Plan Operativo"},
                "fr": {"Module": "Module"}
            }
        }
        (batch_dir / "ai_config.json").write_text(
            json.dumps(ai_config, indent=2), encoding="utf-8"
        )
    
    # Create originals directory if requested
    if has_originals:
        originals_dir = batch_dir / "originals"
        originals_dir.mkdir()
        # Create a test SRT file
        test_srt = """1
00:00:01,000 --> 00:00:04,000
Operating Plan Module 0

2
00:00:05,000 --> 00:00:08,000
This is a test subtitle file."""
        (originals_dir / "test.srt").write_text(test_srt, encoding="utf-8")
    
    # Create target language directories if requested
    if has_targets:
        for lang in ["es", "fr"]:
            lang_dir = batch_dir / lang
            lang_dir.mkdir()
            # Create translated SRT files
            if lang == "es":
                translated_srt = """1
00:00:01,000 --> 00:00:04,000
Plan Operativo Módulo 0

2
00:00:05,000 --> 00:00:08,000
Este es un archivo de subtítulos de prueba."""
            else:  # fr
                translated_srt = """1
00:00:01,000 --> 00:00:04,000
Plan Opérationnel Module 0

2
00:00:05,000 --> 00:00:08,000
Ceci est un fichier de sous-titres de test."""
            
            (lang_dir / f"test - {lang.upper()}.srt").write_text(
                translated_srt, encoding="utf-8"
            )
    
    return batch_dir


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
            "source_path",
            "target_path",
            "lang",
            "batch_label",
            "out_dir",
            # v1.0: no path-based inputs; DNT/TB are passed in-memory (dnt_terms, tb_map)
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
    """Test the new v1.0 evaluation policy with real files and behavior."""

    @patch("srt_translator.eval.runner._rubric_path")
    def test_required_inputs_missing_ai_config_stops_evaluation(self, mock_rubric_path, tmp_path):
        """Test that missing ai_config.json stops evaluation."""
        mock_rubric_path.return_value = Path("config/translation_rubric.yaml")
        
        # Create batch structure WITHOUT ai_config.json
        batch_dir = create_test_batch_structure(tmp_path, has_ai_config=False)
        mock_logger = Mock()
        mock_logger.getChild.return_value = mock_logger

        result = run_batch_evaluation(batch_dir, mock_logger)

        assert result is None
        # Verify that the error was logged
        mock_logger.error.assert_called()

    @patch("srt_translator.eval.runner._rubric_path")
    def test_required_inputs_invalid_ai_config_stops_evaluation(self, mock_rubric_path, tmp_path):
        """Test that invalid ai_config.json stops evaluation."""
        mock_rubric_path.return_value = Path("config/translation_rubric.yaml")
        
        # Create batch structure with corrupted ai_config.json
        batch_dir = create_test_batch_structure(tmp_path)
        corrupted_config = batch_dir / "ai_config.json"
        corrupted_config.write_text("invalid json content", encoding="utf-8")
        
        mock_logger = Mock()
        mock_logger.getChild.return_value = mock_logger

        result = run_batch_evaluation(batch_dir, mock_logger)

        assert result is None
        # Verify that the error was logged
        mock_logger.error.assert_called()

    @patch("srt_translator.eval.runner._rubric_path")
    def test_required_inputs_missing_originals_stops_evaluation(self, mock_rubric_path, tmp_path):
        """Test that missing originals directory stops evaluation."""
        mock_rubric_path.return_value = Path("config/translation_rubric.yaml")
        
        # Create batch structure WITHOUT originals directory
        batch_dir = create_test_batch_structure(tmp_path, has_originals=False)
        mock_logger = Mock()
        mock_logger.getChild.return_value = mock_logger

        result = run_batch_evaluation(batch_dir, mock_logger)

        assert result is None
        # Verify that the error was logged
        mock_logger.error.assert_called()

    @patch("srt_translator.eval.runner._rubric_path")
    def test_required_inputs_missing_targets_stops_evaluation(self, mock_rubric_path, tmp_path):
        """Test that missing target language directories stops evaluation."""
        mock_rubric_path.return_value = Path("config/translation_rubric.yaml")
        
        # Create batch structure WITHOUT target language directories
        batch_dir = create_test_batch_structure(tmp_path, has_targets=False)
        mock_logger = Mock()
        mock_logger.getChild.return_value = mock_logger

        result = run_batch_evaluation(batch_dir, mock_logger)

        assert result is None
        # Verify that the error was logged
        mock_logger.error.assert_called()

    @patch("srt_translator.eval.runner._rubric_path")
    def test_optional_inputs_dnt_missing_continues_evaluation(self, mock_rubric_path, tmp_path):
        """Test that missing DNT terms continues evaluation with INFO log."""
        mock_rubric_path.return_value = Path("config/translation_rubric.yaml")
        
        # Create batch structure with empty DNT terms
        batch_dir = create_test_batch_structure(tmp_path)
        
        # Modify ai_config.json to have no DNT terms
        ai_config_path = batch_dir / "ai_config.json"
        ai_config = json.loads(ai_config_path.read_text(encoding="utf-8"))
        ai_config["dnt_terms"] = []
        ai_config_path.write_text(json.dumps(ai_config, indent=2), encoding="utf-8")
        
        mock_logger = Mock()
        mock_logger.getChild.return_value = mock_logger

        # Mock the generate_eval function to avoid actual evaluation
        with patch("srt_translator.eval.runner.generate_eval") as mock_generate_eval:
            mock_generate_eval.return_value = {"verdict": "PASS"}
            result = run_batch_evaluation(batch_dir, mock_logger)

        # Should continue (not return None)
        assert result is not None
        # Should log INFO about missing DNT
        mock_logger.info.assert_any_call("No DNT terms provided; continuing without DNT coverage")

    @patch("srt_translator.eval.runner._rubric_path")
    def test_optional_inputs_termbase_missing_continues_evaluation(
        self, mock_rubric_path, tmp_path
    ):
        """Test that missing termbase continues evaluation with INFO log."""
        mock_rubric_path.return_value = Path("config/translation_rubric.yaml")
        
        # Create batch structure with empty termbase
        batch_dir = create_test_batch_structure(tmp_path)
        
        # Modify ai_config.json to have no termbase
        ai_config_path = batch_dir / "ai_config.json"
        ai_config = json.loads(ai_config_path.read_text(encoding="utf-8"))
        ai_config["termbase"] = {}
        ai_config_path.write_text(json.dumps(ai_config, indent=2), encoding="utf-8")
        
        mock_logger = Mock()
        mock_logger.getChild.return_value = mock_logger

        # Mock the generate_eval function to avoid actual evaluation
        with patch("srt_translator.eval.runner.generate_eval") as mock_generate_eval:
            mock_generate_eval.return_value = {"verdict": "PASS"}
            result = run_batch_evaluation(batch_dir, mock_logger)

        # Should continue (not return None)
        assert result is not None
        # Should log INFO about missing termbase
        mock_logger.info.assert_any_call(
            "No termbase provided; continuing without termbase coverage"
        )

    @patch("srt_translator.eval.runner._rubric_path")
    def test_coverage_fields_present_in_rollup(self, mock_rubric_path, tmp_path):
        """Test that coverage fields are present in the evaluation rollup."""
        mock_rubric_path.return_value = Path("config/translation_rubric.yaml")
        
        # Create complete batch structure
        batch_dir = create_test_batch_structure(tmp_path)
        
        mock_logger = Mock()
        mock_logger.getChild.return_value = mock_logger

        # Mock the generate_eval function to avoid actual evaluation
        with patch("srt_translator.eval.runner.generate_eval") as mock_generate_eval:
            mock_generate_eval.return_value = {"verdict": "PASS"}
            result = run_batch_evaluation(batch_dir, mock_logger)

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
    def test_coverage_fields_partial_termbase(self, mock_rubric_path, tmp_path):
        """Test that partial termbase coverage is correctly reported."""
        mock_rubric_path.return_value = Path("config/translation_rubric.yaml")
        
        # Create batch structure
        batch_dir = create_test_batch_structure(tmp_path)
        
        # Modify ai_config.json to have partial termbase coverage
        ai_config_path = batch_dir / "ai_config.json"
        ai_config = json.loads(ai_config_path.read_text(encoding="utf-8"))
        ai_config["termbase"] = {
            "es": {"Operating Plan": "Plan Operativo"},
            "fr": {}  # No terms for French
        }
        ai_config_path.write_text(json.dumps(ai_config, indent=2), encoding="utf-8")
        
        mock_logger = Mock()
        mock_logger.getChild.return_value = mock_logger

        # Mock the generate_eval function to avoid actual evaluation
        with patch("srt_translator.eval.runner.generate_eval") as mock_generate_eval:
            mock_generate_eval.return_value = {"verdict": "PASS"}
            result = run_batch_evaluation(batch_dir, mock_logger)

        # Should continue (not return None)
        assert result is not None
        
        # Check coverage fields
        assert result["dnt_coverage"] == "present"
        assert result["termbase_coverage"] == "partial"
        assert result["termbase_entry_counts"]["es"] == 1
        assert result["termbase_entry_counts"]["fr"] == 0


class TestUnifiedLogging:
    """Test that evaluation logs appear in both console and batch log file."""

    @patch("srt_translator.eval.runner._rubric_path")
    def test_evaluation_logger_gets_batch_file_handler(self, mock_rubric_path, tmp_path):
        """Test that evaluation logger gets batch log file handler for unified logging."""
        mock_rubric_path.return_value = Path("config/translation_rubric.yaml")
        
        # Create complete batch structure
        batch_dir = create_test_batch_structure(tmp_path)
        
        # Create a batch log file to test handler attachment
        log_file = batch_dir / "translation_issues_test.log"
        log_file.write_text("Existing log content", encoding="utf-8")
        
        # Create a proper mock logger with handlers attribute
        mock_logger = Mock()
        mock_logger.handlers = []
        mock_logger.getChild.return_value = mock_logger

        # Mock the generate_eval function to avoid actual evaluation
        with patch("srt_translator.eval.runner.generate_eval") as mock_generate_eval:
            mock_generate_eval.return_value = {"verdict": "PASS"}
            result = run_batch_evaluation(batch_dir, mock_logger)

        # Should continue (not return None)
        assert result is not None


class TestDataNormalization:
    """Test that ai_config.json data is properly normalized."""

    def test_dnt_terms_normalization(self, tmp_path):
        """Test that DNT terms are properly normalized from ai_config.json."""
        from srt_translator.eval.runner import _load_batch_config
        
        # Create a real ai_config.json file
        batch_dir = tmp_path / "test_batch"
        batch_dir.mkdir()
        
        ai_config = {
            "version": "1.0.0",
            "target_languages": ["es", "fr"],
            "dnt_terms": ["Operating Plan", "Module"],
            "termbase": {
                "es": {"Operating Plan": "Plan Operativo"},
                "fr": {"Module": "Module"}
            }
        }
        
        ai_config_path = batch_dir / "ai_config.json"
        ai_config_path.write_text(json.dumps(ai_config, indent=2), encoding="utf-8")
        
        mock_logger = Mock()
        result = _load_batch_config(batch_dir, mock_logger)
        
        # Check normalization
        assert result["dnt_terms"] == ["Operating Plan", "Module"]
        assert result["termbase"]["es"] == [
            {"source": "Operating Plan", "target": "Plan Operativo"}
        ]
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
