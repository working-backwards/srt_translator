# Design brief: fix the termbase pipeline (prompt glossary, restore step, docs)

**Status:** revision 2, after review. **No code has changed yet.**
**Date:** 2026-11-23
**Branch:** `fix/terminology-pipeline`, from `main` at `b6eb630` (release v1.2).
**Implementation plan:** `plans/2026-11-23-terminology-pipeline-plan.md`

| Revision | Commit | Change |
|---|---|---|
| 1 | `40bebd2` | First version, sent for review. |
| 2 | this commit | Review adopted. Glossary matches within each subtitle only (cross-cue matching cut). Glossary added to the plain-string fallback. Validation accepts the `MappingProxyType` the app actually passes. Tests go through the real config boundary. Factual corrections and re-measured figures. |

---

## 1. Background

SRT Translator lets a user supply a **termbase**: per-language `{English term: preferred translation}` pairs, alongside a **DNT** (do-not-translate) list. A review of translated output showed terms not being applied as configured. Tracing the code found that the termbase reaches the model by only one of the two routes it was designed to use, and that the documentation describes behaviour the code doesn't have.

**This brief covers only the termbase plumbing in this repo.** Separate, related work elsewhere:
- a post-translation script that re-cuts Chinese subtitle lines (a separate repo, with its own brief later);
- English source corrections;
- terminology data fixes.

## 2. How terminology works today (verified by reading and running the code)

```
English cue ──► (1) termbase find-and-replace ──► (2) DNT → placeholders ──► prompt ──► model
                    per cue, case-insensitive          case-sensitive              │
                    English term replaced by           __DNT_TERM_n__              │
                    the TARGET-language string                                     ▼
                                                           (3) "TERMINOLOGY:" glossary section
                                                               ALWAYS "(none)"  ← bug
model output ──► (4) restore DNT placeholders ──► (5) restore_termbase  ← runs, has no effect (bug)
```

| Step | Code | Today |
|---|---|---|
| 1. Hard find-and-replace | `TermHandler.apply_termbase`, `srt_translator/core/translator/term_handler.py:164` | **Works.** Each English term in a cue is replaced with its target-language string *before* the model sees it. The model therefore does see the substituted translations, but it can still rewrite them: this is input, not enforcement of the output. |
| 2. DNT placeholders | `TermHandler.apply_dnt_placeholders`, `term_handler.py:118` | Works, but runs *after* step 1, so a termbase entry inside a DNT phrase breaks the phrase first (§3, B8). |
| 3. Prompt glossary | `build_termbase_block`, `srt_translator/core/translator/translator.py:195`; `srt_translator/prompts/translation.py:64` | **Broken.** The explicit glossary section is always `(none)`. |
| 4. DNT restore | `TermHandler.restore_dnt_placeholders` | Works. |
| 5. Termbase restore | `TermHandler.restore_termbase`, `term_handler.py:176`; called at `translator.py:558, 733, 832` | **Runs, but has no effect** in the app. |

## 3. Bugs found

| # | Bug | Evidence | Since |
|---|---|---|---|
| B1 | **Glossary gets the wrong shape.** `core/main.py:155` passes the flat per-language mapping `{term: translation}`. `build_termbase_block()` expects `{lang: {term: translation}}`, looks for a language key, finds none, and returns `(none)`. (Edge case: a source term spelled exactly like the lowercased language code raises `AttributeError` instead.) | Called directly: flat input → `'(none)'` | `83669f5` (2025-08-23) |
| B2 | **Glossary lowercases the language code.** Even with the nested shape it looks up `zh-hans`, while the keys are `zh-Hans` and `pt-BR`. | nested with `zh-Hans` key → `'(none)'`; only a lowercase key works | same function |
| B3 | **The restore step has no effect.** It is called, but it is built from the same flat mapping, so its per-language lookup always misses. With the nested shape it would work (`share price` → `股价`). | `restore_all('… share price …', 'zh-Hans')` leaves the English unchanged | never effective in the app |
| B4 | **The tests use a different shape from the app.** `tests/test_prompts_snapshot.py:49` builds `SRTTranslator` with a nested **French** termbase, so the glossary works there. `tests/test_golden_srt.py:117` passes a nested **Spanish** termbase to every target language (es, zh-Hans, fr). With the nested shape, `TermHandler` merges every language's entries into one find-and-replace table. | read | — |
| B5 | `allow_global_termbase_fallback` is stored and never read. | `translator.py:337/353`, `main.py:157` | — |
| B6 | **No tests** cover `build_termbase_block`, `TermHandler` termbase behaviour, or the path from configuration to prompt. | `tests/` | — |
| B7 | **The plain-string fallback has no glossary.** A single malformed JSON reply falls back to `_translate_single_string_fallback` (`translator.py:1192`), whose prompt (`prompts/translation.py:92`) has no terminology section. | read | — |
| B8 | *(pre-existing; not fixed here)* **A termbase entry inside a DNT phrase breaks the phrase**, because step 1 runs before step 2. Real case: a DNT book title containing a word that also has a zh-Hans termbase entry was translated in the live zh-Hans output; pt-BR, which has no such entry, kept it. | reproduced; one live case across 8 merged configs | — |

