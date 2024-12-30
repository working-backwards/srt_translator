import os

# Dynamically calculate BASE_DIR based on the project's root
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# Path to the source directory containing .srt files
SOURCE_DIR = os.path.join(BASE_DIR, 'original_captions')

# Path to the output directory for translated .srt files
OUTPUT_BASE_DIR = os.path.join(BASE_DIR, 'Translated_SRT_Files')

LOG_DIRECTORY = os.path.join(BASE_DIR, 'translation_logs')

print(f"BASE_DIR: {os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))}")
print(f"SOURCE_DIR: {SOURCE_DIR}")

# General settings
SOURCE_LANG = 'EN'  # Default source language
LOG_MODE = 'Standard'  # Can be 'Standard' or 'Verbose'
OPENAI_MODEL = 'gpt-3.5-turbo'  # OpenAI model to use for translations

# Aggressiveness of automatic placeholder fixes (0 to 1 scale)
# - 0.0: No automatic fixes, all issues require manual intervention
# - 0.5: Fix missing placeholders
# - 0.75: Fix simple phrase order changes (e.g., placeholder reordering)
# - 1.0: Aggressively fix context mismatches (may risk translation integrity)
FIX_AGGRESSIVENESS = 0.75  # Default level: conservative fixes

# Dictionary of target languages with their ISO codes
TARGET_LANGUAGES = {
    'Spanish': 'ES',
    # Uncomment additional languages as needed:
    # 'French': 'FR',
    # 'German': 'DE',
    # 'Italian': 'IT',
    # 'Azerbaijani': 'AZ',
    # 'Turkish': 'TR',
    # 'Portuguese - Brazilian': 'PT-BR',
    # 'Portuguese - European': 'PT-EU',
    # 'Chinese (Simplified)': 'ZH-HANS',
    # 'Chinese (Traditional)': 'ZH-HANT',
    # 'Arabic': 'AR',
    'Japanese': 'JA',
}

# Excluded terms that will not be translated
EXCLUDED_TERMS = [
    "Colin",
    "Bill",
    "Colin Bryar",
    "Bill Carr",
    "Jeff",
    "Jeff Bezos",
    "Amazon",
    "LinkedIn",
]

# Language mapping for special variants
LANGUAGE_MAP = {
    'Portuguese - Brazilian': 'Brazilian Portuguese',
    'Portuguese - European': 'European Portuguese',
    'Chinese (Simplified)': 'Simplified Chinese',
    'Chinese (Traditional)': 'Traditional Chinese',
}
