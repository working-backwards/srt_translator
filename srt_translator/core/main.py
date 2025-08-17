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

from srt_translator import __version__
from srt_translator.core.config.models import TranslationConfig
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
):
    """Translate SRT files. Configuration must be provided via the config parameter."""

    # TranslationConfig is required - no fallbacks to global settings
    if config is None:
        raise ValueError(
            "TranslationConfig must be provided. The core engine does not support fallbacks to global settings."
        )

    translation_config = config

    # File paths must be provided explicitly
    if not file_paths:
        raise ValueError(
            "file_paths must be provided. The core engine does not support fallbacks to global SOURCE_DIR."
        )

    # Create batch directory (with local timezone offset) under configured output
    ts_local = datetime.now().astimezone()
    ts_str = ts_local.strftime("%Y%m%d_%H%M%S%z")  # e.g., 20250809_120000-0700
    batch_dir = os.path.join(
        translation_config.output_directory or "translated_srt_files",
        f"translation-batch-{ts_str}",
    )
    os.makedirs(batch_dir, exist_ok=True)

    # Create a log file inside the batch directory and initialize logging
    log_file = os.path.join(batch_dir, f"translation_issues_{ts_str}.log")
    setup_logging(log_file_override=log_file)

    logger = logging.getLogger(__name__)
    logger.info(f"Batch folder: {batch_dir}")
    logger.info(f"Log file: {log_file}")
    logger.info(f"Translating with batch size: {translation_config.batch_size}")

    # Apply numeric filtering to DNT terms before creating translator
    filtered_dnt_terms = translation_config.dnt_terms
    dnt_filtered_out = []
    if translation_config.dnt_terms:
        # Import the filtering function from ai_config
        from srt_translator.gui.ai_config import AIConfigGenerator
        temp_config = AIConfigGenerator("dummy_key")  # Temporary instance for filtering
        filtered_dnt_terms, dnt_filtered_out = temp_config.filter_dnt_terms_with_metadata(translation_config.dnt_terms)
        
        if len(filtered_dnt_terms) != len(translation_config.dnt_terms):
            logger.info(f"DNT terms filtered: {len(translation_config.dnt_terms)} → {len(filtered_dnt_terms)} (numeric items removed)")

    # Create translator with filtered DNT terms
    translator = SRTTranslator(
        dnt_terms=filtered_dnt_terms,
        termbase=translation_config.termbase,
        api_key=translation_config.api_key,
        allow_global_termbase_fallback=translation_config.mode
        == "CLI",  # GUI: no fallback; CLI: allow
        model_name=translation_config.model_name,
        batch_size=translation_config.batch_size,
        logger=logger,  # Pass the configured logger
    )

    # Capture filtering results for enhanced output
    processing_summary = {
        "dnt_terms": {
            "provided": len(translation_config.dnt_terms) if translation_config.dnt_terms else 0,
            "used": len(translator.term_handler.dnt_terms) if translator.term_handler.dnt_terms else 0,
            "filtered": 0,
            "filtering_details": []
        },
        "termbase": {
            "provided_entries": 0,
            "used_entries": 0,
            "collisions_resolved": 0,
            "filtering_details": {}
        },
        "quality_improvements": [
            "Numeric DNT terms automatically filtered",
            "DNT precedence enforced over termbase",
            "Relevant-only termbase injection"
        ]
    }

    # Calculate DNT filtering details
    if translation_config.dnt_terms:
        processing_summary["dnt_terms"]["filtered"] = len(dnt_filtered_out)
        processing_summary["dnt_terms"]["filtering_details"] = dnt_filtered_out

    # Calculate termbase filtering details
    if translation_config.termbase:
        total_provided = sum(len(lang_terms) for lang_terms in translation_config.termbase.values())
        processing_summary["termbase"]["provided_entries"] = total_provided
        
        # Get filtered termbase from translator
        filtered_tb = translator.term_handler.get_filtered_termbase()
        total_used = sum(len(lang_terms) for lang_terms in filtered_tb.values())
        processing_summary["termbase"]["used_entries"] = total_used
        processing_summary["termbase"]["collisions_resolved"] = total_provided - total_used
        
        # Track what was filtered out per language
        for lang_code in translation_config.termbase:
            if lang_code in translation_config.termbase and lang_code in filtered_tb:
                original_lang_terms = translation_config.termbase[lang_code]
                filtered_lang_terms = filtered_tb[lang_code]
                filtered_out_lang = set(original_lang_terms.keys()) - set(filtered_lang_terms.keys())
                if filtered_out_lang:
                    if "filtering_details" not in processing_summary["termbase"]:
                        processing_summary["termbase"]["filtering_details"] = {}
                    processing_summary["termbase"]["filtering_details"][lang_code] = {
                        "filtered_out": list(filtered_out_lang),
                        "reason": "DNT collision"
                    }

    # Log configuration debug info using the new debug_log_config method
    SRTTranslator.debug_log_config(translation_config, full_termbase=True)

    # Create summary with proper typing
    summary: SummaryDict = {
        "total_files": 0,
        "unique_languages": 0,
        "total_operations": 0,
        "successes": 0,
        "skipped": 0,
        "errors": 0,
        "error_details": [],
    }

    # Track which files were actually translated in this session
    translated_files = []

    for input_filepath in file_paths:
        filename = os.path.basename(input_filepath)
        summary["total_files"] += 1

        # Track files translated for this specific SRT file
        current_file_translations = []

        for lang_name, lang_code in translation_config.target_languages.items():
            summary["total_operations"] += 1
            file_base, file_ext = os.path.splitext(filename)
            new_filename = f"{file_base} - {lang_code.upper()}{file_ext}"  # Convert language code to uppercase for filename
            lang_dir = os.path.join(batch_dir, lang_code.upper())
            os.makedirs(lang_dir, exist_ok=True)
            output_filepath = os.path.join(lang_dir, new_filename)

            # Log progress: translated by X / Y
            current_operation = summary["total_operations"]
            total_operations = len(file_paths) * len(translation_config.target_languages)
            logger.info(f"translated by {current_operation} / {total_operations} - {filename} → {lang_name}")

            try:
                result = translator.translate_file(
                    input_filepath=input_filepath,
                    output_filepath=output_filepath,
                    target_lang=lang_code,
                )
                if result is None:
                    summary["skipped"] += 1
                else:
                    summary["successes"] += 1
                    # Track successfully translated files
                    current_file_translations.append(output_filepath)
                    translated_files.append(output_filepath)
            except Exception as e:
                summary["errors"] += 1
                error_details = summary["error_details"]
                if isinstance(error_details, list):
                    error_details.append(f"{filename} ({lang_name}): {e}")
                logger.error(f"Error translating {filename} to {lang_name}: {e}")

        # Run fixer after each SRT file is complete
        # Use aggressiveness from config - no hardcoded values
        if translation_config.aggressiveness > 0 and current_file_translations:
            logger.info(f"Running automatic fixes for {filename}...")
            fixer = SRTFixer(log_file, batch_dir)
            fixer.parse_log_file()
            fixer.fix_specific_srt_files(
                current_file_translations,
                aggressiveness=translation_config.aggressiveness,
            )
            fixer.report_status()

    # Set unique languages count
    summary["unique_languages"] = len(translation_config.target_languages)

    # Print summary
    logger.info("\n=== Translation Summary ===")
    logger.info(f"Files processed: {summary['total_files']}")
    logger.info(f"Languages processed: {summary['unique_languages']}")
    logger.info(f"Total translation operations: {summary['total_operations']}")
    logger.info(f"Successful translations: {summary['successes']}")
    logger.info(f"Skipped (empty/corrupt): {summary['skipped']}")
    logger.info(f"Errors: {summary['errors']}")
    error_details = summary["error_details"]
    if isinstance(error_details, list) and error_details:
        logger.info("Error details:")
        for detail in error_details:
            logger.info(f"  - {detail}")
    logger.info("==========================\n")

    # Build standardized artifacts using new utilities
    try:
        from srt_translator.core.utils.run_summaries import (
            create_dnt_summary,
            create_termbase_summary,
            create_manifest_summary,
            write_run_artifacts,
            get_filtering_rules,
        )
        
        # Get filtering rules
        filtering_rules = get_filtering_rules()
        
        # Create artifacts directory structure
        artifacts_dir = os.path.join(batch_dir, "artifacts")
        os.makedirs(artifacts_dir, exist_ok=True)
        
        # Write root-level manifest for backward compatibility
        root_manifest_path = os.path.join(batch_dir, "manifest.json")
        root_manifest_data = {
            "version": __version__,
            "timestamp": ts_str,
            "mode": translation_config.mode,
            "source_files": [os.path.basename(f) for f in file_paths],
            "target_languages": list(translation_config.target_languages.values()),
            "summary": summary,
            "processing_summary": processing_summary,
        }
        with open(root_manifest_path, "w", encoding="utf-8") as f:
            json.dump(root_manifest_data, f, ensure_ascii=False, indent=2)
        logger.info(f"Root manifest written: {os.path.relpath(root_manifest_path, batch_dir)}")

        # Write per-language artifacts
        try:
            # Get filtered termbase for comparison
            filtered_tb = translator.term_handler.get_filtered_termbase()
            
            for lang_name, lang_code in translation_config.target_languages.items():
                # Create DNT summary for this language
                dnt_meta = create_dnt_summary(
                    user_terms=translation_config.dnt_terms or [],
                    filtered_terms=filtered_dnt_terms or [],
                    filtered_out=processing_summary["dnt_terms"]["filtering_details"],
                    lang_code=lang_code,
                    filtering_rules=filtering_rules
                )
                
                # Create termbase summary for this language
                tb_meta = create_termbase_summary(
                    user_termbase=translation_config.termbase or {},
                    filtered_termbase=filtered_tb or {},
                    collisions_removed=processing_summary["termbase"].get("filtering_details", {}),
                    lang_code=lang_code,
                    filtering_rules=filtering_rules
                )
                
                # Create enriched manifest for this language
                lang_manifest = create_manifest_summary(
                    version=__version__,
                    timestamp=ts_str,
                    mode=translation_config.mode,
                    source_files=[os.path.basename(f) for f in file_paths],
                    target_languages=[lang_code],
                    summary=summary,
                    processing_summary=processing_summary,
                    dnt_meta=dnt_meta,
                    tb_meta=tb_meta
                )
                
                # Write all artifacts for this language
                dnt_path, tb_path, manifest_path = write_run_artifacts(
                    artifacts_dir=artifacts_dir,
                    lang_code=lang_code,
                    dnt_meta=dnt_meta,
                    tb_meta=tb_meta,
                    manifest_data=lang_manifest
                )
                
                logger.info(f"Language artifacts written for {lang_code}: {os.path.relpath(artifacts_dir, batch_dir)}/{lang_code}/")

        except Exception as e:
            logger.warning(f"Failed to write per-language artifacts: {e}")

        logger.info(f"Batch folder: {batch_dir}")
        logger.info(f"Artifacts directory: {os.path.relpath(artifacts_dir, batch_dir)}")
    except Exception as e:
        logger.warning(f"Failed to write artifacts: {e}")

    # Always run the fixer after translation
    try:
        if log_file and batch_dir:
            logger.info("Running automatic SRT fixer on translated files...")
            fixer = SRTFixer(log_file, batch_dir)
            fixer.parse_log_file()
            fixer.fix_srt_files(aggressiveness=translation_config.aggressiveness)
            fixer.report_status()
            logger.info("Automatic SRT fixes completed.")
        else:
            logger.warning("Fixer skipped (missing log_file or batch_dir).")
    except Exception as e:
        logger.error(f"Automatic SRT fixer failed: {e}", exc_info=True)

    # Return results for GUI integration
    return {
        "success": summary["errors"] == 0,
        "total_files": summary["total_files"],
        "completed": summary["successes"],
        "failed": summary["errors"],
        "skipped": summary["skipped"],
        "error_details": summary["error_details"],
        "log_file": log_file,
        "batch_dir": batch_dir,
    }
