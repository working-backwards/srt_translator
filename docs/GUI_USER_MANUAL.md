## SRT Translator GUI User Manual

### Welcome

Thank you for using the SRT Translator. This guide is your friendly companion. It explains how the application works, and it walks you through a typical translation from start to finish. You do not need to write any code. You only need your subtitle files and your OpenAI API key.

### What the application does

The SRT Translator reads your original SRT subtitle files, translates them into one or more target languages, and writes clean, well‑timed SRT files to an output folder. It keeps your important terms intact when you tell it which words or phrases should never be translated. It can also apply a custom termbase so your business terms remain consistent. The application processes files one at a time to ensure quality and prevent resource conflicts.

---

## Getting Started

### How to get the app

- **Download a packaged build** from `dist/<platform>/SRT_Translator/` (or from a release zip).
- If you are a developer, you can build it yourself following **INSTALLATION.md**.

Then launch the app and go to **API Configuration** to paste your OpenAI API key.

---

## A Quick Tour of the Interface

The main window is divided into clear sections. Each section has a simple job.

### API Configuration

This section stores your OpenAI API key. The application uses this key to contact the translation models. You can test your key and update it at any time.

### Files & Output

This section lets you choose the folder that contains your original SRT files and the folder where translated files will be written. The application never deletes or modifies your original files. It reads them and writes new files to the output directory. The output directory will contain translated SRT files, a manifest of all translations, your DNT terms, termbase, and detailed log files for troubleshooting.

### Language Selection

This section lets you choose the languages you want to translate into. You can select one language or many languages. The application normalizes language names and codes for you, so you can choose “Japanese” or “ja” and the result will be the same.

### AI Configuration

This section controls the translation models and options. The application chooses sensible defaults. If you are new to the tool, you can accept the defaults. If you want to change the model for quality, speed, or cost, you can do so here.

### Translation

This section starts and monitors your translation. It shows progress and it writes a log that you can review later. It also shows any errors that occur. When the translation finishes, it tells you where the new files are located.

### Preview (optional)

Some builds include a preview section. If you see it, you can preview how a translated SRT block will look before you translate the entire file. This is helpful if you are adjusting your DNT terms or your termbase. The preview shows exactly how your DNT terms and termbase will be applied to a small sample of text.

---

## Step‑by‑Step Guide

These steps describe a typical translation workflow in complete sentences.

1. Open the application. Confirm that your API key is set in the API Configuration section.
2. Select the folder that contains your original SRT files. Confirm your output folder.
3. Open the Language Selection section. Choose your target languages. You may use common names or ISO codes. The application handles normalization.
4. (Optional) Open the Do Not Translate Terms editor. Add names, brands, and technical acronyms that should remain in the original language.
5. (Optional) Open the Termbase editor. Add consistent translations for business terms so the output remains professional and predictable.
6. Click Translate All Files. Watch the progress bar and the live log. The application creates a separate translated SRT for each target language.
7. The application automatically runs fixes after each SRT file is translated to all languages. You will see "Running automatic fixes for [filename]..." in the log.
8. When the translation completes, open the output folder. You'll find:
   - Translated SRT files (one per target language)
   - A manifest file listing all translations
   - Your DNT terms and termbase files
   - Detailed log files for troubleshooting
   Review the translated files in your media player or subtitle editor.

If you notice a term that should not have been translated, add it to your DNT list and translate again. If you want a term to be translated in a specific way, add it to the termbase and translate again. The application will respect your preferences.

---

## Understanding Translation (Advanced Concepts)

> **For users who want to understand how the translation process works and how to get the best results.**

### Translation 101 (for Content Creators)

#### Do-Not-Translate (DNT) Terms

A DNT list is a set of tokens we preserve exactly across languages—brand names, product names, file paths, hashtags, model numbers, proper nouns, commands, code, etc.

**Why it matters:** Translation systems may "help" by changing names or formatting in ways that hurt comprehension, branding, or technical accuracy.

