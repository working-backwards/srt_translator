# Terminology Pipeline Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make configured termbase entries reach the translation model through the prompt glossary, remove the termbase code that never had an effect, and correct the docs, without changing the find-and-replace or DNT behaviour.

**Architecture:**
- The configuration keeps its nested `{language: {term: translation}}` format.
- At the translator boundary, `SRTTranslator` and `TermHandler` accept exactly one language's flat `{term: translation}` mapping, validated by a new `ensure_flat_termbase()`.
- `build_termbase_block()` builds the prompt glossary from the batch's subtitles *after* find-and-replace, matching within each subtitle.
- The same glossary goes into the plain-string fallback prompt.
- Design and rationale: `plans/2026-11-23-terminology-pipeline-brief.md` (revision 2).

**Tech Stack:** Python 3.11+, pytest, ruff, mypy. OpenAI SDK (mocked in every test).

## Global Constraints

- Work on branch `fix/terminology-pipeline` in the `srt_translator` repo root. Don't push or merge; the owner decides that.
- Python 3.11+. Ruff config lives in `pyproject.toml`; run it from the repo root.
- **Logging:** never use f-strings, `.format()` or `%` inside logger calls. Always parameterized: `logger.debug("msg %s", val)`.
- **Core engine** (`srt_translator/core/`) reads only from `TranslationConfig`, never from env vars or global settings.
- **This repo is public.** No course text, reviewer names or private paths in code, tests, docs or commit messages. Test data uses generic terms only.
- **Tests make no network calls.** The OpenAI client is always faked.
- **Behaviour that must NOT change:**
  - `TermHandler.apply_termbase` (case-insensitive, whole-word, longest key first) and its order (termbase, then DNT);
  - DNT matching (exact case);
  - the main prompt text other than the glossary contents;
  - the configuration file format.
- **Do not add** (brief §10), even as small extras:
  - automatic identifier detection;
  - a hard/soft terminology schema;
  - first-mention explanations;
  - generalized or case-tolerant DNT matching;
  - stemming or general morphology in glossary matching.
- **Every commit message ends with:**
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`
- Run commands from the repo root with the repo venv: `venv/bin/python -m pytest …`, `venv/bin/ruff …`, `venv/bin/python -m mypy …`.

**Baselines (2026-11-23, `main` at `b6eb630`):**
- `venv/bin/python -m pytest -q` → `305 passed`.
- `venv/bin/ruff check srt_translator tests` → `All checks passed!`
- `venv/bin/ruff format --check srt_translator tests` → 1 pre-existing failure (`tests/test_translation_retry_status.py`). Leave that file alone.
- `venv/bin/python -m mypy srt_translator/core/translator/translator.py srt_translator/core/translator/term_handler.py srt_translator/core/main.py srt_translator/prompts/translation.py --config-file=mypy.ini` → `Success: no issues found in 4 source files`.

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `srt_translator/core/translator/term_handler.py` | Termbase find-and-replace and DNT placeholders | Add `ensure_flat_termbase()`; accept a flat mapping only; remove `restore_termbase` and `termbase_target_map`; `restore_all(text)` restores DNT only |
| `srt_translator/core/translator/translator.py` | Batching, prompts, model calls | Validate the termbase at `__init__`; drop `allow_global_termbase_fallback`; new `build_termbase_block(termbase, src_items)` and `_glossary_pattern()`; glossary to the fallback; `restore_all` call sites |
| `srt_translator/prompts/translation.py` | Prompt text | `build_single_string_fallback_prompt(..., termbase_block="(none)")` |
| `srt_translator/core/main.py` | Orchestration | Drop the `allow_global_termbase_fallback=` argument |
| `tests/test_termbase_pipeline.py` (new) | Config → orchestration → prompt, OpenAI faked | Regression test for the empty glossary |
| `tests/test_termbase_glossary.py` (new) | Unit tests | Validation, `TermHandler`, glossary matching, fallback |
| `tests/test_prompts_snapshot.py`, `tests/test_golden_srt.py` | Existing | Flat per-language termbase |
| `docs/…`, `CHANGELOG.md` | Docs | Corrections listed in Task 5 |

---

### Task 1: Regression test through the real configuration path (expected to fail)

**Files:**
- Create: `tests/test_termbase_pipeline.py`

**Interfaces:**
- Consumes: `TranslationConfig.from_raw(raw, mode="GUI")` (`srt_translator/core/config/models.py`); `translate_srt_files(file_paths, config)` (`srt_translator/core/main.py`). The OpenAI client is constructed in `SRTTranslator.__init__` as `OpenAI(api_key=..., timeout=120.0)` (`srt_translator/core/translator/translator.py`).
- Produces: the test `test_each_language_prompt_lists_only_its_own_relevant_entries`, marked `xfail(strict=True)`. Task 3 removes the marker.

- [ ] **Step 1: Write the test**

```python
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

import pytest

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


