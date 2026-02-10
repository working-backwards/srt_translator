# Content Creator Guide

This guide helps content creators understand how to use the SRT Translator and interpret its outputs.

## What is ai_config.json?

The `ai_config.json` file is a **snapshot** of your translation run that contains:

### Essential Information
- **Version**: The SRT Translator version used
- **Timestamp**: When the translation was performed
- **Target Languages**: Which languages you translated to
- **Source Files**: Which files were translated

### Translation Settings
- **DNT Terms**: "Do Not Translate" terms that were preserved
- **Termbases**: Custom translations for specific terms in each language
- **Model**: Which AI model was used for translation
- **Mode**: Whether you used CLI or GUI

### Why This Matters
This file ensures that:
- **Quality evaluation** uses the exact same settings as your translation
- **Reproducibility** - you can re-run evaluation later with identical results
- **Audit trail** - complete record of what was translated and how

## Understanding Coverage Reports

When you run evaluation, you'll see coverage information that tells you how complete your translation setup was:

### DNT Coverage
- **`dnt_coverage: "present"`** - You provided "Do Not Translate" terms
- **`dnt_coverage: "none"`** - No DNT terms were specified

**What this means**: DNT terms help preserve important terminology (like product names, technical terms) that shouldn't be translated.

### Termbase Coverage
- **`termbase_coverage: "full"`** - All target languages have custom term translations
- **`termbase_coverage: "partial"`** - Some languages have custom terms, others don't
- **`termbase_coverage: "none"`** - No custom term translations were provided

**What this means**: Termbases ensure consistent translation of important terms across all languages.

### Entry Counts
The report shows how many custom terms you have for each language:
```json
"termbase_entry_counts": {
  "es": 15,
  "fr": 12,
  "de": 8
}
```

## Reading Quality Reports

### What to Look For
1. **Decision Banner**: Shows pass (✅), review (⚠️), or fail (❌)
2. **Coverage**: Make sure DNT and termbase coverage match your expectations
3. **Issues**: Review any flagged problems in the punch list
4. **Language-specific**: Check file status for each target language

### Common Issues and Solutions

#### "Term Issues" - High Count
- **Cause**: Important terms being translated when they shouldn't be
- **Solution**: Add missing terms to your DNT list or termbase

#### "Empty Subtitles"
- **Cause**: Usually segmentation artifacts, not translation problems
- **Solution**: This is normal and doesn't affect quality

#### "CPS Violations"
- **Cause**: Text too long for subtitle timing
- **Solution**: Consider breaking long sentences or adjusting timing

## If Evaluation Fails

### Common Failure Reasons
1. **Missing `ai_config.json`** - Translation didn't complete properly
2. **Missing source files** - Original SRT files not found
3. **Missing translated files** - Translation output incomplete
4. **Corrupted files** - Files damaged during processing

### What to Do
1. **Re-run translation** - Most failures are due to incomplete translation
2. **Check file permissions** - Ensure the app can read/write to the output directory
3. **Verify disk space** - Translation needs space for output files
4. **Contact support** - If the problem persists, include the error message

### Recovery Steps
1. **Delete the failed batch folder** (starts with `translation-batch-`)
2. **Check your input files** - Ensure they're valid SRT files
3. **Verify settings** - Make sure your configuration is correct
4. **Try again** - Most issues resolve with a fresh run

## Best Practices

### Before Translation
1. **Prepare your DNT list** - Identify terms that shouldn't change
2. **Build your termbase** - Create custom translations for important terms
3. **Test with a small file** - Verify settings work as expected

### During Translation
1. **Monitor progress** - Watch for any error messages
2. **Don't interrupt** - Let the process complete
3. **Check output** - Verify files are created in the expected locations

### After Translation
1. **Run evaluation** - Get quality metrics and identify issues
2. **Review reports** - Understand what went well and what didn't
3. **Save results** - Keep the batch folder for future reference

## Getting Help

### Documentation
- **README.md** - Project overview and quick start
- **INSTALLATION.md** - Setup instructions
- **GUI_USER_MANUAL.md** - Detailed GUI usage

### Support
- **GitHub Issues** - Report bugs or ask questions
- **Discussions** - Community help and tips
- **Wiki** - Additional guides and examples

### Before Asking for Help
1. **Check the logs** - Look in `translation_issues_*.log` for error details
2. **Verify your setup** - Ensure you have the latest version
3. **Include details** - Version, error messages, and steps to reproduce

## Quick Reference

### File Locations
- **Input**: `original_captions/` folder
- **Output**: `translated_srt_files/translation-batch-YYYYMMDD_HHMMSS_/`
- **Logs**: `translation_issues_YYYYMMDD_HHMMSS_.log`
- **Reports**: `artifacts/eval_report.json`

### Key Commands
- **GUI**: Run `srtx` from command line
- **CLI**: Run `srtx-cli` with appropriate flags
- **Evaluation**: Automatically runs after translation

### Success Indicators
- ✅ Translation completes without errors
- ✅ Output files created for each target language
- ✅ Evaluation runs and produces reports
- ✅ Coverage matches your expectations

Remember: The SRT Translator is designed to be reliable and user-friendly. Most issues can be resolved by re-running the translation or checking your configuration. When in doubt, start with a small test file to verify everything is working correctly.