**User-visible effect of B1 + B2** (measured on five real courses, 8,064 cues):
- A three-word product name was configured in the pt-BR termbase to **stay in English** (an "identity" entry, translation = English).
- The find-and-replace can't enforce an identity entry, because the text doesn't change. With the glossary empty, the model was never told either.
- The live pt-BR output translated the name in **68 of 71** occurrences and kept it in English in 3.

## 4. What the fix changes

1. **Flat mapping at the translator boundary only.**
   - The configuration format (nested by language) does not change.
   - `SRTTranslator` and `TermHandler` take a flat `{term: translation}` mapping for one language, which is what `main.py` already passes. In practice that is a read-only `MappingProxyType`, so validation accepts any `collections.abc.Mapping`.
   - Passing a nested mapping (a dict or a proxy) **raises `TypeError`** instead of merging languages or crashing later.
2. **A working glossary, relevant entries only.**
   - Change: `build_termbase_block(termbase, src_items)`.
   - An entry is listed only if its English still appears in **at least one subtitle of the batch**, checked one subtitle at a time, **after** step 1. Terms already replaced aren't repeated.
   - **No matching across subtitles.** A term split over two cues is not listed. This avoids conflicting with the prompt rule that each subtitle is translated independently.
   - **Matching rule.** Case-insensitive. Words of a multi-word term may be separated by any whitespace. The term must start at a Unicode word boundary (`(?<!\w)`). It may be followed by one optional suffix (`s`, `es`, `'s` or `’s`), then must end at a word boundary (`(?!\w)`). So "processes" and "Fulfillment Centers" match; "processor" and "processing" don't. Irregular plurals and hyphen variants are not handled; this is an English-oriented heuristic.
   - **Entries that differ only in capitalisation and have the same translation** are listed once.
   - If nothing is relevant, the section stays `(none)`, as today.
3. **Glossary in the plain-string fallback.** The same block is passed to the fallback prompt, so behaviour doesn't depend on which recovery path succeeded.
4. **Remove the restore step** (`restore_termbase`, `termbase_target_map`). `restore_all()` restores DNT placeholders only. No output changes, because it never had an effect in the app.
5. **Remove `allow_global_termbase_fallback`** (B5). No behaviour change.
6. **Tests**, including one that goes through the real configuration boundary (§6).
7. **Docs and code comments** that describe these mechanisms are corrected (§7), plus a CHANGELOG entry.

**Not changed:**
- the find-and-replace itself (step 1), and its order relative to DNT (B8);
- DNT matching;
- the main prompt's wording and subtitle rules.

**Size [estimate]:**
- 4 code files, net fewer lines;
- 2 test files updated and 2 new;
- 7 doc files plus the CHANGELOG.

## 5. Decisions (owner and reviewer, 2026-11-23)

| Decision | Choice | Why |
|---|---|---|
| Glossary contents | **Relevant entries only, matched within each subtitle** | With the final rule, over 1,422 batches per language, **5.6%** (zh-Hans) and **9.2%** (pt-BR) of requests carry any entry, at most 3 lines. Measurement shows the size of a full list (35–60 lines on every request), not its quality effect; the choice keeps prompts focused and avoids wrong-sense hints. |
| Cross-cue matching | **Cut** (reviewer) | Worth only 2–4 batches across five courses, and it conflicts with the prompt's independent-subtitle rule. Revisit alongside the separate line-alignment work. |
| Restore step | **Remove** | It never had an effect; removing it changes no output. Making it work would be new behaviour. |
| Identity entries | **Hints only**; measure retention first (reviewer Q1) | Promoting them to DNT raises case, overlap and preservation-policy questions. |
| Find-and-replace | **Unchanged** for now (reviewer Q2) | Changing it would confound the evaluation of this repair. |
| Docs describing features the code lacks | **Correct the docs; log follow-ups**, in a **separate docs-only change** | Keeps this branch reviewable (§7). |
| Rollout | **Always on**, recorded in the CHANGELOG | The original intended behaviour. Measured before it's relied on (§6). |

## 6. Tests and measurement

**New `tests/test_termbase_glossary.py`:**
- `build_termbase_block`:
  - empty mapping → `(none)`;
  - unrelated term → excluded;
  - term already replaced → excluded;
  - plural, possessive (`'s` and `’s`) → listed;
  - extra whitespace or a line break inside a term → listed;
  - `processor` / `processing` → not listed;
  - a term split across two items → **not** listed;
  - identity entry → listed;
  - capitalisation duplicates → listed once;
  - order follows the termbase;
  - `MappingProxyType` input accepted.
