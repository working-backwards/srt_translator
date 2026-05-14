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

1. **Files**
2. **Target Languages**
3. **Translation Settings**
4. **Translate**
5. **Settings**

---

## 1. Files

- Click **Browse Files** to select one or more `.srt` subtitle files.
- Multiple subtitle files can be selected at the same time using your system file dialog.
- After adding files, you can:
  - Click **Select All** to select all loaded files
  - Click **Clear All** to remove all loaded files

### Output Directory

After selecting your subtitle files, choose an **Output Directory**.

- Translated `.srt` files will be written to this location.
- The application automatically creates organized output folders for translation batches.
- Each target language receives its own translated output files.

Typical workflow:

1. Select one or more `.srt` files
2. Choose target languages
3. Configure translation settings
4. Select an output directory
5. Start translation

The original subtitle files are never modified.

---

## 2. Target Languages

- Choose the target languages you want to translate into.
- You can select one or multiple target languages.
- The application displays readable language names (for example, “Japanese”) instead of technical language codes (such as `ja`).
- Language names are automatically mapped internally, so no manual configuration is required.

### Language Selection Features

The Languages panel also supports:
- Multi-language selection
- Popular language shortcuts
- Language search and filtering
- Review of currently selected languages

The application avoids generating duplicate translations when the source and target language are the same.
---


## 3. Translation Settings

Here you can control how the translator handles **terminology**:

- **Do Not Translate (DNT)** — These are words or phrases that should never be translated (e.g., brand names like “iPhone” or proper names such as video authors or character names). DNT terms remain exactly the same in each language translation. There can be up to one DNT list per translation batch.

- **Termbase** — A termbase is a glossary of approved translations for important terms in your video. It helps maintain consistency (e.g., “cloud computing” → always translated the same way) across translations. Termbases are especially useful for specialized vocabulary such as medical, legal, technical, or company-specific terminology. Each target language can have up to one termbase.

- You do not need to create these manually — the SRT app can generate sensible defaults that you can later review and edit. To generate DNT terms or termbases automatically, first select your original language SRT files and target languages, then click the **Regenerate** button. When generation is complete, click **Edit/View Settings** to review or modify the generated configuration.

### Translation Settings Actions

The Translation Settings panel also includes tools for importing, exporting, generating, and editing translation terminology and configuration.

#### Import Termbase

Import an approved glossary of translated terms to maintain consistent terminology across subtitle translations.

#### Import DNT Terms

Import a Do Not Translate (DNT) list containing words or phrases that must remain unchanged during translation.

Examples include:
- Product names
- Brand names
- Character names
- Technical identifiers

#### Edit/View Settings

Open the detailed translation configuration editor to:
- Review generated settings
- Edit DNT terms
- Edit termbase entries
- Adjust language-specific translation behavior

#### Export

Export the current translation settings configuration for reuse, backup, or sharing.

You can export:
- DNT terms
- Termbase entries
- Generated translation configuration

This is useful when:
- Reusing settings across projects
- Sharing approved terminology with a team
- Backing up translation configurations

#### Regenerate

Regenerate translation settings using the currently selected:
- Source subtitle files
- Target languages
- Tone selection

This refreshes:
- Suggested DNT terms
- Suggested termbases
- AI-generated translation configuration

#### Translation Settings Status

A status indicator appears beside Translation Settings:

- “Configured”

This indicates that the translation configuration has been successfully prepared and is ready for translation.

While DNT terms, termbases, and Tone are optional, using them will typically produce higher-quality and more consistent translations.

### Tone

Choose the translation register for your content:

- **Casual** — Informal, conversational style suitable for vlogs and personal channels
- **Neutral (recommended)** — Professional and approachable style recommended for general content and business training
- **Formal** — Polite, official style suitable for corporate communications and professional presentations

The Tone setting affects how the translator approaches formality and politeness. Some languages (such as Chinese, Japanese, German, and French) automatically apply language-specific tone hints based on the selected option. These hints are automatic and not user-configurable.

---

## 4. Translate

The final section is where translations are started and monitored.

Features include:

