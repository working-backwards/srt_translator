"""Unit tests for _is_invalid_translation in srt_translator.core.translator.translator.

Bug history (2026-04-26): A real translation batch produced empty subtitles
in 8 of 12 target languages for a single cue whose source was the bare year
"2023." (an awkwardly split sentence in the original SRT). The shape-lock
validator's regex `[\\W\\d_]+` matched both source and target, treating the
correct identity translation as invalid. The model retried 2x, still got
the same correct answer, and the cue was abandoned.

The fix: when source is itself punctuation/digit-only (years, dollar
amounts, ellipses, chapter markers), accepting an identity translation is
correct, not a failure.
"""

from srt_translator.core.translator.translator import _is_invalid_translation


def test_empty_text_is_invalid():
    assert _is_invalid_translation("") is True
    assert _is_invalid_translation("", src="hello") is True


def test_whitespace_only_is_invalid():
    assert _is_invalid_translation("   ") is True
    assert _is_invalid_translation("\t\n", src="hello") is True


def test_real_text_is_valid():
    """Letters present → never matches the punctuation/digit regex."""
    assert _is_invalid_translation("hello") is False
    assert _is_invalid_translation("Bonjour, monde.", src="Hello, world.") is False


def test_punctuation_only_without_src_is_invalid():
    """Backward-compatible: omitting src preserves the original strict behavior."""
    assert _is_invalid_translation("...") is True
    assert _is_invalid_translation("2023.") is True
    assert _is_invalid_translation("$50,000.") is True


def test_punctuation_only_matches_src_is_valid():
    """Regression: identity translation of non-linguistic source is correct.

    These are the exact cases that produced today's empty cues across
    8 languages."""
    assert _is_invalid_translation("2023.", src="2023.") is False
    assert _is_invalid_translation("$50,000.", src="$50,000.") is False
    assert _is_invalid_translation("...", src="...") is False
    assert _is_invalid_translation("38%", src="38%") is False


def test_punctuation_only_differs_from_src_is_invalid():
    """Real model failures still get caught: dropped content where output
    is just trailing punctuation but source had real text."""
    assert _is_invalid_translation(".", src="2023.") is True
    assert _is_invalid_translation("2023.", src="In the year 2023.") is True
    assert _is_invalid_translation("...", src="And then we waited.") is True


def test_identity_match_strips_whitespace():
    """Trailing/leading whitespace on either side shouldn't defeat identity match."""
    assert _is_invalid_translation("  2023.  ", src="2023.") is False
    assert _is_invalid_translation("2023.", src="  2023.  ") is False


def test_partial_drop_is_still_invalid():
    """If model dropped even one character of non-linguistic source, treat
    it as failure — conservative on purpose."""
    assert _is_invalid_translation("2023", src="2023.") is True
    assert _is_invalid_translation("2023.", src="2023") is True
