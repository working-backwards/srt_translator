#!/usr/bin/env python3
"""
Regression tests for DNT placeholder validation.
These tests ensure the validator maintains per-item validation and doesn't regress to global allowlists.
"""

import re
import pytest

from srt_translator.core.translator.translator import validate_placeholders_pair

PH_RE = re.compile(r"__DNT_TERM_(\d+)__")


def test_per_item_placeholder_validation_no_false_invented():
    """Test that correctly preserved placeholders don't trigger false 'invented' warnings."""
    src = [
        "__DNT_TERM_8__: Hi ... __DNT_TERM_8__",
        "I worked at __DNT_TERM_0__ with __DNT_TERM_11__",
    ]
    tgt = [
        "__DNT_TERM_8__: Hola ... __DNT_TERM_8__",
        "Trabajé en __DNT_TERM_0__ con __DNT_TERM_11__",
    ]

    issues = validate_placeholders_pair(src, tgt, PH_RE)
    assert issues == {}, f"Expected no issues, got {issues}"


def test_per_item_placeholder_validation_detects_real_errors():
    """Test that the validator correctly detects actual placeholder mismatches."""
    # Move a placeholder to the wrong item and drop one
    src = [
        "A __DNT_TERM_1__ B",
        "C __DNT_TERM_2__ D",
    ]
    tgt = [
        "A __DNT_TERM_2__ B",  # invented=2, missing=1
        "C D",  # missing=2
    ]

    issues = validate_placeholders_pair(src, tgt, PH_RE)

    # Check first item: invented=2, missing=1
    assert 0 in issues, "Expected issues for item 0"
    assert issues[0]["invented"] == {
        "2"
    }, f"Expected invented={{'2'}}, got {issues[0]['invented']}"
    assert issues[0]["missing"] == {
        "1"
    }, f"Expected missing={{'1'}}, got {issues[0]['missing']}"

    # Check second item: missing=2
    assert 1 in issues, "Expected issues for item 1"
    assert (
        issues[1]["invented"] == set()
    ), f"Expected invented=set(), got {issues[1]['invented']}"
    assert issues[1]["missing"] == {
        "2"
    }, f"Expected missing={{'2'}}, got {issues[1]['missing']}"


def test_per_item_placeholder_validation_function_signature():
    """Test that the function signature remains per-item (no global allowlist parameter)."""
    import inspect

    sig = inspect.signature(validate_placeholders_pair)
    params = list(sig.parameters.keys())

    # Should have exactly 3 parameters: src_items, tgt_items, ph_regex
    assert len(params) == 3, f"Expected 3 parameters, got {len(params)}: {params}"
    assert params == [
        "src_items",
        "tgt_items",
        "ph_regex",
    ], f"Expected specific parameters, got {params}"

    # Should NOT have an allowed_ids parameter
    assert "allowed_ids" not in params, "Function should not have allowed_ids parameter"


def test_per_item_placeholder_validation_empty_placeholders():
    """Test validation with items that have no placeholders."""
    src = ["Hello world", "Goodbye"]
    tgt = ["Hola mundo", "Adiós"]

    issues = validate_placeholders_pair(src, tgt, PH_RE)
    assert (
        issues == {}
    ), f"Expected no issues for items without placeholders, got {issues}"


def test_per_item_placeholder_validation_mixed_content():
    """Test validation with mixed content (some items have placeholders, others don't)."""
    src = [
        "Hello __DNT_TERM_1__ world",
        "No placeholders here",
        "Another __DNT_TERM_2__ example",
    ]
    tgt = [
        "Hola __DNT_TERM_1__ mundo",  # Correct
        "Sin marcadores aquí",  # Correct
        "Otro ejemplo",  # Missing placeholder
    ]

    issues = validate_placeholders_pair(src, tgt, PH_RE)

    # Only item 2 should have issues (missing placeholder)
    assert len(issues) == 1, f"Expected 1 item with issues, got {len(issues)}"
    assert 2 in issues, "Expected issues for item 2"
    assert issues[2]["missing"] == {
        "2"
    }, f"Expected missing={{'2'}}, got {issues[2]['missing']}"
    assert (
        issues[2]["invented"] == set()
    ), f"Expected invented=set(), got {issues[2]['invented']}"


if __name__ == "__main__":
    pytest.main([__file__])
