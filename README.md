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

- Download a packaged build from `dist/<platform>/SRT_Translator/` (or from a release zip)
- Double‑click to run the app (see INSTALLATION.md for OS‑specific notes)
- Open **API Configuration** in the app and paste your OpenAI API key
- Add your `.srt` files and click **Translate All Files**

See **INSTALLATION.md** for building per‑platform and packaging details.

---

## Features

- **Multi-language Translation**: Translate to multiple languages at once
- **Preserve Important Terms**: Keep names, brands, and technical terms untranslated
- **Maintains Timing**: Subtitle timing and formatting stay intact with improved batch boundary enforcement
- **Automatic Error Fixing**: Intelligently fixes common translation issues
- **Professional Results**: High-quality translations suitable for public content
- **Smart Batching**: Sentence-aware batch processing for better context and translation quality
- **Centralized Configuration**: Single source of truth for all translation settings
- **Thread-Safe GUI**: Improved reliability for concurrent operations

---

## Installation

### For Content Creators (Executable)

1. **Download** the latest release for your platform
2. **Extract** the files to a folder
3. **Run** the executable
4. **Follow** the on-screen setup instructions

**Note**: Windows may show security warnings because this is free, open-source software. This is normal and safe.

### For Developers (Source Code)

1. **Clone the repository**
2. **Create virtual environment**: `python -m venv venv`
3. **Activate environment**: 
   - Windows: `venv\Scripts\activate`
   - Mac/Linux: `source venv/bin/activate`
4. **Install**: `pip install -e .`
5. **Run**: `python run_gui.py`

### Developers: Build Binaries (macOS/Windows/Linux)

If you want a standalone app without requiring Python, you can build it with PyInstaller.

Prerequisites:
- Python 3.11+ recommended
- Create and activate a virtual environment
- Install dependencies and PyInstaller

```
pip install -e .
pip install pyinstaller
```

Build commands:

- Windows (no console window):
```
pyinstaller --noconsole --name SRT-Translator \
  --add-data "config\\languages.json;config" \
  run_gui.py
```

- macOS (GUI app bundle):
```
pyinstaller --windowed --name SRT-Translator \
  --add-data "config/languages.json:config" \
  run_gui.py
```

- Linux (one-folder recommended for Qt apps):
```
pyinstaller --windowed --name SRT-Translator \
  --add-data "config/languages.json:config" \
  run_gui.py
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
To choose the languages for translation, click the checkboxes under Popular Languages for quick access to common options.
If your desired language isn’t listed there, scroll through or use the Search Languages box in the list below to find and select it.

### 3. Do Not Translate (DNT) Terms (Optional)
- Add names, brands, or technical terms that shouldn't be translated
- Examples: Your name, company name, product names, technical acronyms

---

## Log Files and Troubleshooting

### Log File Locations

**All Modes (GUI and CLI):**
- Logs are now created inside batch-specific directories under your output directory
- Each translation session creates a new batch directory with format: `translation-batch-YYYYMMDD_HHMMSS±TZ/`
- Log files are located inside these batch directories as `translation_issues_YYYYMMDD_HHMMSS±TZ.log`

**Example Structure:**
```
Your Output Directory/
├── translation-batch-20250810_111157-0700/
│   ├── translation_issues_20250810_111157-0700.log
│   ├── manifest.json
│   ├── termbase.json
│   ├── dnt_terms.json
│   ├── ES/                    # Spanish translations
│   │   └── video1 - ES.srt
│   ├── FR/                    # French translations
│   │   └── video1 - FR.srt
│   └── DE/                    # German translations
│       └── video1 - DE.srt
└── translation-batch-20250810_143022-0700/
    ├── translation_issues_20250810_143022-0700.log
    ├── manifest.json
    └── ... (translated files)
