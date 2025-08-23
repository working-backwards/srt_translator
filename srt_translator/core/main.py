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
    logger.info(f"Translating with batch size: {config.batch_size}")

    # Load language configuration for the core engine
    try:
        import json

        languages_path = "config/languages.json"
        with open(languages_path, "r", encoding="utf-8") as f:
            lang_data = json.load(f)
        language_config = LanguageConfig(lang_data)
        logger.info(
            "Loaded language configuration with %d languages",
            len(language_config.get_all_languages()),
        )
    except Exception as e:
        logger.error("Failed to load language configuration: %s", e)
        raise RuntimeError(f"Language configuration load failed: {e}")

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
            # Create translator instance
            translator = SRTTranslator(
                dnt_terms=config.dnt_terms,
                termbase=config.termbase.get(lang_code, {}),
                api_key=config.api_key,
                allow_global_termbase_fallback=config.mode
                == "CLI",  # GUI: no fallback; CLI: allow
                model_name=config.model_name,
                batch_size=config.batch_size,
                logger=logger.getChild("core.translator"),
                error_policy=config.error_policy,  # Pass error policy
                language_config=language_config,  # Pass language configuration
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

    # Write per-language artifacts and manifests
    for lang_name, lang_code in config.target_languages.items():
        if not lang_code:
            continue

        try:
            # Create language-specific artifacts directory
            lang_artifacts_dir = os.path.join(artifacts_dir, lang_code)
            os.makedirs(lang_artifacts_dir, exist_ok=True)

            # Generate summaries and manifests
            from srt_translator.core.utils.run_summaries import (
                create_dnt_summary,
                create_termbase_summary,
                create_manifest_summary,
                write_run_artifacts,
                get_filtering_rules,
                create_batch_manifest,
            )

            # Create summaries
            dnt_meta = create_dnt_summary(
                user_terms=config.dnt_terms or [],
                filtered_terms=config.dnt_terms or [],
                filtered_out=[],
                lang_code=lang_code,
                filtering_rules=get_filtering_rules(),
            )
            tb_meta = create_termbase_summary(
                user_termbase=config.termbase or {},
                filtered_termbase=config.termbase.get(lang_code, {}) or {},
                collisions_removed={},
                lang_code=lang_code,
                filtering_rules=get_filtering_rules(),
            )

            # Create processing summary
            processing_summary = {
                "batch_size": config.batch_size,
                "aggressiveness": config.aggressiveness,
                "model": config.model_name,
                "filtering_rules": get_filtering_rules(),
            }

            # Create summary for this language
            summary = {
                "total_files": len(file_paths),
                "unique_languages": 1,
                "total_operations": 1,
                "successes": 1,  # Each language translation is a separate operation
                "skipped": 0,
                "errors": 0,
                "error_details": [],
            }

            # Create manifest for this language
            lang_manifest = create_manifest_summary(
                version=__version__,
                timestamp=ts_str,
                mode=config.mode,
                source_files=[os.path.basename(f) for f in file_paths],
                target_languages=[lang_code],
                summary=summary,
                processing_summary=processing_summary,
                dnt_meta=dnt_meta,
                tb_meta=tb_meta,
                source_language=source_lang,
            )

            # Write artifacts for this language
            write_run_artifacts(
                artifacts_dir,
                lang_code,
                dnt_meta,
                tb_meta,
                lang_manifest,
            )

            logger.info(
                f"Language artifacts written for {lang_code}: artifacts/{lang_code}/"
            )

        except Exception as e:
            logger.error(f"Failed to write artifacts for {lang_code}: {e}")
            continue

    # Create batch-level summary and processing summary
    batch_summary = {
        "total_files": len(file_paths),
        "unique_languages": len(config.target_languages),
        "total_operations": total_operations,
        "successes": successful_translations,
        "skipped": 0,
        "errors": total_operations - successful_translations,
        "error_details": [],
    }

    # Import get_filtering_rules for batch summary
    from srt_translator.core.utils.run_summaries import get_filtering_rules

    batch_processing_summary = {
        "batch_size": config.batch_size,
        "aggressiveness": config.aggressiveness,
        "model": config.model_name,
        "filtering_rules": get_filtering_rules(),
    }

    # Write batch-root manifest (top-level)
    try:
        batch_manifest = create_batch_manifest(
            version=__version__,
            timestamp=ts_str,
            mode=config.mode,
            source_files=[os.path.basename(f) for f in file_paths],
            target_languages=list(config.target_languages.values()),
            summary=batch_summary,
            processing_summary=batch_processing_summary,
            source_language=source_lang,
        )
        batch_manifest_path = os.path.join(batch_dir, "manifest.json")
        with open(batch_manifest_path, "w", encoding="utf-8") as f:
            json.dump(batch_manifest, f, ensure_ascii=False, indent=2)
        logger.info("Wrote batch-root manifest.json")
    except Exception as e:
        logger.warning(f"Failed to write batch-root manifest: {e}")

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

    # Return summary of translation results
    return SummaryDict(
        total_files=len(file_paths),
        unique_languages=len(config.target_languages),
        total_operations=total_operations,
        successes=successful_translations,
        skipped=0,
        errors=total_operations - successful_translations,
        error_details=[],
    )
