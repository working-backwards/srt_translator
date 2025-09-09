# SRT Translator — GUI User Manual

## Introduction

Thank you for using the SRT Translator. This guide explains how the application works, and it walks you through a typical translation from start to finish. You do not need to write any code. You only need your original language subtitle files and your OpenAI API key.

An **SRT file** is a subtitle file format. It contains:
- A numbered list of captions
- Start and end times for each caption
- The text of the caption

The SRT Translator helps you create **high-quality translated subtitles** from your original SRT files.

The SRT Translator reads your original SRT subtitle files, translates them into one or more target languages, and writes clean, well‑timed SRT files to an output folder. It keeps your important terms intact when you tell it which words or phrases should never be translated. It can also apply a custom termbase so your business terms remain consistent.

The SRT Translator can help you if you are:
- A **content creator** who wants to reach a broader audience with multilingual subtitles.
- Someone who wants **control over your subtitles** (e.g., YouTube auto-generates subtitles but doesn’t let you edit them easily).
- A person or team who needs **Do Not Translate (DNT) lists** or **Termbases** to ensure brand names, technical terms, or special vocabulary are handled correctly.

With this tool, you stay in control of your content and ensure your subtitles are accurate and consistent.

---

## Getting Started

When you open the application, the main window guides you through these steps (in order):

1. **Original Language SRT Files**
2. **Target Languages**
3. **API Configuration**
4. **Translation Settings**
5. **Files & Output**
6. **Translation**

---

## 1. Original Language SRT Files

- First, choose a **folder** that contains your `.srt` files.
- After selecting the folder, the app will show you all available SRT files.
- You can:
  - Select individual files
  - Or click **Select All**

This ensures you’re working with the right source files before translation.

---

## 2. Target Languages

- Choose the **languages you want to translate into**.
- You can pick one or many.
- The app shows language **names** (e.g., “Japanese”), not codes (like `ja`).
- Internally, the tool maps names to codes for you, so you don’t need to worry about technical details.

---

## 3. API Configuration

This section is where you enter your **OpenAI API key**.