- Termbase validation: proxy accepted; nested dict, nested proxy and non-mapping rejected; `None` → empty.
- `TermHandler`:
  - nested mapping raises `TypeError`;
  - a flat proxy replaces terms as before;
  - `restore_all` restores placeholders and leaves English words alone;
  - `restore_termbase` no longer exists.
- Fallback:
  - the fallback prompt includes the glossary when given one;
  - its text is unchanged when not;
  - a fake-client test drives `_translate_batch_json` into the fallback and checks the glossary reaches that prompt.

**New `tests/test_termbase_pipeline.py`:**
- Build the configuration with `TranslationConfig.from_raw()`, with a two-language termbase (`zh-Hans`, `pt-BR`).
- Run the real `translate_srt_files()`, mocking only the OpenAI client.
- Assert each language's prompts list only that language's entries: the plural and identity entries appear, and the other language's translations don't.
- This is the test that would have caught B1.

**Updated:**
- The snapshot test uses the flat shape; the expected prompt text is unchanged.
- The golden test passes each language only its own entries (`termbase.get(target_lang, {})`).

**Measurement before relying on it.** The next planned re-translation of one course (zh-Hans and pt-BR) is compared with the current output, holding source, terminology and model settings constant:
- identity-entry retention (today 3 of 71);
- consistency of plural terms;
- **no regression** in Chinese line drift, using the existing private measurement scripts.

The glossary-size figures in §5 are re-measured with the final implementation.

## 7. Documentation

**In this branch** (statements about the glossary, the restore step, the termbase flow, and what reaches the model):

| File | Change |
|---|---|
| `docs/user-guide/quality-features.md` | §3: describe the actual rule (after find-and-replace, within each subtitle, plurals and possessives). §4: remove the "30 terms per language" cap, which doesn't exist. |
| `docs/user-guide/gui-manual.md` | The termbase is described as both a find-and-replace and a glossary hint. "The AI receives your DNT list": correct it (DNT terms are protected as placeholders; the list itself isn't sent). Qualify "applies your preference whenever it finds the term", and the DNT advice (exact case; an overlapping termbase entry can break a DNT phrase). |
| `docs/user-guide/customizing-termbase.md` | Variant advice: capitalisation variants are unnecessary. Plurals and possessives are hinted; add a plural key to force one. Identity entries are hints. DNT protects exact-case phrases unless a termbase entry overlaps them. |
| `docs/user-guide/terminology.md` | The TermHandler description gains the termbase steps. |
| `docs/developer/translation-core.md`, `docs/developer/technical-flow.md` | Add steps 1 and 3 to the flow; note that substitution is input, not output enforcement. |
| `docs/developer/model-config-plan.md` | Correct the per-call payload description. |
| Code comments | `term_handler.py` class docstring; `translator.py:557` restore comment. |
| `CHANGELOG.md` | Unreleased → Fixed. |

**Separate docs-only change** (described but not implemented; each also logged as a follow-up):
- hard/soft DNT precedence: `build_effective_dnt` exists and is tested but is never called;
- case-insensitive "tolerant" DNT matching;
- DNT-collision filtering, and its report fields `filtered_for_translation` / `collisions_removed`;
- the post-translation "search and reorder DNT terms" claim.

Mostly in `docs/user-guide/terminology.md` and `docs/user-guide/quality-features.md`, plus `docs/user-guide/gui-manual.md:417–419`.

## 8. Review outcome (revision 1 → 2)

Verdict: **approve with changes.** All changes are adopted in §3–§7.
- **Q1:** keep identity entries as hints; measure.
- **Q2:** defer find-and-replace changes.
- **Q3:** remove the restore step (its documented intent was a safety net for terms surviving translation; never effective in the app).
- **Q4:** the suffix rule is acceptable as a documented English-oriented heuristic, specified precisely (§4.2).
- **Q5:** cut cross-cue matching.

## 9. Follow-ups (not in this change)

- **B8 DNT/termbase overlap.** Extend the merge containment check in `srt_boundary_review` (`08492aa`) to flag a termbase key inside a DNT phrase. Separately, consider running DNT protection before the termbase.
- Hard/soft DNT precedence at runtime, or delete `build_effective_dnt`.
- Case- and variant-tolerant DNT matching.
- Moving ambiguous single-word entries from forced to hinted.
- Irregular plurals and hyphen variants in glossary matching.
- Making `under_ratio` / `oversize_ratio` act instead of only logging at debug (`translator.py:1113–1133`).
- Version reporting: three different version numbers in the package, the batch manifests and the release tag.
