## SRT Translator GUI User Manual

### Welcome

Thank you for using the SRT Translator. This guide is your friendly companion. It explains how the application works, and it walks you through a typical translation from start to finish. You do not need to write any code. You only need your subtitle files and your OpenAI API key.

### What the application does

The SRT Translator reads your original SRT subtitle files, translates them into one or more target languages, and writes clean, well‑timed SRT files to an output folder. It keeps your important terms intact when you tell it which words or phrases should never be translated. It can also apply a custom termbase so your business terms remain consistent.

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

This section lets you choose the folder that contains your original SRT files and the folder where translated files will be written. The application never deletes or modifies your original files. It reads them and writes new files to the output directory.

### Language Selection

This section lets you choose the languages you want to translate into. You can select one language or many languages. The application normalizes language names and codes for you, so you can choose “Japanese” or “ja” and the result will be the same.

### AI Configuration

This section controls the translation models and options. The application chooses sensible defaults. If you are new to the tool, you can accept the defaults. If you want to change the model for quality, speed, or cost, you can do so here.

### Translation

This section starts and monitors your translation. It shows progress and it writes a log that you can review later. It also shows any errors that occur. When the translation finishes, it tells you where the new files are located.

### Preview (optional)

Some builds include a preview section. If you see it, you can preview how a translated SRT block will look before you translate the entire file. This is helpful if you are adjusting your DNT terms or your termbase.

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
8. When the translation completes, open the output folder. Review the files in your media player or subtitle editor.

If you notice a term that should not have been translated, add it to your DNT list and translate again. If you want a term to be translated in a specific way, add it to the termbase and translate again. The application will respect your preferences.

---

## Advanced Concepts Explained Simply

### Do Not Translate (DNT) Terms

DNT terms are exact strings that the translator preserves. They protect names, brands, acronyms, and sensitive phrases. You can add, remove, and reorder these terms. When a DNT placeholder appears during an intermediate step, the application keeps it unchanged so the final output remains correct. Use DNT terms when a word should never change.

### Custom Termbase

A termbase is a list of terms and their preferred translations for one or more languages. It helps your translations sound consistent and professional. You can provide a termbase for a single language or several languages. The translator applies the termbase when the terms appear in context. Use a termbase when you want consistent terminology across many files.

### Timing and Structure

The application keeps subtitle numbering and structure stable. It processes the file in batches so the model can understand context. It enforces the start time of the first subtitle and the end time of the last subtitle within each batch. This clamping prevents drift across batches. When the model returns fewer or more subtitles than expected, the application redistributes content within the same time boundaries. It does not create blank subtitles. It produces clean output that players can read easily.

---

## Settings That Matter

### Source and Target Languages

The source language is the language of your original SRT file. The application defaults to English. You can change it if needed. The target languages are the languages you want to generate. You can map names to codes or simply select by name.

### Output Directory

The output directory is where the application writes the translated SRT files. You may choose any writable folder. The application creates language‑specific filenames so you can find results quickly.

### Models

The application uses reliable, cost‑effective models by default. If you want higher quality, you can select a stronger model in the AI Configuration section. If you want faster or cheaper results, you can select a lighter model. The defaults will serve most projects well.

---

## Troubleshooting

### I do not see any translations.

Please confirm your API key in the API Configuration section. Make sure your internet connection is stable. Check the log for any error messages. If the log reports an authentication error, you may need to create a new key.

### The timing looks unusual in a few places.

The application enforces batch boundaries. It clamps the first subtitle of each batch to the original batch start and clamps the last subtitle of each batch to the original batch end. If a model returns more or fewer subtitles than expected, the application redistributes content within the batch without creating blank lines. This approach prevents cross‑batch drift while keeping subtitles readable.

### Some terms should have stayed in English.

Add those exact phrases to the DNT Terms list and run the translation again. The translator will keep those phrases as written.

### A business term needs a specific translation.

Add the term and its preferred translation to your termbase for that language. Then translate again. The translator will apply your preference whenever it finds the term.

### The application feels slow.

Large files and many target languages take more time. You can translate fewer languages at once to speed things up. You can also select a faster model in the AI Configuration section. The log shows progress so you can see the work as it happens.

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

### Where can I find log files for troubleshooting?

The application creates detailed log files that you can check if something goes wrong. You can find them here:

**Windows:**
- `C:\Users\[YourUsername]\AppData\Local\SRTTranslator\Logs\`

**macOS:**
- `~/Library/Application Support/SRTTranslator/Logs/`

**Linux:**
- `~/.local/share/SRTTranslator/Logs/`

Log files are named with timestamps like `translation_issues_20250807_171613.log`. They contain detailed information about what happened during translation, including any errors or issues that the automatic fixer addressed.

---

## Tips for Better Results

- Keep your DNT list focused. Add proper names and acronyms that should remain unchanged.
- Build a small termbase for your domain. Consistent terminology improves quality and user trust.
- Preview a small section before you translate a long file. This habit helps you confirm that your settings produce the tone you want.
- Review translated files in a player that you trust. Adjust your lists and run the translation again if needed.

---

## Final Notes

This guide is meant to be your companion. It uses complete sentences so you can skim quickly or read carefully. If you follow the steps in order, you will create professional translations with minimal effort. If you ever feel unsure, return to the top, and read through the Getting Started and Step‑by‑Step sections again. They will bring you back on track.
