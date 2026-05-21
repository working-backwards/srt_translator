"""Regression tests for two public claims made about the OpenAI API key:

  1. The key is never written to log files or terminal output.
  2. The key is never written to translated SRT files, evaluation
     reports, batch artifacts (ai_config.json, manifest.json, dnt.json,
     termbase.json), or any other file the app produces.

Both claims appear in docs/user-guide/gui-manual.md ("API Key Storage"
section) and .github/SECURITY.md ("API Key Handling" bullet). They were
audited manually when the docs were rewritten in 2026-05-21 to remove
the inaccurate "secure storage" claim. These tests guard against future
code paths quietly violating either claim — e.g., a debug log that
interpolates the config object, or a manifest field that someone adds
without thinking about secret hygiene.

A distinctive sentinel value is used so any leak shows up unambiguously
in test failure output (no false positives from generic test keys).
"""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

from srt_translator.core.config.models import LogMode, TranslationConfig
from srt_translator.core.main import translate_srt_files

SENTINEL_API_KEY = "sk-test-SENTINEL-NEVER-LEAK-2026-05-21"


def _policies() -> dict:
    return {
        "policy_defaults": {
            "target_batch_size": 5,
            "max_batch_size": 10,
            "allow_placeholder_apostrophe": True,
        },
        "languages": {
            "es": {"name": "Spanish", "cps_cap": 20},
            "fr": {"name": "French", "cps_cap": 20},
        },
    }


def _make_config(tmp_path: Path) -> TranslationConfig:
    src = tmp_path / "input.srt"
    src.write_text(
        "1\n00:00:01,000 --> 00:00:02,000\nHello\n\n",
        encoding="utf-8",
    )
    out = tmp_path / "out"
    out.mkdir()
    return TranslationConfig(
        target_languages={"Spanish": "es", "French": "fr"},
        output_directory=out,
        api_key=SENTINEL_API_KEY,
        log_mode=LogMode.STANDARD,
        mode="GUI",
        language_policies=_policies(),
        files=(src,),
    )


def _make_translator_factory():
    """Build a SRTTranslator factory whose translate_file writes a stub SRT
    so the manifest/audit writers run normally."""

    def factory(**_kwargs):
        inst = MagicMock()

        def translate_file(*, input_filepath: str, output_filepath: str, target_lang: str):
            Path(output_filepath).parent.mkdir(parents=True, exist_ok=True)
            Path(output_filepath).write_text(
                "1\n00:00:01,000 --> 00:00:02,000\nHola\n\n",
                encoding="utf-8",
            )

        inst.translate_file.side_effect = translate_file
        return inst

    return factory


def test_api_key_never_appears_in_logs(tmp_path, caplog):
    """Run a translation and assert the sentinel API key does not appear
    in any captured log record (message, args, or formatted output).
    """
    cfg = _make_config(tmp_path)

    with (
        caplog.at_level(logging.DEBUG),
        patch(
            "srt_translator.core.main.SRTTranslator",
            side_effect=_make_translator_factory(),
        ),
    ):
        translate_srt_files(file_paths=[str(next(iter(cfg.files)))], config=cfg)

    # Check every angle the key could surface through:
    for record in caplog.records:
        assert SENTINEL_API_KEY not in record.getMessage(), f"API key leaked into log message: {record.getMessage()!r}"
        # record.args may be a tuple of arguments yet-to-be-formatted; stringify them.
        for arg in record.args or ():
            assert SENTINEL_API_KEY not in str(arg), f"API key leaked into log args: {arg!r}"
        if record.exc_info:
            assert SENTINEL_API_KEY not in str(record.exc_info), "API key leaked into exception info"

    # And the consolidated capture text as a belt-and-braces check.
    assert SENTINEL_API_KEY not in caplog.text


def test_api_key_never_appears_in_batch_artifacts(tmp_path):
    """Run a translation and assert no file in the produced batch
    directory contains the sentinel API key. Covers ai_config.json,
    manifest.json, dnt.json, termbase.json, translated SRTs, plus any
    future artifact that gets written under output_directory.
    """
    cfg = _make_config(tmp_path)

    with patch(
        "srt_translator.core.main.SRTTranslator",
        side_effect=_make_translator_factory(),
    ):
        translate_srt_files(file_paths=[str(next(iter(cfg.files)))], config=cfg)

    output_dir = cfg.output_directory
    leaks: list[str] = []
    for path in output_dir.rglob("*"):
        if not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # Binary file (unlikely but possible — e.g. cached images in eval
            # reports). Fall back to bytes search.
            content_bytes = path.read_bytes()
            if SENTINEL_API_KEY.encode("utf-8") in content_bytes:
                leaks.append(str(path.relative_to(output_dir)))
            continue
        if SENTINEL_API_KEY in content:
            leaks.append(str(path.relative_to(output_dir)))

    assert not leaks, (
        "API key leaked into the following batch artifacts:\n  - "
        + "\n  - ".join(leaks)
        + "\n\nReview the writer of each file and ensure config.api_key is not "
        "serialized."
    )
