# Unified Report Headers and Rubric

This document describes the unified report format used by both HTML and Markdown presenters in the SRT Translator evaluation system.

## Overview

Both HTML and Markdown evaluation reports now follow a consistent structure with three main sections at the top:

1. **Publish readiness banner** - Clear status indicator with emoji and one-liner
2. **What to do next** - Actionable steps based on the current status
3. **KPIs** - Key performance indicators in a consistent order

## Status Rubric

The system uses a three-tier status classification:

### ✅ Ready to publish
- **Condition**: No critical issues detected
- **Banner**: "Everything looks great. Your translated files are ready to use."
- **Next steps**:
  1. Spot-check a few captions for tone and brand terms.
  2. Publish when satisfied.

### ⚠️ Review recommended
- **Condition**: No critical issues, but warnings present
- **Banner**: "Looks good overall. Address the items below to improve quality before publishing."
- **Next steps**:
  1. Scan warnings (timing drift, high CPS) and tweak a few problem captions.
  2. Re-export and spot-check brand terms.
  3. Publish when satisfied.

### ❌ Fix before publishing
- **Condition**: Critical issues detected
- **Banner**: "We found issues that will degrade quality. Fix the items below before publishing."
- **Next steps**:
  1. Resolve DNT or termbase violations in the listed files.
  2. Fix cue parity mismatches or missing translations.
  3. Re-run evaluation and confirm 'Ready to publish'.

## Critical Issues

The following are considered critical issues that prevent publishing:

- **DNT violations**: Terms marked as "Do Not Translate" that were translated
- **Termbase violations**: Terms that should use approved translations but don't
- **Cue parity mismatches**: Different number of subtitle cues between original and translation
- **Missing translations**: Empty or missing translation segments
- **Malformed segments**: Segments that prevent proper evaluation
- **Hard CPS limit breaches**: Character-per-second limits that exceed hard thresholds

## Warnings

The following are considered warnings (non-critical):

- **Soft CPS overage**: Character-per-second that exceeds soft thresholds
- **Timing drift**: Cue timing deviations that exceed soft thresholds

## KPI Strip

Both presenters display the same KPIs in the same order:

1. **Files total** - Number of unique files processed
2. **Languages** - Number of target languages
3. **Issues (critical)** - Count of critical issues
4. **Warnings (non-critical)** - Count of warning-level issues
5. **Detected source language** - Automatically detected source language
6. **DNT coverage** - Whether DNT terms are present ("present" or "missing")
7. **Termbase coverage** - Coverage across languages (e.g., "2/3 languages")

## Input Requirements

Both presenters require the following files in the `artifacts/` directory:

- `eval_report.json` - Must contain: `files_total`, `languages_total`, `issues_total`
- `ai_config.json` - Must contain: `dnt_terms`, `termbase`, and either `target_languages` or `target_language_codes`

If any required files or keys are missing, both presenters will fail fast with clear error messages.

## Deterministic Behavior

- Language codes are sorted alphabetically for consistent display
- Number formatting is locale-independent
- Both presenters use identical wording and logic
- Status determination is based on the same criteria

## Implementation Notes

- The HTML presenter uses CSS classes for styling the KPI grid
- The Markdown presenter uses bullet points for the KPI list
- Both presenters share the same helper functions for status computation
- Error handling is consistent across both formats

## Future Enhancements

- Warning detection will be enhanced to include soft threshold violations
- Additional KPI metrics may be added while maintaining backward compatibility
- The rubric may be extended to include more granular status levels
