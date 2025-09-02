# SRT Translator

## Overview

The **SRT Translator** is a tool that uses AI to translate subtitle files while preserving important terms like names, brands, and technical terms. Perfect for content creators who want to reach international audiences.

### Who is this for?

**Perfect for:**
- **Content creators** translating videos for international viewers
- **YouTubers and podcasters** expanding to global audiences
- **Course creators** offering multilingual educational content
- **Business professionals** localizing training videos

**What you need to know:**
- Basic computer skills (no programming required)
- An OpenAI API key (costs ~$0.01-0.05 per minute of video)
- Subtitle files in .srt format

---

## Quick Start (5 minutes)

### For GUI Users (Recommended for most users)
- Download a packaged build from `dist/<platform>/SRT_Translator/` (or from a release zip)
- Double‑click to run the app (see INSTALLATION.md for OS‑specific notes)
- Open **API Configuration** in the app and paste your OpenAI API key
- Add your `.srt` files and click **Translate All Files**

### For CLI Users
- Install with `pip install srt-translator`
- Run `srtx` after configuring your `.env` file

See **INSTALLATION.md** for building per‑platform and packaging details.

---

## Features

- **Multi-language Translation**: Translate to multiple languages at once
- **Preserve Important Terms**: Keep names, brands, and technical terms untranslated
- **Maintains Timing**: Subtitle timing and formatting stay intact with deterministic subtitle-based formatting
- **Automatic Error Fixing**: Intelligently fixes common translation issues
- **Professional Results**: High-quality translations suitable for public content
- **Smart Batching**: Subtitle-aware processing for better context and translation quality
- **Translation Quality Improvements**: Progressive shrinking and no-orphans protection eliminate quality cliffs
- **Centralized Configuration**: Single source of truth for all translation settings
- **Thread-Safe GUI**: Improved reliability for concurrent operations
- **Quality Hardening**: Automatic filtering of numeric DNT terms and DNT precedence enforcement
- **Script-Aware Termbase**: AI-generated translations validated against proper script requirements
- **Hard-Preserve DNT**: Intelligent DNT filtering that keeps only truly important terms (acronyms, tech tokens)
- **Enhanced Output**: Complete transparency into what was provided vs. what was used during translation
- **Subtitle-Based Translation**: New subtitle-level processing system that eliminates timing drift while improving translation quality
- **Language-Specific Termbases**: AI generates optimal termbases for each target language, improving translation quality
- **Automatic Evaluation**: Quality assessment with configurable thresholds and comprehensive reporting

---

## Evaluation

After each translation, the evaluator runs automatically and writes artifacts to your batch folder.

### Where config is discovered

- **Rubric:** `config/translation_rubric.yaml` (project-level). This defines thresholds and reporting behavior. It is **not** overridden at runtime.
- **DNT / Termbase:** the **client writes** these to the **batch root**:
  - `dnt_summary.json` — **audit mirror** of DNT terms (optional; not used by eval).
  - `termbase_summary.json` — **audit mirror** of termbase (optional; not used by eval).

> The evaluator **does not** fall back to `ai_config.json`. If you want DNT/TB coverage, ensure those two JSON files are written to the batch root.

### What the evaluator writes

At the batch root:

- `eval_report.md` — creator-friendly, consolidated punch list (shows **all** issues).
- `artifacts/<lang>/…` — per-language CSVs and summaries (DNT coverage, termbase coverage, untranslated after DNT, optional fragments).
  - DNT/TB snapshots **may** be copied into each `artifacts/<lang>/` as `dnt_summary.json` / `termbase_summary.json` for auditing. Evaluation does **not** read them.
  - **Fragments CSV** is only written when non-empty and the rubric's fragments policy applies (e.g., non-Latin scripts under `auto_non_latin`).

### Re-running evaluation

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

### Reporting behavior

- **Untranslated after DNT:** ignores trivial single-word cognates; upper-case acronyms are **INFO** unless covered by DNT/TB.
- **Missing translation:** empty cues are listed explicitly.
- **Timing drift:** omitted unless there are findings.

### Language labels

The report uses the **language config abstraction** (`srt_translator.core.config.language_config`) to resolve friendly names. The source language label comes from `manifest.json` (`original_language.name`/`code`) when available.

