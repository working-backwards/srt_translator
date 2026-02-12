# Translator Architecture (SRT → SRT)

This document is the one-pager for anyone touching the translator core. It explains **where** batching, retries, DNT handling, and writing happen; the **non-negotiable invariants**; and the **logs** you should expect when resilience kicks in.

---

## High-level flow

translate_file()
├─ parse input SRT → List[Subtitle] (start, end, text)
├─ build sentence-aware batches (size ≈ 5–8 items)
├─ for each batch:
│ ├─ _translate_with_simple_shape_lock(src_items, ...) → handles retries/splits
│ ├─ restore DNT placeholders back into the model output
│ ├─ guard: in-batch empty target → one-shot pair-retry with next cue
│ └─ append batch outputs to global result
└─ render_srt(all target texts, original timings)


**Important:** `_translate_with_simple_shape_lock()` wraps `_translate_batch_json()` and handles retries, splits, and backoff. It must **not** change item counts; 1:1 parity with the batch is non-negotiable.

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
- Pair-retry (in-batch) always uses **placeholder-applied** source strings.

---

## Batching & retries

The translator has two layers of resilience for empty or invalid translations:

1. **Shape-lock** (first line): Catches invalid JSON, shape mismatches, and empty translations. Splits batches and retries with backoff.
2. **In-batch pair-retry** (fallback): If shape-lock exhausts its budget and an item is still empty, pairs it with the next cue for one more attempt.

### Iterative shape-lock with exponential backoff
When JSON parsing or shape validation fails, the system uses a bounded, iterative approach instead of recursion:

- **Maximum depth**: 3 split levels per segment
- **Retry budget**: 2 retries per single-item segment (retry 0 and retry 1)
- **Exponential backoff**: 250ms → 500ms
- **Circuit breaker**: Stops after 8 consecutive failures per file/lang

**Backoff progression:**
- **Retry 0**: 250ms base delay
- **Retry 1**: 500ms (2× base)
- **Retry 2+**: Not allowed (segment marked as empty)

Each new segment gets a fresh retry budget, so backoff doesn't compound across the entire file.

### In-batch pair-retry
When cue `i` is empty after shape-lock and `i+1` exists **in the same batch**, make one retry with the pair `(i, i+1)`. If the first returned item is non-empty, fill `i`. Else:
- **STRICT**: raise
- **BOUNDED/DEV**: leave empty (evaluator flags it)

---

## Writer behavior

`render_srt(subs: Sequence[Subtitle])` emits **every** cue (text is already in each Subtitle object):
<index> <start> --> <end> <translated text or empty line>
An empty line for the text is intentional and correct. It preserves structure, and the evaluator can then flag **Missing translation** cleanly.

---

## Logging lexicon

- `INFO Processing <n> subtitles for <filename>`
- `INFO Batch <k>/<K>: processing <n> subtitles (file=<filename> ids=[...])`
- `DEBUG Empty target at idx=<id>; attempting pair retry with next cue.`
- `DEBUG Pair retry filled idx=<id> successfully.`
- `DEBUG Pair retry failed for idx=<id>: <err>`
- `WARNING Empty translation for subtitle idx=<id>; leaving empty for evaluator.`

**Shape-lock and backoff logs:**
- `INFO Shape-lock failure (size=<n> depth=<d> retries=<r>): <error>`
- `WARNING Giving up on cue id=<id> after <n> retries; leaving empty.`
- `ERROR Circuit breaker hit after <n> consecutive failures; emitting empties for remaining segments.`
- `ERROR Shape-lock guard tripped; emitting empties for remaining <n> item(s).`

These lines are intentionally specific so you can search logs and quickly spot which resilience path fired.

---

## Troubleshooting checklist

- **Missing translations spike?**
  - Check for shape-lock failures: look for `Shape-lock failure` or `Giving up on cue` logs.
  - Check for in-batch retry failures: look for `Pair retry failed` logs.
- **Cue count mismatch?**
  - Should never happen. If it does, fail fast—do not attempt to invent or drop cues.