- **Estimated Cost** — Displays an estimated OpenAI usage cost before translation begins.
- **Translate All Files** — Starts translation for all selected subtitle files and target languages.
- **Cancel Translation** — Allows an active translation session to be stopped safely. Completed translations are preserved.
- **Progress Bar** — Displays translation progress while processing is active.
- **Logs Window** — Shows real-time translation progress, status updates, retry activity, and warnings.
- **Open HTML Report** — Opens the generated translation evaluation report after translation completes. The button is enabled only when a report was successfully generated.
- **Automatic Retry Recovery** — Temporary OpenAI, API, timeout, and network interruptions are automatically retried using exponential backoff delays.

- **Inline Connection Status** — During temporary connection failures, the application displays live retry progress messages such as:
  - “Connection issue, retrying in 5s (attempt 1/5)…”
  - “Connection interrupted — retrying every 30s…”

- **Retry Failed Languages** — Failed target languages can be retried without retranslating successful languages.
- **Partial Completion Handling** — Successfully translated languages are preserved even if some target languages fail.
- **User-Friendly Error Dialogs** — Authentication failures, quota exhaustion, rate limits, invalid models, and connection failures display clear recovery dialogs instead of raw technical exceptions.

### Translation Recovery Behavior

The translator automatically attempts to recover from temporary failures including:
- API connection interruptions
- Timeout failures
- OpenAI throttling
- Temporary OpenAI service instability

Retry delays increase automatically between attempts to reduce unnecessary request spam.

### Translation Results

When translation completes, the application displays:
- Successful languages
- Failed languages
- Failure reasons
- Output directory location
- Retry options for failed languages

The original subtitle files are never modified.

---


## 5. Settings

The Settings window is accessed using the gear icon in the upper-right corner of the application.

The Settings window contains API configuration and advanced translation settings.

### API Configuration

The API Configuration section is used to connect the application to OpenAI.

Features include:
- API key entry
- Secure masked API key storage
- Test Connection button
- API key validation
- API key update and replacement

#### Test Connection

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

The **Test Connection** button verifies:
- Your API key is valid
- OpenAI is reachable
- Your account can access the selected model
- The selected model exists

If validation succeeds, the application confirms that the connection is ready for translation.

### Advanced Settings

The Advanced Settings section contains model and translation behavior controls.

#### Generation Model

The **Generation Model** dropdown controls which OpenAI model is used for subtitle translation.

Available models may include:
- `gpt-4o-mini`
- `gpt-4o`
- `gpt-4.1-mini`
- `gpt-5-mini`

Different models may provide different:
- Translation quality
- Speed
- Cost characteristics

If the selected model:
- does not exist,
- is unavailable,
- or your account does not have permission to access it,

the application displays a user-friendly recovery dialog.

#### Fix Aggressiveness

The **Fix Aggressiveness** slider controls how aggressively the subtitle repair and cleanup system modifies translated subtitles after generation.

Higher values:
- Apply stronger cleanup behavior
- More aggressively repair formatting and subtitle issues

Lower values:
- Preserve more of the original AI-generated output
- Apply lighter cleanup behavior

#### Reset to Defaults

The **Reset to Defaults** button restores the default application configuration for:
- Generation model
- Fix aggressiveness
- Advanced translation settings

#### Settings Persistence

Application settings are automatically saved between sessions, including:
- API key
- Selected generation model
- Fix aggressiveness value

### API Error Handling

The application converts technical OpenAI and network exceptions into user-friendly recovery dialogs.

Examples include:

| Error Type | User Dialog |
|---|---|
| Invalid API key | “Your API key was rejected” |
| Quota exhausted | “Your OpenAI account is out of credits” |
| Permission denied | “Permission denied” |
| Invalid model | “Model not found” |
| Connection failure | “Internet connection lost” |
| Timeout | “Request timed out” |
| Rate limit | “OpenAI is throttling requests” |

Some failures are considered permanent and stop immediately:
- Invalid API key
- Missing OpenAI credits
- Invalid model selection
- Permission denied

Temporary failures are retried automatically using exponential backoff recovery.

---

## Step‑by‑Step Guide

These steps describe a typical translation workflow in complete sentences.