```

**Note:** This new approach keeps all related files (logs, translations, configuration) organized together in batch-specific directories, making it easier to track and manage translation sessions.

### Log File Naming
- Format: `translation_issues_YYYYMMDD_HHMMSS±TZ.log`
- Example: `translation_issues_20250810_111157-0700.log`
- The timestamp includes timezone offset for precise session tracking

### Troubleshooting
- Check log files for detailed error messages
### Long Runs on macOS (Prevent Sleep)

For multi‑hour jobs, prevent the system from sleeping while allowing the display to turn off:

- Recommended: run the app under `caffeinate` from Terminal:
```
caffeinate -imsu python3 run_gui.py
```
  - Drop `-d` to allow the screen to sleep, keep the system awake. Use your packaged app path if running the .app bundle.
- Alternatively, in System Settings → Battery, disable Low Power Mode and enable “Prevent automatic sleeping when the display is off” on Power Adapter.
- Logs show translation progress, API responses, and fixer results
- Each translation session creates a new timestamped log file

### 4. AI-Generated Translation Settings (Recommended)
To improve translation quality, the SRT Translator app supports two professional tools: Do Not Translate (DNT) terms and a Termbase—and both can be created for you automatically using AI. DNT terms are names, acronyms, or product references (like "Amazon" or "ROI") that should remain in the original language. The Termbase is a glossary that ensures consistent translations for important business or technical terms, such as "operating plan" or "input metrics." Creating these lists is easy: just upload a few representative subtitle files and click "Generate Translation Settings." The app analyzes your content and uses AI to suggest DNT terms and generate a Termbase for each selected language. While optional, these tools are highly recommended for videos that contain brand names, industry jargon, or educational content—helping ensure your translations are clear, accurate, and consistent across all languages.

---

## Usage

### Step-by-Step Process

1. **Select your .srt files**
   - Click "Browse Files" to select the subtitle files you want to translate
   - Use "Select All" to choose all files in a folder, or "Clear All" to start over
   - Supported format: .srt files

2. **Configure settings**
   - Enter your API key
   - Select target languages
   - Add any DNT terms to preserve

3. **Start translation**
   - Click "Translate All Files"
   - Monitor progress in the interface
   - Check logs for any issues

4. **Find your results**
   - Translated files appear in language-specific folders
   - Each language gets its own subfolder
   - Original timing and formatting preserved

### Example Output Structure
```
Your Selected Output Directory/
├── ES/                    # Spanish translations
│   └── video1 - ES.srt
├── FR/                    # French translations
│   └── video1 - FR.srt
└── DE/                    # German translations
    └── video1 - DE.srt
```

**Note:** The GUI shows a "Files & Output" section where you can browse and select SRT files, then choose where to save the translated versions.

---

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

**Tips to reduce costs:**
- Remove unnecessary subtitles before translation
- Use fewer target languages initially
- Test with a short video first

---

## Troubleshooting

### Common Issues

**"API key not found"**
- Check that you entered the API key correctly
- Verify the key is active in your OpenAI account

**"Source directory does not exist"**
- Create the input folder: `mkdir original_captions`
- Place your .srt files in this folder

**Translation quality issues**
- Review and adjust your DNT terms list
- Check the logs for specific issues
- Try translating to fewer languages first

**Security warnings (Windows)**
- This is normal for free, open-source software
- Right-click → Properties → Unblock if needed
- The software is safe to run

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

The SRT Translator now uses a **clean architecture** with centralized configuration management:

- **`TranslationConfig`**: Immutable configuration object containing all translation settings
- **`ConfigResolver`**: Centralized logic for resolving configuration from different sources
- **`SettingsManager`**: Single source of truth for GUI state management
- **Environment Variables**: Used only for CLI mode, eliminated from GUI runtime

### Required Parameters

The SRT Translator requires these parameters to function:

| Parameter | Purpose | GUI Source | CLI Source | Configurable? |
|-----------|---------|------------|------------|---------------|
| `OPENAI_API_KEY` | Your OpenAI API key for translation | Settings → API Configuration | `.env` file | ✅ Yes |
| `TARGET_LANGUAGES` | Languages to translate to | Language Selection UI | `.env` file | ✅ Yes |
| `SOURCE_LANG` | Source language (usually English) | Settings → Translation Settings | `.env` file | ✅ Yes |
| `OPENAI_MODEL` | AI model to use | Settings → Translation Settings | `.env` file | ✅ Yes |
| `BATCH_SIZE` | Translation batch size | Settings → Translation Settings | `.env` file | ✅ Yes |

### Optional Parameters

| Parameter | Purpose | GUI Source | CLI Source | Configurable? |
|-----------|---------|------------|------------|---------------|
| `DNT_TERMS` | Terms not to translate | AI Configuration Generation | `.env` file | ✅ Yes |
| `TERMBASE_JSON` | Translation glossary | AI Configuration Generation | Manual file | ✅ Yes |
| `OUTPUT_DIRECTORY` | Where to save translations | File Selection UI | `.env` file | ✅ Yes |
| `FIX_AGGRESSIVENESS` | Auto-fix level (0-1) | Hardcoded to 0.75 | `.env` file | ❌ GUI only |

### Parameter Sources by Mode

#### **GUI Mode (New Architecture)**
- **Settings Storage**: Uses Qt's QSettings with `ConfigState` dataclass for thread-safe access
- **Language Selection**: Real-time UI updates with centralized `SettingsManager` state
- **File Selection**: UI file browser and output directory picker
- **AI Configuration**: Automatic generation of DNT terms and termbase
- **Environment Variables**: **No longer used for runtime state** - all configuration passed explicitly

#### **CLI Mode (Updated)**
- **Settings Storage**: Uses `ConfigResolver` to load from `.env` file
- **Language Selection**: Must be configured in `.env` file
- **File Selection**: Uses `original_captions/` directory
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
1. **Create `.env` file** in project root with required parameters
2. **Place .srt files** in `original_captions/` directory
3. **Configure languages** in `TARGET_LANGUAGES` environment variable
4. **Set up DNT terms** and termbase.json manually (optional)

### Example CLI Configuration (.env file)
```bash
# Required parameters
OPENAI_API_KEY=your_api_key_here
TARGET_LANGUAGES={"Spanish": "es", "French": "fr", "German": "de"}
SOURCE_LANG=en
OPENAI_MODEL=gpt-4o-mini
BATCH_SIZE=5