@pytest.mark.xfail(strict=True, reason="B1/B2: prompt glossary is always '(none)'; fixed in Task 3")
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
        },
        mode="GUI",
    )
    calls: list[dict] = []
    with patch("srt_translator.core.translator.translator.OpenAI", side_effect=_fake_openai_factory(calls)):
        translate_srt_files(file_paths=[str(src)], config=cfg)

    zh = _prompts_for(calls, "zh-Hans")
    pt = _prompts_for(calls, "pt-BR")
    assert zh and pt, "expected translation calls for both languages"

    assert "- fulfillment center → 订单履约中心" in zh
    assert "Launch Review →" not in zh  # already substituted, not repeated

    assert "- fulfillment center → centro de distribuição" in pt
    assert "- Launch Review → Launch Review" in pt  # identity entry hinted

    assert "centro de distribuição" not in zh  # no cross-language leakage
    assert "订单履约中心" not in pt
```

- [ ] **Step 2: Run it and confirm it fails for the right reason**

Run: `venv/bin/python -m pytest tests/test_termbase_pipeline.py -v -rx`
Expected: `1 xfailed`. To see the underlying assertion, temporarily run with `--runxfail`. Expect `AssertionError` on `"- fulfillment center → 订单履约中心" in zh`, because the prompt shows `(none)`. If it fails for any other reason (an import error, a crash in `translate_srt_files`, or no calls recorded), fix the test before continuing.

- [ ] **Step 3: Run the full suite**

Run: `venv/bin/python -m pytest -q`
Expected: `305 passed, 1 xfailed`.

- [ ] **Step 4: Commit**

```bash
git add tests/test_termbase_pipeline.py
git commit -m "test: add failing regression test for the empty termbase glossary

Drives TranslationConfig.from_raw -> translate_srt_files with a fake
OpenAI client and asserts each language's prompt lists its relevant
termbase entries. Marked xfail(strict=True) until the fix lands.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Remove the ineffective restore step and the unused fallback flag

No translation output changes. `restore_termbase` never took effect with the flat mapping the app passes, and `allow_global_termbase_fallback` is never read.

**Files:**
- Modify: `srt_translator/core/translator/term_handler.py` (`__init__` target-map block ~lines 56–64; `restore_termbase` ~176–190; `restore_all` ~197–200)
- Modify: `srt_translator/core/translator/translator.py` (`__init__` ~337 and ~353; `restore_all` call sites ~558, ~733, ~832, and the comment above ~558)
- Modify: `srt_translator/core/main.py:157`
- Create: `tests/test_termbase_glossary.py`

**Interfaces:**
- Produces: `TermHandler.restore_all(self, text: str) -> str` (one argument; restores DNT placeholders only). `TermHandler` has no `restore_termbase` and no `termbase_target_map`. `SRTTranslator.__init__` has no `allow_global_termbase_fallback` parameter.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_termbase_glossary.py`:

```python
"""Unit tests for the termbase pipeline: validation, TermHandler, prompt glossary, fallback."""

from __future__ import annotations

import inspect

from srt_translator.core.translator.term_handler import TermHandler
from srt_translator.core.translator.translator import SRTTranslator

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
```

- [ ] **Step 2: Run them to verify they fail**

Run: `venv/bin/python -m pytest tests/test_termbase_glossary.py -v`
Expected: 3 FAIL. `restore_all()` is missing the `lang_code` argument (TypeError), `restore_termbase` exists, and the flag is present.

- [ ] **Step 3: Edit `term_handler.py`**

In `TermHandler.__init__`, delete the target-map attribute and the loop that fills it (the lines between `self.termbase_patterns: ... = []` and the `# Flatten the termbase into term_map` comment):

```python
        self.termbase_target_map: dict[str, dict[str, str]] = {}

        for lang, entries in self.termbase.items():
            if isinstance(entries, dict):
                self.termbase_target_map[lang] = entries.copy()
            else:
                # wrap single string entry into a dict with itself as key/value
                self.termbase_target_map[lang] = {entries: entries}

```

Delete the whole `restore_termbase` method (from `def restore_termbase(self, text: str, lang_code: str) -> str:` through its final `return out`).

Replace `restore_all` with:

```python
    def restore_all(self, text: str) -> str:
        """Restore DNT placeholders in translated text.

        Termbase substitutions are not re-applied to model output: the find-and-replace
        runs on the source before translation, so the model already sees the preferred
        target strings.
        """
        return self.restore_dnt_placeholders(text)
```

- [ ] **Step 4: Edit `translator.py`**

In `SRTTranslator.__init__`, delete the parameter line `allow_global_termbase_fallback: bool = False,` and the assignment `self.allow_global_termbase_fallback = allow_global_termbase_fallback`.

Update the three call sites:

```python
        # Restore DNT placeholders
        tgt_texts = [self.term_handler.restore_all(t) for t in tgt_texts]
```

```python
                            tgt_texts[i] = self.term_handler.restore_all(candidate)
```

```python
                            fixed = self.term_handler.restore_all(fixed)
```

(The first replaces `# Restore DNT placeholders and termbase substitutions` and the line under it.)

