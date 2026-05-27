"""Unit tests for _filter_termbase_response in srt_translator.gui.ai_config.

The filter sanitizes raw termbase dicts returned by the model. Without it,
malformed responses (e.g. Japanese-source-key bug, model over-generation,
case-only duplicates) reach the saved termbase file and produce dead entries
that never match source text — or worse, silently orphan one of two
conflicting translations.
"""

from srt_translator.gui.ai_config import _filter_termbase_response


def _terms(*items):
    """Shorthand: build the allowed-terms list of {term, reason} dicts."""
    return [{"term": t, "reason": "x"} for t in items]


def test_passes_well_formed_entries_through():
    tb = {"two pizza teams": "2ピザチーム", "input metrics": "入力指標"}
    allowed = _terms("two pizza teams", "input metrics")
    filtered, drops = _filter_termbase_response(tb, allowed, dnt_set=set())
    assert filtered == {"two pizza teams": "2ピザチーム", "input metrics": "入力指標"}
    assert sum(drops.values()) == 0


def test_drops_self_referential_entry():
    """Reproduces the Japanese-source-key bug: model emits target=target."""
    tb = {"2ピザチーム": "2ピザチーム", "two pizza teams": "2ピザチーム"}
    # Note: the model put the Japanese form in pass1 too, so unknown-key
    # filter alone wouldn't catch this — the self-ref filter is needed.
    allowed = _terms("two pizza teams", "2ピザチーム")
    filtered, drops = _filter_termbase_response(tb, allowed, dnt_set=set())
    assert filtered == {"two pizza teams": "2ピザチーム"}
    assert drops["self_reference"] == 1


def test_drops_unknown_key_not_in_allowed_terms():
    """Model emitted a termbase entry for a term not in the kept set."""
    tb = {"input metrics": "入力指標", "hallucinated term": "妄想語"}
    allowed = _terms("input metrics")
    filtered, drops = _filter_termbase_response(tb, allowed, dnt_set=set())
    assert filtered == {"input metrics": "入力指標"}
    assert drops["unknown_key"] == 1


def test_drops_dnt_collision():
    tb = {"WBR": "WBR", "weekly business review": "週次ビジネスレビュー"}
    # Note: "WBR" is a DNT collision AND a self-reference. DNT check fires first.
    allowed = _terms("WBR", "weekly business review")
    filtered, drops = _filter_termbase_response(tb, allowed, dnt_set={"wbr"})
    assert filtered == {"weekly business review": "週次ビジネスレビュー"}
    assert drops["dnt_collision"] == 1
    assert drops["self_reference"] == 0  # DNT was caught first, not double-counted


def test_unknown_key_filter_skipped_when_allowed_is_empty():
    """If allowed_terms is empty, we have no source-of-truth, so don't drop on
    unknown-key grounds. Other filters still apply.
    """
    tb = {"some term": "translated"}
    filtered, drops = _filter_termbase_response(tb, allowed_terms=[], dnt_set=set())
    assert filtered == {"some term": "translated"}
    assert drops["unknown_key"] == 0


def test_skips_empty_keys_and_values_silently():
    tb = {"": "x", "y": "", "  ": "z", "valid": "ok"}
    allowed = _terms("valid", "y")
    filtered, drops = _filter_termbase_response(tb, allowed, dnt_set=set())
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


def test_case_insensitive_matching_and_canonical_normalization():
    """Self-ref and unknown-key checks are case-insensitive on the key.

    Surviving keys are normalized to the canonical surface form from
    allowed_terms — the model's casing on tb keys is discarded so post-fill's
    case-sensitive lookup against cleaned_terms doesn't miss.
    """
    tb = {
        "Input Metrics": "入力指標",  # case mismatch with allowed — should still pass, normalized
        "Two Pizza Teams": "two pizza teams",  # self-ref despite case difference
    }
    allowed = _terms("input metrics", "two pizza teams")
    filtered, drops = _filter_termbase_response(tb, allowed, dnt_set=set())
    # Key normalized to canonical "input metrics", not the model's "Input Metrics".
    assert filtered == {"input metrics": "入力指標"}
    assert drops["self_reference"] == 1


def test_strips_whitespace_from_keys_and_values():
    tb = {"  input metrics  ": "  入力指標  "}
    allowed = _terms("input metrics")
    filtered, drops = _filter_termbase_response(tb, allowed, dnt_set=set())
    assert filtered == {"input metrics": "入力指標"}


