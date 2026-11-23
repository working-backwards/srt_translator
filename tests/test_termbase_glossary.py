"""Unit tests for the termbase pipeline: validation, TermHandler, prompt glossary, fallback."""

from __future__ import annotations

import inspect

from srt_translator.core.translator.term_handler import TermHandler
from srt_translator.core.translator.translator import SRTTranslator

# --- TermHandler restore ---------------------------------------------------------------


def test_restore_all_restores_dnt_and_leaves_english_terms_alone() -> None:
    th = TermHandler(dnt_terms=["FastTrack"], termbase={"share price": "股价"})
    assert th.apply_all("FastTrack and share price") == "__DNT_TERM_0__ and 股价"
    # A model reply that still contains an English termbase key is left as-is.
    assert th.restore_all("__DNT_TERM_0__ share price") == "FastTrack share price"


def test_restore_termbase_is_gone() -> None:
    assert not hasattr(TermHandler, "restore_termbase")


def test_translator_has_no_global_termbase_fallback_flag() -> None:
    assert "allow_global_termbase_fallback" not in inspect.signature(SRTTranslator.__init__).parameters
