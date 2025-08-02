# SRT Translator
## Overview

The **SRT Translator** is a Python-based tool that uses OpenAI’s GPT API to translate `.srt` subtitle files while preserving specific terms—like names, brands, or technical terms—that should *not* be translated. It supports multiple target languages and ensures subtitle timing, numbering, and formatting remain intact.

### Who is this for?

This tool is ideal for:

* **Content creators** translating videos for international viewers
* **Course creators and educators** offering multilingual educational content
* **Business professionals** localizing training videos, presentations, or internal communications
* **YouTubers and podcasters** expanding to global audiences
* **Localization teams** managing subtitles with branded terms or specialized vocabulary
* **Small businesses** looking for a cost-effective alternative to full-service localization

**Best suited for users who:**

* Have subtitle files (in srt format) that need translation into one or more languages
* Need to preserve specific terms like names, product names, or acronyms
* Want consistent, professional subtitle formatting without manual editing

**May not be ideal if:**

* You only need a quick, one-time translation of a single file (an online tool might be faster)
* Your subtitles don’t include terms that must be preserved
* You require human-level localization, cultural nuance, or creative rewriting

### What You Need (and Don’t Need) to Know

To use the SRT Translator, you **don’t need to be a developer**—but you should be comfortable with a few basic tasks.

✅ You **should know how to**:

* Use the command line on Windows, macOS, or Linux
* Run simple Python commands like `python run.py`
* Install packages with `pip`
* Edit a `.env` configuration file
* Copy your `.srt` files into folders

🚫 You **don’t need to know how to**:

* Write or debug Python code
* Understand the OpenAI API
* Use Git or GitHub
* Read complex error logs
* Know anything about programming

If you’ve used basic command-line tools before (or followed setup instructions for a Python-based app), you’ll feel right at home using the SRT Translator app.


## Features
- **Multi-language Translation**: Translate `.srt` files into multiple languages simultaneously.
- **Preserve Specific Terms**: Exclude names, brands, and other terms from translation.
- **Maintains Timing and Structure**: Ensures subtitles retain proper formatting.
- **Automatic Error Fixing**: Intelligently fixes common translation issues with placeholders.
- **Logging**: Provides detailed logs of translation processes and errors.
- **Customizable Settings**: Configure through environment variables.

---

## Two-Pass Translation System

The SRT Translator uses a **two-pass system** to ensure high-quality translations while reliably preserving important terms such as names, product names, and technical phrases. These DNT terms are temporarily replaced with special **placeholders** like `__DNT_TERM_0__` during translation, and then restored afterward.

### Pass 1: Real-Time Translation Fixes

During translation, the system automatically detects and fixes **missing placeholder** issues. If OpenAI omits a required placeholder in the output, the translator immediately adds it back to preserve the DNT term.

**Example:**
- **Original**: "We use the same infrastructure as __DNT_TERM_0__"
- **OpenAI returns**: "我们使用相同的基础设施" (placeholder is missing)
- **Immediate fix**: "__DNT_TERM_0__ 我们使用相同的基础设施" (placeholder restored)

### Pass 2: Batch Placeholder Fixing

Once all translations are complete, the fixer scans the output files for **position mismatch** issues—cases where the placeholder is present but awkwardly placed. These are corrected in bulk using a configurable "aggressiveness" setting.

**Example:**
- **Original**: "Amazon's retail business model"
- **Translation**: "小売業__DNT_TERM_0__のビジネスモデル" (placeholder placement sounds unnatural)
- **Batch fix**: "Amazonの小売業ビジネスモデル" (term is placed more naturally)

### Why Two Passes Are Necessary

- **Missing placeholders** must be fixed immediately to prevent loss of critical terms
- **Position mismatches** benefit from post-processing, which can be tuned for different languages
- **Language structure varies**, so what's natural in English may not be in Japanese, Arabic, etc.
- **Reviewable logs** ensure transparency and help you refine your translation settings over time

This two-pass approach ensures that key terms like company names, technical jargon, and proper nouns are always preserved—while still producing natural-sounding, professional translations in every supported language.


## Supported Languages

