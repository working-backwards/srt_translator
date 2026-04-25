"""Unit tests for failed-language tracking in AI config generation.

Pre-fix, languages whose per-language termbase call failed were silently
dropped: the GUI showed "Generated termbase for 9 languages" with no
indication that 3 of 12 requested languages had been lost. This module
tests the four-part fix:

  - BatchAIConfig has a `failed_languages` field
  - generate_termbase returns (termbase, failed_languages) and tracks
    each of the three failure modes (no language name, empty result,
    exception)
  - The list is empty when all languages succeed
"""

from unittest.mock import MagicMock

from srt_translator.core.config.language_config import LanguageConfig
from srt_translator.gui.ai_config import AIConfigGenerator, BatchAIConfig


def _make_generator():
    """Construct an AIConfigGenerator that won't make real network calls.

    The OpenAI() constructor only stores the API key; it does not make a
    network request. We then mock generate_language_termbase_two_pass on
    the instance so the test controls per-language results.
    """
    lang_cfg = LanguageConfig(
        {
            "languages": {
                "en": {"name": "English"},
                "es": {"name": "Spanish"},
                "fr": {"name": "French"},
                "de": {"name": "German"},
                "ja": {"name": "Japanese"},
            }
        }
    )
    return AIConfigGenerator(api_key="test-key", language_config=lang_cfg)


def test_batch_ai_config_has_failed_languages_field():
    cfg = BatchAIConfig(dnt_terms=[], termbase={})
    assert cfg.failed_languages == []
    cfg2 = BatchAIConfig(dnt_terms=[], termbase={}, failed_languages=["az", "de"])
    assert cfg2.failed_languages == ["az", "de"]


def test_generate_termbase_returns_empty_failures_on_full_success():
    gen = _make_generator()
    gen.generate_language_termbase_two_pass = MagicMock(
        return_value=({"hello": "hola"}, [{"term": "hello", "reason": "x"}])
    )

    termbase, failed = gen.generate_termbase("text", ["es", "fr"])

    assert set(termbase.keys()) == {"es", "fr"}
    assert failed == []


def test_generate_termbase_records_empty_result_as_failure():
    """Inner method returned an empty dict — treat as failure for surfacing."""
    gen = _make_generator()
    # First call (es): empty. Second call (fr): real result.
    gen.generate_language_termbase_two_pass = MagicMock(
        side_effect=[({}, []), ({"hello": "bonjour"}, [{"term": "hello", "reason": "x"}])]
    )

    termbase, failed = gen.generate_termbase("text", ["es", "fr"])

    assert "es" not in termbase
    assert "fr" in termbase
    assert failed == ["es"]


def test_generate_termbase_records_exception_as_failure():
    """Inner method raised — record the language and continue."""
    gen = _make_generator()
    gen.generate_language_termbase_two_pass = MagicMock(
        side_effect=[
            RuntimeError("transient API failure"),
            ({"hello": "hallo"}, [{"term": "hello", "reason": "x"}]),
        ]
    )

    termbase, failed = gen.generate_termbase("text", ["de", "fr"])

    assert "de" not in termbase
    assert "fr" in termbase
    assert failed == ["de"]


def test_generate_termbase_records_multiple_failures_in_request_order():
    """The original bug was 3 of 12 languages timing out. Verify each is
    recorded in the order encountered."""
    gen = _make_generator()
    gen.generate_language_termbase_two_pass = MagicMock(
        side_effect=[
            RuntimeError("timeout 1"),  # es
            ({}, []),  # fr -> empty
            ({"hello": "hallo"}, [{"term": "hello", "reason": "x"}]),  # de -> ok
            RuntimeError("timeout 2"),  # ja
        ]
    )

    termbase, failed = gen.generate_termbase("text", ["es", "fr", "de", "ja"])

    assert set(termbase.keys()) == {"de"}
    assert failed == ["es", "fr", "ja"]


def test_generate_termbase_returns_empty_failures_when_no_valid_languages():
    """If the input has no recognized languages, the early-return path
    should still produce an empty failures list (not None, not crash)."""
    gen = _make_generator()
    gen.generate_language_termbase_two_pass = MagicMock(return_value=({"hello": "hola"}, []))

    termbase, failed = gen.generate_termbase("text", ["unrecognized-code"])

    assert termbase == {}
    assert failed == []