**Examples:**
- **Brand/product names:** SuperCut, ProMix 3000
- **Handles/hashtags:** @CreatorName, #NoFilter
- **Technical strings:** Ctrl+C, CUDA, render_settings.json
- **Part numbers / SKUs:** XC-200, M2-MAX

The SRT Translator passes your DNT list to the AI and also pre-protects it so it survives translation intact.

#### Custom Termbase

A Termbase is your curated glossary mapping each source term to its preferred translations for each target language.

Unlike the DNT list, the Termbase tells the translator how to translate important terms, ensuring consistency across all your videos.

**Example Termbase:**

| English | Spanish | Chinese (Simplified) |
|---------|---------|---------------------|
| lower third | rótulo | 下三分之一 |
| b-roll | recurso | 补充镜头 |
| cold open | apertura fría | 冷开场 |
| operating cadence | cadencia operativa | 运营节奏 |
| input metrics | métricas de entrada | 输入指标 |
| jump cut | corte brusco | 跳切 |
| call to action | llamada a la acción | 行动号召 |

The AI suggests a Termbase for each language based on your content. The lists do not need to be identical across languages — each is optimized for that language's context.

### Why Subtitle Translation is Different from Document Translation

Subtitles have timecodes, line-length constraints, and reading-speed limits. That creates unique challenges:

- **Lip-sync vs. readability:** We preserve your original timing, but translated text may need more or fewer characters. We prioritize readability and matching the speaker's intent over perfect lip movement.
- **Segment structure changes:** A batch of 5 source subtitles might translate naturally into 4 or 6 in the target language. The app allows controlled merge/split, then fits results to your original timing grid.
- **Punctuation and sentence boundaries:** Languages break sentences differently; we normalize punctuation for readability.

**In practice:** The app makes a best effort to keep your cues aligned with speaker turns and major pauses, while allowing small changes so the translation reads naturally.

### How SRT Translator Works

1. **Ingest your SRT** — already speaker-synced
2. **Prepare terminology** — AI suggests DNT and Termbase candidates; you review/edit
3. **Batching sentences** — We group subtitles into batches of around 5 subtitles before sending them to the translator. Through experimentation, this has proven to be a good balance between providing enough context for accurate translation and making it possible to reassemble the output into correctly timed subtitles.
   - **GUI users:** Batch size is fixed at ~5
   - **CLI (expert) users:** Batch size can be changed via command-line options
4. **Translate with instructions** — The AI receives your DNT list, Termbase, and subtitle-specific constraints
5. **Reassemble & retime** — We map translated text back to subtitles, allowing minimal merge/split, then snap results to your original timecodes
6. **Quality passes** — After translation, we:
   - Search for DNT terms and ensure they are present in the correct sentence order
   - Replace incorrectly translated or misplaced DNT terms with the exact term from your list
   - Flag cases for manual intervention where DNT placement can't be resolved automatically
   - Perform other internal cleanup steps to preserve subtitle integrity

### Batching: Context vs. Reassembly

Batching balances context for better translation against ease of reassembly into timed subtitles.

**Why ~5?** More context helps the translator resolve pronouns and maintain tone, but very large batches can make timing reconstruction harder and occasionally confuse the translator. Through testing, 5 subtitles per batch is the sweet spot for most content.

**GUI users don't need to worry about this** — it's fixed for optimal results. Advanced CLI users can override it if they have a special case.

### Getting Great Results: DNT & Termbase Setup

- **Start with AI suggestions** — Accept obvious DNT terms and promote important repeated terms to the Termbase
- **Add variants** — Include common capitalization or plural forms in DNT if they must be preserved exactly
- **Lock critical tokens** — File paths, JSON keys, function names should be in DNT
- **Keep it lean** — Too many DNTs can over-constrain; focus on must-preserve items

### Post-Translation Review Checklist

- **DNT integrity:** All DNT terms are preserved exactly and in the right place
- **Termbase consistency:** Terms match approved translations for each language
- **Readability:** Lines are concise and easy to read at intended display speed
- **Timing:** No overlaps, speaker changes align with cue changes
- **Locale formatting:** Numbers, dates, and other formats match target language norms
- **Tone/register:** Consistent with your audience

