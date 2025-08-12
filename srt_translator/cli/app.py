#!/usr/bin/env python3
"""
CLI Entry Point for SRT Translator
"""

from __future__ import annotations

import argparse
import logging
import os
import sys


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="SRT Translator CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  srt-cli                 # Run with default settings
  srt-cli --debug         # Enable debug logging
  srt-cli --version       # Show version information
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
            return 0
        except ImportError:
            print("SRT Translator CLI (version unknown)")
            return 0

    # Set up logging
    setup_logging(args.debug)
    logger = logging.getLogger(__name__)

    if args.debug:
        logger.debug("Debug mode enabled - detailed logging will be shown")

    # Collect raw configuration and build TranslationConfig
    try:
        from srt_translator.cli.config_loader import collect_cli_raw
        from srt_translator.core.config.models import TranslationConfig

        raw_config = collect_cli_raw()
        config = TranslationConfig.from_raw(raw_config, mode="CLI")

        logger.info("Configuration loaded successfully")
        logger.debug(f"API key source: {raw_config.get('api_key_source', 'unknown')}")

        # Debug logging for termbase and DNT terms
        if args.debug:
            logger.debug(f"DNT terms count: {len(config.dnt_terms)}")
            logger.debug(f"Termbase languages count: {len(config.termbase)}")
            if config.termbase:
                logger.debug(f"Termbase languages: {list(config.termbase.keys())}")
            else:
                logger.warning(
                    "No termbase loaded - check if termbase.json exists and is accessible"
                )

    except ImportError as e:
        logger.error(f"Import error: {e}")
        logger.error("Make sure you have installed the package: pip install -e .")
        return 1
    except Exception as e:
        logger.error(f"Configuration error: {e}")
        return 2

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
                logger.info(f"Found {len(file_paths)} .srt files to translate")
                translate_srt_files(file_paths=file_paths, config=config)
                logger.info("Translation completed successfully")
            else:
                logger.info(f"No .srt files found in {source_dir}")
        else:
            logger.error(f"Source directory {source_dir} does not exist")
            return 1

    except ImportError as e:
        logger.error(f"Import error: {e}")
        logger.error("Make sure you have installed the package: pip install -e .")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
