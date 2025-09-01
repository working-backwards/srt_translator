# Stage 0: snapshot the exact messages payload built by _translate_batch_json.
# NOTE: This test asserts byte-for-byte equality of both system and user prompts.
import json
import logging
import types

from srt_translator.core.config.language_config import LanguageConfig
from srt_translator.core.translator.translator import (
    SRTTranslator,
)  # noqa: E402


class _DummyClient:
    def __init__(self):
        self.last_kwargs = None

    class _Msg:
        def __init__(self, content):
            self.content = content

    class _Choice:
        def __init__(self, content):
            self.message = _DummyClient._Msg(content)

    class _Resp:
        def __init__(self, content):
            self.choices = [_DummyClient._Choice(content)]


def _mk_translator():
    # Minimal config; we will stub .client afterwards
    logger = logging.getLogger("test")
    logger.setLevel(logging.DEBUG)
    t = SRTTranslator(
        dnt_terms=[],
        termbase={"fr": {"Amazon": "Amazon"}},
        api_key="sk-test",
        logger=logger,
        batch_size=5,
        error_policy="STRICT",
        language_config=LanguageConfig({"languages": {}}),
    )
    # Inject dummy client
    dc = _DummyClient()

    def _create(**kwargs):
        dc.last_kwargs = kwargs
        return _DummyClient._Resp(
            content=json.dumps(
                {"items": [{"id": 1, "tgt": "x"}, {"id": 2, "tgt": "y"}]}
            )
        )

    t.client = types.SimpleNamespace(
        chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=_create))
    )
    return t, dc


def test_prompts_non_strict_snapshot():
    t, dc = _mk_translator()
    src_items = ["Hello Amazon", "World"]
    batch_ids = [1, 2]
    _ = t._translate_batch_json(
        src_items=src_items,
        target_lang="fr",
        termbase=t.termbase,
        batch_ids=batch_ids,
        strict=False,
    )
    messages = dc.last_kwargs["messages"]
    system = messages[0]["content"]
    user = messages[1]["content"]

    expected_system = (
        "You are a professional subtitle translator. Return valid JSON ONLY, never prose."
    )
    assert system == expected_system

    termbase_block = "- Amazon \u2192 Amazon"
    expected_user = (
        "Translate each item to fr. Keep 1:1 count and order.\n\n"
        "TERMINOLOGY:\n"
        'Use these business term mappings when present (source \u2192 target). '
        'If "(none)", ignore:\n'
        f"{termbase_block}\n\n"
        "DNT PLACEHOLDERS:\n"
        "- If you see placeholders like __DNT_TERM_7__, keep them EXACTLY as written.\n"
        "- Do not invent or drop placeholders.\n"
        "- Never invent __DNT_TERM_n__ placeholders. Only preserve those already present in the input.\n\n"
        "STRUCTURE:\n"
        '- Return JSON ONLY as: {"items":[{"id":<int>,"tgt":"..."}, ...]}\n'
        '- The "items" array MUST have exactly 2 objects.\n'
        "- Use the provided ids 1:1 with the inputs below. Do not merge or split.\n"
        "- Do not include SRT timestamps in the output. Only JSON.\n\n"
        "STYLE:\n"
        "- Natural, fluent translation.\n"
        "- Numbers: keep digits; localize formatting where normal. No rounding.\n"
        "- No added/removed content.\n\n"
        "INPUT ITEMS:\n"
        "1) Hello Amazon\n"
        "2) World\n"
    )
    assert user == expected_user


def test_prompts_strict_snapshot():
    t, dc = _mk_translator()
    src_items = ["Hello Amazon", "World"]
    batch_ids = [1, 2]
    _ = t._translate_batch_json(
        src_items=src_items,
        target_lang="fr",
        termbase=t.termbase,
        batch_ids=batch_ids,
        strict=True,
    )
    messages = dc.last_kwargs["messages"]
    system = messages[0]["content"]
    user = messages[1]["content"]

    expected_system = (
        "You are a professional subtitle translator. Return valid JSON ONLY, never prose."
        " Hard constraint: never repeat any single word/syllable/token more than 3 times consecutively;"
        " do not pad, chant, or fill with repeated fragments."
    )
    assert system == expected_system

    termbase_block = "- Amazon \u2192 Amazon"
    expected_user = (
        "Translate each item to fr. Keep 1:1 count and order.\n\n"
        "TERMINOLOGY:\n"
        'Use these business term mappings when present (source \u2192 target). '
        'If "(none)", ignore:\n'
        f"{termbase_block}\n\n"
        "DNT PLACEHOLDERS:\n"
        "- If you see placeholders like __DNT_TERM_7__, keep them EXACTLY as written.\n"
        "- Do not invent or drop placeholders.\n"
        "- Never invent __DNT_TERM_n__ placeholders. Only preserve those already present in the input.\n\n"
        "STRUCTURE:\n"
        '- Return JSON ONLY as: {"items":[{"id":<int>,"tgt":"..."}, ...]}\n'
        '- The "items" array MUST have exactly 2 objects.\n'
        "- Use the provided ids 1:1 with the inputs below. Do not merge or split.\n"
        "- Do not include SRT timestamps in the output. Only JSON.\n\n"
        "STYLE:\n"
        "- Natural, fluent translation.\n"
        "- Numbers: keep digits; localize formatting where normal. No rounding.\n"
        "- No added/removed content.\n\n"
        "INPUT ITEMS:\n"
        "1) Hello Amazon\n"
        "2) World\n"
    )
    assert user == expected_user
