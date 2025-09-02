# tests/test_untranslated_after_dnt_rule.py
from typing import Any

from srt_translator.eval.tools import strip_terms, untranslated_after_dnt_check

DNT = ["Amazon", "flywheel"]
RUBRIC: dict[str, Any] = {}  # use defaults (short-cognate ignore, acronym handling, etc.)


def test_dnt_only_cue_passes():
    # Source is only a DNT term (+ punct). Nothing remains to translate.
    src = "Amazon."
    tgt = "Amazon."
    src_after = strip_terms(src, DNT)  # "."  (ignored for eval)
    status, _ = untranslated_after_dnt_check(src_after, tgt, RUBRIC)
    assert status == "pass"


def test_numbers_only_cue_passes():
    # Numbers/punctuation-only should not be flagged as untranslated.
    src = "2001."
    tgt = "2001."
    src_after = strip_terms(src, DNT)  # still "2001."
    status, _ = untranslated_after_dnt_check(src_after, tgt, RUBRIC)
    assert status == "pass"


def test_mixed_text_left_untranslated_fails():
    # Here is the REAL fail case for this rule:
    # After removing DNT from the SOURCE, the remainder equals the TARGET.
    # That means the non-DNT remainder was left in the source language.
    src = "The Amazon flywheel is spinning."
    tgt = "The is spinning."  # untranslated remainder
    src_after = strip_terms(src, DNT)  # "The  is spinning."
    status, _ = untranslated_after_dnt_check(src_after, tgt, RUBRIC)
    assert status == "fail"


def test_mixed_text_translated_passes():
    # If the target is a translation (different from source remainder),
    # it should NOT be flagged.
    src = "The Amazon flywheel is spinning."
    tgt = "الدولاب يدور."  # translated target
    src_after = strip_terms(src, DNT)  # "The  is spinning."
    status, _ = untranslated_after_dnt_check(src_after, tgt, RUBRIC)
    assert status == "pass"
