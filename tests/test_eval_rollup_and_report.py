# tests/test_eval_rollup_and_report.py
from types import SimpleNamespace as NS
from srt_translator.eval.tools import Cue, classify_empty_target_rollup, normalize_for_empty_check
from srt_translator.eval.report import _status_label

def cue(i, txt):  # helper for brevity
    return Cue(index=i, start_ms=0, end_ms=1000, text=txt)

def test_benign_rollup_full_sentence_az():
    # en 23+24 merged into az 23; az 24 blank
    lang = "az"
    dnt = []
    tb_map = {}
    source = [cue(23, "First, after debates, we had clarity."),
              cue(24, "First, after debates, we had clarity.")]
    target = [cue(23, "Birincisi, müzakirələrdən sonra aydınlıq əldə etdik."),
              cue(24, "")]
    
    # Debug: Let's see what the classifier is calculating
    from srt_translator.eval.tools import strip_terms, normalize_for_empty_check, median_expansion_ratio
    
    src_after_all = [strip_terms(c.text, dnt) for c in source]
    tgt_norm_all = [normalize_for_empty_check(c.text) for c in target]
    R = median_expansion_ratio(src_after_all, tgt_norm_all)
    
    print(f"DEBUG: Source after DNT: {src_after_all}")
    print(f"DEBUG: Target normalized: {tgt_norm_all}")
    print(f"DEBUG: Expansion ratio R: {R}")
    print(f"DEBUG: Source cue 24 length: {len(src_after_all[1])}")
    print(f"DEBUG: Target cue 23 length: {len(tgt_norm_all[0])}")
    
    cls, reason = classify_empty_target_rollup(
        lang=lang, cue_index=1,
        source_cues=source, target_cues=target,
        do_not_translate_terms=dnt, termbase_map_for_lang=tb_map,
    )
    print(f"DEBUG: Classifier returned: {cls} - {reason}")
    print(f"DEBUG: Source cue 24 text: '{source[1].text}'")
    print(f"DEBUG: Target cue 24 text: '{target[1].text}'")
    print(f"DEBUG: Target cue 23 text: '{target[0].text}'")
    assert cls != "MISSING"  # treat as rolled-up (benign/suspect), hence not error

def test_tiny_remainder_ar():
    lang = "ar"; dnt=[]; tb_map={}
    source = [cue(45, "with results from the prior year,"), cue(46, "year.")]
    target = [cue(45, "مع نتائج من العام السابق،"), cue(46, "")]
    cls, _ = classify_empty_target_rollup(
        lang=lang, cue_index=1,
        source_cues=source, target_cues=target,
        do_not_translate_terms=dnt, termbase_map_for_lang=tb_map,
    )
    assert cls != "MISSING"  # tiny tail merges to previous: not an error

def test_status_label_uses_error_totals_only():
    # one file with 2 error categories present
    per_file = {
        "issues": {
            "untranslated_after_dnt": [{"cue": 10}],
            "missing_translation": [{"idx": 12}],
            "timing_fail": False,
        },
        "metrics": {"parity_ok": True},
        "status": "PASS",  # should be ignored for Ready? decision
    }
    assert _status_label(per_file) == "❌ Not ready"