- [ ] **Step 5: Edit `main.py`**

Delete the line `allow_global_termbase_fallback=config.mode == "CLI",  # GUI: no fallback; CLI: allow` from the `SRTTranslator(...)` call.

- [ ] **Step 6: Run the tests**

Run: `venv/bin/python -m pytest tests/test_termbase_glossary.py -v` → 3 passed.
Run: `venv/bin/python -m pytest -q` → `308 passed, 1 xfailed`.
Run: `grep -rn "restore_termbase\|termbase_target_map\|allow_global_termbase_fallback" srt_translator tests` → no output.

- [ ] **Step 7: Commit**

```bash
git add srt_translator/core/translator/term_handler.py srt_translator/core/translator/translator.py srt_translator/core/main.py tests/test_termbase_glossary.py
git commit -m "refactor: remove termbase restore step and unused fallback flag

restore_termbase() never took effect with the flat per-language mapping
the app passes, and allow_global_termbase_fallback was never read.
restore_all() now restores DNT placeholders only. No output changes.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Flat termbase at the translator boundary, and a working glossary

This is the core fix.

**Files:**
- Modify: `srt_translator/core/translator/term_handler.py` (imports; new `ensure_flat_termbase`; class docstring; `__init__` termbase block and debug log)
- Modify: `srt_translator/core/translator/translator.py` (imports; `build_termbase_block` ~195–205; `__init__` ~334 and ~352; type hints on `_translate_with_simple_shape_lock` and `_translate_batch_json`; the glossary call ~951)
- Modify: `tests/test_prompts_snapshot.py:49`, `tests/test_golden_srt.py:117,123`
- Modify: `tests/test_termbase_glossary.py` (append)
- Modify: `tests/test_termbase_pipeline.py` (remove the `xfail` marker)

**Interfaces:**
- Consumes: `TermHandler.restore_all(text)` from Task 2.
- Produces:
  - `ensure_flat_termbase(termbase: Mapping[str, Any] | None) -> dict[str, str]` in `term_handler.py`. Raises `TypeError` on a non-mapping, a nested mapping value, or non-string entries.
  - `build_termbase_block(termbase: Mapping[str, str], src_items: Sequence[str]) -> str` in `translator.py`. Returns `"(none)"` or lines `"- {source} → {target}"` joined by `"\n"`.
  - `_glossary_pattern(term: str) -> Pattern[str]` (module-private, cached).
  - `SRTTranslator.termbase: dict[str, str]`.

- [ ] **Step 1: Append the failing unit tests to `tests/test_termbase_glossary.py`**

Add these imports to the top import block (keep `inspect`, `TermHandler`, `SRTTranslator`):

```python
import logging
from types import MappingProxyType

import pytest

from srt_translator.core.config.language_config import LanguageConfig
from srt_translator.core.translator.term_handler import ensure_flat_termbase
from srt_translator.core.translator.translator import build_termbase_block
```

Append:

```python
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


