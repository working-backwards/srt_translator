# Design brief: fix the termbase pipeline (prompt glossary, restore step, docs)

**Status:** for review. **No code has changed yet.**
**Date:** 2026-11-23
**Branch:** `fix/terminology-pipeline`, from `main` at `b6eb630` (release v1.2).

**What to review.** The design and the questions in §8. After review, a detailed task-by-task implementation plan will be written from this brief.

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
model output ──► (4) restore DNT placeholders ──► (5) restore_termbase  ← never takes effect (bug)
```

| Step | Code | Today |
|---|---|---|
| 1. Hard find-and-replace | `TermHandler.apply_termbase`, `srt_translator/core/translator/term_handler.py:164` | **Works.** Each English term in a cue is replaced with its target-language string *before* the model sees it. |
| 2. DNT placeholders | `TermHandler.apply_dnt_placeholders`, `term_handler.py:118` | Works. |
| 3. Prompt glossary | `build_termbase_block`, `srt_translator/core/translator/translator.py:195`; `srt_translator/prompts/translation.py:64` | **Broken: always `(none)`.** The model never sees the termbase. |
| 4. DNT restore | `TermHandler.restore_dnt_placeholders` | Works. |
| 5. Termbase restore | `TermHandler.restore_termbase`, `term_handler.py:176` | **Broken: a no-op.** |

## 3. Bugs found

| # | Bug | Evidence | Since |
|---|---|---|---|
| B1 | **Glossary gets the wrong shape.** `core/main.py:155` passes the flat per-language mapping `{term: translation}`. `build_termbase_block()` expects `{lang: {term: translation}}`, looks for a language key, finds none, and returns `(none)`. | Called directly: flat input → `'(none)'` | `83669f5` (2025-08-23) |
| B2 | **Glossary lowercases the language code.** Even with the nested shape, it looks up `zh-hans` while the keys are `zh-Hans` and `pt-BR`. | nested with `zh-Hans` key → `'(none)'`; only a lowercase key works | same function |
| B3 | **The restore step never takes effect.** It is built from the same flat mapping, so its per-language lookup always misses. | `restore_all('… share price …', 'zh-Hans')` leaves the English unchanged | never worked in the app |
| B4 | **The tests use a different shape from the app.** `tests/test_prompts_snapshot.py` and `tests/test_golden_srt.py` build `SRTTranslator` with the nested shape and a lowercase-safe code (`fr`), so the glossary works in tests and not in the app. With the nested shape, `TermHandler` would also merge *every* language's entries into one find-and-replace table. | read | — |
| B5 | `allow_global_termbase_fallback` is stored and never read. | `translator.py:337/353`, `main.py:157` | — |
| B6 | **No tests** cover `build_termbase_block`, `TermHandler` termbase behaviour, or the path from `main.py` to the prompt. | `tests/` | — |

**User-visible effect of B1 + B2** (measured on five real courses, 8,064 cues):
- A three-word product name was configured in the pt-BR termbase to **stay in English** (an "identity" entry, translation = English).
- The find-and-replace can't enforce an identity entry, because the text doesn't change. With the glossary empty, the model was never told either.
- The live pt-BR output translated the name in **63 of 71** occurrences.

## 4. What the fix changes

1. **One termbase shape everywhere.** `SRTTranslator` and `TermHandler` take a **flat `{term: translation}` mapping for one language**, which is what the app already passes. Type hints change to `Mapping[str, str]`. Passing the nested shape **raises `TypeError`** instead of silently merging languages.
2. **A working glossary, relevant entries only.**
   - Change: `build_termbase_block(termbase, src_items)`.
   - It lists an entry only if its English still appears in the batch text **after** step 1, joined across cues.
   - Matching is case-insensitive and whitespace-tolerant, and allows a plural or possessive suffix (`s`, `es`, `'s`). That excludes accidental matches such as "process" in "processor".
   - So the glossary carries exactly what the find-and-replace couldn't handle:
     - plurals and other variants;
     - identity entries;
     - the rare term split across two cues.
   - Terms already replaced aren't repeated. If nothing is relevant, the section stays `(none)`, as today.
3. **Remove the restore step** (`restore_termbase`, `termbase_target_map`). `restore_all()` restores DNT placeholders only. No output changes, because it never took effect.
4. **Remove `allow_global_termbase_fallback`** (B5). No behaviour change.
5. **Tests**, including the end-to-end test that would have caught B1 (§6).
6. **Docs and code comments** that describe these mechanisms are corrected (§7), plus a CHANGELOG entry.

**Not changed:**
- the find-and-replace itself (step 1);
- DNT matching;
- the prompt wording;
- the subtitle rules in the prompt.

**Size [estimate]:**
- about 4 code files, net fewer lines (deletions outweigh additions);
- 2 test files updated and 1 new;
- about 8 doc files touched.

## 5. Decisions already taken (owner, 2026-11-23)