Edit SRTs in any text editor. Keep the **cue number** and **timings** unchanged; only modify the subtitle text.

### Global fragments policy

- Rubric key: `fragments.mode` (`auto_non_latin` | `always` | `never`), with `min_ascii_run`.
- Default is `auto_non_latin`: generate the source-fragments CSV only when the **target text** is predominantly non-Latin script.

---

## Translation Quality Improvements

The latest version includes significant improvements to translation quality that eliminate the "quality cliff" issue:

### Progressive Shrinking
When batch translation fails (e.g., 5 inputs → 4 outputs), the system now uses intelligent batch size reduction instead of immediately falling back to individual translation:

- **Preserves context**: Phrases like "me llamo Colin Bryar" stay together
- **Maintains quality**: Batch translation advantages preserved as long as possible
- **Graceful degradation**: Smooth quality reduction instead of immediate cliff

### No-Orphans Protection
Language-aware subtitle optimization prevents orphaned function words at subtitle boundaries:

- **Spanish**: "Me llamo | Colin" instead of "Me | llamo Colin"
- **English**: "I am going | to the store" instead of "I am | going to the store"
- **Japanese**: "私 | は行きました" instead of "私は | 行きました"

### Language Support
Works across all supported language families with configurable rules:
- **Latin scripts**: English, Spanish, French, German, etc.
- **CJK scripts**: Chinese, Japanese, Korean
- **Other families**: Cyrillic, RTL, Indic languages

See [TRANSLATION_QUALITY_GUIDE.md](docs/TRANSLATION_QUALITY_GUIDE.md) for detailed configuration options.

### Source Language Assumptions

The app **does not require you to specify the original language**; the AI infers it from the transcript text. However, to keep terminology extraction reliable and evaluation artifacts consistent, **all original `.srt` files you select for a single run should be in the SAME language**. Mixing different source languages in one batch is not supported and may degrade results.

**DNT precedence:** If a term appears in both DNT and the termbase, **DNT wins**. DNT items are excluded from the termbase at generation time. See the evaluation guide for coverage goals and collision policy.

---

## Resilience to model under-runs

The translator preserves 1:1 cue parity and original timings by design. When a model returns an empty line for a cue:
1) A one-shot **pair retry** is attempted with the next cue. If the empty cue is the last in a batch, a **cross-batch pair retry** is performed using the first cue of the next batch.
2) If retry fails (BOUNDED/DEV), the cue remains **empty** (we do not paste source text). The evaluator will clearly flag it as **Missing translation**.
3) The SRT writer **always emits** a cue block (even if text is empty), avoiding "missing cue" shifts downstream.

---

## Installation

### Console Scripts (Recommended)

After installation, you can use these simple commands from any terminal:

- **GUI**: `srtx` - Launches the graphical interface (default, requires `pip install srt-translator[gui]`)
- **CLI**: `srtx-cli` - Launches the command-line interface
- **Evaluation**: `st-eval` - Re-runs evaluation on completed translation batches

### For Content Creators (Executable)

1. **Download** the latest release for your platform
2. **Extract** the files to a folder
3. **Run** the executable
4. **Follow** the on-screen setup instructions

**Note**: Windows may show security warnings because this is free, open-source software. This is normal and safe.

## Installation Options

### CLI Only (Lightweight)
```bash
pip install srt-translator
srtx-cli --help
```

### With GUI Support
```bash
pip install srt-translator[gui]
srtx
```

### From Source (Development)
```bash
git clone https://github.com/working-backwards/srt_translator.git
cd srt_translator
pip install -e .[gui]  # Includes GUI dependencies
```

### For Developers (Source Code)

1. **Clone the repository**
2. **Create virtual environment**: `python -m venv venv`
3. **Activate environment**:
   - Windows: `venv\Scripts\activate`
   - Mac/Linux: `source venv/bin/activate`
4. **Install**:
   - CLI only: `pip install -e .`
   - With GUI: `pip install -e .[gui]`
5. **Run**:
   - CLI: `srtx-cli`
   - GUI: `srtx` (if installed with GUI extras)

### Developers: Build Binaries (macOS/Windows/Linux)

If you want a standalone app without requiring Python, you can build it with PyInstaller.

Prerequisites:
- Python 3.11+ recommended
- Create and activate a virtual environment
- Install dependencies and PyInstaller