def _mk_translator(termbase) -> SRTTranslator:
    return SRTTranslator(
        dnt_terms=[],
        termbase=termbase,
        api_key="sk-test-offline",
        translation_model_name="gpt-4o-mini",
        logger=logging.getLogger("test.termbase"),
        batch_size=5,
        language_config=LanguageConfig({"languages": {"fr": {"name": "French"}}}),
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


@pytest.mark.parametrize(
    "text",
    [
        "Two fulfillment centers.",
        "The FULFILLMENT CENTER's dock.",
        "The fulfillment center’s dock.",
        "fulfillment  \n center",
    ],
)
def test_glossary_lists_plural_possessive_case_and_whitespace_variants(text: str) -> None:
    assert build_termbase_block({"fulfillment center": "订单履约中心"}, [text]) == "- fulfillment center → 订单履约中心"


def test_glossary_es_plural() -> None:
    assert build_termbase_block({"process": "流程"}, ["Our processes"]) == "- process → 流程"


@pytest.mark.parametrize("text", ["a processor", "processing data", "preprocess"])
def test_glossary_rejects_other_words_containing_the_term(text: str) -> None:
    assert build_termbase_block({"process": "流程"}, [text]) == "(none)"


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
```

- [ ] **Step 2: Run them to verify they fail**

Run: `venv/bin/python -m pytest tests/test_termbase_glossary.py -v`
Expected:
- the import of `ensure_flat_termbase` fails (ImportError), so the whole module errors;
- after Step 3 adds it, the glossary tests fail, because `build_termbase_block` still takes `lang_code`.

- [ ] **Step 3: Implement `ensure_flat_termbase` and the flat `TermHandler`**

In `term_handler.py`, add these imports after `import re`:

```python
from collections.abc import Mapping
from typing import Any
```

Add this module-level function after `_compile_word_safe_pattern`:

```python
def ensure_flat_termbase(termbase: Mapping[str, Any] | None) -> dict[str, str]:
    """Validate one language's termbase and return a plain-dict copy.

    The translator works on a single language's entries, ``{source_term: target_term}``.
    ``TranslationConfig`` stores them as read-only ``MappingProxyType`` objects, so any
    ``Mapping`` is accepted. A nested ``{language: {source: target}}`` mapping is rejected:
    it is the configuration shape, not the translator's, and passing it used to merge
    every language's entries into one table.

    Raises:
        TypeError: if ``termbase`` is not a mapping, a value is itself a mapping, or an
            entry is not a string.
    """
    if termbase is None:
        return {}
    if not isinstance(termbase, Mapping):
        raise TypeError(f"termbase must be a mapping of source term to target term, got {type(termbase).__name__}")
    flat: dict[str, str] = {}
    for source, target in termbase.items():
        if isinstance(target, Mapping):
            raise TypeError(
                "termbase must be a flat {source: target} mapping for one language; "
                f"got a nested mapping under {source!r}. Pass config.termbase.get(lang_code, {{}})."
            )
        if not isinstance(source, str) or not isinstance(target, str):
            raise TypeError(f"termbase entries must be strings, got {source!r}: {target!r}")
        flat[source] = target
    return flat
```

Replace the class docstring with:

```python
    """
    Central place for termbase find-and-replace and DNT placeholders, for ONE language.
    - Takes that language's flat termbase {source_term: target_term}.
    - apply_all(): replaces termbase terms with their target strings, then DNT terms
      with placeholders (term -> __DNT_TERM_i__), before translation.
    - restore_all(): restores DNT placeholders after translation.
    - Exposes `placeholder_regex` so other modules (Fixer/logs) can detect them.
    The prompt glossary is built separately (translator.build_termbase_block).
    """
```

In `__init__`, change the parameter annotation `termbase: dict[str, dict[str, str]] | None = None,` to `termbase: Mapping[str, str] | None = None,`. Then replace everything from `self.termbase = termbase or {}` down to the end of the `for term, replacement in sorted(...)` loop with:

```python
        # One language's entries: {source_term: target_term}
        self.termbase: dict[str, str] = ensure_flat_termbase(termbase)
        self.term_map: dict[str, str] = dict(self.termbase)
        self.termbase_patterns: list[tuple[re.Pattern, str]] = []
        for term, replacement in sorted(self.term_map.items(), key=lambda x: len(x[0]), reverse=True):
            pat = re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)
            self.termbase_patterns.append((pat, replacement))
```

In the `TermHandler initialized` debug log, replace the last argument `sum(len(v) for v in self.termbase.values()),` with `len(self.termbase),`. The old expression summed the *lengths of the target strings* for a flat mapping.

- [ ] **Step 4: Implement the glossary and the boundary in `translator.py`**

Imports: add `import functools` immediately before `import json`. Change `from srt_translator.core.translator.term_handler import TermHandler` to:

```python
from srt_translator.core.translator.term_handler import TermHandler, ensure_flat_termbase
```

Replace the whole `build_termbase_block` function with:

```python
@functools.lru_cache(maxsize=1024)
def _glossary_pattern(term: str) -> Pattern[str]:
    """Relevance pattern for one termbase source term (prompt glossary only).

    Case-insensitive; the term's words may be separated by any whitespace; the match must
    start at a word boundary and may end with one English plural or possessive suffix
    (s, es, 's, ’s) before a word boundary. "processes" matches "process"; "processor"
    does not. Irregular plurals and hyphen variants are not handled.
    """
    words = [re.escape(w) for w in term.split()]
    return re.compile(r"(?<!\w)" + r"\s+".join(words) + r"(?:s|es|'s|’s)?(?!\w)", re.IGNORECASE)


def build_termbase_block(termbase: Mapping[str, str], src_items: Sequence[str]) -> str:
    """Render the prompt's TERMINOLOGY glossary for one batch.

    Args:
        termbase: One language's flat ``{source_term: target_term}`` mapping.
        src_items: The batch's source texts AFTER termbase substitution and DNT
            placeholders. A term the find-and-replace already handled is no longer
            present and is not repeated.

    An entry is listed when its source term still appears in at least one item, checked
    item by item (never across items, because the prompt treats each item as an
    independent subtitle). Entries that differ only in capitalisation and share a target
    are listed once. Returns "(none)" when nothing is relevant.
    """
    lines: list[str] = []
    seen: set[tuple[str, str]] = set()
    for source, target in termbase.items():
        term = source.strip()
        if not term:
            continue
        key = (term.casefold(), target.strip())
        if key in seen:
            continue
        pattern = _glossary_pattern(term)
        if any(pattern.search(item or "") for item in src_items):
            seen.add(key)
            lines.append(f"- {source} → {target}")
    return "\n".join(lines) if lines else "(none)"
```

In `SRTTranslator.__init__`:
- change `termbase: dict[str, dict[str, str]],` to `termbase: Mapping[str, str],`;
- change `self.termbase = termbase or {}` to:

```python
        # One language's flat termbase {source_term: target_term}; rejects the nested config shape.
        self.termbase: dict[str, str] = ensure_flat_termbase(termbase)