The SRT Translator supports **78 languages** through a unified language configuration system. You **must** specify which languages to translate to using the `TARGET_LANGUAGES` setting in your `.env` file.

**This is required to prevent accidentally translating to all 78 languages, which would be expensive.**

### Popular Languages (12)
- Spanish (ES), French (FR), German (DE), Italian (IT)
- Portuguese (Brazil) (PT-BR), Chinese Simplified (ZH-HANS)
- Japanese (JA), Korean (KO), Arabic (AR), Hindi (HI)
- Russian (RU), Dutch (NL)

### All Available Languages (78 total)
The system includes languages from Albanian to Zulu, covering major world languages and many regional variants.

### Language Management CLI

Use the built-in language manager to explore available languages:

```bash
# List all available languages
python run_language_manager.py list-all

# List popular languages only
python run_language_manager.py popular

# Search for specific languages
python run_language_manager.py search spanish

# Get information about a language
python run_language_manager.py info es

# Show language statistics
python run_language_manager.py stats


```

### Language Codes

The system uses standard ISO language codes:
- **Simple codes**: `es` (Spanish), `fr` (French), `de` (German)
- **Regional variants**: `pt-BR` (Portuguese Brazil), `zh-Hans` (Chinese Simplified)
- **Full support**: All 78 languages use proper ISO codes for maximum compatibility

---

## Project Structure
```
srt_translator/
├── scripts/                    # Utility scripts
│   ├── run_fixer_only.py      # Run placeholder fixer only
│   └── __init__.py
├── srt/                       # Main application package
│   ├── config/
│   │   ├── settings.py        # Configuration settings
│   │   └── __init__.py
│   ├── translator/
│   │   ├── fixer.py           # Fixes subtitle errors
│   │   ├── srt_parser.py      # Parses .srt files
│   │   ├── term_handler.py    # Handles translation terms
│   │   ├── translator.py      # Core translation logic
│   │   └── __init__.py
│   ├── utils/
│   │   ├── logging_setup.py   # Logging utilities
│   │   └── __init__.py
│   ├── main.py                # Entry point of the application
│   └── __init__.py
├── original_captions/         # Input directory (place .srt files here)
├── run.py                     # Main executable script
├── setup.py                   # Package setup configuration
├── .env.example              # Environment configuration template
├── .gitignore                # Git ignore rules
├── requirements.txt          # Python dependencies
└── README.md                 # Project documentation
```

---

## Prerequisites
- Python 3.7 or higher
- OpenAI API key
- Required Python packages (see requirements.txt)

---

## Installation

1. **Clone this repository:**
   ```bash
   git clone https://github.com/working-backwards/srt_translator.git
   cd srt_translator
   ```

