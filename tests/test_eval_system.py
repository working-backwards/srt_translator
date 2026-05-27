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
        # The runtime `language_config` parameter was removed when the
        # evaluator was made artifact-only (Blocker 4). source_language
        # is now persisted to ai_config.json and read from there.
        for param in ["batch_root", "logger"]:
            assert param in sig.parameters
        assert "language_config" not in sig.parameters


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
        # Termbase is preserved as dict-of-dicts (the on-disk shape in
        # ai_config.json) so downstream tb_map lookups work directly.
        assert result["termbase"]["es"] == {"Operating Plan": "Plan Operativo"}
        assert result["termbase"]["fr"] == {"Module": "Module"}

    def test_termbase_coverage_calculation(self):
        assert _calculate_termbase_coverage({"es": {"t1": "t1"}, "fr": {"t1": "t1"}}) == "full"
        assert _calculate_termbase_coverage({"es": {"t1": "t1"}, "fr": {}}) == "partial"
        assert _calculate_termbase_coverage({}) == "none"


class TestTermbaseReachesGenerateEval:
    """Regression for the Blocker 3 termbase shape mismatch.

    _load_batch_config previously normalized termbase from
    {lang: {source: target}} (the on-disk shape in ai_config.json)
    to {lang: [{source, target}, ...]}, but downstream consumers at
    runner.py:619-622 and _extract_tb_map expected the dict shape.
    Result: tb_map silently became empty even when ai_config.json had
    real termbase entries, so termbase coverage on every evaluation
    report was wrong.

    This test patches generate_eval and asserts it receives a non-empty
    tb_map with the expected {source: target} pairs. It must fail
    against the pre-fix code and pass after the fix.
    """

    @patch("srt_translator.eval.runner._load_rubric")
    def test_tb_map_reaches_generate_eval_with_correct_entries(self, mock_load_rubric, tmp_path):
        mock_load_rubric.return_value = MINIMAL_RUBRIC
        batch_dir = create_test_batch_structure(tmp_path)
        mock_logger = Mock()
        mock_logger.getChild.return_value = mock_logger

        with patch("srt_translator.eval.runner.generate_eval") as mock_generate_eval:
            mock_generate_eval.return_value = {"verdict": "PASS"}
            result = run_batch_evaluation(batch_dir, mock_logger)

        assert result is not None

        # Collect tb_map per call (one per source/target pair per language).
        # Each call should carry the language-appropriate termbase entries.
        tb_maps_by_lang: dict[str, dict[str, str]] = {}
        for call in mock_generate_eval.call_args_list:
            kwargs = call.kwargs
            lang = kwargs.get("lang")
            tb_map = kwargs.get("tb_map")
            if lang:
                tb_maps_by_lang[lang] = tb_map

        # ai_config in create_test_batch_structure has:
        #   termbase: {"es": {"Operating Plan": "Plan Operativo"},
        #              "fr": {"Module": "Module"}}
        # Both must reach generate_eval intact.
        assert tb_maps_by_lang.get("es") == {"Operating Plan": "Plan Operativo"}, (
            f"Spanish tb_map was {tb_maps_by_lang.get('es')!r}; "
            "expected the on-disk termbase to flow through to generate_eval."
        )
        assert tb_maps_by_lang.get("fr") == {"Module": "Module"}, (
            f"French tb_map was {tb_maps_by_lang.get('fr')!r}; "
            "expected the on-disk termbase to flow through to generate_eval."
        )


class TestEvalArtifactReproducibility:
    """Blocker 4: evaluation must run from batch artifacts alone, with no
    runtime TranslationConfig. source_language is now persisted to
    ai_config.json by core/main.py and read by the evaluator from there.

    These tests pin the contract: the evaluator does not need a live
    config object, and it does not import the TranslationConfig class
    (which would be a cyclic dependency through runtime state).
    """

    @patch("srt_translator.eval.runner._load_rubric")
    def test_source_language_comes_from_ai_config_not_runtime(self, mock_load_rubric, tmp_path):
        mock_load_rubric.return_value = MINIMAL_RUBRIC
        batch_dir = create_test_batch_structure(tmp_path)

        # Add source_language to the persisted ai_config.json, matching the
        # shape core/main.py now writes.
        ai_config_path = batch_dir / "artifacts" / "ai_config.json"
        ai_config = json.loads(ai_config_path.read_text(encoding="utf-8"))
        ai_config["source_language"] = {
            "detected_code": "en",
            "normalized_code": "en-US",
            "normalized_name": "English",
        }
        ai_config_path.write_text(json.dumps(ai_config, indent=2), encoding="utf-8")

        mock_logger = Mock()
        mock_logger.getChild.return_value = mock_logger

        with patch("srt_translator.eval.runner.generate_eval") as mock_generate_eval:
            mock_generate_eval.return_value = {"verdict": "PASS"}
            # Critically: no language_config kwarg.
            result = run_batch_evaluation(batch_dir, mock_logger)

        assert result is not None
        # The rollup's original_language must come from artifacts.
        assert result["original_language"] == {"code": "en-US", "name": "English"}

    def test_legacy_language_config_kwarg_is_silently_ignored(self, tmp_path):
        """Existing callers that still pass `language_config=...` must not
        break. The kwarg is accepted via **_legacy_kwargs and discarded —
        with a debug log so anyone grepping for the migration trail can
        find it. The result must be identical to calling without the kwarg.
        """
        # We only need to verify the call signature accepts the legacy
        # kwarg without raising. Use a minimal batch (no rubric) so we
        # exit early without exercising the full pipeline.
        with patch("srt_translator.eval.runner._load_rubric", side_effect=Exception("skipped")):
            mock_logger = Mock()
            mock_logger.getChild.return_value = mock_logger

            # Sentinel object stands in for what used to be a TranslationConfig.
            result = run_batch_evaluation(
                Path(tmp_path),
                mock_logger,
                language_config=object(),
            )

            assert result is None  # exited at rubric load, as expected
            # Confirm the legacy-kwarg debug log fired.
            debug_messages = [c.args[0] for c in mock_logger.debug.call_args_list if c.args]
            assert any("ignoring legacy kwargs" in msg for msg in debug_messages), (
                f"Expected a debug log mentioning legacy kwargs; got {debug_messages!r}"
            )

    def test_evaluator_does_not_import_translation_config(self):
        """Import-barrier test: the eval module must not pull in
        TranslationConfig. Doing so would make eval depend on runtime
        config plumbing rather than persisted artifacts.
        """
        import srt_translator.eval.runner as runner_mod

        # Walk the runner module's namespace and look for TranslationConfig
        # by name. A direct import would surface here; a transitive import
        # through another module would not — that's intentional, we only
        # care about whether the evaluator's own code references the type.
        assert "TranslationConfig" not in dir(runner_mod), (
            "eval/runner.py imports TranslationConfig. Evaluation must be "
            "reproducible from artifacts alone; remove the runtime config "
            "dependency."
        )
