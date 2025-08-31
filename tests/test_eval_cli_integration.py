# tests/test_eval_cli_integration.py
"""
Integration tests for the evaluation CLI that test actual functionality.
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from srt_translator.eval.cli import main


def create_real_batch_structure(temp_dir: Path) -> Path:
    """Create a real batch structure that would pass actual evaluation."""
    batch_dir = temp_dir / "translation-batch-test"
    batch_dir.mkdir()

    # Create ai_config.json with realistic data
    ai_config = {
        "version": "1.0.0",
        "timestamp": "2025-01-01T00:00:00Z",
        "target_languages": ["es", "fr"],
        "dnt_terms": ["Operating Plan", "Module"],
        "termbase": {
            "es": {"Operating Plan": "Plan Operativo"},
            "fr": {"Module": "Module"},
        },
    }
    (batch_dir / "ai_config.json").write_text(
        json.dumps(ai_config, indent=2), encoding="utf-8"
    )

    # Create originals directory with realistic SRT files
    originals_dir = batch_dir / "originals"
    originals_dir.mkdir()

    # Create multiple SRT files to test batch processing
    srt_files = {
        "video1.srt": """1
00:00:01,000 --> 00:00:04,000
Operating Plan Module 0

2
00:00:05,000 --> 00:00:08,000
This is a test subtitle file.

3
00:00:09,000 --> 00:00:12,000
Another subtitle for testing.""",
        "video2.srt": """1
00:00:01,000 --> 00:00:03,000
Welcome to the presentation.

2
00:00:04,000 --> 00:00:07,000
Today we will discuss the Operating Plan.""",
    }

    for filename, content in srt_files.items():
        (originals_dir / filename).write_text(content, encoding="utf-8")

    # Create target language directories with translated SRT files
    translations = {
        "es": {
            "video1 - ES.srt": """1
00:00:01,000 --> 00:00:04,000
Plan Operativo Módulo 0

2
00:00:05,000 --> 00:00:08,000
Este es un archivo de subtítulos de prueba.

3
00:00:09,000 --> 00:00:12,000
Otro subtítulo para pruebas.""",
            "video2 - ES.srt": """1
00:00:01,000 --> 00:00:03,000
Bienvenido a la presentación.

2
00:00:04,000 --> 00:00:07,000
Hoy discutiremos el Plan Operativo.""",
        },
        "fr": {
            "video1 - FR.srt": """1
00:00:01,000 --> 00:00:04,000
Plan Opérationnel Module 0

2
00:00:05,000 --> 00:00:08,000
Ceci est un fichier de sous-titres de test.

3
00:00:09,000 --> 00:00:12,000
Un autre sous-titre pour les tests.""",
            "video2 - FR.srt": """1
00:00:01,000 --> 00:00:03,000
Bienvenue à la présentation.

2
00:00:04,000 --> 00:00:07,000
Aujourd'hui, nous discuterons du Plan Opérationnel.""",
        },
    }

    for lang, files in translations.items():
        lang_dir = batch_dir / lang
        lang_dir.mkdir()
        for filename, content in files.items():
            (lang_dir / filename).write_text(content, encoding="utf-8")

    return batch_dir


