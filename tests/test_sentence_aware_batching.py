"""Regression tests for source-language-keyed sentence-aware batching.

Guards the two bugs fixed in BATCHING_SENTENCE_AWARE_FIX_PLAN.md:
  Bug 1 — an empty config sentence_endings list used to clobber the default.
  Bug 2 — batching used the *target* language's terminators on *source* text.

Batching is now a source-side decision driven by ``SRTTranslator.source_lang``.
These call ``_create_batches`` through a lightweight shim (real LanguageConfig,
no network) and build cues via ``parse_srt`` so they don't couple to Subtitle.
"""

import json
import logging
from pathlib import Path

import srt_translator
from srt_translator.core.config.language_config import LanguageConfig
from srt_translator.core.translator import translator as T

_CFG = Path(srt_translator.__file__).parent / "config" / "languages.json"
LC = LanguageConfig(json.loads(_CFG.read_text(encoding="utf-8")))


def _shim(source_lang):
    class S:
        language_config = LC
        logger = logging.getLogger("test.batching")
        batch_size = 5
        MAX_BATCH_SIZE = 8
        # real methods under test, bound to the shim instance
        _source_sentence_endings = T.SRTTranslator._source_sentence_endings

    s = S()
    s.source_lang = source_lang
    return s


def _srt(lines):
    """Build minimal SRT text from a list of cue strings."""
    blocks = [f"{i}\n00:00:{i:02d},000 --> 00:00:{i:02d},900\n{t}" for i, t in enumerate(lines, 1)]
    return "\n\n".join(blocks) + "\n"


def sizes(source_lang, srt_text, target_size=5, max_size=8):
    subs = T.parse_srt(srt_text)
    batches = T.SRTTranslator._create_batches(_shim(source_lang), subs, target_size, max_size)
    return [len(b) for b in batches]


# ---- fixtures -------------------------------------------------------------

# 21 English cues; every 3rd ends a sentence with '.' (positions 6,9,12,... are
# within the target..max window, so real breaks are available).
EN_SENTENCES = _srt(
    [f"clause {i} keeps going" if i % 3 else f"and the sentence ends here number {i}." for i in range(1, 22)]
)

# 16 English cues, none terminal -> must force-cut at max_size.
EN_NO_TERM = _srt([f"this clause just keeps going part {i}" for i in range(1, 17)])

# Ellipsis is the ONLY terminator, placed at cue 6 (within [target, max)).
# If '…' is recognized, the first batch ends at 6; if not, it runs to max (8).
EN_ELLIPSIS = _srt(
    [
        "first clause here",
        "second clause here",
        "third clause here",
        "fourth clause here",
        "fifth clause here",
        "and then it trails off…",  # cue 6
        "a brand new thought",
        "continuing onward",
        "still more to say",
        "and a final clause",
    ]
)

# 15 Chinese cues; every 3rd ends with '。'. English '.' never appears, so a
# break here proves the SOURCE language's endings are used.
ZH_SENTENCES = _srt([f"这是第{i}个子句" if i % 3 else f"这是一个完整的句子{i}。" for i in range(1, 16)])


# ---- tests ----------------------------------------------------------------


def test_latin_source_breaks_on_sentence_end():
    # Bug 1 regression: an English source must produce sub-max, sentence-aware batches.
    s = sizes("en-US", EN_SENTENCES)
    assert any(n < 8 for n in s[:-1]), s


def test_english_ellipsis_triggers_break():
    # GATE: ellipsis must be a recognized terminator (couples to the get_sentence_endings
    # default now including '…'). First batch should end exactly at the ellipsis cue (6).
    s = sizes("en-US", EN_ELLIPSIS)
    assert s[0] == 6, s


def test_cjk_source_uses_source_endings():
    # GATE / Bug 2: a Chinese source must break on '。', not English '.'.
    s = sizes("zh-Hans", ZH_SENTENCES)
    assert any(n < 8 for n in s[:-1]), s


def test_no_terminators_forces_max_size():
    # Legitimate fallback: no terminators -> every non-final batch is max_size.
    s = sizes("en-US", EN_NO_TERM)
    assert all(n == 8 for n in s[:-1]), s


def test_batch_sizes_within_bounds():
    for n in sizes("en-US", EN_SENTENCES):
        assert 1 <= n <= 8


def test_latin_and_unknown_sources_agree():
    # Bug 1 + Bug 2 together: all Latin/empty/unknown sources behave like the default
    # (en-US has no explicit endings, es has none, None falls back) -> identical batching.
    a = sizes("en-US", EN_SENTENCES)
    b = sizes("es", EN_SENTENCES)
    c = sizes(None, EN_SENTENCES)
    assert a == b == c, (a, b, c)
    assert any(n < 8 for n in a[:-1]), a