```

In `_translate_with_simple_shape_lock` and `_translate_batch_json`, change the parameter annotation `termbase: dict[str, dict[str, str]],` to `termbase: Mapping[str, str],`.

In `_translate_batch_json`, replace `termbase_block = build_termbase_block(termbase, target_lang)` with:

```python
        termbase_block = build_termbase_block(termbase, src_items)
        if termbase_block != "(none)":
            self.logger.debug(
                "Glossary entries for batch (lang=%s, ids=%s): %d",
                target_lang,
                batch_ids,
                termbase_block.count("\n") + 1,
            )
```

- [ ] **Step 5: Switch the existing tests to the flat shape**

`tests/test_prompts_snapshot.py`, in `_mk_translator`: change `termbase={"fr": {"Amazon": "Amazon"}},` to `termbase={"Amazon": "Amazon"},`. The expected prompts stay the same: "Amazon" is still present in "Hello Amazon", so the block is still `- Amazon → Amazon`.

`tests/test_golden_srt.py`:
- change `termbase = {"es": TERMS_ES}  # non-ES languages may have empty mappings` to `termbases = {"es": TERMS_ES}  # per language; other languages get no entries`;
- inside the loop, change `termbase=termbase,` to `termbase=termbases.get(target_lang, {}),`.

`tests/test_termbase_pipeline.py`: delete the line `@pytest.mark.xfail(strict=True, reason="B1/B2: prompt glossary is always '(none)'; fixed in Task 3")`. If `pytest` is then unused in that file, also delete `import pytest`.

- [ ] **Step 6: Run the tests**

Run: `venv/bin/python -m pytest tests/test_termbase_glossary.py tests/test_termbase_pipeline.py tests/test_prompts_snapshot.py tests/test_golden_srt.py -v`
Expected: all pass, with no xfail.

Run: `venv/bin/python -m pytest -q`
Expected: `334 passed`, `0 failed`, `0 xfailed`. That is 305 baseline + 1 pipeline + 3 from Task 2 + 25 from Task 3, counting each parametrized case. If the count differs, confirm that only these new tests account for it.

- [ ] **Step 7: Lint and types**

Run: `venv/bin/ruff check srt_translator tests` → `All checks passed!`
Run: `venv/bin/ruff format --check srt_translator/core/translator/term_handler.py srt_translator/core/translator/translator.py tests/test_termbase_glossary.py tests/test_termbase_pipeline.py tests/test_prompts_snapshot.py tests/test_golden_srt.py` → nothing to reformat. If not, run `venv/bin/ruff format` on those files only.
Run: `venv/bin/python -m mypy srt_translator/core/translator/translator.py srt_translator/core/translator/term_handler.py srt_translator/core/main.py srt_translator/prompts/translation.py --config-file=mypy.ini` → `Success: no issues found`.

- [ ] **Step 8: Commit**

```bash
git add srt_translator/core/translator/term_handler.py srt_translator/core/translator/translator.py tests/test_termbase_glossary.py tests/test_termbase_pipeline.py tests/test_prompts_snapshot.py tests/test_golden_srt.py
git commit -m "fix(translator): make the termbase glossary reach the prompt

The prompt's TERMINOLOGY section was always '(none)': main.py passes one
language's flat mapping while build_termbase_block() expected a nested
one, and it also lowercased the language code. The translator boundary
now accepts exactly one language's flat mapping (any Mapping, including
the MappingProxyType the config supplies) and rejects the nested shape.
The glossary lists entries still present in a subtitle after
find-and-replace (plurals, possessives, keep-in-English entries),
matched per subtitle. Tests now use the shape the app uses.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Glossary in the plain-string fallback

**Files:**
- Modify: `srt_translator/prompts/translation.py` (`build_single_string_fallback_prompt` ~92–118)
- Modify: `srt_translator/core/translator/translator.py` (`_translate_single_string_fallback` ~1205; its call site in `_translate_batch_json` ~1192)
- Modify: `tests/test_termbase_glossary.py` (append)

**Interfaces:**
- Consumes: `build_termbase_block` from Task 3 (`termbase_block` is already a local variable in `_translate_batch_json`).
- Produces:
  - `build_single_string_fallback_prompt(target_lang: str, src_text: str, termbase_block: str = "(none)") -> tuple[str, str]`;
  - `SRTTranslator._translate_single_string_fallback(self, *, _src_text: str, target_lang: str, termbase_block: str = "(none)") -> str`.

- [ ] **Step 1: Append the failing tests**

Add to the imports in `tests/test_termbase_glossary.py`:

```python
from types import SimpleNamespace

