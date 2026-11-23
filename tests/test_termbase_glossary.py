"""Unit tests for the termbase pipeline: validation, TermHandler, prompt glossary, fallback."""

from __future__ import annotations

import inspect
import logging
from types import MappingProxyType, SimpleNamespace

import pytest

from srt_translator.core.config.language_config import LanguageConfig
from srt_translator.core.translator.term_handler import TermHandler, ensure_flat_termbase
from srt_translator.core.translator.translator import SRTTranslator, _is_english_code, build_termbase_block
from srt_translator.prompts.translation import build_single_string_fallback_prompt

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


# --- validation at the translator boundary ---------------------------------------------


def test_ensure_flat_accepts_mapping_proxy() -> None:
    tb = MappingProxyType({"fulfillment center": "订单履约中心"})
    assert ensure_flat_termbase(tb) == {"fulfillment center": "订单履约中心"}


def test_ensure_flat_none_is_empty() -> None:
    assert ensure_flat_termbase(None) == {}


@pytest.mark.parametrize(
    "nested",
    [
        {"zh-Hans": {"a": "b"}},
        MappingProxyType({"zh-Hans": MappingProxyType({"a": "b"})}),
    ],
)
def test_ensure_flat_rejects_nested(nested) -> None:
    with pytest.raises(TypeError, match="flat"):
        ensure_flat_termbase(nested)


def test_ensure_flat_rejects_non_mapping() -> None:
    with pytest.raises(TypeError):
        ensure_flat_termbase([("a", "b")])  # type: ignore[arg-type]


def test_term_handler_rejects_nested_proxy() -> None:
    with pytest.raises(TypeError):
        TermHandler(dnt_terms=[], termbase=MappingProxyType({"zh-Hans": MappingProxyType({"a": "b"})}))


def test_term_handler_flat_proxy_replaces_whole_words_case_insensitively() -> None:
    th = TermHandler(dnt_terms=[], termbase=MappingProxyType({"share price": "股价"}))
    assert th.apply_all("The Share Price fell.") == "The 股价 fell."


def _mk_translator(termbase, source_lang: str | None = None) -> SRTTranslator:
    return SRTTranslator(
        dnt_terms=[],
        termbase=termbase,
        api_key="sk-test-offline",
        translation_model_name="gpt-4o-mini",
        logger=logging.getLogger("test.termbase"),
        batch_size=5,
        language_config=LanguageConfig({"languages": {"fr": {"name": "French"}}}),
        source_lang=source_lang,
    )


def test_translator_rejects_nested_termbase() -> None:
    with pytest.raises(TypeError):
        _mk_translator({"fr": {"deck": "présentation"}})


def test_translator_stores_flat_copy() -> None:
    t = _mk_translator(MappingProxyType({"deck": "présentation"}))
    assert t.termbase == {"deck": "présentation"}


# --- prompt glossary --------------------------------------------------------------------


def test_glossary_empty_termbase() -> None:
    assert build_termbase_block({}, ["anything"]) == "(none)"


def test_glossary_unrelated_term_excluded() -> None:
    assert build_termbase_block({"deck": "汇报材料"}, ["No match here."]) == "(none)"


def test_glossary_term_already_replaced_is_not_repeated() -> None:
    assert build_termbase_block({"share price": "股价"}, ["The 股价 fell."]) == "(none)"


FC = {"fulfillment center": "订单履约中心"}


@pytest.mark.parametrize("text", ["Two fulfillment centers.", "The FULFILLMENT CENTERS are full."])
def test_glossary_english_source_lists_plurals_any_case(text: str) -> None:
    assert build_termbase_block(FC, [text], english_source=True) == "- fulfillment center → 订单履约中心"


def test_glossary_whitespace_inside_term() -> None:
    assert build_termbase_block(FC, ["fulfillment  \n center"]) == "- fulfillment center → 订单履约中心"


def test_glossary_english_source_es_plural() -> None:
    assert build_termbase_block({"process": "流程"}, ["Our processes"], english_source=True) == "- process → 流程"


@pytest.mark.parametrize("text", ["a processor", "processing data", "preprocess"])
def test_glossary_rejects_other_words_containing_the_term(text: str) -> None:
    assert build_termbase_block({"process": "流程"}, [text], english_source=True) == "(none)"


def test_glossary_non_english_source_matches_exact_phrase_only() -> None:
    # French "car" means "because"; "cars" means "buses". No English plural rule for French.
    assert build_termbase_block({"car": "因为"}, ["Les cars arrivent."]) == "(none)"
    assert build_termbase_block({"car": "因为"}, ["Je reste, car il pleut."]) == "- car → 因为"


def test_glossary_unknown_source_gets_no_plural_rule() -> None:
    assert build_termbase_block(FC, ["Two fulfillment centers."]) == "(none)"


