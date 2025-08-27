# Translator Architecture (SRT → SRT)

This document is the one-pager for anyone touching the translator core. It explains **where** batching, retries, DNT handling, and writing happen; the **non-negotiable invariants**; and the **logs** you should expect when resilience kicks in.

---

## High-level flow

translate_file()
├─ parse input SRT → List[Subtitle] (start, end, text)
├─ build sentence-aware batches (size ≈ 5–8 items)
├─ for each batch:
│ ├─ _translate_batch_json(src_items, target_lang, termbase, batch_ids)
│ ├─ restore DNT placeholders back into the model output
│ ├─ guard: in-batch empty target → one-shot pair-retry with next cue
│ ├─ if last item still empty → defer cross-batch pair-retry
│ ├─ append batch outputs to global result
│ └─ fulfill any deferred cross-batch pair-retry using head of next batch
└─ render_srt(all target texts, original timings)


**Important:** `_translate_batch_json()` may call a private salvage helper to coerce a *non-JSON* model response back into valid JSON. It must **not** change item counts; 1:1 parity with the batch is non-negotiable.

---

## Non-negotiable invariants

- **1:1 cue parity** with the source. The number of cues in the target **must** equal the source.
- **Preserve timings**. Start/end times for each cue are **identical** to the source.
- **Never paste source text** into the target to "paper over" empties.
- **Always emit** an SRT block—even if the translated text is empty. (This keeps IDs/timing stable and makes issues visible to the evaluator.)

---

## DNT placeholders & termbase

- Pre-translation: source cue text is passed through DNT placeholder application (`__DNT_TERM_n__`).
- Post-translation: placeholders are restored back into the translated text.
- Pair-retry (in-batch or cross-batch) always uses **placeholder-applied** source strings.

---

## Batching & retries

### In-batch pair-retry (existing)
When cue `i` is empty and `i+1` exists **in the same batch**, make one retry with the pair `(i, i+1)`. If the first returned item is non-empty, fill `i`. Else:
- **STRICT**: raise
- **BOUNDED/DEV**: leave empty (evaluator flags it)

### Cross-batch pair-retry (new)
The model sometimes under-runs on the **last item of a batch**. When the last item is empty:
1) **Defer** a one-shot pair retry into a small structure `{ cue_index, source_text_with_placeholders, out_index }`.
2) After translating the **next** batch, perform a two-item call with the deferred source and the **first** cue of the new batch. If non-empty, patch the output at `out_index`. Otherwise treat as above (STRICT → raise, BOUNDED/DEV → leave empty).

> We only keep **one** deferred slot at a time, resolved immediately on the next batch.

---

## Writer behavior

`render_srt(subs: Sequence[Subtitle], texts: Sequence[str])` emits **every** cue:
<index> <start> --> <end> <translated text or empty line>
An empty line for the text is intentional and correct. It preserves structure, and the evaluator can then flag **Missing translation** cleanly.

---

## Logging lexicon

- `INFO Processing <n> subtitles in batch <k>/<K>`
- `INFO Empty target at idx=<id>; attempting pair retry with next cue.`
- `INFO Pair retry filled idx=<id> successfully.`
- `WARNING Pair retry failed for idx=<id>: <err>`
- `INFO Deferred cross-batch pair retry for end-of-batch empty at idx=<id>.`
- `INFO Empty target at idx=<id>; attempting pair retry with next cue across batch boundary.`
- `ERROR Empty translation for subtitle idx=<id>; leaving empty for evaluator.`

These lines are intentionally specific so you can search logs and quickly spot which resilience path fired.

---

## Troubleshooting checklist

- **Missing translations spike?**
  - Check for boundary empties (8th item of a batch). Look for `Deferred cross-batch pair retry…` followed by cross-batch logs.
- **Numbers mismatches "move" around?**
  - Likely a prior missing/empty caused alignment drift. Once empties are filled (or rendered as empty without dropping blocks), numbers stabilize.
- **Cue count mismatch?**
  - Should never happen post-fix. If it does, fail fast—do not attempt to invent or drop cues.
