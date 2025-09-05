# Evaluation Reports

After each translation, the evaluator runs automatically and writes artifacts to your batch folder.

> **Tip:** If reports show brand/term issues, go back to **AI Config**, put your most term-dense files first, **Regenerate**, then re-translate. See **Create AI Config** for the workflow.

## Where config is discovered

- **Rubric:** `config/translation_rubric.yaml` (project-level). This defines thresholds and reporting behavior. It is **not** overridden at runtime.
- **DNT / Termbase:** the **client writes** these to the **batch root**:
  - `dnt_summary.json` — **audit mirror** of DNT terms (optional; not used by eval).
  - `termbase_summary.json` — **audit mirror** of termbase (optional; not used by eval).

> The evaluator **does not** fall back to `ai_config.json`. If you want DNT/TB coverage, ensure those two JSON files are written to the batch root.

## What the evaluator writes

At the batch root:

- `eval_report.md` — creator-friendly, consolidated punch list (shows **all** issues).
- `artifacts/<lang>/…` — per-language CSVs and summaries (DNT coverage, termbase coverage, untranslated after DNT, optional fragments).
  - DNT/TB snapshots **may** be copied into each `artifacts/<lang>/` as `dnt_summary.json` / `termbase_summary.json` for auditing. Evaluation does **not** read them.
  - **Fragments CSV** is only written when non-empty and the rubric's fragments policy applies (e.g., non-Latin scripts under `auto_non_latin`).

## Re-running evaluation

After translation is complete, you can re-run the evaluator to regenerate artifacts:

```bash
# From within the batch directory
st-eval

# From anywhere, specifying the batch path
st-eval --batch-root "path/to/translation-batch-YYYYMMDD_HHMMSS"

# With verbose logging
st-eval -v
```

This rewrites only the evaluation artifacts (CSV/JSON/MD under `artifacts/…`) and leaves your translated SRT files untouched.

## Reporting behavior

- **Untranslated after DNT:** ignores trivial single-word cognates; upper-case acronyms are **INFO** unless covered by DNT/TB.
- **Missing translation:** empty cues are listed explicitly.
- **Timing drift:** omitted unless there are findings.

## Language labels

The report uses the **language config abstraction** (`srt_translator.core.config.language_config`) to resolve friendly names. The source language label comes from `manifest.json` (`original_language.name`/`code`) when available.

Edit SRTs in any text editor. Keep the **cue number** and **timings** unchanged; only modify the subtitle text.

## Global fragments policy

- Rubric key: `fragments.mode` (`auto_non_latin` | `always` | `never`), with `min_ascii_run`.
- Default is `auto_non_latin`: generate the source-fragments CSV only when the **target text** is predominantly non-Latin script.
