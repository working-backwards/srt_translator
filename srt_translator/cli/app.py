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

    # Always squelch noisy HTTP client logs for creator-facing runs
    for name in (
        "httpx",
        "httpcore",
        "httpcore.http11",
        "openai",
        "openai._base_client",
    ):
        logging.getLogger(name).setLevel(logging.WARNING)

    # Ensure that all loggers inherit the DEBUG level when debug mode is enabled
    if debug:
        # Set the root logger to DEBUG
        logging.getLogger().setLevel(logging.DEBUG)
        # Also set our main application logger to DEBUG to ensure child loggers inherit it
        logging.getLogger("srt_translator").setLevel(logging.DEBUG)

        # Optional: re-enable HTTP traces when debugging HTTP specifically
        if os.getenv("SRTX_HTTP_DEBUG") == "1":
            logging.getLogger("httpx").setLevel(logging.INFO)
            logging.getLogger("httpcore").setLevel(logging.INFO)


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
    parser.add_argument("--version", action="store_true", help="Show version information")
    parser.add_argument(
        "--report",
        choices=["html", "md", "both", "none"],
        default="none",
        help=(
            "Generate report after evaluation: html (HTML only), md (Markdown only), "
            "both (HTML then MD), none (no reports)"
        ),
    )
    parser.add_argument(
        "--tone",
        choices=["casual", "neutral", "formal"],
        default=None,
        help="Translation tone/register: casual, neutral (default), or formal",
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
        from srt_translator.api import Translator
        from srt_translator.cli.config_loader import collect_cli_raw
        from srt_translator.core.config.models import TranslationConfig

        raw_config = collect_cli_raw()

        # Override tone from CLI argument if provided (takes precedence over env)
        if args.tone:
            raw_config["tone"] = args.tone

        # Architecture note: Filter same-language targets at CLI boundary
        # before constructing TranslationConfig. The core engine receives
        # a clean, immutable config with filtered targets.
        target_languages = raw_config.get("target_languages") or {}
        source_language = raw_config.get("source_language")

        if source_language and isinstance(source_language, dict):
            source_code = (source_language.get("normalized_code") or source_language.get("detected_code") or "").strip()
            if source_code:
                # Filter out target languages matching the detected source
                filtered = {
                    name: code
                    for name, code in target_languages.items()
                    if (code or "").strip().lower() != source_code.lower()
                }
                if len(filtered) != len(target_languages):
                    logger.warning(
                        "Dropping target identical to detected source (%s); %s target(s) removed.",
                        source_code,
                        len(target_languages) - len(filtered),
                    )
                target_languages = filtered

        # Build normalized TranslationConfig using from_raw() to handle
        # defaults and convert to immutable containers (tuple, MappingProxyType)
        normalized_raw = dict(raw_config)
        normalized_raw["target_languages"] = target_languages
        api_cfg = TranslationConfig.from_raw(normalized_raw, mode="CLI")

        logger.info("Configuration loaded successfully")
        logger.debug("API key source: %s", raw_config.get("api_key_source", "unknown"))

        # Debug logging for termbase and DNT terms
        if args.debug:
            logger.debug("DNT terms count: %s", len(api_cfg.dnt_terms))
            logger.debug("Termbase languages count: %s", len(api_cfg.termbase))
            if api_cfg.termbase:
                logger.debug("Termbase languages: %s", list(api_cfg.termbase.keys()))
            else:
                logger.warning("No termbase loaded - check if termbase.json exists and is accessible")

    except ImportError as e:
        logger.error("Import error: %s", e)
        logger.error("Make sure you have installed the package: pip install -e .")
        return 1
    except Exception as e:
        logger.error("Configuration error: %s", e)
        return 2

    # Call main function with the configuration
    try:
        # input_dir = raw_config.get("input_directory", "original_captions")
        BASE_DIR = Path(__file__).resolve().parent.parent.parent  # project root
        input_dir = Path(raw_config.get("input_directory", "original_captions"))
        input_dir = BASE_DIR / input_dir
        if not os.path.exists(input_dir):
            logger.error("INPUT_DIRECTORY not found: %s", input_dir)
            return 1
        files = [Path(input_dir) / f for f in sorted(os.listdir(input_dir)) if f.endswith(".srt")]
        if not files:
            logger.info("No .srt files found in %s", input_dir)
            return 0
        logger.info("Found %s .srt files to translate", len(files))
        cfg_with_files = api_cfg.__class__(**{**api_cfg.__dict__, "files": files})
        # Run translation and get results including batch directory
        results = Translator(cfg_with_files).run()
        logger.info("Translation completed successfully")

        # Post-translation evaluation (config-gated)
        try:
            eval_logger = logger.getChild("eval")

            # Prefer an explicit batch root if your translation returns it
            batch_root = results.get("batch_directory")  # <— add this in your pipeline if possible
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
                    candidates = [d for d in parent.iterdir() if d.is_dir() and d.name.startswith("translation-batch-")]
                    # Choose by modification time to avoid lexicographic surprises
                    latest_batch = max(candidates, key=lambda d: d.stat().st_mtime) if candidates else None

            if latest_batch and latest_batch.exists():
                logger.info("Running evaluation", extra={"batch": latest_batch.name})
                rollup = run_batch_evaluation(batch_root=latest_batch, logger=eval_logger, language_config=api_cfg)

                if rollup:
                    artifacts_dir = latest_batch / "artifacts"
                    ai_config_path = artifacts_dir / "ai_config.json"

                    if not ai_config_path.exists():
                        raise FileNotFoundError(f"ai_config.json not found at: {ai_config_path}")

                    # Call the orchestrator
                    from srt_translator.eval.report import emit_all_reports

                    try:
                        paths = emit_all_reports(artifacts_dir, rollup)
                        logger.info("Generated all reports:")
                        for name, path in paths.items():
                            logger.info("  %s: %s", name, path.absolute())
                    except Exception as e:
                        logger.error("Failed to generate reports: %s", e)
                        return 1

                    logger.info("Evaluation completed successfully")

                else:
                    logger.info("Evaluation skipped (no rubric found)")
            else:
                logger.warning("No batch directory found for evaluation")

        except Exception as e:
            logger.exception("Evaluation failed", extra={"error": str(e)})
            # Don't fail the translation - evaluation is optional

    except ImportError as e:
        logger.error("Import error: %s", e)
        logger.error("Make sure you have installed the package: pip install -e .")
        return 1
    except Exception as e:
        logger.error("Unexpected error: %s", e)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
