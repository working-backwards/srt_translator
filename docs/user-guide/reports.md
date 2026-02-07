# Evaluation Reports

After each translation, the evaluator runs automatically and writes artifacts to your batch folder.

> **Tip:** If reports show brand/term issues, go back to **AI Config**, put your most term-dense files first, **Regenerate**, then re-translate. See **Create AI Config** for the workflow.

## Configuration and Pipeline

- **Rubric:** `config/translation_rubric.yaml` (project-level). This defines thresholds and reporting behavior. It is **not** overridden at runtime.
- **AI Config:** `_artifacts/ai_config.json` (single source of truth). Contains DNT terms, termbase, and target languages.
- **Unified Pipeline:** The evaluator orchestrates all report generation in one pass:
  1. **Evaluator** writes `eval_report.json` (raw evaluation data with issue details)
  2. **Compiler** creates `report_v1.json` (single source of truth for presenters)
  3. **Presenters** render `eval_report.md` and `eval_report.html` from compiled data only
- **No Double Rendering:** GUI and CLI call the orchestrator; no direct presenter calls elsewhere.

## What the evaluator writes

In the `_artifacts/` directory:

- `eval_report.json` — Raw evaluation data (internal format)
- `report_v1.json` — Compiled report data (single source of truth for presenters)
- `eval_report.md` — Creator-friendly Markdown report
- `eval_report.html` — Interactive HTML report
- `ai_config.json` — Configuration snapshot used for evaluation

In `_artifacts/<lang>/` directories:
- Per-language CSVs and summaries (DNT coverage, termbase coverage, untranslated after DNT, optional fragments)
- **Fragments CSV** is only written when non-empty and the rubric's fragments policy applies (e.g., non-Latin scripts under `auto_non_latin`)

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