| Decision | Choice | Why |
|---|---|---|
| Glossary contents | **Relevant entries only** | Measured over 1,422 batches per language: only **6%** (zh-Hans) and **10%** (pt-BR) of batches would carry any entry, at most 3 lines. A full list would add 35–60 lines to every request for no gain, and invite wrong-sense use. |
| Restore step | **Remove** | It never ran; removing it changes no output. Making it work would be new behaviour, with a risk of rewriting English the model kept on purpose or DNT names that contain a termbase word. |
| Docs describing features the code lacks | **Correct the docs; log the features as follow-ups**, in a **separate docs-only change** | Keeps this branch reviewable. See §7. |
| Rollout | **Always on**, recorded in the CHANGELOG | It is the original intended behaviour; a setting adds surface for little benefit. Measured before it's relied on (§6). |

## 6. Tests and measurement

**Unit tests (new: `tests/test_termbase_glossary.py`):**

`build_termbase_block`:
- empty mapping → `(none)`;
- a term already replaced in the cue → not listed;
- a term split across two items → listed;
- plural variant (`centers`) → listed;
- identity entry still present → listed;
- `processor` doesn't match `process`;
- case-insensitive;
- output order is stable.

`TermHandler`:
- a nested mapping raises `TypeError`;
- a flat mapping replaces as before;
- `restore_all` restores DNT placeholders and leaves English words alone.

**End-to-end test:**
- run `main.py`'s per-language construction with a two-language termbase (`zh-Hans`, `pt-BR`);
- use a fake client that captures the prompt;
- assert that the zh-Hans prompt lists only zh-Hans entries, and that it contains the identity and plural entries.

**Updated tests:** the snapshot and golden tests switch to the flat shape. The expected prompt text is unchanged.

**Measurement before relying on it.** The next planned re-translation of one course (zh-Hans and pt-BR) is compared with the current output:
- identity-entry retention (expect a large rise from 3 of 71);
- consistency of plural terms;
- **no regression** in Chinese line drift, using the existing private measurement scripts (automated drift rate, and a fixed-seed hand sample).

## 7. Documentation

**In this branch** (statements about the glossary, the restore step and the termbase flow):

| File | Change |
|---|---|
| `docs/user-guide/quality-features.md` | "Relevant-only" glossary section: describe the actual rule (after find-and-replace, joined across cues, plurals). Remove the "30 terms per language" cap, which doesn't exist. Keep "Relevant-only termbase injection" (now true). |
| `docs/user-guide/gui-manual.md` | Termbase described as both a find-and-replace and a glossary hint. Correct "the AI receives your DNT list and termbase": the termbase yes, the DNT list as placeholders only. |
| `docs/user-guide/customizing-termbase.md` | Variant advice: capitalisation variants are unnecessary; plurals are now hinted, but add a plural key if the translation must be forced; identity entries are hints, not guarantees, so use DNT to guarantee them. |
| `docs/user-guide/terminology.md` | The TermHandler description gains the termbase steps. |
| `docs/developer/translation-core.md`, `docs/developer/technical-flow.md` | Add steps 1 and 3 to the flow. Drop any mention of termbase restore. |
| `docs/developer/model-config-plan.md` | Correct the per-call payload description. |
| Code comments | `term_handler.py` class docstring; `translator.py` restore comment; `main.py:157` comment. |
| `CHANGELOG.md` | Unreleased → Fixed: glossary now reaches the model; restore step removed; termbase shape enforced. |

**Separate docs-only change** (features described but not implemented; each also logged as a follow-up):
- hard/soft DNT precedence: `build_effective_dnt` exists and is tested but is never called;
- case-insensitive "tolerant" DNT matching;
- DNT-collision filtering, and its report fields `filtered_for_translation` / `collisions_removed`;
- the claim that the DNT list itself is sent to the model.

Mostly in `docs/user-guide/terminology.md` and `docs/user-guide/quality-features.md`, plus `docs/user-guide/gui-manual.md:375, 417–419`.

## 8. Questions for the reviewer

1. **Identity entries.** Keep-in-English entries are only *hinted* by the glossary in this design. Should they instead be **enforced**, by treating them as DNT terms (placeholder-protected)? That would guarantee retention, but it changes DNT behaviour and DNT matching is case-sensitive. Current proposal: hint now, and decide after measuring retention.
2. **The find-and-replace stays as is.** It still forces one sense on ambiguous single words (e.g. "process" as a noun, also applied to the verb) and puts target-language text into the English. Once the glossary works, moving such entries from forced to hinted is the natural next step. Is it right to defer that so this change stays small and measurable?
3. **Removing the restore step.** It never took effect. Does anyone know a case it was meant to catch (introduced in `4af9c37`)?
4. **Relevance rule.** The plural-suffix rule (`s`, `es`, `'s`) assumes an English source. For non-English sources it would only match the bare term. It also inherits the existing `\w`-boundary limitation for scripts without spaces, the same as today's find-and-replace. Acceptable?
5. **Glossary vs. the "each line is independent" prompt rule.** A term split across two lines is now hinted while the prompt also tells the model to keep lines separate. Measured, this happens in only 3–5 batches across five courses, so the risk looks low. Any concern?

## 9. Follow-ups (not in this change)

- Hard/soft DNT precedence at runtime, or delete `build_effective_dnt`.
- Case- and variant-tolerant DNT matching.
- Moving ambiguous single-word entries from forced to hinted (Q2).
- Making `under_ratio` / `oversize_ratio` act instead of only logging at debug (`translator.py:1113–1133`).
- Version reporting: three different version numbers in the package, the batch manifests and the release tag.