def test_possessive_is_substituted_before_the_glossary_sees_it() -> None:
    th = TermHandler(dnt_terms=[], termbase=FC)
    singular = [th.apply_all("The fulfillment center's dock.")]
    assert singular == ["The 订单履约中心's dock."]
    assert build_termbase_block(FC, singular, english_source=True) == "(none)"
    plural = [th.apply_all("The fulfillment centers' docks.")]
    assert build_termbase_block(FC, plural, english_source=True) == "- fulfillment center → 订单履约中心"


@pytest.mark.parametrize(
    ("code", "expected"),
    [("en", True), ("en-US", True), ("EN-gb", True), ("eng", False), ("fr", False), (None, False), ("", False)],
)
def test_is_english_code(code, expected) -> None:
    assert _is_english_code(code) is expected


@pytest.mark.parametrize(
    ("source_lang", "text", "termbase", "expected_line"),
    [
        ("en", "Two fulfillment centers.", FC, "- fulfillment center → 订单履约中心"),
        ("fr", "Les cars arrivent.", {"car": "因为"}, None),
    ],
)
def test_translator_gates_plural_endings_on_source_language(source_lang, text, termbase, expected_line) -> None:
    t = _mk_translator(termbase, source_lang=source_lang)
    prompts: list[str] = []

    def create(**kwargs):
        prompts.append(kwargs["messages"][1]["content"])
        content = '{"items": [{"id": 1, "tgt": "x"}]}'
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])

    t.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    t._translate_batch_json(src_items=[text], target_lang="fr", termbase=t.termbase, batch_ids=[1])
    block = prompts[0].split("TERMINOLOGY:", 1)[1].split("DNT PLACEHOLDERS:", 1)[0]
    if expected_line:
        assert expected_line in block
    else:
        assert "(none)" in block


def test_glossary_never_matches_across_items() -> None:
    assert build_termbase_block({"share price": "股价"}, ["such as share", "price."]) == "(none)"


def test_glossary_lists_identity_entry() -> None:
    tb = {"Launch Review": "Launch Review"}
    assert build_termbase_block(tb, ["Our Launch Review"]) == "- Launch Review → Launch Review"


def test_glossary_lists_capitalisation_duplicates_once() -> None:
    tb = {"Launch Review": "Launch Review", "launch review": "Launch Review"}
    assert build_termbase_block(tb, ["the launch review"]) == "- Launch Review → Launch Review"


def test_glossary_order_follows_termbase_and_accepts_proxy() -> None:
    tb = MappingProxyType({"zeta term": "Z", "alpha term": "A"})
    assert build_termbase_block(tb, ["alpha term and zeta term"]) == "- zeta term → Z\n- alpha term → A"


def test_glossary_ignores_blank_keys() -> None:
    assert build_termbase_block({"  ": "X"}, ["anything"]) == "(none)"


# --- plain-string fallback --------------------------------------------------------------

_FALLBACK_NO_GLOSSARY = (
    "Translate to fr.\n\n"
    "DNT PLACEHOLDERS:\n"
    "- If you see placeholders like __DNT_TERM_7__, keep them EXACTLY as written.\n"
    "- Do not invent or drop placeholders.\n\n"
    "TEXT:\nHello\n"
)


def test_fallback_prompt_unchanged_without_glossary() -> None:
    _sys, usr = build_single_string_fallback_prompt("fr", "Hello")
    assert usr == _FALLBACK_NO_GLOSSARY
    _sys, usr = build_single_string_fallback_prompt("fr", "Hello", "(none)")
    assert usr == _FALLBACK_NO_GLOSSARY


def test_fallback_prompt_includes_glossary() -> None:
    _sys, usr = build_single_string_fallback_prompt("fr", "Hello", "- deck → présentation")
    assert usr.startswith("Translate to fr.\n\nTERMINOLOGY:\n")
    assert "- deck → présentation\n\nDNT PLACEHOLDERS:" in usr


def test_malformed_single_item_falls_back_with_glossary() -> None:
    t = _mk_translator({"fulfillment center": "centre de distribution"}, source_lang="en")  # plural needs English
    calls: list[dict] = []

    def create(**kwargs):
        calls.append(kwargs)
        system = kwargs["messages"][0]["content"]
        content = "Bonjour" if "Reply with the translation ONLY" in system else "not json at all"
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])

    t.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    items = t._translate_batch_json(
        src_items=["Our fulfillment centers"],
        target_lang="fr",
        termbase=t.termbase,
        batch_ids=[1],
    )
    assert items == [{"id": 1, "tgt": "Bonjour"}]
    fallback = [c for c in calls if "Reply with the translation ONLY" in c["messages"][0]["content"]]
    assert len(fallback) == 1
    assert "- fulfillment center → centre de distribution" in fallback[0]["messages"][1]["content"]
