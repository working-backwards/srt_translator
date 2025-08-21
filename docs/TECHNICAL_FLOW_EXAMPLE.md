# Subtitle Translation Flow — Current System (Module 0 → Spanish)

This page documents the **actual** end-to-end pipeline the app runs **today** using the **subtitle-based translation system**, including what the **smart subtitle formatter** does and how it ensures high-quality output with proper word-boundary trimming.

---

## High-Level Diagram

```
      Source SRT (EN)
            │
            ▼
  1) Subtitle Batching
     - 5 input subtitles → 1 batch of 5 subtitles (context preserved)
            │
            ▼
  2) JSON-Formatted Batch Request
     - {"items":[{"id":1,"src":"..."},...]} with strict 1:1 mapping requirement
            │
            ▼
  3) Model Response
     - JSON format: {"items":[{"id":1,"tgt":"..."},...]}
     - Fallback handling for non-JSON responses
     - Strict ID matching ensures 1:1 subtitle mapping
            │
            ▼
  4) Smart Subtitle Formatter (per subtitle)
     - Word-boundary trimming with ellipsis
     - Tiny-window exceptions (+20% for <1s subtitles)
     - 2-line wrapping with orphan prevention
     - CPS enforcement with overshoot policy
            │
            ▼
  5) Post Checks (Fixer)
     - Phantom placeholders, structure checks
            │
            ▼
  6) Artifacts + Output SRT
     - Per-language artifacts, logs
     - Final SRT with original timings/subtitle count
```

---

## Inputs (this example)

- **File**: `Operating Plan Module 0.srt` (5 subtitles)
- **Target**: Spanish (`es`)
- **Language config**: `languages.json` (CPS limits, rules)
- **AI config (optional)**: DNT/Termbase if present
- **Batch size**: 5 (entire file is one batch here)

---

## JSON Payload We Send (Subtitle-based)

```json
{
  "items": [
    {"id": 1, "src": "Colin Bryar: Hi, and welcome to our class on mastering the operating cadence. My name's Colin Bryar"},
    {"id": 2, "src": "I spent 12 years at Amazon as a Technical Vice President and served two years with Jeff Bezos"},
    {"id": 3, "src": "as his chief of staff."},
    {"id": 4, "src": "Bill Carr: Hi, I'm Bill Carr. I spent 15 years at Amazon as a Vice President of Digital Media, working"},
    {"id": 5, "src": "on Amazon Music and Prime Video. Let's get started."}
  ]
}
```

> The prompt instructions enforce strict JSON contract: the model **must** return exactly 5 items with matching IDs. This prevents subtitle fusion/splitting and maintains perfect 1:1 mapping.

---

## Model Response (JSON Format) → Parsed Items

The model returns properly formatted JSON with exact ID matching:

```json
{
  "items": [
    {"id": 1, "tgt": "Colin Bryar: Hola, y bienvenidos a nuestra clase sobre cómo dominar el ritmo operativo. Me llamo Colin Bryar."},
    {"id": 2, "tgt": "Pasé 12 años en Amazon como Vicepresidente Técnico y serví dos años con Jeff Bezos."},
    {"id": 3, "tgt": "como su jefe de personal."},
    {"id": 4, "tgt": "Bill Carr: Hola, soy Bill Carr. Pasé 15 años en Amazon como Vicepresidente de Medios Digitales, trabajando"},
    {"id": 5, "tgt": "en Amazon Music y Prime Video. Comencemos."}
  ]
}
```

At this point, **translation quality is intact** and the 1:1 mapping is preserved. Note that item 3 shows "como su jefe de personal" (complete phrase) before any formatting is applied.

---

## Smart Subtitle Formatter — How Text Is Formatted Per Subtitle

For each subtitle *i*, the smart formatter **applies intelligent formatting** to the translated text within the **original subtitle i's** timing window:

- **CPS caps** from `languages.json` (per language):
  - `cps_soft`: soft reading limit
  - `cps_hard`: hard limit the subtitle should not exceed
- **Overshoot tolerance**: a small cushion (≈ **+10%** over `cps_hard`) is allowed **before** trimming.
- **Tiny-window exception**: For subtitles under 1 second, an additional **+20%** allowance is added to preserve important short phrases.
- **Word-boundary trimming**: Never cuts mid-word; adds ellipsis "…" when trimming is required.
- **Smart line wrapping**: Wraps long text to max 2 lines with language-specific orphan prevention.

### Why the Smart Formatter Preserves Quality
- **Subtitle 3**: Original duration 0.96 seconds (very short)
- **Without tiny-window exception**: Would be trimmed to ~19 characters → "como su jefe de…"
- **With tiny-window exception**: Gets +20% allowance → ~25 characters → "como su jefe de personal." ✅
- **Result**: Complete meaningful phrase preserved instead of awkward mid-word cut

This is **working as designed**: we preserve important short phrases while maintaining readability and sync. The system intelligently balances timing constraints with content preservation.

---

## Post-Translation Checks

- **Fixer** runs (phantom placeholders, structural sanity) — none found in this run.
- **Artifacts** saved (per language): raw/parsed outputs, logs, the final SRT.

---

## What to Watch in Logs

- `JSON batch input:` — the JSON payload we send with subtitle items
- `JSON batch raw output:` — the model's JSON response
- `JSON batch parsed N items:` — count integrity (should match input count)
- `Subtitle trim (lang=…)` — smart trimming occurred with tiny-window exception info
- `=== Translation Summary ===` — totals + artifact paths

---

## Notes on Design Trade-offs

- If a translated line is **too long** for its time window, the smart formatter **trims on word boundaries** rather than stretching timing or changing counts. This preserves sync and readability while avoiding mid-word cuts.
- **Tiny-window exception**: Short subtitles (under 1 second) get extra allowance to preserve meaningful phrases.
- In Spanish intros, a **leading speaker label** can push otherwise fine lines over the cap. The system intelligently handles this with:
  - Smart word-boundary trimming with ellipsis
  - Tiny-window exceptions for very short subtitles
  - 2-line wrapping when beneficial

---

### Glossary

- **Subtitle**: One timed on-screen text block (start → end).
- **Subtitle-based processing**: Translation system that processes each subtitle individually while maintaining exact timing alignment.
- **Smart formatting**: Intelligent text formatting with word-boundary trimming, line wrapping, and tiny-window exceptions.
- **CPS**: Characters per second; a simple proxy for readability within a duration.
- **Tiny-window exception**: Additional CPS allowance (+20%) for subtitles under 1 second to preserve important short phrases.
