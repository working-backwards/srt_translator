#!/usr/bin/env python3
"""
CLI Entry Point for SRT Translator
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

# Evaluation imports (config-gated)
from srt_translator.eval.runner import run_batch_evaluation
from srt_translator.eval.report import write_batch_report


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
        from srt_translator.api import TranslationConfiguration, Translator
        from srt_translator.cli.config_loader import collect_cli_raw

        raw_config = collect_cli_raw()
        api_cfg = TranslationConfiguration(
            files=None,  # set after enumeration
            output_dir=Path(raw_config.get("output_directory", "translated_srt_files")),
            target_languages=raw_config.get("target_languages"),
            dnt_terms=raw_config.get("dnt_terms"),
            termbase=raw_config.get("termbase") or {},
            openai_model=raw_config.get("openai_model", "gpt-4o-mini"),
            batch_size=int(raw_config.get("batch_size", 5)),
            aggressiveness=float(raw_config.get("aggressiveness", 0.75)),
            log_mode=raw_config.get("log_mode", "Standard"),
            api_key=raw_config.get("api_key"),
            mode="CLI",
        )

        logger.info("Configuration loaded successfully")
        logger.debug(f"API key source: {raw_config.get('api_key_source', 'unknown')}")

        # Debug logging for termbase and DNT terms
        if args.debug:
            logger.debug(f"DNT terms count: {len(api_cfg.dnt_terms)}")
            logger.debug(f"Termbase languages count: {len(api_cfg.termbase)}")
            if api_cfg.termbase:
                logger.debug(f"Termbase languages: {list(api_cfg.termbase.keys())}")
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
        input_dir = raw_config.get("input_directory", "original_captions")
        if not os.path.exists(input_dir):
            logger.error(f"INPUT_DIRECTORY not found: {input_dir}")
            return 1
        files = [
            Path(input_dir) / f
            for f in sorted(os.listdir(input_dir))
            if f.endswith(".srt")
        ]
        if not files:
            logger.info(f"No .srt files found in {input_dir}")
            return 0
        logger.info(f"Found {len(files)} .srt files to translate")
        cfg_with_files = api_cfg.__class__(**{**api_cfg.__dict__, "files": files})
        # Run translation and get results including batch directory
        results = Translator(cfg_with_files).run()
        logger.info("Translation completed successfully")

        # Post-translation evaluation (config-gated)
        try:
            eval_logger = logger.getChild("eval")

            # Prefer an explicit batch root if your translation returns it
            batch_root = results.get(
                "batch_directory"
            )  # <— add this in your pipeline if possible
            if batch_root:
                latest_batch = Path(batch_root)
            else:
                # Fallback: derive from the known output_directory
                out_dir = results.get("output_directory")
                if not out_dir:
                    logger.warning("No output directory found for evaluation")
                    latest_batch = None
                else:
                    parent = Path(out_dir)
                    candidates = [
                        d
                        for d in parent.iterdir()
                        if d.is_dir() and d.name.startswith("translation-batch-")
                    ]
                    # Choose by modification time to avoid lexicographic surprises
                    latest_batch = (
                        max(candidates, key=lambda d: d.stat().st_mtime)
                        if candidates
                        else None
                    )

            if latest_batch and latest_batch.exists():
                logger.info("Running evaluation", extra={"batch": latest_batch.name})
                rollup = run_batch_evaluation(
                    batch_root=latest_batch, logger=eval_logger
                )

                if rollup:
                    write_batch_report(
                        batch_root=latest_batch,
                        rollup=rollup,
                        logger=eval_logger,
                    )
                    logger.info("Evaluation completed successfully")
                else:
                    logger.info("Evaluation skipped (no rubric found)")
            else:
                logger.warning("No batch directory found for evaluation")

        except Exception as e:
            logger.error("Evaluation failed", extra={"error": str(e)}, exc_info=True)
            # Don't fail the translation - evaluation is optional

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
