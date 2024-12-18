# config/settings.py

# Predefined configuration
SOURCE_LANG = 'EN'
SOURCE_DIR = 'Original_Captions'
OUTPUT_BASE_DIR = 'Translated_SRT_Files'
LOG_MODE = 'Standard'  # Can be 'Standard' or 'Verbose'
OPENAI_MODEL = 'gpt-3.5-turbo'  # OpenAI model to use for translations

# Dictionary of target languages with their ISO codes and variants
TARGET_LANGUAGES = {
    'Spanish': 'ES',
    'French': 'FR',
    'German': 'DE',
    'Italian': 'IT',
    'Azerbaijani': 'AZ',
    'Turkish': 'TR',
    'Portuguese - Brazilian': 'PT-BR',
    'Portuguese - European': 'PT-EU',
    'Chinese (Simplified)': 'ZH-HANS',
    'Chinese (Traditional)': 'ZH-HANT',
    'Arabic': 'AR',
    'Japanese': 'JA'
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
    "LinkedIn"
]

# Language mapping for special variants
LANGUAGE_MAP = {
    'Portuguese - Brazilian': 'Brazilian Portuguese',
    'Portuguese - European': 'European Portuguese',
    'Chinese (Simplified)': 'Simplified Chinese',
    'Chinese (Traditional)': 'Traditional Chinese'
}