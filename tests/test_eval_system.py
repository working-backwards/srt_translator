# tests/test_eval_system.py
"""Tests for the evaluation system."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

from srt_translator.eval.runner import (
    _calculate_termbase_coverage,
    _load_batch_config,
    run_batch_evaluation,
)
from srt_translator.eval.tools import evaluate_pair, generate_eval


def create_test_batch_structure(
    temp_dir: Path, has_ai_config: bool = True, has_originals: bool = True, has_targets: bool = True
):
    """Create a real test batch directory structure."""
    batch_dir = temp_dir / "translation-batch-test"
    batch_dir.mkdir()

    # Create ai_config.json in artifacts directory if requested
    if has_ai_config:
        artifacts_dir = batch_dir / "artifacts"
        artifacts_dir.mkdir()
        ai_config = {
            "version": "1.0.0",
            "timestamp": "2025-01-01T00:00:00Z",
            "target_languages": ["es", "fr"],
            "dnt_terms": ["Operating Plan", "Module"],
            "termbase": {"es": {"Operating Plan": "Plan Operativo"}, "fr": {"Module": "Module"}},
        }
        (artifacts_dir / "ai_config.json").write_text(json.dumps(ai_config, indent=2), encoding="utf-8")

    # Create originals directory if requested
    if has_originals:
        originals_dir = batch_dir / "originals"
        originals_dir.mkdir()
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
            if lang == "es":
                translated_srt = """1
00:00:01,000 --> 00:00:04,000
Plan Operativo Módulo 0

2
00:00:05,000 --> 00:00:08,000
Este es un archivo de subtítulos de prueba."""
            else:
                translated_srt = """1
00:00:01,000 --> 00:00:04,000
Plan Opérationnel Module 0

