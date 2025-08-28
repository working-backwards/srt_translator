#!/usr/bin/env python3
"""
Main module for SRT Translator.
Provides the core translation functionality for both CLI and GUI interfaces.
"""

import json
import logging
import os
from datetime import datetime
from typing import List, TypedDict
from dataclasses import replace

from srt_translator import __version__
from srt_translator.core.config.models import TranslationConfig
from srt_translator.core.config.language_config import LanguageConfig
from srt_translator.core.translator.fixer import SRTFixer
from srt_translator.core.translator.translator import SRTTranslator
from srt_translator.core.utils.logging_setup import setup_logging

# Do not configure logging at import time. The caller (GUI worker or CLI entrypoint)
# is responsible for initializing logging via setup_logging().


class SummaryDict(TypedDict):
    total_files: int
    unique_languages: int
    total_operations: int
    successes: int
    skipped: int
    errors: int
    error_details: List[str]


def translate_srt_files(
    file_paths: List[str],
    config: TranslationConfig,
    *,
    logger: logging.Logger = None,
) -> SummaryDict:
    """
    Translate SRT files to multiple target languages.

    Args:
        file_paths: List of SRT file paths to translate
        config: Translation configuration object
        logger: Logger instance (optional)

    Returns:
        SummaryDict: Summary of translation results
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    # Create batch directory with timestamp inside the configured output directory
    timestamp = datetime.now()
    ts_str = timestamp.strftime("%Y%m%d_%H%M%S_%z")
    # Convert Path to string for os.path.join compatibility
    output_dir_str = str(config.output_directory)
    batch_dir = os.path.join(output_dir_str, f"translation-batch-{ts_str}")
    os.makedirs(batch_dir, exist_ok=True)

    # Set up logging
    log_file = os.path.join(batch_dir, f"translation_issues_{ts_str}.log")
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.info(f"Batch folder: {batch_dir}")
    logger.info(f"Log file: {log_file}")
    logger.info("Translating with per-language batch sizes from injected policies")

    # Stage 3: the core must not read languages.json directly.
    # Language policy is injected by GUI/CLI loaders via config.language_policies.
    if not config.language_policies:
        raise RuntimeError(
            "Missing language_policies in TranslationConfig. "
            "Entry points (GUI/CLI) must load languages.json and inject the policy."
        )
    language_config = LanguageConfig(config.language_policies)
    try:
        num_langs = len(language_config.codes())
    except AttributeError:
        # Backward compatibility if codes() is not present
        num_langs = len(getattr(language_config, "_langs", {}) or {})
    logger.info("Language policy injected (languages=%d)", num_langs)

    # === Same-language guard: drop targets that match detected source ===
    source_lang = getattr(config, "source_language", None)
    source_code = None
    try:
        if isinstance(source_lang, dict):
            source_code = (
                source_lang.get("normalized_code")
                or source_lang.get("detected_code")
                or ""
            ).strip()
    except Exception:
        source_code = None

    if source_code:
        # Compare case-insensitively against requested target codes
        keep = {
            name: code
            for name, code in config.target_languages.items()
            if (code or "").strip().lower() != source_code.lower()
        }
        if len(keep) != len(config.target_languages):
            logger.warning(
                f"Dropping target identical to detected source ({source_code}); "
                f"{len(config.target_languages) - len(keep)} target(s) removed."
            )
            config = replace(config, target_languages=keep)
    if isinstance(source_lang, dict) and source_lang.get("mixed"):
        logger.warning(
            "Detected mixed-language source; proceeding with dominant language."
        )

    # Process each target language
    successful_translations = 0
    total_operations = 0

    for lang_name, lang_code in config.target_languages.items():
        if not lang_code:
            logger.warning(f"Skipping language '{lang_name}' with empty code")
            continue

        total_operations += 1
        logger.info(
            f"translated by {total_operations} / {len(config.target_languages)} - {os.path.basename(file_paths[0])} → {lang_name}"
        )

        try:
            # Create translator instance with per-language batch size
            batch_size_for_lang = language_config.get_target_batch_size(lang_code)
            translator = SRTTranslator(
                dnt_terms=config.dnt_terms,
                termbase=config.termbase.get(lang_code, {}),
                api_key=config.api_key,
                allow_global_termbase_fallback=config.mode
                == "CLI",  # GUI: no fallback; CLI: allow
                model_name=config.model_name,
                batch_size=batch_size_for_lang,
                logger=logger,
                error_policy=config.error_policy,  # Pass error policy
                language_config=language_config,  # Pass language configuration
            )
            logger.info(
                "Language run: %s (%s) batch_size=%d cps_cap=%s apostrophe_allowed=%s",
                lang_name,
                lang_code,
                batch_size_for_lang,
                language_config.get_cps_cap(lang_code),
                language_config.allows_placeholder_apostrophe(lang_code),
            )

            # Translate files for this language
            for file_path in file_paths:
                # Create output filename with language suffix
                file_base, file_ext = os.path.splitext(os.path.basename(file_path))
                output_filename = f"{file_base} - {lang_code.upper()}{file_ext}"
                # Write files inside the batch directory structure
                output_filepath = os.path.join(batch_dir, lang_code, output_filename)

                # Ensure output directory exists
                os.makedirs(os.path.dirname(output_filepath), exist_ok=True)

                # Translate the file
                translator.translate_file(
                    input_filepath=file_path,
                    output_filepath=output_filepath,
                    target_lang=lang_code,
                )

            successful_translations += 1
            logger.info(f"Successfully translated to {lang_name}")

        except Exception as e:
            logger.error(f"Failed to translate to {lang_name}: {e}")
            continue

    # Write AI config manifest
    try:
        manifest_data = {
            "version": __version__,
            "timestamp": ts_str,
            "mode": config.mode,
            "source_files": [os.path.basename(f) for f in file_paths],
            "target_languages": list(config.target_languages.values()),
            "dnt_terms": config.dnt_terms,
            "termbase": config.termbase,
            "batch_size": config.batch_size,
            "aggressiveness": config.aggressiveness,
        }

        manifest_path = os.path.join(batch_dir, "ai_config.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, ensure_ascii=False, indent=2)
        logger.info("Wrote batch-level AI config: ai_config.json")
    except Exception as e:
        logger.warning(f"Failed to write AI config manifest: {e}")

    # Create artifacts directory
    artifacts_dir = os.path.join(batch_dir, "artifacts")
    os.makedirs(artifacts_dir, exist_ok=True)

    # Create originals directory and copy source files for evaluation
    originals_dir = os.path.join(batch_dir, "originals")
    os.makedirs(originals_dir, exist_ok=True)

    # Copy source files to originals directory for evaluation pairing
    for file_path in file_paths:
        try:
            import shutil

            source_filename = os.path.basename(file_path)
            dest_path = os.path.join(originals_dir, source_filename)
            shutil.copy2(file_path, dest_path)
            logger.info(f"Copied source file to originals: {source_filename}")
        except Exception as e:
            logger.warning(f"Failed to copy source file {file_path}: {e}")

    # Per-language artifacts are now handled by the evaluation system
    # The core translation focuses only on translation, not artifact creation

    # Batch-level artifacts are now handled by the evaluation system
    # The core translation focuses only on translation, not artifact creation

    # Print summary
    logger.info(" === Translation Summary ===")
    logger.info(f"Files processed: {len(file_paths)}")
    logger.info(f"Languages processed: {len(config.target_languages)}")
    logger.info(f"Total translation operations: {total_operations}")
    logger.info(f"Successful translations: {successful_translations}")
    logger.info(f"Failed translations: {total_operations - successful_translations}")
    logger.info("==========================")

    # Remove file handler to avoid duplicate logging
    logger.removeHandler(file_handler)

    # Run automatic fixes
    for lang_name, lang_code in config.target_languages.items():
        if not lang_code:
            continue

        logger.info(f"Running automatic fixes for {os.path.basename(file_paths[0])}...")
        try:
            from srt_translator.core.translator.fixer import SRTFixer

            fixer = SRTFixer(log_file, batch_dir)
            fixer.parse_log_file()
            fixer.fix_srt_files(aggressiveness=config.aggressiveness)
            fixer.report_status()
        except Exception as e:
            logger.error(f"Failed to run automatic fixes for {lang_code}: {e}")

    logger.info("Automatic SRT fixes completed.")

    # Evaluation artifacts are written per-language above

    # Run automatic fixes again after evaluation
    logger.info(f"Batch folder: {batch_dir}")
    logger.info(f"Artifacts directory: {os.path.relpath(artifacts_dir, batch_dir)}")

    for lang_name, lang_code in config.target_languages.items():
        if not lang_code:
            continue

        logger.info(f"Running automatic SRT fixer on translated files...")
        try:
            from srt_translator.core.translator.fixer import SRTFixer

            fixer = SRTFixer(log_file, batch_dir)
            fixer.parse_log_file()
            fixer.fix_srt_files(aggressiveness=config.aggressiveness)
            fixer.report_status()
        except Exception as e:
            logger.error(f"Failed to run automatic fixes for {lang_code}: {e}")

    logger.info("Automatic SRT fixes completed.")

    # Return summary of translation results with batch directory
    return {
        "total_files": len(file_paths),
        "unique_languages": len(config.target_languages),
        "total_operations": total_operations,
        "successes": successful_translations,
        "skipped": 0,
        "errors": total_operations - successful_translations,
        "error_details": [],
        "batch_directory": batch_dir,  # Include batch directory for evaluation
    }
