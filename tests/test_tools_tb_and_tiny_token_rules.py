from srt_translator.eval.tools import termbase_hit_in_text, untranslated_after_dnt_check


def test_termbase_ok_with_trailing_punct():
    tb = {"OKRs": "OKRs"}  # target-side mapping
    assert termbase_hit_in_text(tb, "… nuestros OKRs? son claros …") is True


def test_untranslated_single_token_okrs_passes():
    # Identical carry-through but tiny/acronym-like => pass
    status, _ = untranslated_after_dnt_check("OKRs?", "OKRs?", rubric={})
    assert status == "pass"
