"""Unit tests for _filter_termbase_response in srt_translator.gui.ai_config.

The filter sanitizes raw termbase dicts returned by the model. Without it,
malformed responses (e.g. Japanese-source-key bug) reach the saved termbase
file and produce dead entries that never match English source text.
"""

from srt_translator.gui.ai_config import _filter_termbase_response


def _terms(*items):
    """Shorthand: build the pass1+pass2 list of {term, reason} dicts."""
    return [{"term": t, "reason": "x"} for t in items]


def test_passes_well_formed_entries_through():
    tb = {"two pizza teams": "2ピザチーム", "input metrics": "入力指標"}
    extracted = _terms("two pizza teams", "input metrics")
    filtered, drops = _filter_termbase_response(tb, extracted, dnt_set=set())
    assert filtered == {"two pizza teams": "2ピザチーム", "input metrics": "入力指標"}
    assert sum(drops.values()) == 0


def test_drops_self_referential_entry():
    """Reproduces the Japanese-source-key bug: model emits target=target."""
    tb = {"2ピザチーム": "2ピザチーム", "two pizza teams": "2ピザチーム"}
    # Note: the model put the Japanese form in pass1 too, so unknown-key
    # filter alone wouldn't catch this — the self-ref filter is needed.
    extracted = _terms("two pizza teams", "2ピザチーム")
    filtered, drops = _filter_termbase_response(tb, extracted, dnt_set=set())
    assert filtered == {"two pizza teams": "2ピザチーム"}
    assert drops["self_reference"] == 1


def test_drops_unknown_key_not_in_pass_terms():
    """Model invented a termbase entry for a term it never extracted."""
    tb = {"input metrics": "入力指標", "hallucinated term": "妄想語"}
    extracted = _terms("input metrics")
    filtered, drops = _filter_termbase_response(tb, extracted, dnt_set=set())
    assert filtered == {"input metrics": "入力指標"}
    assert drops["unknown_key"] == 1


def test_drops_dnt_collision():
    tb = {"WBR": "WBR", "weekly business review": "週次ビジネスレビュー"}
    # Note: "WBR" is a DNT collision AND a self-reference. DNT check fires first.
    extracted = _terms("WBR", "weekly business review")
    filtered, drops = _filter_termbase_response(tb, extracted, dnt_set={"wbr"})
    assert filtered == {"weekly business review": "週次ビジネスレビュー"}
    assert drops["dnt_collision"] == 1
    assert drops["self_reference"] == 0  # DNT was caught first, not double-counted


def test_unknown_key_filter_skipped_when_extracted_is_empty():
    """If extracted is empty, we have no source-of-truth, so don't drop on
    unknown-key grounds. Other filters still apply.
    """
    tb = {"some term": "translated"}
    filtered, drops = _filter_termbase_response(tb, extracted=[], dnt_set=set())
    assert filtered == {"some term": "translated"}
    assert drops["unknown_key"] == 0


def test_skips_empty_keys_and_values_silently():
    tb = {"": "x", "y": "", "  ": "z", "valid": "ok"}
    extracted = _terms("valid", "y")
    filtered, drops = _filter_termbase_response(tb, extracted, dnt_set=set())
    assert filtered == {"valid": "ok"}
    # Empty entries don't count toward drops — they're not "malformed",
    # they're just empty.
    assert sum(drops.values()) == 0


def test_handles_non_dict_input():
    """If the model returns something other than a dict (None, list, str),
    the helper should return an empty dict rather than crash."""
    for bad in (None, [], "not a dict", 42):
        filtered, drops = _filter_termbase_response(bad, _terms("x"), dnt_set=set())
        assert filtered == {}
        assert sum(drops.values()) == 0


def test_case_insensitive_matching_for_filters():
    """Self-ref and unknown-key checks are case-insensitive on the key."""
    tb = {
        "Input Metrics": "入力指標",  # case mismatch with extracted — should still pass
        "Two Pizza Teams": "two pizza teams",  # self-ref despite case difference
    }
    extracted = _terms("input metrics", "two pizza teams")
    filtered, drops = _filter_termbase_response(tb, extracted, dnt_set=set())
    assert filtered == {"Input Metrics": "入力指標"}
    assert drops["self_reference"] == 1


def test_strips_whitespace_from_keys_and_values():
    tb = {"  input metrics  ": "  入力指標  "}
    extracted = _terms("input metrics")
    filtered, drops = _filter_termbase_response(tb, extracted, dnt_set=set())
    assert filtered == {"input metrics": "入力指標"}


def test_japanese_bug_reproduction_real_response():
    """End-to-end check using the actual malformed response observed in
    production (subset of the user's exported termbase): 7 self-referential
    Japanese entries among 26 total. After the filter, the 7 should be gone.
    """
    tb = {
        "input metrics": "入力指標",
        "output metrics": "出力指標",
        "controllable input metrics": "制御可能な入力指標",
        "Weekly Business Review": "週次ビジネスレビュー",
        "two pizza teams": "2ピザチーム",
        "four blocker": "4ブロッカー",
        "6-12 report": "6-12レポート",
        "root mean square error": "二乗平均平方根誤差",
        "fitness function": "評価関数",
        "top percentile": "上位パーセンタイル",
        # The 7 malformed self-references:
        "2ピザチーム": "2ピザチーム",
        "4ブロッカー": "4ブロッカー",
        "6-12レポート": "6-12レポート",
        "二乗平均平方根誤差": "二乗平均平方根誤差",
        "評価関数": "評価関数",
        "上位パーセンタイル": "上位パーセンタイル",
        "販売・オペレーション計画（S&OP）": "販売・オペレーション計画（S&OP）",
    }
    # Model included the Japanese forms in its own pass1 list, mirroring
    # the real bug — so unknown-key filter alone wouldn't catch them.
    extracted = _terms(
        "input metrics",
        "output metrics",
        "controllable input metrics",
        "Weekly Business Review",
        "two pizza teams",
        "four blocker",
        "6-12 report",
        "root mean square error",
        "fitness function",
        "top percentile",
        "2ピザチーム",
        "4ブロッカー",
        "6-12レポート",
        "二乗平均平方根誤差",
        "評価関数",
        "上位パーセンタイル",
        "販売・オペレーション計画（S&OP）",
    )
    filtered, drops = _filter_termbase_response(tb, extracted, dnt_set=set())
    assert len(filtered) == 10
    assert drops["self_reference"] == 7
    # No legitimate entry was dropped:
    assert filtered["two pizza teams"] == "2ピザチーム"
    assert filtered["four blocker"] == "4ブロッカー"