1. Open the application. Select your original language SRT files.
2. Select your Output Directory.
3. Choose your target languages.
4. Open Settings using the gear icon, enter your OpenAI API key, choose your generation model if needed, then click "Test Connection".
5. (Optional) Open the Translation Settings panel, click on the "Regenerate" button to build your DNT and Termbases.
6. (Optional) Click on the "Edit Settings" button, then review your DNT and Termbases. Edit, if necessary. Usually the default is fine.
7. Click Translate All Files. Watch the progress bar and the live log. If temporary connection problems occur, the application automatically retries translation requests and displays live retry status updates. The application creates a separate translated SRT file for each target language. If only some languages fail, the application preserves successful outputs and allows retrying failed languages separately. If you need to stop the run, click the **Cancel Translation** button — the in-flight request finishes, then the loop stops between languages and the partial output is kept.
8. The application automatically runs fixes after each SRT file is translated to all languages. You will see "Running automatic fixes for [filename]..." in the log.
9. When the translation completes, click on the "Open HTML Report" button to view and fix any translation issues. Remember SRT files are just text files, so you can make any minor changes with your favorite text editor.
10. Go to your Output Directory. A new folder will be created for each translation batch. Upload your newly translated SRT files in your video hosting system!

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

### The application says “Connection interrupted — retrying...”

This message means the application temporarily lost connection to the OpenAI API or your network connection became unstable.
The translator automatically retries requests using exponential backoff. In many cases, translation resumes automatically without user intervention.
If the connection does not recover after all retry attempts are exhausted, the affected language will be marked as failed while successful languages are preserved.

### I see “Translation complete with errors.”

The final summary dialog appears at the end of every run, even when some languages failed. It contains:

- A line listing the languages that succeeded by code, e.g. *"Successfully translated 8 languages: en, es, fr, de, ja, pt-BR, vi, zh-Hans"*.
- A list of failed languages grouped by error type, e.g. *"Failed 4 languages: - ar, az, id, tr (APIConnectionError)"*.
- An **Open Output Folder** button that opens the batch directory in your file manager so you can inspect what was kept.
- A **Retry Failed Languages** button, shown only when at least one failure is in the retryable set: `APIConnectionError`, `APITimeoutError`, `RateLimitError`, `InternalServerError`. Clicking it reruns just the affected languages.

Authentication, permission, and bad-model errors do **not** appear in this dialog because they abort the whole run instead and surface.

### I see an OpenAI quota or billing error.

If your OpenAI account has run out of credits, the application shows a dialog:

- Title: *"Your OpenAI account is out of credits"*.
- Message: *"OpenAI rejected the request because the quota is exhausted."*
- Button: **Open platform.openai.com** — opens the OpenAI billing page in your default browser so you can add credits.

This is distinct from a temporary throttling event. If you see the title *"OpenAI is throttling requests"* with a **Wait and Retry** button, the API is rate-limiting your requests but your account is fine — wait a minute and click Retry.

The quota dialog appears almost immediately when your account is exhausted. The application detects the *"insufficient_quota"* marker in OpenAI's response and skips the retry budget for this case, since retrying the same call against an empty quota would never succeed. You won't have to wait ~1.5 minutes of pointless retries before the dialog shows up.

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

### Cancelling a translation run

While a run is active a **Cancel Translation** button is visible next to the Translate button. Cancellation is cooperative:

- The in-flight OpenAI request finishes (so no token charge is wasted mid-call).
- The per-language loop then stops between languages — languages that hadn't started yet are skipped.
- Languages that already finished keep their output files on disk in the batch directory.
- The final results dialog still appears so you can see what was kept and decide whether to retry the rest later.

Cancel takes effect at the next language boundary; for a long single-file run it may take a few seconds to settle.

### Authentication, permission, or model errors abort the whole batch

These errors are guaranteed to fail every target language, so the application aborts the run immediately instead of cycling through the same failure for every language. Each one produces a  dialog with a single primary action button:

| Problem                                 | Dialog title                                       | Action button |
|-----------------------------------------|----------------------------------------------------|---|
| Wrong API key                           | *"Your API key was rejected"*                      | **Open Settings** |
| API key lacks model access              | *"Permission denied"*                              | **Open Settings** |
| Saved generation model is no longer available | *"Model not found"* / *"Invalid generation model"* | **Open Settings** |

After you fix the cause in Settings, return to the Translate tab and click Translate All Files again.