from srt_translator.prompts.translation import build_single_string_fallback_prompt
```

Append:

```python
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
    t = _mk_translator({"fulfillment center": "centre de distribution"})
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
```

(The fake client is also called once by the existing malformed-JSON diagnostic probe. That call is expected, and the filter above ignores it.)

- [ ] **Step 2: Run them to verify they fail**

Run: `venv/bin/python -m pytest tests/test_termbase_glossary.py -k fallback -v`
Expected:
- `test_fallback_prompt_includes_glossary` fails with TypeError (an unexpected third argument);
- `test_malformed_single_item_falls_back_with_glossary` fails on the glossary assertion;
- `test_fallback_prompt_unchanged_without_glossary` fails on the call with three arguments.

- [ ] **Step 3: Implement the prompt change**

In `srt_translator/prompts/translation.py`, replace `build_single_string_fallback_prompt` with:

```python
def build_single_string_fallback_prompt(
    target_lang: str,
    src_text: str,
    termbase_block: str = "(none)",
) -> tuple[str, str]:
    """Build the single-string fallback prompts (no JSON wrapper).

    Args:
        target_lang: Target language code.
        src_text: Source text to translate.
        termbase_block: The batch's prompt glossary (from build_termbase_block);
            omitted from the prompt when "(none)".

    Returns:
        (system_prompt, user_prompt) tuple.
    """
    sys = (
        "You are a professional subtitle translator. "
        "Reply with the translation ONLY—no JSON, no code, no quotes, no commentary."
    )
    usr = f"Translate to {target_lang}.\n\n"
    if termbase_block and termbase_block != "(none)":
        usr += f"TERMINOLOGY:\nUse these business term mappings when present (source → target):\n{termbase_block}\n\n"
    usr += (
        "DNT PLACEHOLDERS:\n"
        "- If you see placeholders like __DNT_TERM_7__, keep them EXACTLY as written.\n"
        "- Do not invent or drop placeholders.\n\n"
        f"TEXT:\n{src_text}\n"
    )
    return sys, usr
```

- [ ] **Step 4: Pass the glossary through**

In `translator.py`, change the method signature and its first line:

```python
    def _translate_single_string_fallback(self, *, _src_text: str, target_lang: str, termbase_block: str = "(none)") -> str:
        """
        Minimal escape hatch for repeated JSON truncation in size=1 strict retries.
        Returns ONLY a translated string; caller will wrap into JSON.
        """
        sys, usr = build_single_string_fallback_prompt(target_lang, _src_text, termbase_block)
```

At the call site in `_translate_batch_json` (the `# LAST-CHANCE FALLBACK` block):

```python
                    fallback_txt = self._translate_single_string_fallback(
                        _src_text=src_items[0],
                        target_lang=target_lang,
                        termbase_block=termbase_block,
                    )
```

- [ ] **Step 5: Run the tests, lint, types**

Run: `venv/bin/python -m pytest tests/test_termbase_glossary.py -v` → all pass.
Run: `venv/bin/python -m pytest -q` → `337 passed`, `0 failed`.
Run: `venv/bin/ruff check srt_translator tests` → `All checks passed!`
Run: `venv/bin/ruff format --check srt_translator/prompts/translation.py srt_translator/core/translator/translator.py tests/test_termbase_glossary.py` → clean (format those files if not).
Run: the mypy command from Global Constraints → `Success`.

- [ ] **Step 6: Commit**

```bash
git add srt_translator/prompts/translation.py srt_translator/core/translator/translator.py tests/test_termbase_glossary.py
git commit -m "fix(translator): pass the termbase glossary to the plain-string fallback

A single malformed JSON reply falls back to a plain-string prompt that
had no terminology section, so terminology depended on which recovery
path succeeded. The fallback now receives the batch's glossary; its
prompt is unchanged when the glossary is '(none)'.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Documentation, code comments and CHANGELOG

Only statements about the changed behaviour. Pre-existing claims about features that don't exist (hard/soft DNT precedence, tolerant DNT matching, collision filtering, the post-translation DNT reorder) belong to the separate docs-only change in §7 of the brief. Leave them untouched here.

**Files:**
- Modify: `docs/user-guide/quality-features.md`, `docs/user-guide/gui-manual.md`, `docs/user-guide/customizing-termbase.md`, `docs/user-guide/terminology.md`, `docs/developer/translation-core.md`, `docs/developer/technical-flow.md`, `docs/developer/model-config-plan.md`, `CHANGELOG.md`

- [ ] **Step 1: `docs/user-guide/quality-features.md`**

Replace the whole `### 3. Relevant Termbase Injection` section, from its heading up to (not including) `### 4. Termbase Size Capping`, with:

```markdown
### 3. Relevant Termbase Glossary

Termbase entries reach the AI in two ways:

1. **Find-and-replace, before translation.** Each English termbase term found in a subtitle is replaced with its translation before the subtitle is sent. Matching ignores case and uses whole words. The AI sees the replacement as input and usually keeps it, but can still reword it, so this is strong guidance rather than a guarantee.
2. **Glossary hint, in the AI's instructions.** The instructions list the termbase entries whose English is still present in a subtitle of the batch after step 1. These are mainly plurals and possessives ("fulfillment centers", "the deck's"), and entries whose translation is the same as the English, which find-and-replace cannot enforce. Terms already replaced are not repeated. If nothing is relevant, the list reads "(none)".

**How the glossary matches**: one subtitle at a time (a term split across two subtitles is not matched); ignoring case; allowing any spacing between words. The term must start at a word boundary and may end with `s`, `es`, `'s` or `’s`: "processes" matches `process`, "processor" does not. Irregular plurals and hyphen variants are not matched.

