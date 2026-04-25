"""Unit tests for _build_pass_assignment in srt_translator.gui.ai_config.

Pre-fix, the per-language termbase loop re-categorized terms by searching
the `reason` text for English keywords like "confusable" or "ambiguous".
For target languages where the model wrote reasons in the target language
itself (e.g. zh-Hans returning Chinese reasons), no English keyword
matched and every term collapsed into Pass 1 — making the "Pass 2: 0"
diagnostic count misleading.

The fix: trust the model's own pass categorization from the response.
This module tests the helper that builds that lookup.
"""

from srt_translator.gui.ai_config import _build_pass_assignment


def test_assigns_pass1_terms_to_pass1():
    p1 = [{"term": "input metrics", "reason": "core concept"}]
    p2 = []
    assignment = _build_pass_assignment(p1, p2)
    assert assignment == {"input metrics": "pass1"}


def test_assigns_pass2_terms_to_pass2():
    p1 = []
    p2 = [{"term": "fitness function", "reason": "easy to misread"}]
    assignment = _build_pass_assignment(p1, p2)
    assert assignment == {"fitness function": "pass2"}


def test_combines_both_passes():
    p1 = [{"term": "input metrics", "reason": "core"}]
    p2 = [{"term": "fitness function", "reason": "ambiguous"}]
    assignment = _build_pass_assignment(p1, p2)
    assert assignment == {"input metrics": "pass1", "fitness function": "pass2"}


def test_pass2_wins_on_duplicate():
    """If a term appears in both arrays, pass2 wins — it's the more
    specific category, so reporting it as confusable is more useful
    than reporting it as topic-critical."""
    p1 = [{"term": "leading indicators", "reason": "topic-critical"}]
    p2 = [{"term": "leading indicators", "reason": "ambiguous"}]
    assignment = _build_pass_assignment(p1, p2)
    assert assignment == {"leading indicators": "pass2"}


def test_lookup_is_case_insensitive_via_lowering():
    """Keys are lowercased so the categorize loop can do
    pass_assignment.get(term.lower())."""
    p1 = [{"term": "Input Metrics", "reason": "x"}]
    p2 = []
    assignment = _build_pass_assignment(p1, p2)
    assert assignment == {"input metrics": "pass1"}
    # Caller does .get(term.lower())
    assert assignment.get("INPUT METRICS".lower()) == "pass1"
    assert assignment.get("Input Metrics".lower()) == "pass1"


def test_strips_whitespace_from_keys():
    p1 = [{"term": "  input metrics  ", "reason": "x"}]
    p2 = []
    assignment = _build_pass_assignment(p1, p2)
    assert assignment == {"input metrics": "pass1"}


def test_skips_empty_or_missing_terms():
    p1 = [
        {"term": "", "reason": "no term"},
        {"term": "  ", "reason": "whitespace only"},
        {"reason": "no term key"},
        {"term": "valid", "reason": "x"},
    ]
    p2 = []
    assignment = _build_pass_assignment(p1, p2)
    assert assignment == {"valid": "pass1"}


def test_skips_non_dict_items():
    """Defensive: model might return strings or None inside the array."""
    p1 = ["not a dict", None, 42, {"term": "real", "reason": "x"}]
    p2 = []
    assignment = _build_pass_assignment(p1, p2)  # type: ignore[arg-type]
    assert assignment == {"real": "pass1"}


def test_handles_none_or_empty_arrays():
    assert _build_pass_assignment([], []) == {}
    assert _build_pass_assignment(None, None) == {}  # type: ignore[arg-type]
    assert _build_pass_assignment(None, [{"term": "x", "reason": "y"}]) == {"x": "pass2"}  # type: ignore[arg-type]


def test_zh_hans_chinese_reason_categorizes_correctly():
    """Regression test for the actual bug. With a Chinese-reason
    response the OLD code (English keyword match) would put every
    term in pass1. The new helper preserves the model's own
    assignment regardless of reason language."""
    p1 = [{"term": "input metrics", "reason": "核心业务概念，若译得不准确会模糊可控性"}]
    p2 = [{"term": "fitness function", "reason": "技术/评估术语，易被误译为一般'适配'词"}]
    assignment = _build_pass_assignment(p1, p2)
    # Both reasons are in Chinese; old code would have put both in pass1.
    assert assignment["input metrics"] == "pass1"
    assert assignment["fitness function"] == "pass2"