def test_drops_case_only_duplicates_keeping_first():
    """When the model emits the same surface form in multiple casings, keep
    only the first-iterated. TermHandler compiles re.IGNORECASE patterns, so
    case variants are functionally one entry — duplicates produce dead
    patterns and (when translations differ) silently orphan one of them.

    The surviving key is normalized to the canonical surface form from
    allowed_terms, not the model's first-iterated casing.
    """
    tb = {
        "Fulfillment center": "仓库",
        "fulfillment center": "仓库",  # same translation, redundant
        "FULFILLMENT CENTER": "仓库",  # third casing, also redundant
    }
    allowed = _terms("fulfillment center")
    filtered, drops = _filter_termbase_response(tb, allowed, dnt_set=set())
    # Normalized to canonical "fulfillment center" from allowed, not the
    # model's first-iterated "Fulfillment center".
    assert filtered == {"fulfillment center": "仓库"}
    assert drops["case_duplicate"] == 2


def test_case_duplicates_with_conflicting_translations_keep_first_drop_rest():
    """Real bug from a zh-Hans run: same key in two casings with different
    translations. Without dedup, both reach TermHandler, but only one
    pattern's substitutions apply at translate-time — the other is silently
    orphaned. Surface that here so the saved JSON matches actual behavior.
    """
    tb = {
        "Single-threaded Leader": "单一负责人",
        "single-threaded leader": "专责负责人",  # conflicting translation, silently orphaned at translate-time
    }
    allowed = _terms("single-threaded leader")
    filtered, drops = _filter_termbase_response(tb, allowed, dnt_set=set())
    # First-iterated *value* wins; key normalized to canonical "single-threaded leader".
    assert filtered == {"single-threaded leader": "单一负责人"}
    assert drops["case_duplicate"] == 1


def test_canonical_normalization_makes_post_fill_lookup_succeed():
    """Regression for the post-fill case-mismatch bug. cleaned_terms uses
    first-seen-wins dedup (lowercase here); the model's tb returned the same
    term in capitalized form. Without normalization the saved tb_dict key
    would be the model's casing, post-fill's `tb_dict.get("fulfillment
    center")` would miss, and the saved JSON would end up with both casings.
    """
    tb = {"Fulfillment Center": "仓库"}  # model's casing
    allowed = _terms("fulfillment center")  # cleaned_terms's casing
    filtered, _drops = _filter_termbase_response(tb, allowed, dnt_set=set())
    # Saved key matches cleaned_terms exactly so post-fill's case-sensitive
    # lookup succeeds.
    assert filtered == {"fulfillment center": "仓库"}


def test_case_duplicate_filter_does_not_fire_on_morphological_variants():
    """Plurals and other morphological variants are NOT case duplicates —
    they're distinct surface forms with different lowercased keys, and
    TermHandler does no stemming. They must remain in the termbase to match
    at translate-time.
    """
    tb = {
        "fulfillment center": "仓库",
        "fulfillment centers": "仓库",  # plural; different lowercased key
        "category manager": "品类经理",
        "category managers": "品类经理",  # plural
    }
    allowed = _terms("fulfillment center", "fulfillment centers", "category manager", "category managers")
    filtered, drops = _filter_termbase_response(tb, allowed, dnt_set=set())
    assert filtered == tb
    assert drops["case_duplicate"] == 0


def test_unknown_key_filter_enforces_size_cap_when_allowed_is_capped():
    """Regression for the soft_hi leak: when the model over-generates and
    the caller passes the post-cap cleaned_terms list (instead of the full
    pass1+pass2 response), the extra entries get dropped as unknown keys.
    """
    # Model returned 5 termbase entries, but only 3 survived the soft cap.
    tb = {
        "term one": "翻译一",
        "term two": "翻译二",
        "term three": "翻译三",
        "term four": "翻译四",  # over the cap
        "term five": "翻译五",  # over the cap
    }
    cleaned_terms = _terms("term one", "term two", "term three")
    filtered, drops = _filter_termbase_response(tb, cleaned_terms, dnt_set=set())
    assert filtered == {"term one": "翻译一", "term two": "翻译二", "term three": "翻译三"}
    assert drops["unknown_key"] == 2


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
    allowed = _terms(
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
    filtered, drops = _filter_termbase_response(tb, allowed, dnt_set=set())
    assert len(filtered) == 10
    assert drops["self_reference"] == 7
    # No legitimate entry was dropped:
    assert filtered["two pizza teams"] == "2ピザチーム"
    assert filtered["four blocker"] == "4ブロッカー"