**Benefits**:
- Small, focused instructions: most batches carry no glossary at all
- Plurals and keep-in-English entries are hinted instead of ignored
```

Delete the whole `### 4. Termbase Size Capping` section, from its heading up to (not including) `## Technical Implementation`. No such cap exists.

- [ ] **Step 2: `docs/user-guide/gui-manual.md`**

(a) After the sentence ending "Each target language can have up to one termbase." in the **Termbase** bullet, append, in the same bullet:

```markdown
 During translation, the app replaces each termbase term it finds in a subtitle with your preferred translation before sending it to the AI, and lists any remaining relevant terms (such as plurals) as hints in the AI's instructions. The AI usually follows both, but can still change the wording, so check important terms.
```

(b) Replace the sentence `The SRT Translator passes your DNT list to the AI and also pre-protects it so it survives translation intact.` with:

```markdown
The SRT Translator protects each DNT phrase before translation by swapping it for a placeholder the AI must keep, then puts the phrase back afterwards. Matching is exact, including capitalization, so add each spelling you use (for example, both "SKU" and "SKUs"). If a word inside a DNT phrase also has a termbase entry, the termbase entry is applied first and can break the phrase.
```

(c) Replace `Unlike the DNT list, the Termbase tells the translator how to translate important terms, ensuring consistency across all your videos.` with:

```markdown
Unlike the DNT list, the Termbase tells the translator how to translate important terms. The app substitutes your preferred translation before translation and hints any remaining matches (such as plurals) in the AI's instructions, which keeps terminology consistent across your videos.
```

(d) Replace `4. **Translate with instructions** — The AI receives your DNT list, Termbase, and subtitle-specific constraints` with:

```markdown
4. **Translate with instructions** — Termbase terms are substituted and DNT phrases are protected as placeholders; the AI receives the subtitles, a short glossary of any remaining relevant termbase entries, and subtitle-specific constraints
```

(e) Under `### Some terms should have stayed in English.`, append to the paragraph:

```markdown
 Matching is exact, including capitalization. If a word inside the phrase also has a termbase entry, remove or adjust that entry, because it is applied first and can break the phrase.
```

(f) Under `### A business term needs a specific translation.`, replace `The translator will apply your preference whenever it finds the term.` with:

```markdown
The app substitutes your preference wherever the exact term appears in a subtitle, and hints it to the AI for plurals and possessives. A term split across two subtitles is not matched.
```

- [ ] **Step 3: `docs/user-guide/customizing-termbase.md`**

Replace the paragraph starting `When customizing a termbase, auto-generate obvious variants` with:

```markdown
When customizing a termbase:

- **Capitalization variants are unnecessary.** Matching ignores case.
- **Hyphenation variants are needed** ("single-threaded" and "single threaded"). Add each as its own key.
- **Plurals and possessives** are hinted to the AI automatically when only the singular is listed. If the plural must be forced (for example, where the target language's plural differs), add it as its own key with the plural translation.
- **Entries whose translation is the same as the English** (names to keep in English) are hints only, because find-and-replace cannot change the text. To keep a name exactly as written, add it to the DNT list instead. DNT matching is exact, including capitalization, and a termbase entry for a word inside the DNT phrase is applied first and can break it.

The AI prompt that generates termbases already asks for variants, but double-check the results.
```

- [ ] **Step 4: `docs/user-guide/terminology.md`**

Replace `- **Term Handler**: DNT replacement and restoration` with:

```markdown
- **Term Handler**: termbase find-and-replace, plus DNT placeholder replacement and restoration (the prompt glossary is built in `translator.py`)
```

- [ ] **Step 5: `docs/developer/translation-core.md`**

Replace the bullet list under `## DNT placeholders & termbase` (the three bullets up to the following `---`) with:

```markdown
- The translator receives one language's flat termbase `{source: target}` (from `config.termbase.get(lang_code, {})`). A nested `{language: {source: target}}` mapping raises `TypeError` (`ensure_flat_termbase`).
- Pre-translation, per subtitle: termbase find-and-replace (case-insensitive, whole word, longest first), then DNT placeholder application (`__DNT_TERM_n__`, exact case).
- Prompt: the TERMINOLOGY glossary (`build_termbase_block`) lists termbase entries still present in at least one subtitle of the batch after substitution, matched per subtitle, with optional `s`/`es`/`'s`/`’s` endings. Otherwise it is "(none)". The plain-string fallback prompt receives the same glossary.
- Post-translation: DNT placeholders are restored. Termbase substitutions are not re-applied to the output; substitution is model input, not output enforcement.
- Pair-retry (in-batch) always uses **placeholder-applied** source strings.
```

- [ ] **Step 6: `docs/developer/technical-flow.md`**

In the High-Level Diagram, replace:

```
  1) Subtitle Batching
     - 5 input subtitles → 1 batch of 5 subtitles (context preserved)
            │
            ▼
  2) JSON-Formatted Batch Request
