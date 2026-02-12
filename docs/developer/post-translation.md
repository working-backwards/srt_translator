# Post-Translation Workflow

This document explains what happens after translation completes and how to interpret the results.

## Quick Start

After translation completes, open **`artifacts/eval_report.html`** in your browser.

This HTML report tells you everything you need to know:
- **Decision**: Pass (ready to use), Review (has warnings), or Fail (has errors)
- **Issues**: What problems exist and exactly how to fix them
- **File status**: Which files are ready, which need attention

For most workflows, this is all you need. The sections below explain how to dig deeper when necessary.

## When You Need More Detail

| Situation | What to check |
|-----------|---------------|
| Debugging a specific cue | Per-language CSVs in `artifacts/{lang}/` |
| Programmatic access | `eval_report.json` (raw) or `report.json` (structured) |
| Audit trail | `ai_config.json` for settings used |
| Timing problems | `timing_{lang}_batch.csv` |
| Untranslated fragments | `source_fragments_{lang}_batch.csv` |

## Understanding the Reports

### Decision Levels

| Decision | Meaning | Action |
|----------|---------|--------|
| `pass` | No issues found | Files are ready to use |
| `review` | Warnings only | Check punch list, fix if needed |
| `fail` | Errors exist | Must fix before publishing |

### File Status

Each file gets a status per language:

| Status | Meaning |
|--------|---------|
| `ready` | No issues, ready to use |
| `review` | Has warnings |
| `blocked` | Has errors, must fix |

### Issue Types

| Code | Level | Description | Suggested Fix |
|------|-------|-------------|---------------|
| `missing_translation` | Warning | Empty target with empty neighbors and substantial source (≥12 chars) | Back-translate target context to verify; add translation if truly missing |
| `timing_fail` | Error | Timing drift too high | Adjust timing in subtitle editor |
| `placeholder_mismatch` | Error | Placeholder indices don't match | Fix placeholder numbering |
| `parity_issue` | Warning | Cue count mismatch | Check source/target alignment |

## Batch Directory Structure

```
translation-batch-{timestamp}/
├── originals/                      # Source files
│   └── *.srt
├── {lang}/                         # Translated files (fr/, ja/, etc.)
│   └── *.srt
├── manifest.json                   # Batch metadata
├── translation_issues_*.log        # Process log
└── artifacts/
    ├── ai_config.json              # Translation settings used
    ├── dnt.json                    # DNT terms snapshot
    ├── termbase.json               # Termbase snapshot
    ├── eval_report.json            # Raw evaluation data
    ├── report.json                 # Compiled report data
    ├── eval_report.md              # Markdown report
    ├── eval_report.html            # HTML report (primary output)
    └── {lang}/                     # Per-language analysis
        ├── timing_{lang}_batch.csv
        ├── cps_{lang}_batch.csv
        ├── dnt_coverage_{lang}_batch.csv
        ├── tb_coverage_{lang}_batch.csv
        ├── source_fragments_{lang}_batch.csv
        └── eval_summary_{lang}_batch.md
```

## Output Files Reference

### Primary Output

**`artifacts/eval_report.html`** — The main deliverable. Open this in a browser to review translation quality.

### Configuration Snapshots

| File | Purpose |
|------|---------|
| `artifacts/ai_config.json` | Translation settings: languages, DNT terms, termbase, batch sizes, tone |
| `artifacts/dnt.json` | DNT terms list |
| `artifacts/termbase.json` | Termbase entries by language |
| `manifest.json` | Batch metadata: versions, languages, files processed |

### Evaluation Data

| File | Purpose |
|------|---------|
| `eval_report.json` | Raw evaluation data. Machine-readable. |
| `report.json` | Compiled data with decision, punch list, file status. Used by presenters. |
| `eval_report.md` | Markdown version of HTML report |

### Per-Language CSVs

| File | Contents |
|------|----------|
| `timing_{lang}_batch.csv` | Cue-by-cue timing differences |
| `cps_{lang}_batch.csv` | Characters per second per cue |
| `dnt_coverage_{lang}_batch.csv` | DNT term preservation stats |
| `tb_coverage_{lang}_batch.csv` | Termbase usage stats |
| `source_fragments_{lang}_batch.csv` | Latin script fragments left in target |
| `eval_summary_{lang}_batch.md` | Per-language pass/fail summary |

## Implementation Notes

For developers working on the evaluation pipeline.

### Pipeline Flow

1. **Setup** (`core/main.py:translate_srt_files`)
   - Creates batch directory structure
   - Writes `ai_config.json`, `dnt.json`, `termbase.json`
   - Copies source files to `originals/`

2. **Evaluation** (`eval/runner.py:run_batch_evaluation`)
   - Pairs source/target files
   - Detects issues per file
   - Generates per-language CSVs

3. **Report Generation** (`eval/report.py:emit_all_reports`)
   - Writes `eval_report.json`
   - Compiles `report.json` via `report/compiler.py`
   - Renders HTML and Markdown via presenters

4. **GUI Integration** (`gui/workers/translation_worker.py`)
   - Emits `eval_report_ready` signal with all report paths

### Architecture

- **File-based presenters**: HTML and Markdown presenters read from `report.json`, not in-memory data
- **Strict schema validation**: Compiler validates eval_report.json structure before processing
- **Fail-fast**: Missing or malformed files raise exceptions immediately

## Troubleshooting

### Evaluation Failures
- Check translation log for errors
- Batch directory remains for manual inspection
- CSVs may be partially generated

### Missing Reports
- Verify `ai_config.json` exists in artifacts/
- Check that source files were copied to `originals/`

## Known Limitations

### Source Language Assumptions
The `source_fragments_{lang}_batch.csv` detection uses regex `[A-Za-z]{6,}` which assumes English source. Non-English Latin-script sources (Spanish, French, German) will produce false positives.
