import argparse
import json
import logging
import os

from dotenv import load_dotenv

# Set up logging - ALWAYS include this
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Get logger for this module
logger = logging.getLogger(__name__)

# For older python-dotenv versions, manually clear OUTPUT_DIRECTORY
# to ensure .env file values take precedence over system environment variables
if "OUTPUT_DIRECTORY" in os.environ:
    # Store the current value to show what we're overriding
    current_output_dir = os.environ["OUTPUT_DIRECTORY"]
    # Clear it so .env file can set it
    del os.environ["OUTPUT_DIRECTORY"]
    logger.info(
        f"Note: Clearing system OUTPUT_DIRECTORY '{current_output_dir}' to use .env file value"
    )

# Load environment variables for CLI mode BEFORE importing any modules
load_dotenv()

# Set default environment variables if not already set (for CLI mode)
# Note: .env file values take precedence over system environment variables
if "TARGET_LANGUAGES" not in os.environ:
    # Default target languages for CLI mode
    default_languages = {
        "Spanish": "es",
        "French": "fr",
        "German": "de",
        "Chinese (Simplified)": "zh-Hans",
    }
    os.environ["TARGET_LANGUAGES"] = json.dumps(default_languages)
    logger.info(f"Using default TARGET_LANGUAGES: {os.environ['TARGET_LANGUAGES']}")

if "OPENAI_MODEL" not in os.environ:
    os.environ["OPENAI_MODEL"] = "gpt-4o-mini"

if "BATCH_SIZE" not in os.environ:
    os.environ["BATCH_SIZE"] = "5"

if "AGGRESSIVENESS" not in os.environ:
    os.environ["AGGRESSIVENESS"] = "0.75"

if "LOG_MODE" not in os.environ:
    os.environ["LOG_MODE"] = "Standard"

# OUTPUT_DIRECTORY: .env file takes precedence, then default
if "OUTPUT_DIRECTORY" not in os.environ:
    os.environ["OUTPUT_DIRECTORY"] = "translated_srt_files"

from srt_translator.core import main
from srt_translator.core.config.translation_config import build_config_from_cli

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="SRT Translator CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_cli.py                    # Run with default settings
  python run_cli.py --debug            # Run with debug logging enabled
        """,
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    # Set debug logging if requested
    if args.debug:
        os.environ["DEBUG_MODE"] = "true"
        logger.info("🔍 Debug mode enabled - detailed logging will be shown")

    # Build configuration from CLI environment variables
    config = build_config_from_cli()

    # Check if API key is available
    if not config.api_key:
        logger.error("❌ Error: OPENAI_API_KEY environment variable is not set")
        logger.error("Please set your OpenAI API key in the .env file or environment")
        exit(1)

    # Call main function with the configuration
    main.translate_srt_files(config=config)