```

with:

```
  1) Subtitle Batching
     - 5 input subtitles → 1 batch of 5 subtitles (context preserved)
            │
            ▼
  1b) Terminology (per subtitle)
     - Termbase find-and-replace, then DNT placeholders
     - Prompt glossary: termbase entries still present, else "(none)"
            │
            ▼
  2) JSON-Formatted Batch Request
```

- [ ] **Step 7: `docs/developer/model-config-plan.md`**

Replace the two lines:

```
Each call receives only 5–8 subtitle cues, the DNT list (~30 phrases), and the matching
subset of termbase entries — a small, bounded prompt. Context window size is irrelevant.
```

with:

```
Each call receives only 5–8 subtitle cues (termbase terms already substituted, DNT phrases
replaced by placeholders) and a short glossary of any termbase entries still present — a
small, bounded prompt. Context window size is irrelevant.
```

- [ ] **Step 8: `CHANGELOG.md`**

Immediately before the line `## [1.0.0] - 2025-02-12`, insert:

```markdown
### Fixed
- **The termbase glossary now reaches the AI.** Since August 2025 the TERMINOLOGY section of the translation instructions was always "(none)": the translator received each language's termbase in a different shape from the one the glossary builder expected, and the builder also lowercased the language code. The glossary now lists the termbase entries still present in each batch after find-and-replace (mainly plurals, possessives and keep-in-English entries), and the plain-string fallback gets the same list. Expect small changes in translations where these occur.
- The translator now rejects a nested `{language: {term: translation}}` termbase at its boundary with a clear `TypeError`, instead of merging languages.

### Removed
- The post-translation termbase "restore" step, which never had an effect in the app.
- The unused `allow_global_termbase_fallback` translator parameter.

```

- [ ] **Step 9: Check for leftovers**

Run: `grep -rn "Termbase Size Capping\|30 terms per language\|passes your DNT list to the AI\|receives your DNT list\|whenever it finds the term\|DNT replacement and restoration" docs README.md`
Expected: no output.

- [ ] **Step 10: Commit**

```bash
git add docs CHANGELOG.md
git commit -m "docs: describe how termbase entries actually reach the model

Corrects the glossary, restore-step and payload descriptions, removes
the nonexistent 30-term cap, and qualifies the DNT advice (exact case;
an overlapping termbase entry is applied first). Pre-existing claims
about unimplemented DNT features are left for a separate docs change.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Verification and hand-off

**Files:**
- Modify (only if the figures differ): `plans/2026-11-23-terminology-pipeline-brief.md` §5

- [ ] **Step 1: Full checks**

Run: `venv/bin/python -m pytest -q` → `0 failed`, `0 xfailed`.
Run: `venv/bin/ruff check srt_translator tests` → `All checks passed!`
Run: `venv/bin/ruff format --check srt_translator tests` → only the pre-existing `tests/test_translation_retry_status.py`.
Run: the mypy command from Global Constraints → `Success`.

- [ ] **Step 2: Docs build**

Run: `venv/bin/python -m pip install -e '.[docs]'` (only if `venv/bin/mkdocs` is missing), then `venv/bin/mkdocs build --clean --site-dir "$(mktemp -d)"`.
Expected: the build completes. Any warning that mentions a file changed in Task 5 must be fixed.

- [ ] **Step 3: Confirm no private content entered the public repo**

Run: `git diff main --stat` and `git diff main | grep -n -i -E "/Users/|course|reviewer"`
Expected: only the files listed in this plan; the grep shows nothing beyond generic wording in the plan and brief.

- [ ] **Step 4: Re-measure the glossary size with the final implementation (owner's private data)**

The brief's §5 figures (5.6% zh-Hans / 9.2% pt-BR of batches, at most 3 entries) came from a dry-run script that re-implemented the rule. The owner runs the private dry-run against the merged configurations, outside this repo, with `build_termbase_block` imported from this branch. If the figures differ, update §5 of the brief and commit:

```bash
git add plans/2026-11-23-terminology-pipeline-brief.md
git commit -m "docs: refresh glossary-size figures from the final implementation

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 5: Hand off**

Report to the owner:
- the commit list (`git log --oneline main..`);
- test counts before and after;
- any deviation from this plan.

Don't push, open a PR or merge; those are the owner's decisions. After merging, delete the branch locally and remotely.

---

## Out of scope (tracked in the brief, §9)

- DNT/termbase overlap (B8): the reverse containment check in `srt_boundary_review`, and DNT-before-termbase ordering.
- The separate docs-only change for unimplemented DNT features.
- Before/after translation-quality measurement on a real course (brief §6). It happens at the next planned re-translation, which waits for two things: English source approval, and the course terminology review that removes unsafe forced mappings (brief §10). It uses a small fixed evaluation set kept in the owner's private files.
- The output review after re-translation (meaning errors, exact identifiers, cross-cue terms), alongside the separate Chinese line-alignment work.
