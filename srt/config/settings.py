import json
import os

from dotenv import load_dotenv

load_dotenv()

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
    os.environ["SOURCE_LANG"] if "SOURCE_LANG" in os.environ else "EN"
)  # Default source language
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
TARGET_LANGUAGES_TEXT = (
    os.environ["TARGET_LANGUAGES"] if "TARGET_LANGUAGES" in os.environ else "{}"
)
TARGET_LANGUAGES = json.loads(TARGET_LANGUAGES_TEXT)

# Excluded terms that will not be translated
EXCLUDED_TERMS_TEXT = (
    os.environ["EXCLUDED_TERMS"] if "EXCLUDED_TERMS" in os.environ else ""
)
EXCLUDED_TERMS = EXCLUDED_TERMS_TEXT.split(",")

# Language mapping for special variants
LANGUAGE_MAP = {
    "Portuguese - Brazilian": "Brazilian Portuguese",
    "Portuguese - European": "European Portuguese",
    "Chinese Simplified": "Simplified Chinese",
    "Chinese Traditional": "Traditional Chinese",
}

# Business Glossary Support
BUSINESS_GLOSSARY_PATH = os.path.join(BASE_DIR, "business_glossary.json")
BUSINESS_GLOSSARY = {}


def load_business_glossary():
    """Load business glossary from JSON file if it exists"""
    global BUSINESS_GLOSSARY
    if os.path.exists(BUSINESS_GLOSSARY_PATH):
        try:
            with open(BUSINESS_GLOSSARY_PATH, "r", encoding="utf-8") as f:
                BUSINESS_GLOSSARY = json.load(f)
            print(f"Loaded business glossary with {len(BUSINESS_GLOSSARY)} languages")
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Warning: Could not load business glossary: {e}")
            BUSINESS_GLOSSARY = {}
    else:
        print("No business glossary found - using default translations")


# Load glossary on import
load_business_glossary()


def get_glossary_terms(target_lang):
    """Get glossary terms for a specific language"""
    return BUSINESS_GLOSSARY.get(target_lang, {})