### Internet connection lost during a long batch

The application makes up to 5 silent retry attempts on connection / timeout / rate-limit errors before surfacing a dialog:

- **First three attempts** show the  inline status: *"Connection issue, retrying in Ns (attempt N/5)…"*
- **Fourth attempt and beyond** escalate to the  banner: *"Connection interrupted — retrying every Ns…"* with a second line showing *"N of M languages translated so far."*
- If all five attempts exhaust without recovery, the  dialog *"Internet connection lost"* appears with **Retry** and **Cancel** buttons.

Total silent budget is roughly 2.5 minutes (5 attempts × 30s cap). For rate-limit responses the application also honors OpenAI's `Retry-After` header when present (clamped to 60s so a misbehaving server can't park the run indefinitely).

### Other  error dialogs

When the silent-retry budget exhausts on something other than a generic connection drop, you may see one of these less common dialogs. Each has a distinct title so the cause is clear from a glance, and a single primary action button matched to the recovery path:

| Cause | Dialog title | Message | Primary button |
|---|---|---|---|
| Request didn't return in time (after 5 retries) | *"Request timed out"* | "OpenAI did not respond in time." | **Retry** (Cancel also available) |
| OpenAI server-side outage (HTTP 500) | *"OpenAI server issue"* | "OpenAI is currently experiencing server problems." | **Retry** |
| Request itself was invalid (HTTP 400 — content too long, malformed, content policy) | *"Invalid translation request"* | The raw OpenAI rejection message | **OK** (no retry — same input would fail again) |

**Timeout** and **server issue** behave like any other transient error — clicking Retry reruns the whole batch from the start, which will retranslate already-completed files (Phase 1 cost trade-off; see FAQ). **Invalid translation request** has no Retry button because the underlying problem (input too long, content policy violation, etc.) won't be fixed by trying again with the same input. Check the dialog's message and the log for the specific reason, then adjust your source files, DNT list, or model selection before starting a new run.

---

## Frequently Asked Questions

### What happens if only one language fails?

Successful language translations are preserved automatically.
The failed language appears in the final summary dialog, and you can retry only the failed languages using the **Retry Failed Languages** button — available both inside the results dialog itself and on the Translate tab after the dialog is dismissed.

Only **transient** failures are retryable (connection issues, timeouts, rate-limit / throttling, OpenAI server errors). Authentication, permission, and bad-model errors abort the whole batch instead and are not offered for retry — you must fix the underlying cause in Settings and click Translate All Files again.

### Can I retry after an authentication error?

No, not directly. Authentication failures (bad key, permission denied, invalid model) produce a  dialog with an **Open Settings** button. Open Settings, fix the API key or model, then return to the Translate tab and click Translate All Files. The application doesn't offer a one-click retry for these because retrying the exact same call would just hit the same failure.

### What does the `Retry-After` header do?

For rate-limit (HTTP 429) responses, OpenAI may send a `Retry-After` hint telling the client how many seconds to wait before retrying. The application honors this hint (clamped to 60 seconds so a misbehaving server can't park you for minutes). When OpenAI's hint is shorter than the application's exponential backoff, the backoff wins; when the hint is longer, the hint wins. This makes rate-limit recovery faster and more accurate than a fixed schedule.

### Why was one selected language skipped automatically?

The translator automatically skips target languages that match the detected source language.
For example, if the source subtitles are already in English and English is selected as a target language, the application removes it automatically to prevent duplicate output files.

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

### Behavior summary

The application reacts to errors at four levels, matching the severity of the problem to how much it bothers you:

| State | What you see | Action available |
|---|---|---|
| transient (≤30s) | Inline retry status line, e.g. *"Connection issue, retrying in 5s (attempt 1/5)…"* | None — silent recovery |
| sustained (30s–5min) | Banner escalates to *"Connection interrupted — retrying every Ns…"* with *"N of M languages translated so far."* | Cancel Translation button |
| account-level | Modal dialog with title, plain-English message, and one primary action button | Open Settings / Open platform.openai.com / Wait and Retry / Retry-Cancel / Retry / OK |
| run complete | Final results dialog listing succeeded and failed languages | Open Output Folder / Retry Failed Languages / OK |

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