2. **Create and activate a virtual environment (recommended):**
   ```bash
   python -m venv venv
   
   # On Windows:
   venv\Scripts\activate
   
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install required packages:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment configuration:**
   ```bash
   # Copy the example file
   cp .env.example .env
   
   # Edit .env and add your OpenAI API key
   ```

5. **Create input directory:**
   ```bash
   mkdir original_captions
   ```

## Configuration

### Environment Variables (.env file)

**Required:**
- `OPENAI_API_KEY`: Your OpenAI API key

**Required:**
- `TARGET_LANGUAGES`: Dictionary of target languages (must specify which languages to translate to)

**Optional (with defaults):**
- `DNT_TERMS`: Comma-separated list of terms to preserve
- `INPUT_DIRECTORY`: Input folder name (default: `original_captions`)
- `OUTPUT_DIRECTORY`: Output folder name (default: `translated_srt_files`)
- `LOGS_DIRECTORY`: Logs folder name (default: `translation_logs`)
- `SOURCE_LANG`: Source language code (default: `en`) - **Case-insensitive**
- `OPENAI_MODEL`: OpenAI model to use (default: `gpt-4o-mini`)
- `AGGRESSIVENESS`: Auto-fix aggressiveness 0-1 (default: `0.75`)

**Note:** Language codes are case-insensitive. You can enter `SOURCE_LANG=EN` or `SOURCE_LANG=en`, and `TARGET_LANGUAGES={"Spanish": "ES"}` or `TARGET_LANGUAGES={"Spanish": "es"}` - the system will normalize them to lowercase internally.

### Example .env Configuration

```bash
OPENAI_API_KEY=your_api_key_here
TARGET_LANGUAGES={"Spanish": "es", "French": "fr", "German": "de", "Japanese": "ja"}
DNT_TERMS=YourName,YourCompany,YourProduct,CEO,CFO
SOURCE_LANG=en
INPUT_DIRECTORY=original_captions
OUTPUT_DIRECTORY=translated_srt_files
AGGRESSIVENESS=0.75
```

### DNT Terms
Customize terms that should not be translated by editing the `DNT_TERMS` in your `.env` file:

**Examples of terms to exclude:**
- Instructor names: `YourName,CoInstructorName`
- Company names: `YourCompany,PartnerCompanies`
- Product names: `YourProduct,SoftwareNames`
- Technical terms: `API,SDK,specific methodologies`
- Industry acronyms: `CRM,ERP,KPI,ROI`
- Location names: `YourCity,HeadquartersLocation`


## Customizing the Translation Prompt

The SRT Translator uses OpenAI's GPT models with a carefully crafted prompt to ensure high-quality translations while preserving Do Not Translate (DNT) terms. You can customize this prompt if needed.

### When to Customize the Prompt

Consider customizing the prompt if you experience:
- **Inconsistent translation style** - You need more formal/informal tone
- **Domain-specific terminology issues** - Technical, medical, or legal content needs specialized handling
- **Cultural adaptation needs** - Certain phrases need localization beyond direct translation
- **Persistent placeholder issues** - The default anti-hallucination instructions aren't working for your content

### How to Customize the Prompt

1. **Modify the `TRANSLATION_PROMPT` in your `.env` file:**
   The prompt is already included in your `.env` file when you copy from `.env.example`. Simply edit it to meet your needs.

   ```bash
   TRANSLATION_PROMPT=Your custom prompt here with {source_lang} and {target_lang} variables
   ```

2. **Required template variables:**
   - `{source_lang}` - Will be replaced with source language (e.g., "en")
   - `{target_lang}` - Will be replaced with target language (e.g., "Spanish")

3. **Example customization for formal business content:**
   ```bash
   TRANSLATION_PROMPT=You are an expert business translator. Translate the following text from {source_lang} to {target_lang} using formal, professional language appropriate for corporate communications.

   CRITICAL REQUIREMENTS:
   - Maintain formal business tone throughout
   - Do NOT create any new placeholders like __DNT_TERM_X__
   - Preserve existing placeholders exactly as written
   - Use industry-standard terminology when available
   
   Translate professionally while preserving all formatting.
   ```

### Best Practices for Prompt Customization

- **Keep placeholder instructions** - Always include instructions about not creating new `__DNT_TERM_X__` placeholders
- **Test incrementally** - Try small changes first, then evaluate translation quality
- **Use specific language** - Vague instructions like "translate well" are less effective than specific requirements
- **Consider your content type** - Business documents need different handling than casual content
- **Validate with samples** - Test your custom prompt on a few subtitles before running full translations

### Troubleshooting Prompt Issues

If your custom prompt causes problems:

1. **Check template variables** - Ensure you included `{source_lang}` and `{target_lang}`
2. **Review logs** - Look for template error warnings in the translation logs
3. **Revert to default** - Comment out `TRANSLATION_PROMPT` in your `.env` to use the built-in prompt
4. **Test with simpler changes** - Start with minor modifications to the default prompt

The default prompt is designed to work well for most content types. Only customize if you have specific requirements that aren't being met.

---

## Usage

1. **Place your SRT files** in the `original_captions` directory (or your configured input directory).

2. **Run the translator:**
   ```bash
   python run.py
   ```

3. **Find translated files** in language-specific subdirectories under `translated_srt_files`:
   ```
   translated_srt_files/
   ├── ES/
   │   └── video1 - ES.srt
   ├── FR/
   │   └── video1 - FR.srt
   └── DE/
       └── video1 - DE.srt
   ```

4. **Check logs** in the `translation_logs` directory for any issues or fixes applied.


## Testing

The project includes a comprehensive test suite to ensure reliability and functionality.

### Running Tests

**All Tests:**
```bash
python run_tests.py
```

**GUI Tests Only:**
```bash
python run_tests.py gui
```

**Using pytest directly:**
```bash
# All tests
pytest tests/ -v

