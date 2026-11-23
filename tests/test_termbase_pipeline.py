"""End-to-end: configured termbase entries reach the translation prompt.

Goes through the real configuration boundary (TranslationConfig.from_raw) and the real
orchestration (translate_srt_files -> SRTTranslator), faking only the OpenAI client.
This is the path where the prompt glossary was silently "(none)": main.py passes one
language's flat mapping, while build_termbase_block expected a nested one.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from srt_translator.core.config.models import TranslationConfig
from srt_translator.core.main import translate_srt_files

SRT = (
    "1\n00:00:01,000 --> 00:00:03,000\nOur fulfillment centers are busy.\n\n"
    "2\n00:00:03,500 --> 00:00:06,000\nThe Launch Review starts at nine.\n\n"
)

# "fulfillment centers" (plural) is NOT handled by the whole-word find-and-replace, so it
# should be hinted. zh-Hans "Launch Review" IS replaced, so it must not be repeated.
# pt-BR "Launch Review" maps to itself (keep in English): find-and-replace can't enforce
# that, so it should be hinted.
TERMBASE = {
    "zh-Hans": {"fulfillment center": "订单履约中心", "Launch Review": "发布评审"},
    "pt-BR": {"fulfillment center": "centro de distribuição", "Launch Review": "Launch Review"},
}


def _policies() -> dict:
    return {
        "policy_defaults": {"target_batch_size": 5, "max_batch_size": 8, "allow_placeholder_apostrophe": True},
        "languages": {
            "zh-Hans": {"name": "Chinese (Simplified)", "cps_cap": 15},
            "pt-BR": {"name": "Portuguese (Brazil)", "cps_cap": 20},
        },
    }


def _fake_openai_factory(calls: list[dict]):
    """Return a stand-in for openai.OpenAI that records each chat call and answers in the
    batch JSON shape ({"items": [{"id": n, "tgt": "..."}]})."""

    def factory(*_args, **_kwargs):
        def create(**kwargs):
            calls.append(kwargs)
            user = kwargs["messages"][-1]["content"]
            items_part = user.split("INPUT ITEMS:", 1)[-1]
            ids = [int(m) for m in re.findall(r"^(\d+)\) ", items_part, flags=re.MULTILINE)]
            content = json.dumps({"items": [{"id": i, "tgt": f"T{i}"} for i in ids]}, ensure_ascii=False)
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])

        return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))

    return factory


def _prompts_for(calls: list[dict], lang: str) -> str:
    marker = f"Translate each item to {lang}."
    return "\n".join(c["messages"][-1]["content"] for c in calls if marker in c["messages"][-1]["content"])


def test_each_language_prompt_lists_only_its_own_relevant_entries(tmp_path: Path) -> None:
    src = tmp_path / "lesson.srt"
    src.write_text(SRT, encoding="utf-8")
    out = tmp_path / "out"
    out.mkdir()
    cfg = TranslationConfig.from_raw(
        {
            "target_languages": {"Chinese (Simplified)": "zh-Hans", "Portuguese (Brazil)": "pt-BR"},
            "termbase": TERMBASE,
            "output_directory": str(out),
            "api_key": "sk-test-offline",
            "files": (src,),
            "language_policies": _policies(),
            # English source: plural endings ("centers") are only hinted for English sources.
            "source_language": {"normalized_code": "en", "detected_code": "en", "mixed": False},
        },
        mode="GUI",
    )
    calls: list[dict] = []
    with patch("srt_translator.core.translator.translator.OpenAI", side_effect=_fake_openai_factory(calls)):
        summary = translate_srt_files(file_paths=[str(src)], config=cfg)

    # translate_srt_files catches per-language errors, so prompts alone don't prove success.
    assert summary["successes"] == 2, summary
    assert summary["errors"] == 0, summary
    assert summary["failed_languages"] == [], summary

    zh = _prompts_for(calls, "zh-Hans")
    pt = _prompts_for(calls, "pt-BR")
    assert zh and pt, "expected translation calls for both languages"

    assert "- fulfillment center → 订单履约中心" in zh
    assert "Launch Review →" not in zh  # already substituted, not repeated

    assert "- fulfillment center → centro de distribuição" in pt
    assert "- Launch Review → Launch Review" in pt  # identity entry hinted

    assert "centro de distribuição" not in zh  # no cross-language leakage
    assert "订单履约中心" not in pt
