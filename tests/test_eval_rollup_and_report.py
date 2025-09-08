# tests/test_eval_rollup_and_report.py
from srt_translator.eval.tools import Cue, classify_empty_target_rollup, normalize_for_empty_check


def cue(i, txt):  # helper for brevity
    return Cue(index=i, start_ms=0, end_ms=1000, text=txt)


def test_benign_rollup_full_sentence_az():
    # en 23+24 merged into az 23; az 24 blank
    lang = "az"
    dnt = []
    tb_map = {}
    source = [
        cue(23, "First, after debates, we had clarity."),
        cue(24, "First, after debates, we had clarity."),
    ]
    target = [cue(23, "Birincisi, müzakirələrdən sonra aydınlıq əldə etdik."), cue(24, "")]

    # Debug: Let's see what the classifier is calculating
    from srt_translator.eval.tools import median_expansion_ratio, strip_terms

    src_after_all = [strip_terms(c.text, dnt) for c in source]
    tgt_norm_all = [normalize_for_empty_check(c.text) for c in target]
    R = median_expansion_ratio(src_after_all, tgt_norm_all)

    print(f"DEBUG: Source after DNT: {src_after_all}")
    print(f"DEBUG: Target normalized: {tgt_norm_all}")
    print(f"DEBUG: Expansion ratio R: {R}")
    print(f"DEBUG: Source cue 24 length: {len(src_after_all[1])}")
    print(f"DEBUG: Target cue 23 length: {len(tgt_norm_all[0])}")

    cls, reason = classify_empty_target_rollup(
        lang=lang,
        cue_index=1,
        source_cues=source,
        target_cues=target,
        do_not_translate_terms=dnt,
        termbase_map_for_lang=tb_map,
    )
    print(f"DEBUG: Classifier returned: {cls} - {reason}")
    print(f"DEBUG: Source cue 24 text: '{source[1].text}'")
    print(f"DEBUG: Target cue 24 text: '{target[1].text}'")
    print(f"DEBUG: Target cue 23 text: '{target[0].text}'")
    assert cls != "MISSING"  # treat as rolled-up (benign/suspect), hence not error


def test_tiny_remainder_ar():
    lang = "ar"
    dnt = []
    tb_map = {}
    source = [cue(45, "with results from the prior year,"), cue(46, "year.")]
    target = [cue(45, "مع نتائج من العام السابق،"), cue(46, "")]
    cls, _ = classify_empty_target_rollup(
        lang=lang,
        cue_index=1,
        source_cues=source,
        target_cues=target,
        do_not_translate_terms=dnt,
        termbase_map_for_lang=tb_map,
    )
    assert cls != "MISSING"  # tiny tail merges to previous: not an error


# test_status_label_uses_error_totals_only() removed - _status_label function was removed during refactor


def test_missing_translation_skipped_when_neighbor_nonempty():
    """Test that missing_translation is skipped when either neighbor is non-empty."""
    lang = "en"
    dnt = []
    tb_map = {}
    source = [
        cue(1, "Hello world."),  # cur
    ]
    target = [
        cue(1, ""),  # cur empty
    ]
    # Simulate non-empty next neighbor
    target.append(cue(2, "Hola mundo."))

    cls, reason = classify_empty_target_rollup(
        lang=lang,
        cue_index=0,
        source_cues=source,
        target_cues=target,
        do_not_translate_terms=dnt,
        termbase_map_for_lang=tb_map,
    )
    # Expected: no missing issue created (should be BENIGN_ROLLUP due to neighbor)
    assert cls == "BENIGN_ROLLUP"
    assert "neighbor non-empty" in reason


def test_missing_translation_warns_when_both_neighbors_empty_and_long_source():
    """Test that missing_translation warns when both neighbors are empty and source is long."""
    lang = "en"
    dnt = []
    tb_map = {}
    source = [
        cue(1, "This sentence should not be empty in target."),  # long source
    ]
    target = [
        cue(1, ""),  # cur empty
    ]
    # No neighbors; both effectively empty
    # Expected: one missing issue created (should fall through to MISSING)
    cls, reason = classify_empty_target_rollup(
        lang=lang,
        cue_index=0,
        source_cues=source,
        target_cues=target,
        do_not_translate_terms=dnt,
        termbase_map_for_lang=tb_map,
    )
    # Expected: missing issue created since no neighbors and long source
    assert cls == "MISSING"
    assert "no non-empty neighbors" in reason


def test_missing_translation_skipped_when_short_source():
    """Test that missing_translation is skipped when source is very short."""
    lang = "en"
    dnt = []
    tb_map = {}
    source = [
        cue(1, "Hi"),  # short source
    ]
    target = [
        cue(1, ""),  # cur empty
    ]
    # No neighbors; both effectively empty
    # Expected: no missing issue created due to short source
    cls, reason = classify_empty_target_rollup(
        lang=lang,
        cue_index=0,
        source_cues=source,
        target_cues=target,
        do_not_translate_terms=dnt,
        termbase_map_for_lang=tb_map,
    )
    # Expected: BENIGN_ROLLUP due to short source
    assert cls == "BENIGN_ROLLUP"
    assert "short source" in reason