### FAQ (Short)

**Will the translated text match lip movement exactly?**

No. We optimize for readability and timing with speaker intent, not exact lip flaps.

**Why did the number of subtitles change after translation?**

Some languages express ideas in more or fewer words. We allow small changes and then re-fit to your original timeline so the viewing rhythm stays intact.

**Do I need a Termbase if I already have DNT?**

Yes. DNT preserves exact tokens; the Termbase defines how domain terms should be translated.

**How long will it take to translate my content?**

Translation time depends on your content length and the number of target languages. The good news is that our system translates faster than real-time, so you won't be waiting as long as your video duration.

**For a single language:**
- **5 minutes of content:** 1-2 minutes to translate
- **15 minutes of content:** 6-8 minutes to translate  
- **30 minutes of content:** 12-16 minutes to translate
- **60 minutes of content:** 24-32 minutes to translate

**For multiple languages (processing in parallel):**

| Content Length | 3 Languages | 5 Languages | 10 Languages | 12 Languages |
|----------------|-------------|-------------|--------------|---------------|
| 5 minutes     | 2-3 min     | 3-4 min     | 5-7 min      | 6-8 min       |
| 15 minutes    | 18-24 min   | 30-40 min   | 1-1.3 hours  | 1.2-1.6 hours |
| 30 minutes    | 36-48 min   | 1-1.3 hours | 2-2.6 hours  | 2.4-3.2 hours |
| 60 minutes    | 1.2-1.6 hr | 2-2.6 hours | 4-5.2 hours  | 4.8-6.4 hours |

**Real-world example:** A recent translation of 9 modules (ranging from 1 minute to 27 minutes each) to 12 languages took 5 hours and 18 minutes total. The system processed 108 translation operations successfully with zero errors.

**Performance tip:** Translation speed is consistent across all languages. Spanish, Chinese, Arabic, and Japanese all translate at roughly the same speed, so you can plan your workflow confidently regardless of your target languages.

**How much will it cost to translate my content?**

Translation costs depend on content length, number of languages, and the AI model you choose. Our system uses GPT-4o-mini for optimal balance of quality and cost.

**Cost factors:**
- **Content length:** More content = more tokens = higher cost
- **Language count:** Each language requires separate API calls
- **Model efficiency:** GPT-4o-mini provides high quality at ~1/10th the cost of GPT-4

**Estimated costs (using GPT-4o-mini):**

| Content Length | 1 Language | 3 Languages | 5 Languages | 10 Languages | 12 Languages |
|----------------|-------------|-------------|-------------|--------------|---------------|
| 5 minutes     | $0.03 - $0.05 | $0.09 - $0.15 | $0.15 - $0.25 | $0.30 - $0.50 | $0.36 - $0.60 |
| 15 minutes    | $0.08 - $0.12 | $0.24 - $0.36 | $0.40 - $0.60 | $0.80 - $1.20 | $0.96 - $1.44 |
| 30 minutes    | $0.15 - $0.25 | $0.45 - $0.75 | $0.75 - $1.25 | $1.50 - $2.50 | $1.80 - $3.00 |
| 60 minutes    | $0.30 - $0.50 | $0.90 - $1.50 | $1.50 - $2.50 | $3.00 - $5.00 | $3.60 - $6.00 |
| 90 minutes    | $0.45 - $0.75 | $1.35 - $2.25 | $2.25 - $3.75 | $4.50 - $7.50 | $5.40 - $9.00 |



## Troubleshooting

### I do not see any translations.

Please confirm your API key in the API Configuration section. Make sure your internet connection is stable. Check the log for any error messages. If the log reports an authentication error, you may need to create a new key.

### The timing looks unusual in a few places.

The application enforces batch boundaries. It clamps the first subtitle of each batch to the original batch start and clamps the last subtitle of each batch to the original batch end. If a model returns more or fewer subtitles than expected, the application redistributes content within the batch without creating blank lines. This approach prevents cross‑batch drift while keeping subtitles readable.

