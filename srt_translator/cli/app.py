#!/usr/bin/env python3
"""
CLI Entry Point for SRT Translator
"""

from __future__ import annotations
import os
import json
import argparse
from dotenv import load_dotenv, find_dotenv


def bootstrap_env() -> None:
    # Preserve old behavior: let .env override OUTPUT_DIRECTORY if one is set in the OS env
    if "OUTPUT_DIRECTORY" in os.environ:
        current_output_dir = os.environ["OUTPUT_DIRECTORY"]
        del os.environ["OUTPUT_DIRECTORY"]
        print(
            f"Note: Clearing system OUTPUT_DIRECTORY '{current_output_dir}' to use .env file value"
        )

    # Load the nearest .env starting from the current working dir
    load_dotenv(find_dotenv(usecwd=True), override=False)  # don't clobber OS env

    # Defaults (only if not already set)
    if "TARGET_LANGUAGES" not in os.environ:
        default_languages = {
            "Spanish": "es",
            "French": "fr",
            "German": "de",
            "Chinese (Simplified)": "zh-Hans",
        }
        os.environ["TARGET_LANGUAGES"] = json.dumps(default_languages)
        print(f"Using default TARGET_LANGUAGES: {os.environ['TARGET_LANGUAGES']}")

    os.environ.setdefault("OPENAI_MODEL", "gpt-4o-mini")
    os.environ.setdefault("BATCH_SIZE", "5")
    os.environ.setdefault("AGGRESSIVENESS", "0.75")
    os.environ.setdefault("LOG_MODE", "Standard")
    os.environ.setdefault("OUTPUT_DIRECTORY", "translated_srt_files")


def main(argv: list[str] | None = None) -> None:
    bootstrap_env()

    parser = argparse.ArgumentParser(
        description="SRT Translator CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  srt-translator                 # Run with default settings
  srt-translator --debug         # Enable debug logging
        """,
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args(argv)

    if args.debug:
        os.environ["DEBUG_MODE"] = "true"
        print("🔍 Debug mode enabled - detailed logging will be shown")

    # Build configuration from CLI environment variables
    try:
        from srt_translator.core.config.translation_config import build_config_from_cli

        config = build_config_from_cli()
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure you have installed the package: pip install -e .")
        raise SystemExit(1)

    # Check if API key is available
    if not config.api_key:
        print("❌ Error: OPENAI_API_KEY environment variable is not set")
        print("Please set your OpenAI API key in the .env file or environment")
        raise SystemExit(1)

    # Call main function with the configuration
    try:
        from srt_translator.core.main import translate_srt_files

        translate_srt_files(config=config)
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure you have installed the package: pip install -e .")
        raise SystemExit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