- An API key is like a password that lets the translator connect securely to OpenAI’s translation models.
- You can get an API key by creating an account at [platform.openai.com](https://platform.openai.com/) and going to your **API Keys** page.
- Copy your key and paste it into the app.
- You can test your key and update it at any time.

### API Key Security

The SRT Translator takes your API key security seriously:

- **Secure Storage**: Your API key is stored securely in your system's registry (Windows) or preferences (macOS/Linux) using Qt's built-in [settings system]( https://doc.qt.io/qt-6/qsettings.html)
- **Masked Input**: The key is hidden with dots as you type it
- **No Logging**: Your API key is never written to log files or reports
- **HTTPS Only**: The key is only transmitted over secure HTTPS connections to OpenAI
- **Easy Management**: You can update or clear your API key at any time through the app settings

Your API key stays on your computer and is only used to communicate with OpenAI's translation services.

---

## 4. Translation Settings

Here you can control how the translator handles **terminology**:

- **Do Not Translate (DNT)** - These are words or phrases that should never be translated (e.g., brand names like “iPhone” or proper names, like the author of the video). DNT terms will remain exactly the same in each laguage translation. There can be up to one DNT list per translation batch.

- **Termbase**  - Termbase is a glossary of approved translations for important terms in your video. They are used to ensure consistency (e.g., “cloud computing” → always translated the same way) across translations. Termbases are useful your content has specialized vocabulary (like medicine, law, or company-specific terms). Each target language can have up to one termbase.

**Good news:**
- You don’t need to create these yourself — the SRT app can provide sensible defaults that can you can view and edit. If you want to the SRT app to generate a DNT or Termbases for you, choose your original language SRT files, the target languages, then click on the "Regenerate" button. The SRT app will send the first 12,500 tokens (about 9,000 - 10,000 English words) to the AI translator. When finished, click on the "Edit Settings" button to view and/or change them.

While DNT and Termbases are optional, using them will typically yield a higher quality translation.

---

## 5. Files & Output

- After selecting your input files and target languages, you choose an **output folder**.
- The translated `.srt` files will be written here.
- The workflow is:
  1. Pick an input folder.
  2. Select one or more `.srt` files.
  3. Choose an output folder.
  4. The app saves your translated subtitles into subfolders for each language.

---

## 6. Translation

The final section is where you run the translations.

Features include:
- **Estimated Cost** — shows you an estimate of OpenAI usage cost before you begin.
- **Translate All Files** button — runs translations for all selected files.
- **Progress Bar** — shows progress while translations are running.
- **Logs Window** — shows real-time progress messages.
- **Open HTML Report** button — once translations finish, you can open a detailed evaluation report (helpful for quality checks).

---

## Step‑by‑Step Guide

These steps describe a typical translation workflow in complete sentences.

1. Open the application. Select your original language SRT files.
2. Select your Output Directory.
3. Choose your target languages.
4. Open the API Configuration box, enter your OpenAI API key, and click on the "Test Connection" button.
5. (Optional) Open Translations Setting box, click on the "Regenerate" button to build your DNT and Termbases.
6. (Optional) Click on the "Edit Settings" button, then review your DNT and Termbases. Edit, if necessary. Usually the default is fine.
6. Click Translate All Files. Watch the progress bar and the live log. The application creates a separate translated SRT for each target language.
7. The application automatically runs fixes after each SRT file is translated to all languages. You will see "Running automatic fixes for [filename]..." in the log.
8. When the translation completes, click on the Open HTML Report" button to view and fix any translation issues. Remember SRT files are just text files, so you can make any minor changes with our favorite text editor.
9. Go to your Output Directory. A new folder will be created for each translation batch. Upload your newly translated SRT files in your video hosting system!

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
- **Segment structure changes:** The app now uses subtitle-based processing that translates each subtitle individually while maintaining perfect timing alignment.
- **Punctuation and sentence boundaries:** Languages break sentences differently; we normalize punctuation for readability.

**In practice:** The app makes a best effort to keep your subtitles aligned with speaker turns and major pauses, while allowing small changes so the translation reads naturally.

### How SRT Translator Works

1. **Ingest your SRT** — already speaker-synced
2. **Prepare terminology** — AI suggests DNT and Termbase candidates; you review/edit
3. **Subtitle-based processing** — We now translate each subtitle individually while maintaining perfect timing alignment. This provides better context for accurate translation while maintaining exact timing.
   - **GUI users:** Subtitle processing is automatic and optimized
   - **CLI (expert) users:** Can configure error policies and concurrency settings
4. **Translate with instructions** — The AI receives your DNT list, Termbase, and subtitle-specific constraints
5. **Reassemble & retime** — We map translated text back to subtitles, allowing minimal merge/split, then snap results to your original timecodes
6. **Quality passes** — After translation, we:
   - Search for DNT terms and ensure they are present in the correct sentence order
   - Replace incorrectly translated or misplaced DNT terms with the exact term from your list
   - Flag cases for manual intervention where DNT placement can't be resolved automatically
   - Perform other internal cleanup steps to preserve subtitle integrity

### Subtitle Processing: Context vs. Timing

**The Challenge:** Subtitle translation requires balancing two competing needs:

Subtitle-based processing balances context for better translation against perfect timing preservation.

**How it works:** We translate each subtitle individually while maintaining exact timing. Each subtitle keeps its original start and end time, ensuring perfect synchronization with your video.

**Benefits:** Better translation quality through sentence-level context, while maintaining perfect timing alignment with the new subtitle-based approach.

**GUI users don't need to worry about this** — it's automatic and optimized. Advanced CLI users can configure error policies and concurrency settings.

### Getting Great Results: DNT & Termbase Setup

- **Start with AI suggestions** — Accept obvious DNT terms and promote important repeated terms to the Termbase
- **Add variants** — Include common capitalization or plural forms in DNT if they must be preserved exactly
- **Lock critical tokens** — File paths, JSON keys, function names should be in DNT
- **Keep it lean** — Too many DNTs can over-constrain; focus on must-preserve items

### Post-Translation Review Checklist

- **DNT integrity:** All DNT terms are preserved exactly and in the right place
- **Termbase consistency:** Terms match approved translations for each language
- **Readability:** Lines are concise and easy to read at intended display speed
- **Timing:** No overlaps, speaker changes align with subtitle changes
- **Locale formatting:** Numbers, dates, and other formats match target language norms
- **Tone/register:** Consistent with your audience

### FAQ (Short)

**Will the translated text match lip movement exactly?**

No. We optimize for readability and timing with speaker intent, not exact lip flaps.

**Why did the number of subtitles change after translation?**

Some languages express ideas in more or fewer words. We allow small changes and then re-fit to your original timeline so the viewing rhythm stays intact.

**Do I need a Termbase if I already have DNT?**

Yes. DNT preserves exact tokens; the Termbase defines how domain terms should be translated.

## How long will it take to translate my content?

Translation time depends on your content length, complexity and the number of target languages. It’s typically **faster than real-time**.

### Rule of thumb (based on real runs)

* **Speed:** \~**42–54 seconds per 100 subtitles per language**
* **What 100 subtitles represents:** roughly **3–5 minutes of video**
* **Per-file overhead:** add **\~15–30 seconds** for each additional file in a job
* **Languages are processed serially (one after another) in the current version.**

---

### For a single language

*(Assumes one file; add \~15–30 sec per extra file.)*

* **5 minutes of content:** **\~1.1–1.6 min**
* **15 minutes of content:** **\~2.9–3.9 min**
* **30 minutes of content:** **\~5.5–7.2 min**
* **60 minutes of content:** **\~10.8–14.0 min**

---

### For multiple languages *(current app = serial processing)*

Multiply the single-language time by the number of languages:

| Content Length |   3 Languages |   5 Languages |  10 Languages |  12 Languages |
| -------------- | ------------: | ------------: | ------------: | ------------: |
| **5 minutes**  |   3.4–4.9 min |   5.6–8.1 min | 11.2–16.2 min | 13.5–19.5 min |
| **15 minutes** |  8.6–11.6 min | 14.4–19.4 min | 28.8–38.8 min | 34.5–46.5 min |
| **30 minutes** | 16.5–21.8 min | 27.5–36.2 min | 55.0–72.5 min | 66.0–87.0 min |
| **60 minutes** | 32.2–42.0 min | 53.8–70.0 min |    1.8–2.3 hr |    2.1–2.8 hr |

---

### Real-world example

A recent translation of 9 modules (ranging from 1–27 minutes each) into **12 languages** took **\~5 hours 18 minutes** end-to-end. The system processed 108 translation operations successfully with zero errors.

> **Performance tip:** Speed is broadly consistent across languages (Spanish, Chinese, Arabic, Japanese, etc.), so you can plan confidently regardless of target languages.


## Troubleshooting

### I do not see any translations.

Please confirm your API key in the API Configuration section. Make sure your internet connection is stable. Check the log for any error messages. If the log reports an authentication error, you may need to create a new key.

### The timing looks unusual in a few places.

The application now uses subtitle-based processing that preserves exact timing. Each subtitle maintains its original start and end time, while the translated text is intelligently formatted within the original timing window. This approach eliminates timing drift completely while keeping subtitles readable and properly synchronized.

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
- The application automatically optimizes subtitle processing for your content

### Quality vs. Speed
- The default model provides a good balance of quality and speed
- For critical content, the system maintains quality while preserving exact timing
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
- Single-file processing ensures consistent performance
- Rate limiting to respect API constraints
- Efficient subtitle processing with individual subtitle translation
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
