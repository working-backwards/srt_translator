from dotenv import load_dotenv
import os
import json

# Load environment variables for CLI mode BEFORE importing any modules
load_dotenv()

# Set default environment variables if not already set (for CLI mode)
if "TARGET_LANGUAGES" not in os.environ:
    # Default target languages for CLI mode
    default_languages = {
        "Spanish": "es",
        "French": "fr",
        "German": "de",
        "Chinese (Simplified)": "zh-Hans",
    }
    os.environ["TARGET_LANGUAGES"] = json.dumps(default_languages)
    print(f"Using default TARGET_LANGUAGES: {os.environ['TARGET_LANGUAGES']}")


if "OPENAI_MODEL" not in os.environ:
    os.environ["OPENAI_MODEL"] = "gpt-4o-mini"

if "BATCH_SIZE" not in os.environ:
    os.environ["BATCH_SIZE"] = "5"

if "AGGRESSIVENESS" not in os.environ:
    os.environ["AGGRESSIVENESS"] = "0.75"

if "LOG_MODE" not in os.environ:
    os.environ["LOG_MODE"] = "Standard"

if "OUTPUT_DIRECTORY" not in os.environ:
    os.environ["OUTPUT_DIRECTORY"] = "translated_srt_files"

if "LOGS_DIRECTORY" not in os.environ:
    os.environ["LOGS_DIRECTORY"] = "translation_logs"

from srt_core import main

if __name__ == "__main__":
    main.translate_srt_files()
