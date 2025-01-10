# SRT Translator

## Overview
The **SRT Translator** is a Python-based application that uses OpenAI's GPT API to translate `.srt` subtitle files while preserving specific terms that should not be translated. It offers multi-language support and ensures subtitle timing, numbering, and formatting are maintained.

---

## Features
- **Multi-language Translation**: Translate `.srt` files into multiple languages simultaneously.
- **Preserve Specific Terms**: Exclude names, brands, and other terms from translation.
- **Maintains Timing and Structure**: Ensures subtitles retain proper formatting.
- **Logging**: Provides detailed logs of translation processes and errors.
- **Backups**: Automatically creates backups before modifying files.
- **Customizable Logging Modes**: Switch between standard and verbose logging.

---

## Supported Languages
Currently supports translation to:
- Spanish (ES)
- French (FR)
- German (DE)
- Italian (IT)
- Azerbaijani (AZ)
- Turkish (TR)
- Portuguese (Brazilian) (PT-BR)
- Portuguese (European) (PT-EU)
- Chinese (Simplified) (ZH-HANS)
- Chinese (Traditional) (ZH-HANT)
- Arabic (AR)
- Japanese (JA)

---

## Project Structure
```
srt/
├── config/
│   │── settings.py         # Configuration settings
│   └── __init__.py
├── translator/
│   ├── fixer.py            # Fixes subtitle errors
│   ├── srt_parser.py       # Parses .srt files
│   ├── term_handler.py     # Handles translation terms
│   ├── translator.py       # Core translation logic
│   └── __init__.py
├── utils/
│   ├── logging_setup.py    # Logging utilities
│   └── __init__.py
├── main.py                 # Entry point of the application
└── __init__.py
```

---

## Prerequisites
- Python 3.7 or higher
- OpenAI API key
- Required Python packages:
  ```
  python-dotenv
  openai
  ```

---

## Installation
1. Clone this repository:
   ```bash
   git clone [repository-url]
   cd srt-translator
   ```

2. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project root directory:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```

---

## Environment Variables

### Required
1. OPENAI_API_KEY: OpenAI API key.
2. SOURCE_DIR: Source directory where the input srt files are located.
3. TARGET_LANGUAGES: A dictionary of target languages. 

### Optional
1. OUTPUT_BASE_DIR: The location where the application should save the translated srt files, defaults to `Translated_SRT_Files` directory in the project directory.
2. LOG_DIRECTORY: The location where the translation logs files should be saved, defaults to `translation_logs` directory in the project directory.
3. EXCLUDED_TERMS: Terms that you want to exclude from translation.
4. SOURCE_LANG: Source language, defaults to EN
5. LOG_MODE: Can be 'Standard' or 'Verbose', defaults to standard
6. AGGRESSIVENESS: Aggressiveness of automatic placeholder fixes (0 to 1 scale), defaults to 0.75 

---

## Usage
1. Place your original SRT files in the `Original_Captions` directory.

2. Run the application:
   ```bash
   python run.py
   ```

3. Translated files will be saved in language-specific subdirectories under `Translated_SRT_Files`:
   - `video1 - ES.srt` in the `ES` directory
   - `video1 - FR.srt` in the `FR` directory
   etc.

---

## Configuration
### Excluded Terms
Modify the list of terms that should not be translated by editing the `EXCLUDED_TERMS` list in the relevant script:

```python
EXCLUDED_TERMS = [
    "Colin",
    "Bill",
    "Jeff Bezos",
    "Amazon",
    "LinkedIn"
]
```

### Logging Modes
Switch between logging modes by updating `LOG_MODE`:
```python
LOG_MODE = 'Standard'  # or 'Verbose'
- `Standard` (default): Logs important translation events and errors
- `Verbose`: Logs all events including HTTP requests and responses
```

---

## Error Handling
- Backups are created for original files before modifications.
- Translation errors are logged for review.
- Handles API errors gracefully.

---

## Contributing
Contributions are welcome! Feel free to submit a pull request.

---

## License
This project is licensed under the [MIT License](LICENSE).

---

## Notes
- API costs vary based on the length and number of subtitles.
- Translation quality should be reviewed for critical content.

---

## Support
For issues and feature requests, please use the GitHub issues page.