```
pip install -e .[gui]
pip install pyinstaller
```

Build commands:

**Quick Build (Recommended):**
```bash
# Use the provided build script
python scripts/build_gui.py
```

**Manual Build:**
- Windows (no console window):
```
pyinstaller --noconsole --name SRT-Translator \
  --add-data "srt_translator/core/config/languages.json;srt_translator/core/config" \
  srt_translator/gui/main_window.py
```

- macOS (GUI app bundle):
```
pyinstaller --windowed --name SRT-Translator \
  --add-data "srt_translator/core/config/languages.json:srt_translator/core/config" \
  srt_translator/gui/main_window.py
```

- Linux (one-folder recommended for Qt apps):
```
pyinstaller --windowed --name SRT-Translator \
  --add-data "srt_translator/core/config/languages.json:config" \
  srt_translator/gui/main_window.py
```

Output is created in `dist/`. On macOS you will get `SRT-Translator.app`; on Windows `SRT-Translator\SRT-Translator.exe`.

Notes:
- The `--add-data` syntax uses `;` on Windows and `:` on macOS/Linux.
- For Linux distribution, shipping source with a virtualenv is often simpler than distributing a binary because of glibc/Qt variations.

---

## Basic Configuration

### 1. API Key Setup
- Get an OpenAI API key from [OpenAI's website](https://platform.openai.com/api-keys)
- Enter it in the GUI's API Configuration section
- Test the connection to verify it works

### 2. Target Languages
Choose languages via checkboxes. The **Popular Languages** row is **adaptive**:
it learns from your recent runs (and your manual picks), so your most commonly
used languages (e.g., **az**) stay easy to access. If a language isn't shown,
use the search to find and select it.

### 3. Translation Quality Tools (Optional but Recommended)

The SRT Translator app supports two professional tools that work together to improve translation quality:

**Do Not Translate (DNT) Terms:**
- Names, brands, or technical terms that shouldn't be translated
- Examples: Your name, company name, product names, technical acronyms
- Can be added manually or generated automatically using AI

**Termbase:**
- A glossary that ensures consistent translations for important business or technical terms
- Examples: "operating plan", "input metrics", industry-specific terminology
- Automatically generated using AI analysis of your content

**AI Generation Process:**
Both tools can be created automatically by uploading a few representative subtitle files and clicking "Generate Translation Settings." The app analyzes your content and uses AI to suggest DNT terms and generate a Termbase for each selected language. While optional, these tools are highly recommended for videos that contain brand names, industry jargon, or educational content—helping ensure your translations are clear, accurate, and consistent across all languages.

### 4. Quality Hardening Features

The SRT Translator includes advanced quality improvements that automatically enhance translation results:

**Automatic DNT Filtering:**
- Numeric and number-like terms (e.g., "300 milliseconds", "2025", "6.7") are automatically filtered from DNT lists
- Prevents these terms from blocking proper localization (e.g., "300毫秒" instead of "300 milliseconds")
- Maintains important non-numeric DNT terms like brand names and technical acronyms

**DNT Precedence Enforcement:**
- DNT terms always take priority over termbase entries
- Automatically resolves conflicts between DNT terms and termbase translations
- Ensures consistent behavior across all languages

**Relevant Termbase Injection:**
- Only termbase entries actually present in the current batch are injected
- Reduces AI hallucinations and improves translation relevance
- Automatic size capping prevents termbase overload

**Enhanced Output Transparency:**
- Complete visibility into what was provided vs. what was actually used
- Detailed filtering logs showing what was removed and why
- Per-language processing summaries for quality validation

### 4. Example Output Structure

By default, outputs are written to your OS’s standard application data directory:
macOS ~/Library/Application Support/srt-translator/translated_files/,
Windows %LOCALAPPDATA%\srt-translator\translated_files\,
Linux ~/.local/share/srt-translator/translated_files/.

You can override this location in the GUI or in your .env file for the CLI.

After translation, your files will be organized in batch-specific directories with enhanced output files:

```
Your Selected Output Directory/
├── translation-batch-20250810_111157-0700/
│   ├── translation_issues_20250810_111157-0700.log
│   ├── artifacts/                       # Per-language artifacts
│   │   ├── es/                         # Spanish artifacts
│   │   │   ├── dnt_summary.json       # (audit mirror) optional; not used by eval
│   │   │   ├── termbase_summary.json  # (audit mirror) optional; not used by eval
│   │   │   └── manifest.json          # Language-specific manifest
│   │   ├── fr/                         # French artifacts
│   │   │   ├── dnt_summary.json       # (audit mirror)
│   │   │   ├── termbase_summary.json  # (audit mirror)
│   │   │   └── manifest.json
│   │   └── de/                         # German artifacts
│   │       ├── dnt_summary.json       # (audit mirror)
│   │       ├── termbase_summary.json  # (audit mirror)
│   │       └── manifest.json
│   ├── ES/                              # Spanish translations
│   │   └── video1 - ES.srt
│   ├── FR/                              # French translations
│   │   └── video1 - FR.srt
│   └── DE/                              # German translations
│       └── video1 - DE.srt
└── translation-batch-20250810_143022-0700/
    ├── translation_issues_20250810_143022-0700.log
    └── ... (translated files)
```

**Enhanced Output Files:**
- **`artifacts/<lang>/dnt_summary.json`**: (audit mirror) optional snapshot; eval does **not** use this file
- **`artifacts/<lang>/termbase_summary.json`**: (audit mirror) optional snapshot; eval does **not** use this file
- **`artifacts/<lang>/manifest.json`**: Language-specific manifest with complete metadata

**Note:** Each translation session creates a new batch directory with logs and configuration files, making it easier to track and manage translation sessions. The GUI shows a "Files & Output" section where you can browse and select SRT files, then choose where to save the translated versions.

### Enhanced Output Format

The SRT Translator now provides complete transparency into the translation process:

**Processing Summary (in artifacts/<lang>/manifest.json):**
```json
{
  "processing_summary": {
    "dnt_terms": {
      "provided": 25,
      "used": 22,
      "filtered": 3
    },
    "termbase": {
      "provided_entries": 45,
      "used_entries": 38,
      "collisions_resolved": 7
    },
    "quality_improvements": [
      "Numeric DNT terms automatically filtered",
      "DNT precedence enforced over termbase",
      "Relevant-only termbase injection"
    ]
  }
}
```

**DNT Terms Details (in artifacts/<lang>/dnt_summary.json):**
- **User provided**: Your original DNT terms
- **Filtered for translation**: Terms actually used (numeric items removed)
- **Filtering details**: What was removed and why

**Termbase Details (in artifacts/<lang>/termbase_summary.json):**
- **User provided**: Your original termbase
- **Filtered for translation**: Termbase actually used (DNT collisions resolved)
- **Collision details**: What was removed due to DNT conflicts

This transparency helps you:
- **Validate quality improvements** applied during translation
- **Debug configuration issues** by seeing exactly what was used
- **Track changes** across different translation runs
- **Share results** with reviewers or other team members

---

## Log Files and Troubleshooting

### Log File Locations

**All Modes (GUI and CLI):**
- Logs are now created inside batch-specific directories under your output directory
- Each translation session creates a new batch directory with format: `translation-batch-YYYYMMDD_HHMMSS±TZ/`
- Log files are located inside these batch directories as `translation_issues_YYYYMMDD_HHMMSS±TZ.log`

### Log File Naming
- Format: `translation_issues_YYYYMMDD_HHMMSS±TZ.log`
- Example: `translation_issues_20250810_111157-0700.log`
- The timestamp shows your local time, making it easy to find logs from specific translation sessions

### Troubleshooting
- Check log files for detailed error messages

### Long Runs on macOS (Prevent Sleep)

For multi‑hour translation jobs, you'll want to prevent your Mac from going to sleep while allowing the screen to turn off to save power:

**Option 1: System Settings (Recommended for most users)**
1. Go to **System Settings** → **Battery**
2. Disable **Low Power Mode**
3. Enable **"Prevent automatic sleeping when the display is off"** under Power Adapter settings

**Option 2: Terminal Command (For users familiar with Mac Terminal)**
If you're comfortable using Terminal, you can run the app with a command that keeps the system awake:
```
caffeinate -imsu srtx
```

**Note:** Both methods will keep your Mac awake during long translations while allowing the screen to sleep to save power. The app will continue working in the background, and you can check progress in the logs.

## Cost Estimation

**Typical costs:**
- **Short video (5-10 minutes)**: $0.05-0.15
- **Medium video (20-30 minutes)**: $0.20-0.50
- **Long video (60+ minutes)**: $0.50-1.50

**Factors affecting cost:**
- Length of video
- Number of languages
- Complexity of content
- Number of subtitles

---

## Troubleshooting

### Common Issues

**"API key not found"**
- Check that you entered the API key correctly
- Verify the key is active in your OpenAI account

**Translation quality issues**
- Review and adjust your DNT terms and termbase
- Check the logs for specific issues
- Try translating to fewer languages first

**Security warnings (Windows)**
- This is normal for free, open-source software
- Right-click → Properties → Unblock if needed
- If your antivirus software flags the program, you may need to create an exception for it

---

## FAQ

**Q: Do I need to edit my .srt files first?**
A: No, just place them in the input folder as-is.

**Q: Can I translate to multiple languages at once?**
A: Yes! Select multiple target languages in the interface.

**Q: What if some terms get translated that shouldn't be?**
A: Add them to your DNT terms list and re-run the translation.

**Q: How accurate are the translations?**
A: Very good for most content. Review important videos before publishing.

**Q: Can I use this on Windows/Mac/Linux?**
A: Yes, the tool works on all major platforms.

**Q: Is my content secure?**
A: Yes, only subtitle text is sent to OpenAI. Your video files stay local.

---

## Configuration Parameters

### Architecture Overview

The SRT Translator now uses a **clean architecture** with centralized configuration management and a **subtitle-based translation system**:

- **Subtitle-Based Processing**: Subtitle-level translation with deterministic formatting to preserve timing

### Required Parameters

The SRT Translator requires these parameters to function:

| Parameter | Purpose | GUI Source | CLI Source | Configurable? |
|-----------|---------|------------|------------|---------------|
| `OPENAI_API_KEY` | Your OpenAI API key for translation | Settings → API Configuration | `.env` file | ✅ Yes |
| `TARGET_LANGUAGES` | Languages to translate to | Language Selection UI | `.env` file | ✅ Yes |
| `OPENAI_MODEL` | AI model to use | Settings → Translation Settings | `.env` file | ✅ Yes |
| `BATCH_SIZE` | Translation batch size | Settings → Translation Settings | `.env` file | ✅ Yes |

### Optional Parameters

| Parameter | Purpose | GUI Source | CLI Source | Configurable? |
|-----------|---------|------------|------------|---------------|
| `DNT_TERMS` | Terms not to translate (JSON array format) | AI Configuration Generation | `.env` file | ✅ Yes |
| `OUTPUT_DIRECTORY` | Where to save translations | File Selection UI | `.env` file | ✅ Yes |
| `FIX_AGGRESSIVENESS` | Auto-fix level (0-1) | Hardcoded to 0.75 | `.env` file | ❌ GUI only |

### Parameter Sources by Mode

#### **GUI Mode (New Architecture)**
- **Settings Storage**: Uses Qt's QSettings; AI Config is the single source of truth (no duplicate GUI state)
- **Language Selection**: Real-time UI updates with centralized `SettingsManager` state
- **File Selection**: UI file browser and output directory picker
- **AI Configuration**: Automatic generation of DNT terms and termbase
- **Environment Variables**: **No longer used for runtime state** - all configuration passed explicitly

#### **CLI Mode (Updated)**
- **Settings Storage**: Uses `ConfigResolver` to load from `.env` file
- **Language Selection**: Must be configured in `.env` file
- **File Selection**: Configured via `INPUT_DIRECTORY=` in `.env` file (defaults to `./original_captions/` relative to project root)
- **AI Configuration**: Manual setup of DNT terms and termbase.json
- **Environment Variables**: Loaded from `.env` file via `ConfigResolver`

### Quick Configuration Guide

#### **For GUI Users:**
1. **First Time Setup**: Enter API key in Settings → API Configuration
2. **Language Selection**: Use the Popular Languages checkboxes or search the full list
3. **File Selection**: Browse and select your .srt files
4. **Output Directory**: Choose where to save translations (optional)
5. **AI Configuration**: Generate DNT terms and termbase automatically

#### **For CLI Users:**
1. **Copy the example configuration file** to your project root:
   - **Windows/Linux/macOS:** `cp examples/env_example .env`
   - **Windows (PowerShell):** `Copy-Item examples/env_example .env`
2. **Edit the `.env` file** with your actual values
3. **Configure input directory** with `INPUT_DIRECTORY=path/to/your/srt/files` (optional, defaults to `./original_captions/` relative to project root)
4. **Configure languages** in `TARGET_LANGUAGES` environment variable
5. **Set up DNT terms** and termbase.json manually (optional)

**Note**: The CLI (`srtx`) works independently of the GUI and can be installed on headless servers without GUI dependencies.

### Example CLI Configuration (.env file)
```bash
# Required parameters
OPENAI_API_KEY=your_api_key_here
TARGET_LANGUAGES={"Spanish": "es", "French": "fr", "German": "de"}
OPENAI_MODEL=gpt-4o-mini
BATCH_SIZE=5

# Optional parameters
DNT_TERMS=["YourName", "YourCompany", "YourProduct"]
OUTPUT_DIRECTORY=translated_srt_files
FIX_AGGRESSIVENESS=0.75
```

---

## Advanced Configuration

### Environment Variables (For Advanced Users)

**Important Configuration Policy:**
The CLI reads configuration from `.env` files only. OS environment variables are ignored for all settings **except** `OPENAI_API_KEY`, which may be provided via OS environment and overrides `.env` if both are present.

**Required:**
- `OPENAI_API_KEY`: Your OpenAI API key (may also be set via OS environment)

**Optional (`.env` only):**
- `TARGET_LANGUAGES`: Dictionary of target languages (JSON or CSV format)
- `DNT_TERMS`: Terms not to translate (JSON array or CSV format)
- `OPENAI_MODEL`: AI model to use (default: gpt-4o-mini)
- `BATCH_SIZE`: Translation batch size (default: 5)
- `AGGRESSIVENESS`: Auto-fix level 0-1 (default: 0.75)
- `LOG_MODE`: Logging verbosity (Standard/Verbose, default: Standard)
- `OUTPUT_DIRECTORY`: Where to save translations (default: translated_srt_files)
- `TERMBASE_PATH`: Path to termbase file (default: termbase.json)

**Format Examples:**
- `TARGET_LANGUAGES`: `{"Spanish": "es", "French": "fr"}` or `Spanish,French`
- `DNT_TERMS`: `["YourName", "YourCompany"]` or `YourName,YourCompany`

### Termbase Configuration

The termbase is a JSON file that ensures consistent translations for important business or technical terms across all languages. It's particularly useful for:

- **Industry-specific terminology** (e.g., "operating plan", "input metrics")
- **Company-specific language** (e.g., product names, service descriptions)
- **Technical jargon** that should be translated consistently

**Termbase Structure:**
```json
{
  "operating plan": {
    "es": "plan operativo",
    "fr": "plan opérationnel",
    "de": "Betriebsplan"
  },
  "input metrics": {
    "es": "métricas de entrada",
    "fr": "métriques d'entrée",
    "de": "Eingangsmetriken"
  }
}
```

**Creating a Termbase:**
1. **AI-Generated**: Use the GUI's "Generate Translation Settings" feature
2. **Manual Creation**: Create a `termbase.json` file in the project root directory
3. **Hybrid Approach**: Start with AI generation, then manually refine

**CLI Mode Usage:**
- Place your `termbase.json` file in the project root directory
- The CLI will automatically load it when you run `srt-cli`
- No environment variable configuration needed for the termbase

### Example Configuration
```bash
OPENAI_API_KEY=your_api_key_here
TARGET_LANGUAGES={"Spanish": "es", "French": "fr", "German": "de"}
DNT_TERMS=YourName,YourCompany,YourProduct
INPUT_DIRECTORY=./my_subtitle_files
```

**Note:** For CLI mode, place your `termbase.json` file in the project root directory. The CLI will automatically load it.

---

## Supported Languages
**Total Available:** 78 languages including regional variants

---

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue.

**We use pre-commit hooks to ensure code quality.** See [CONTRIBUTING.md](CONTRIBUTING.md) for setup instructions.

## License

This project is licensed under the [MIT License](LICENSE).

## Support

For issues and feature requests, please use the [GitHub issues page](https://github.com/working-backwards/srt_translator/issues).