# GUI tests only  
pytest tests/gui/ -v

# Specific test file
pytest tests/test_ai_config_integration.py -v
```

### Test Structure

```
tests/
├── conftest.py                 # Pytest configuration and fixtures
├── test_ai_config_basic.py     # Basic AI configuration tests
├── test_ai_config_integration.py # Integration tests for AI config system
└── gui/                        # GUI component tests
    ├── test_business_glossary_editor.py
    ├── test_editors_integration.py
    └── test_dnt_terms_editor.py
```

### Test Types

- **Unit Tests**: Test individual components and functions
- **Integration Tests**: Test how components work together
- **GUI Tests**: Test user interface components (standalone applications)

For more details, see `tests/README.md`.


## Automatic Error Fixing

The translator includes intelligent error fixing with configurable aggressiveness:

- **0.0**: No automatic fixes (manual intervention required)
- **0.5**: Fix missing placeholders only
- **0.75**: Fix missing placeholders + simple reordering (recommended)
- **1.0**: Aggressive fixes including context mismatches (may risk translation integrity)


## Error Handling
- Creates backups before making any modifications
- Logs all translation events and errors
- Handles API errors gracefully with retry logic
- Automatically fixes common placeholder issues


## Troubleshooting

**Common Issues:**
- **"Source directory does not exist"**: Create the input directory (`mkdir original_captions`)
- **"OpenAI API key not found"**: Check your `.env` file has the correct API key
- **Translation quality issues**: Review and adjust `DNT_TERMS` for your content
- **Placeholder errors**: Adjust `AGGRESSIVENESS` setting (try 0.5 for more conservative fixes)


## FAQ

**Q: Do I need to edit my srt files before running this?**\
A: No. Just place them in `original_captions/` as-is.

**Q: Can I translate to more than one language at a time?**\
A: Yes! You can translate to multiple languages by specifying them in the `TARGET_LANGUAGES` setting in your `.env` file. You must specify which languages you want to translate to.

**Q: What if my subtitles break or translate the wrong terms?**\
A: Check the logs. The fixer will attempt auto-corrections, but logs will report issues.

**Q: Can I use this on Windows? macOS?**\
A: Yes. The tool is cross-platform.

**Q: How much will this cost?**\
A: You pay OpenAI per token. This script is efficient and uses GPT only for translation.


## Utility Scripts

The project includes several utility scripts in the `scripts/` directory for maintenance and troubleshooting:

### Fix Placeholders Only (`scripts/run_fixer_only.py`)

Run only the placeholder fixer without re-translating files. Useful when you need to fix remaining `__DNT_TERM_X__` placeholders after translation is complete.

```bash
python scripts/run_fixer_only.py
```

**When to use:**
- After translations are complete but some placeholders remain unfixed
- When you've updated your DNT terms and want to apply fixes
- To avoid re-running hours of translation just to fix placeholders

### Debug Log Parser (`scripts/debug_log_parser.py`)

Analyze translation log files to understand what issues occurred during translation and why the fixer might not be working.

```bash
python scripts/debug_log_parser.py
```

**Output includes:**
- Total number of logged issues
- Breakdown of issue types (missing placeholders vs. position mismatches)
- Sample log entries for debugging
- Issue counts by language

**When to use:**
- When the fixer reports "0 issues found" but you expect issues
- To understand what types of problems occurred during translation
- For troubleshooting log file parsing problems

### Running Utilities

All utility scripts automatically:
- Find the most recent log file in your `translation_logs` directory
- Use your current configuration from `.env`
- Provide detailed output for debugging

**Note:** These scripts require that you've run at least one full translation to generate log files.

---

## Contributing
Contributions are welcome! Please feel free to submit a pull request or open an issue.


## License
This project is licensed under the [MIT License](LICENSE).


## Notes
- API costs vary based on the length and number of subtitles
- Translation quality should be reviewed for critical content
- The application creates all necessary directories automatically


## Support
For issues and feature requests, please use the GitHub issues page.
