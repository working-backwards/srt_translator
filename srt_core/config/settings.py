import json
import os
import sys

from .language_config import language_config

# Dynamically calculate BASE_DIR based on the project's root
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Path to the source directory containing .srt files
SOURCE_DIR = (
    os.environ["INPUT_DIRECTORY"]
    if "INPUT_DIRECTORY" in os.environ
    else os.path.join(BASE_DIR, "original_captions")
)

# Path to the output directory for translated .srt files
OUTPUT_BASE_DIR = (
    os.environ["OUTPUT_DIRECTORY"]
    if "OUTPUT_DIRECTORY" in os.environ
    else os.path.join(BASE_DIR, "translated_srt_files")
)

LOG_DIRECTORY = (
    os.environ["LOGS_DIRECTORY"]
    if "LOGS_DIRECTORY" in os.environ
    else os.path.join(BASE_DIR, "translation_logs")
)

print(f"BASE_DIR: {os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))}")
print(f"SOURCE_DIR: {SOURCE_DIR}")

# General settings
SOURCE_LANG = (
    os.environ["SOURCE_LANG"].lower() if "SOURCE_LANG" in os.environ else "en"
)  # Default source language (normalized to lowercase)
LOG_MODE = (
    os.environ["LOG_MODE"] if "LOG_MODE" in os.environ else "Standard"
)  # Can be 'Standard' or 'Verbose'
OPENAI_MODEL = (
    os.environ["OPENAI_MODEL"] if "OPENAI_MODEL" in os.environ else "gpt-4o-mini"
)  # OpenAI model to use for translations

# Aggressiveness of automatic placeholder fixes (0 to 1 scale)
# - 0.0: No automatic fixes, all issues require manual intervention
# - 0.5: Fix missing placeholders
# - 0.75: Fix simple phrase order changes (e.g., placeholder reordering)
# - 1.0: Aggressively fix context mismatches (may risk translation integrity)
FIX_AGGRESSIVENESS = float(
    os.environ.get("AGGRESSIVENESS", "0.75")
)  # Default level: conservative fixes

# Dictionary of target languages with their ISO codes
# TARGET_LANGUAGES must be explicitly configured in environment variables
if "TARGET_LANGUAGES" not in os.environ:
    raise ValueError(
        "TARGET_LANGUAGES must be configured in your environment variables. "
        "This setting is required to specify which languages to translate to. "
        "See env_example_language_configs.txt for configuration examples."
    )

TARGET_LANGUAGES_TEXT = os.environ["TARGET_LANGUAGES"]
try:
    TARGET_LANGUAGES = json.loads(TARGET_LANGUAGES_TEXT)
    if not TARGET_LANGUAGES:
        raise ValueError(
            "TARGET_LANGUAGES cannot be empty. Please specify at least one language."
        )

    # Normalize all language codes to lowercase for consistency
    normalized_target_languages = {}
    for lang_name, lang_code in TARGET_LANGUAGES.items():
        normalized_target_languages[lang_name] = lang_code.lower()

    TARGET_LANGUAGES = normalized_target_languages
    print(
        f"Using TARGET_LANGUAGES from environment with {len(TARGET_LANGUAGES)} languages (normalized to lowercase)"
    )
except json.JSONDecodeError as e:
    raise ValueError(f"Invalid TARGET_LANGUAGES format in environment: {e}")

# DNT terms that will not be translated
DNT_TERMS_TEXT = os.environ["DNT_TERMS"] if "DNT_TERMS" in os.environ else ""
DNT_TERMS = DNT_TERMS_TEXT.split(",")

# Language configuration is now handled by the unified system in config/languages.json

# Termbase Support
TERMBASE_PATH = os.path.join(BASE_DIR, "termbase.json")
TERMBASE = {}


def load_termbase():
    """Load termbase from JSON file if it exists"""
    global TERMBASE
    if os.path.exists(TERMBASE_PATH):
        try:
            with open(TERMBASE_PATH, "r", encoding="utf-8") as f:
                TERMBASE = json.load(f)
            print(f"Loaded termbase with {len(TERMBASE)} languages")
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Warning: Could not load termbase: {e}")
            TERMBASE = {}
    else:
        print("No termbase found - using default translations")


# Load termbase on import
load_termbase()


def get_termbase_terms(target_lang):
    """Get termbase terms for a specific language"""
    return TERMBASE.get(target_lang, {})


BATCH_SIZE = int(
    os.environ.get("BATCH_SIZE", 5)
)  # Number of subtitles per translation batch
