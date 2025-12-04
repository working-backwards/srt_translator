#!/usr/bin/env python3
"""
Test that LanguageConfig correctly handles target_batch_size of 0.

This test ensures that the fix for the 'or' logic bug works correctly.
Previously, using 'or' would treat 0 as falsy and fall through to the default,
but explicit 'in' checks correctly honor 0 as a valid value.
"""

import pytest

from srt_translator.core.config.language_config import LanguageConfig


def test_get_target_batch_size_zero():
    """
    Test that a language-specific batch size of 0 is honored.

    This is a regression test for the bug where:
        batch_size = lang_info.get("target_batch_size") or self._defaults.get("target_batch_size")
    would treat 0 as falsy and incorrectly fall through to the default value.

    The correct implementation uses explicit 'in' checks:
        if "target_batch_size" in lang_info:
            return int(lang_info["target_batch_size"])
    """
    # Create a language config with a language that has batch_size = 0
    data = {"languages": {"xx": {"target_batch_size": 0}}, "policy_defaults": {"target_batch_size": 5}}
    cfg = LanguageConfig(data)

    # The language-specific 0 should be honored, not the default of 5
    assert cfg.get_target_batch_size("xx") == 0, (
        "Language-specific batch_size of 0 should be honored, not fall through to default"
    )


def test_get_target_batch_size_fallback():
    """Test that fallback to policy default works when language has no override."""
    data = {
        "languages": {
            "yy": {}  # No batch_size specified
        },
        "policy_defaults": {"target_batch_size": 5},
    }
    cfg = LanguageConfig(data)

    # Should fall back to policy default
    assert cfg.get_target_batch_size("yy") == 5


def test_get_target_batch_size_missing_raises():
    """Test that missing batch_size in both locations raises an error."""
    data = {
        "languages": {"zz": {}},
        "policy_defaults": {},  # No default either
    }
    cfg = LanguageConfig(data)

    # Should raise RuntimeError
    with pytest.raises(RuntimeError, match="Missing target_batch_size"):
        cfg.get_target_batch_size("zz")