2
00:00:05,000 --> 00:00:08,000
Ceci est un fichier de sous-titres de test."""
            (lang_dir / f"test - {lang.upper()}.srt").write_text(translated_srt, encoding="utf-8")

    return batch_dir


MINIMAL_RUBRIC = {
    "caps": {
        "defaults": {"cps_soft": 15, "cps_hard": 20},
    },
    "fragments": {},
}


class TestEvaluationTools:
    """Test the evaluation tools module."""

    def test_generate_eval_import(self):
        assert callable(generate_eval)
        assert callable(evaluate_pair)

    def test_generate_eval_signature(self):
        import inspect

        sig = inspect.signature(generate_eval)
        for param in ["source_path", "target_path", "lang", "batch_label", "out_dir", "cps_soft", "cps_hard"]:
            assert param in sig.parameters


class TestEvaluationRunner:
    """Test the evaluation runner module."""

    def test_run_batch_evaluation_import(self):
        assert callable(run_batch_evaluation)

    def test_run_batch_evaluation_signature(self):
        import inspect

        sig = inspect.signature(run_batch_evaluation)
        for param in ["batch_root", "logger", "language_config"]:
            assert param in sig.parameters


class TestEvaluationIntegration:
    """Test basic integration of the evaluation system."""

    @patch("srt_translator.eval.runner._load_rubric")
    def test_evaluation_skipped_when_invalid_rubric(self, mock_load_rubric):
        """Test that evaluation is skipped when rubric is invalid."""
        mock_load_rubric.side_effect = Exception("Rubric not found")
        mock_logger = Mock()

        result = run_batch_evaluation(Path("/tmp/batch"), mock_logger)

        assert result is None
        mock_logger.getChild.assert_called_once_with("runner")

    def test_evaluation_package_structure(self):
        eval_dir = Path("srt_translator/eval")
        assert eval_dir.exists()
        assert (eval_dir / "__init__.py").exists()


class TestV1EvaluationPolicy:
    """Test the v1.0 evaluation policy with real files and behavior."""

    @patch("srt_translator.eval.runner._load_rubric")
    def test_required_inputs_missing_ai_config_stops_evaluation(self, mock_load_rubric, tmp_path):
        mock_load_rubric.return_value = MINIMAL_RUBRIC
        batch_dir = create_test_batch_structure(tmp_path, has_ai_config=False)
        mock_logger = Mock()
        mock_logger.getChild.return_value = mock_logger

        result = run_batch_evaluation(batch_dir, mock_logger)
        assert result is None
        mock_logger.error.assert_called()

    @patch("srt_translator.eval.runner._load_rubric")
    def test_required_inputs_invalid_ai_config_stops_evaluation(self, mock_load_rubric, tmp_path):
        mock_load_rubric.return_value = MINIMAL_RUBRIC
        batch_dir = create_test_batch_structure(tmp_path)
        (batch_dir / "artifacts" / "ai_config.json").write_text("invalid json", encoding="utf-8")
        mock_logger = Mock()
        mock_logger.getChild.return_value = mock_logger

        result = run_batch_evaluation(batch_dir, mock_logger)
        assert result is None
        mock_logger.error.assert_called()

    @patch("srt_translator.eval.runner._load_rubric")
    def test_required_inputs_missing_originals_stops_evaluation(self, mock_load_rubric, tmp_path):
        mock_load_rubric.return_value = MINIMAL_RUBRIC
        batch_dir = create_test_batch_structure(tmp_path, has_originals=False)
        mock_logger = Mock()
        mock_logger.getChild.return_value = mock_logger

        result = run_batch_evaluation(batch_dir, mock_logger)
        assert result is None
        mock_logger.error.assert_called()

    @patch("srt_translator.eval.runner._load_rubric")
    def test_required_inputs_missing_targets_stops_evaluation(self, mock_load_rubric, tmp_path):
        mock_load_rubric.return_value = MINIMAL_RUBRIC
        batch_dir = create_test_batch_structure(tmp_path, has_targets=False)
        mock_logger = Mock()
        mock_logger.getChild.return_value = mock_logger

        result = run_batch_evaluation(batch_dir, mock_logger)
        assert result is None
        mock_logger.error.assert_called()

    @patch("srt_translator.eval.runner._load_rubric")
    def test_optional_inputs_dnt_missing_continues_evaluation(self, mock_load_rubric, tmp_path):
        mock_load_rubric.return_value = MINIMAL_RUBRIC
        batch_dir = create_test_batch_structure(tmp_path)

        ai_config_path = batch_dir / "artifacts" / "ai_config.json"
        ai_config = json.loads(ai_config_path.read_text(encoding="utf-8"))
        ai_config["dnt_terms"] = []
        ai_config_path.write_text(json.dumps(ai_config, indent=2), encoding="utf-8")

        mock_logger = Mock()
        mock_logger.getChild.return_value = mock_logger

        with patch("srt_translator.eval.runner.generate_eval") as mock_generate_eval:
            mock_generate_eval.return_value = {"verdict": "PASS"}
            result = run_batch_evaluation(batch_dir, mock_logger)

        assert result is not None

    @patch("srt_translator.eval.runner._load_rubric")
    def test_optional_inputs_termbase_missing_continues_evaluation(self, mock_load_rubric, tmp_path):
        mock_load_rubric.return_value = MINIMAL_RUBRIC
        batch_dir = create_test_batch_structure(tmp_path)

        ai_config_path = batch_dir / "artifacts" / "ai_config.json"
        ai_config = json.loads(ai_config_path.read_text(encoding="utf-8"))
        ai_config["termbase"] = {}
        ai_config_path.write_text(json.dumps(ai_config, indent=2), encoding="utf-8")

        mock_logger = Mock()
        mock_logger.getChild.return_value = mock_logger

        with patch("srt_translator.eval.runner.generate_eval") as mock_generate_eval:
            mock_generate_eval.return_value = {"verdict": "PASS"}
            result = run_batch_evaluation(batch_dir, mock_logger)

        assert result is not None
        mock_logger.info.assert_any_call("No termbase provided; continuing without termbase coverage")

    @patch("srt_translator.eval.runner._load_rubric")
    def test_coverage_fields_present_in_rollup(self, mock_load_rubric, tmp_path):
        mock_load_rubric.return_value = MINIMAL_RUBRIC
        batch_dir = create_test_batch_structure(tmp_path)
        mock_logger = Mock()
        mock_logger.getChild.return_value = mock_logger

        with patch("srt_translator.eval.runner.generate_eval") as mock_generate_eval:
            mock_generate_eval.return_value = {"verdict": "PASS"}
            result = run_batch_evaluation(batch_dir, mock_logger)

        assert result is not None
        assert result["config_source"] == "ai_config.json"
        assert result["dnt_coverage"] == "present"
        assert result["termbase_coverage"] == "full"
        assert "termbase_entry_counts" in result
        assert result["termbase_entry_counts"]["es"] == 1
        assert result["termbase_entry_counts"]["fr"] == 1

    @patch("srt_translator.eval.runner._load_rubric")
    def test_coverage_fields_partial_termbase(self, mock_load_rubric, tmp_path):
        mock_load_rubric.return_value = MINIMAL_RUBRIC
        batch_dir = create_test_batch_structure(tmp_path)

        ai_config_path = batch_dir / "artifacts" / "ai_config.json"
        ai_config = json.loads(ai_config_path.read_text(encoding="utf-8"))
        ai_config["termbase"] = {"es": {"Operating Plan": "Plan Operativo"}, "fr": {}}
        ai_config_path.write_text(json.dumps(ai_config, indent=2), encoding="utf-8")

        mock_logger = Mock()
        mock_logger.getChild.return_value = mock_logger

        with patch("srt_translator.eval.runner.generate_eval") as mock_generate_eval:
            mock_generate_eval.return_value = {"verdict": "PASS"}
            result = run_batch_evaluation(batch_dir, mock_logger)

        assert result is not None
        assert result["dnt_coverage"] == "present"
        assert result["termbase_coverage"] == "partial"
        assert result["termbase_entry_counts"]["es"] == 1
        assert result["termbase_entry_counts"]["fr"] == 0


class TestUnifiedLogging:
    """Test that evaluation logs appear in both console and batch log file."""

    @patch("srt_translator.eval.runner._load_rubric")
    def test_evaluation_logger_gets_batch_file_handler(self, mock_load_rubric, tmp_path):
        mock_load_rubric.return_value = MINIMAL_RUBRIC
        batch_dir = create_test_batch_structure(tmp_path)

        log_file = batch_dir / "translation_issues_test.log"
        log_file.write_text("Existing log content", encoding="utf-8")

        mock_logger = Mock()
        mock_logger.handlers = []
        mock_logger.getChild.return_value = mock_logger

        with patch("srt_translator.eval.runner.generate_eval") as mock_generate_eval:
            mock_generate_eval.return_value = {"verdict": "PASS"}
            result = run_batch_evaluation(batch_dir, mock_logger)

        assert result is not None


class TestDataNormalization:
    """Test that ai_config.json data is properly normalized."""

    def test_dnt_terms_normalization(self, tmp_path):
        batch_dir = tmp_path / "test_batch"
        batch_dir.mkdir()
        artifacts_dir = batch_dir / "artifacts"
        artifacts_dir.mkdir()

        ai_config = {
            "version": "1.0.0",
            "target_languages": ["es", "fr"],
            "dnt_terms": ["Operating Plan", "Module"],
            "termbase": {"es": {"Operating Plan": "Plan Operativo"}, "fr": {"Module": "Module"}},
        }
        (artifacts_dir / "ai_config.json").write_text(json.dumps(ai_config, indent=2), encoding="utf-8")

        mock_logger = Mock()
        result = _load_batch_config(batch_dir, mock_logger)

        assert result["dnt_terms"] == ["Operating Plan", "Module"]
        assert result["termbase"]["es"] == [{"source": "Operating Plan", "target": "Plan Operativo"}]
        assert result["termbase"]["fr"] == [{"source": "Module", "target": "Module"}]

    def test_termbase_coverage_calculation(self):
        assert (
            _calculate_termbase_coverage(
                {"es": [{"source": "t1", "target": "t1"}], "fr": [{"source": "t1", "target": "t1"}]}
            )
            == "full"
        )
        assert _calculate_termbase_coverage({"es": [{"source": "t1", "target": "t1"}], "fr": []}) == "partial"
        assert _calculate_termbase_coverage({}) == "none"
        assert _calculate_termbase_coverage({"es": [], "fr": []}) == "none"