### Some terms should have stayed in English.

Add those exact phrases to the DNT Terms list and run the translation again. The translator will keep those phrases as written.

### A business term needs a specific translation.

Add the term and its preferred translation to your termbase for that language. Then translate again. The translator will apply your preference whenever it finds the term.

### I get an error about "batch in progress."

The application processes one translation at a time to ensure quality and prevent conflicts. If you see this error, wait for the current translation to complete before starting another. This design prevents API rate limit issues and ensures consistent performance.

### What to do when translations fail.

If a translation fails completely, the application will attempt to fall back to individual subtitle translation. Check the log files for detailed information about what went wrong. Common issues include:
- API authentication problems (check your API key)
- Network connectivity issues
- Content that the AI model cannot process
- File format problems

The log files will show exactly what happened and where the process failed.

---

## Frequently Asked Questions

### Where do my new files go?

Your translated files appear in the output directory that you selected in the Files & Output section. Each language receives its own SRT file.

### Does the application edit my original files?

No. The application treats your original files as read‑only. It never deletes them and it never modifies them. It only reads them.

### Can I close the application during a long translation?

You can close the application at any time. When you reopen it, your settings remain. You can start a new translation when you are ready.

### Can I use language names or language codes?

Yes. You can use either. The application maps names to ISO codes for you. It shows your selections clearly in the interface.

### What file formats are supported?

The application currently supports standard SRT subtitle files. Make sure your input files have the `.srt` extension and follow the standard SRT format:
- Subtitle number
- Timestamp (HH:MM:SS,mmm → HH:MM:SS,mmm)
- Subtitle text
- Blank line between subtitles

The application will validate your files and show any format issues in the log.

### Where can I find log files for troubleshooting?

The application creates detailed log files in your output directory that you can check if something goes wrong. These log files are automatically generated alongside your translated SRT files and contain detailed information about what happened during translation, including any errors or issues that the automatic fixer addressed.

The output directory contains:
- **Translated SRT files** - Your main results
- **Manifest file** - A summary of all translations performed
- **DNT terms file** - Your "Do Not Translate" terms for reference
- **Termbase file** - Your custom terminology for reference
- **Log files** - Detailed translation logs with timestamps

---



## Performance and Optimization Tips

### Translation Speed
- Process fewer target languages at once for faster results
- Smaller SRT files translate more quickly than very long ones
- The application automatically optimizes batch sizes for your content

### Quality vs. Speed
- The default model provides a good balance of quality and speed
- For critical content, consider translating in smaller batches
- Use the preview feature to test your settings before processing large files

### Memory and Resource Usage
- The application is designed to handle large subtitle files efficiently
- Processing one file at a time ensures consistent performance
- Log files are automatically managed to prevent disk space issues

## Modern Features

### Enhanced Output Organization
The application now organizes all output files in one convenient location:
- **Translated SRT files** are clearly named with language indicators
- **Manifest file** provides a complete record of all translations
- **Configuration files** (DNT terms, termbase) are saved for future reference
- **Log files** contain detailed information for troubleshooting

### Improved Error Handling
- Clear error messages when translations cannot proceed
- Automatic fallback to individual subtitle translation if batch translation fails
- Detailed logging of all operations and decisions
- Phantom placeholder detection to prevent AI hallucinations

### Performance Optimizations
- Single-batch processing ensures consistent performance
- Rate limiting to respect API constraints
- Efficient batch processing with sentence-aware boundaries
- Memory-conscious file handling for large subtitle files

---

## Best Practices and Workflow

### Before You Start
- Test your API key to ensure it's working
- Review your DNT terms and termbase for accuracy
- Use the preview feature to verify your settings
- Choose an output directory that's easy to find

### During Translation
- Monitor the progress bar and log for any issues
- Don't start multiple translations simultaneously
- Keep the application running until completion
- Check the log if you encounter any errors

### After Translation
- Review the manifest file to confirm all files were processed
- Check a few translated files in your media player
- Save your DNT terms and termbase for future use
- Keep the log files for troubleshooting if needed