# Optional parameters
DNT_TERMS=YourName,YourCompany,YourProduct
OUTPUT_DIRECTORY=translated_srt_files
FIX_AGGRESSIVENESS=0.75
```

### Switching Between Modes

**GUI → CLI**: 
- Copy your API key and target languages to `.env` file
- Place files in `original_captions/` directory
- Run `python run_cli.py`

**CLI → GUI**: 
- Launch GUI with `python run_gui.py`
- Enter API key in Settings
- Select languages using UI checkboxes
- Browse and select files

---

## Advanced Configuration

### Environment Variables (For Advanced Users)

If you're installing from source, you can configure these settings:

**Required:**
- `OPENAI_API_KEY`: Your OpenAI API key
- `TARGET_LANGUAGES`: Dictionary of target languages

**Optional:**
- `DNT_TERMS`: Comma-separated list of DNT terms
- `SOURCE_LANG`: Source language (default: en)
- `OPENAI_MODEL`: AI model to use (default: gpt-4o-mini)
- `AGGRESSIVENESS`: Auto-fix level 0-1 (default: 0.75)

### Example Configuration
```bash
OPENAI_API_KEY=your_api_key_here
TARGET_LANGUAGES={"Spanish": "es", "French": "fr", "German": "de"}
DNT_TERMS=YourName,YourCompany,YourProduct
SOURCE_LANG=en
```

---

## Supported Languages

**Popular Languages (12):**
- Spanish, French, German, Italian
- Portuguese (Brazil), Chinese (Simplified)
- Japanese, Korean, Arabic, Hindi
- Russian, Dutch

**Total Available:** 78 languages including regional variants

---

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue.

## License

This project is licensed under the [MIT License](LICENSE).

## Support

For issues and feature requests, please use the [GitHub issues page](https://github.com/working-backwards/srt_translator/issues).

---

## Recent Improvements (v2.0)

### Architecture Refactoring
- **Eliminated Environment Variable Dependencies**: GUI no longer relies on environment variables for runtime state
- **Centralized State Management**: `SettingsManager` now serves as the single source of truth for all GUI configuration
- **Thread-Safe Operations**: Improved reliability for concurrent translation operations
- **Clean Configuration Abstraction**: New `TranslationConfig` and `ConfigResolver` classes for better maintainability

### Translation Quality Enhancements
- **Improved Prompt Structure**: Streamlined AI prompts for better translation consistency
- **Batch Boundary Enforcement**: Fixed timing drift issues by enforcing exact batch start/end times
- **Smart Termbase Integration**: Only relevant terms are included in each translation batch
- **Enhanced Error Handling**: Better detection and reporting of translation issues

### Bug Fixes
- **Language Selection Bug**: Fixed issue where all languages were used instead of user-selected ones
- **Termbase Lookup Bug**: Resolved problems with AI-generated termbase lookups
- **State Management Inconsistency**: GUI now correctly reflects and updates centralized state
- **Thread Safety Issues**: Background worker threads now properly communicate with GUI using Qt signals

### Performance Improvements
- **Sentence-Aware Batching**: Better context preservation across subtitle boundaries
- **Optimized Configuration Loading**: Faster startup and more efficient state management
- **Reduced Memory Usage**: More efficient handling of large translation projects

---
