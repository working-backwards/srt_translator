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
  4) Subtitle Formatter (per subtitle)
     - Space normalization
     - CPS cap warning (warn-only, no trimming)
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

## Subtitle Formatter — How Text Is Formatted Per Subtitle

For each subtitle *i*, the formatter applies minimal formatting to the translated text:

- **Space normalization**: Collapses multiple whitespace characters into single spaces
- **CPS cap check**: Compares characters-per-second against the language's `cps_cap` from `languages.json`
- **Warn-only policy**: If CPS exceeds the cap, a warning is logged but **no trimming or modification occurs**

The formatter intentionally does **not** perform:
- Text trimming or truncation
- Line wrapping or reflow
- Any content modification beyond space normalization

### Design Philosophy

The system preserves the model's translation output exactly as returned. CPS violations are surfaced as warnings in logs and flagged by the evaluator, allowing human review rather than automated text mutation.

---

## Post-Translation Checks

- **Fixer** runs (phantom placeholders, structural sanity) — none found in this run.
- **Artifacts** saved (per language): raw/parsed outputs, logs, the final SRT.

---

## What to Watch in Logs

- `JSON batch input:` — the JSON payload we send with subtitle items
- `JSON batch raw output:` — the model's JSON response
- `JSON batch parsed N items:` — count integrity (should match input count)
- `CPS over cap (lang=…)` — warning when subtitle exceeds CPS limit
- `=== Translation Summary ===` — totals + artifact paths

---

## Notes on Design Trade-offs

- If a translated line is **too long** for its time window, the formatter **logs a warning** but does not modify the text. This preserves the model's output exactly while surfacing issues for human review.
- The evaluator flags CPS violations in the evaluation report, allowing creators to manually adjust problematic subtitles if needed.
- This warn-only approach prioritizes translation accuracy over automated text mutation.

---

### Glossary

- **Subtitle**: One timed on-screen text block (start → end).
- **Subtitle-based processing**: Translation system that processes each subtitle individually while maintaining exact timing alignment.
- **CPS**: Characters per second; a simple proxy for readability within a duration.
- **CPS cap**: Per-language character-per-second limit defined in `languages.json`.