class TestEvalCLIIntegration:
    """Integration tests that test actual evaluation functionality."""

    def test_real_evaluation_run(self, tmp_path):
        """Test that the CLI can actually run evaluation on real batch data."""
        batch_dir = create_real_batch_structure(tmp_path)

        # Run the actual CLI with real data
        with patch("sys.argv", ["st-eval", "--batch-root", str(batch_dir)]):
            result = main()

        # Should succeed
        assert result == 0

        # Check that evaluation artifacts were actually created
        artifacts_dir = batch_dir / "artifacts"
        assert artifacts_dir.exists(), "Artifacts directory should be created"

        # Check for language-specific artifacts
        for lang in ["es", "fr"]:
            lang_artifacts = artifacts_dir / lang

            assert lang_artifacts.exists(), f"Artifacts for {lang} should be created"

            # Check for expected evaluation files (actual evaluation creates these)
            expected_files = [
                f"cps_{lang}_test.csv",
                f"dnt_coverage_{lang}_test.csv",
                f"dnt_summary.json",
                f"eval_summary_{lang}_test.md",
                f"tb_coverage_{lang}_test.csv",
                f"termbase_summary.json",
                f"timing_{lang}_test.csv",
                f"untranslated_{lang}_test.csv",
            ]

            for expected_file in expected_files:
                file_path = lang_artifacts / expected_file
                assert (
                    file_path.exists()
                ), f"Expected file {expected_file} for {lang} should be created"

        # Check for batch-level manifest.json
        batch_manifest = batch_dir / "manifest.json"
        assert batch_manifest.exists(), "Batch manifest.json should be created"

        # Verify batch manifest contains expected data
        manifest_data = json.loads(batch_manifest.read_text(encoding="utf-8"))
        assert "app_version" in manifest_data, "Manifest should contain app_version"
        assert (
            "evaluator_version" in manifest_data
        ), "Manifest should contain evaluator_version"

        # Check for top-level evaluation report
        eval_report = batch_dir / "eval_report.md"
        assert eval_report.exists(), "Evaluation report should be created"

        # Verify report contains expected content
        report_content = eval_report.read_text(encoding="utf-8")
        assert "Evaluation Report" in report_content, "Report should have proper header"
        assert (
            "Spanish" in report_content or "es" in report_content
        ), "Report should mention Spanish"
        assert (
            "French" in report_content or "fr" in report_content
        ), "Report should mention French"

    def test_evaluation_with_issues(self, tmp_path):
        """Test evaluation with files that have actual issues (missing translations, etc.)."""
        batch_dir = create_real_batch_structure(tmp_path)

        # Introduce a real issue: empty translation
        es_dir = batch_dir / "es"
        problematic_srt = """1
00:00:01,000 --> 00:00:04,000
Plan Operativo Módulo 0

2
00:00:05,000 --> 00:00:08,000


3
00:00:09,000 --> 00:00:12,000
Otro subtítulo para pruebas."""

        (es_dir / "video1 - ES.srt").write_text(problematic_srt, encoding="utf-8")

        # Run evaluation
        with patch("sys.argv", ["st-eval", "--batch-root", str(batch_dir)]):
            result = main()

        # Should still succeed (evaluation handles issues gracefully)
        assert result == 0

        # Check that issues are reported
        eval_report = batch_dir / "eval_report.md"
        assert eval_report.exists(), "Evaluation report should be created"

        report_content = eval_report.read_text(encoding="utf-8")
        # The report should mention issues (though exact text depends on evaluation logic)
        assert (
            "missing" in report_content.lower() or "issue" in report_content.lower()
        ), "Report should mention issues"

    def test_evaluation_with_verbose_logging(self, tmp_path):
        """Test evaluation with verbose logging enabled."""
        batch_dir = create_real_batch_structure(tmp_path)

        # Run with verbose logging
        with patch("sys.argv", ["st-eval", "--batch-root", str(batch_dir), "-v"]):
            result = main()

        # Should succeed
        assert result == 0

        # Verify artifacts were created (same as basic test)
        artifacts_dir = batch_dir / "artifacts"
        assert artifacts_dir.exists(), "Artifacts directory should be created"

        # Check that both languages were processed
        for lang in ["es", "fr"]:
            lang_artifacts = artifacts_dir / lang
            assert lang_artifacts.exists(), f"Artifacts for {lang} should be created"

    def test_evaluation_without_rubric(self, tmp_path):
        """Test evaluation behavior when rubric file is missing."""
        batch_dir = create_real_batch_structure(tmp_path)

        # Remove the rubric file to test fallback behavior
        rubric_file = (
            Path(__file__).resolve().parents[2] / "config" / "translation_rubric.yaml"
        )
        if rubric_file.exists():
            # Temporarily rename it
            backup_name = rubric_file.with_suffix(".yaml.backup")
            rubric_file.rename(backup_name)

            try:
                # Run evaluation without rubric
                with patch("sys.argv", ["st-eval", "--batch-root", str(batch_dir)]):
                    result = main()

                # Should handle missing rubric gracefully
                assert result in [0, 3], "Should either succeed or return no rollup"

            finally:
                # Restore rubric file
                backup_name.rename(rubric_file)
        else:
            # If no rubric file exists, skip this test
            pytest.skip("No rubric file found to test missing rubric behavior")
