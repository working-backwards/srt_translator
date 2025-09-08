# tests/test_es_tb_and_tiny_token_rules.py

from srt_translator.eval.tools import termbase_hit_in_text


def test_termbase_ok_with_trailing_punct():
    tb = {"OKRs": "OKRs"}  # target-side mapping
    assert termbase_hit_in_text(tb, "… y nuestros OKRs? son claros …") is True
