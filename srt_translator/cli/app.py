#!/usr/bin/env python3
"""
CLI Entry Point for SRT Translator
"""

from __future__ import annotations
import os
import json
import argparse
import logging
from dotenv import load_dotenv, find_dotenv


def setup_logging(debug: bool = False) -> None:
    """Set up logging configuration for CLI."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
        ],
    )


def bootstrap_env() -> None:
    """Bootstrap environment variables from .env file."""
    # Preserve old behavior: let .env override OUTPUT_DIRECTORY if one is set in the OS env
    if "OUTPUT_DIRECTORY" in os.environ:
        current_output_dir = os.environ["OUTPUT_DIRECTORY"]
        del os.environ["OUTPUT_DIRECTORY"]
        logger = logging.getLogger(__name__)
        logger.info(
            f"Clearing system OUTPUT_DIRECTORY '{current_output_dir}' to use .env file value"
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
        logger = logging.getLogger(__name__)
        logger.info(f"Using default TARGET_LANGUAGES: {os.environ['TARGET_LANGUAGES']}")

    os.environ.setdefault("OPENAI_MODEL", "gpt-4o-mini")
    os.environ.setdefault("BATCH_SIZE", "5")
    os.environ.setdefault("AGGRESSIVENESS", "0.75")
    os.environ.setdefault("LOG_MODE", "Standard")
    os.environ.setdefault("OUTPUT_DIRECTORY", "translated_srt_files")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="SRT Translator CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  srt-translator                 # Run with default settings
  srt-translator --debug         # Enable debug logging
  srt-translator --version       # Show version information
        """,
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument(
        "--version", action="store_true", help="Show version information"
    )
    args = parser.parse_args(argv)

    # Handle version flag first
    if args.version:
        try:
            from srt_translator import __version__

            print(f"SRT Translator CLI v{__version__}")
            return
        except ImportError:
            print("SRT Translator CLI (version unknown)")
            return

    # Set up logging
    setup_logging(args.debug)
    logger = logging.getLogger(__name__)

    bootstrap_env()

    if args.debug:
        os.environ["DEBUG_MODE"] = "true"
        logger.debug("Debug mode enabled - detailed logging will be shown")

    # Build configuration from CLI environment variables
    try:
        from srt_translator.core.config.translation_config import build_config_from_cli

        config = build_config_from_cli()
    except ImportError as e:
        logger.error(f"Import error: {e}")
        logger.error("Make sure you have installed the package: pip install -e .")
        raise SystemExit(1)

    # Check if API key is available
    if not config.api_key:
        logger.error("OPENAI_API_KEY environment variable is not set")
        logger.error("Please set your OpenAI API key in the .env file or environment")
        raise SystemExit(1)

    # Call main function with the configuration
    try:
        from srt_translator.core.main import translate_srt_files

        # For CLI mode, use the default source directory if no specific files provided
        source_dir = "original_captions"  # Default source directory
        if os.path.exists(source_dir):
            file_paths = [
                os.path.join(source_dir, f)
                for f in os.listdir(source_dir)
                if f.endswith(".srt")
            ]
            if file_paths:
                translate_srt_files(file_paths=file_paths, config=config)
            else:
                logger.info(f"No .srt files found in {source_dir}")
        else:
            logger.error(f"Source directory {source_dir} does not exist")
            raise SystemExit(1)
    except ImportError as e:
        logger.error(f"Import error: {e}")
        logger.error("Make sure you have installed the package: pip install -e .")
        raise SystemExit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
