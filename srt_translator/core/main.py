#!/usr/bin/env python3
"""
Main module for SRT Translator.
Provides the core translation functionality for both CLI and GUI interfaces.
"""

import json
import logging
import os
import shutil
from datetime import datetime

from srt_translator import __version__
from srt_translator.core.config.language_config import LanguageConfig
from srt_translator.core.config.models import SummaryDict, TranslationConfig
from srt_translator.core.translator.translator import SRTTranslator
from pathlib import Path
from srt_translator.core.translator.fixer import SRTFixer

# Do not configure logging at import time. The caller (GUI worker or CLI entrypoint)
# is responsible for initializing logging via setup_logging().


def translate_srt_files(
    file_paths: list[str],
    config: TranslationConfig,
    *,
    logger: logging.Logger | None = None,
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
    #  Moved this check to the very top, Immediate RuntimeError — no side effects, cleaner filesystem.
    if not config.language_policies:
        raise RuntimeError(
            "Missing language_policies in TranslationConfig. "
            "Entry points (GUI/CLI) must load languages.json and inject the policy."
        )


    # ISSUES: logger is always None
    #Always logs to file + INFO-level messages appear in log file.
    if logger is None:
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)

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
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.info("Batch folder: %s", batch_dir)
    logger.info("Log file: %s", log_file)
    logger.info("Translating with per-language batch sizes from injected policies")

    # Stage 3: the core must not read languages.json directly.
    # Language policy is injected by GUI/CLI loaders via config.language_policies.

    # # ISSUES: There is not need initialise any of the above if we are throwing RuntimeError here, since all the above
    # # will remain unused if following condition is true, so move the condition to the top
    # if not config.language_policies:
    #     raise RuntimeError(
    #         "Missing language_policies in TranslationConfig. "
    #         "Entry points (GUI/CLI) must load languages.json and inject the policy."
    #     )

    language_config = LanguageConfig(config.language_policies)

    # try:
    #     num_langs = len(language_config.codes())
    #     # ISSUES: Unwanted catch
    # except AttributeError:
    #     # Backward compatibility if codes() is not present
    #     num_langs = len(getattr(language_config, "_langs", {}) or {})

    #clear errors if codes() missing.
    num_langs = len(language_config.codes())
    logger.info("Language policy injected (languages=%d)", num_langs)

    # === Same-language guard: drop targets that match detected source ===
    source_lang = getattr(config, "source_language", None)
    source_code = None
    # try:
    #     # Instead of checking the instance type, we can check none null here, because the source_lang in config can
    #     # be either NoneType or DictType
    #
    #     if isinstance(source_lang, dict):
    #         source_code = (source_lang.get("normalized_code") or source_lang.get("detected_code") or "").strip()
    # except Exception:
    #     source_code = None


    if source_lang is not None and isinstance(source_lang, dict):
        source_code = (source_lang.get("normalized_code") or source_lang.get("detected_code") or "").strip()

    # UNWANTED: Too much work done to remove source language from the target languages dictionary, we can use dict.__delitem__(source_code)
    # method to directly remove the source language from target languages
    # if source_code:
    #     # Compare case-insensitively against requested target codes
    #     keep = {
    #         name: code
    #         for name, code in config.target_languages.items()
    #         if (code or "").strip().lower() != source_code.lower()
    #     }
    #     if len(keep) != len(config.target_languages):
    #         logger.warning(
    #             "Dropping target identical to detected source (%s); %s target(s) removed.",
    #             source_code,
    #             len(config.target_languages) - len(keep),
    #         )
    #         config = replace(config, target_languages=keep)

    # before Created a temporary dict; more CPU/memory.now Direct removal via del, same functional result, cleaner log:
    if source_code and config.target_languages:
        to_remove = [k for k, v in config.target_languages.items() if (v or "").strip().lower() == source_code.lower()]
        for lang in to_remove:
            del config.target_languages[lang]
        if to_remove:
            logger.warning(
                "Dropping target identical to detected source (%s); %d target(s) removed.",
                source_code,
                len(to_remove),
            )

     # ISSUE: Use none check for source_lang here instead of isinstance check
    # if isinstance(source_lang, dict) and source_lang.get("mixed"):
    #     logger.warning("Detected mixed-language source; proceeding with dominant language.")

    if source_lang and isinstance(source_lang, dict) and source_lang.get("mixed"):
        logger.warning("Detected mixed-language source; proceeding with dominant language.")

    # Process each target language
    successful_translations = 0
    total_operations = 0

    for lang_name, lang_code in config.target_languages.items():
        if not lang_code:
            logger.warning("Skipping language '%s' with empty code", lang_name)
            continue

        total_operations += 1
        logger.info(
            "translated by %s / %s - %s → %s",
            total_operations,
            len(config.target_languages),
            os.path.basename(file_paths[0]),
            lang_name,
        )

        try:
            # Create translator instance with per-language batch size
            batch_size_for_lang = language_config.get_target_batch_size(lang_code)
            translator = SRTTranslator(
                dnt_terms=config.dnt_terms,
                termbase=config.termbase.get(lang_code, {}),
                api_key=config.api_key,
                allow_global_termbase_fallback=config.mode == "CLI",  # GUI: no fallback; CLI: allow
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
            # logger.info("Successfully translated to %s", lang_name)

        except Exception as e:
            logger.error("Failed to translate to %s: %s", lang_name, e)
            # continue

    # Write AI config manifest
    try:
        # Collect the actual batch sizes used for each language
        language_batch_sizes = {}
        for _lang_name, lang_code in config.target_languages.items():
           #ai_config.json might show batch sizes for a language that actually failed.After: Manifest now accurately reflects translation batch sizes for all processed languages.
            if lang_code:
                # try:
                #     batch_size_for_lang = language_config.get_target_batch_size(lang_code)
                #     language_batch_sizes[lang_code] = batch_size_for_lang
                # except Exception:
                #     language_batch_sizes[lang_code] = 5  # Default batch size

                try:
                    language_batch_sizes[lang_code] = language_config.get_target_batch_size(lang_code)
                except Exception:
                    language_batch_sizes[lang_code] = 5


        manifest_data = {
            "version": __version__,
            "timestamp": ts_str,
            "mode": config.mode,
            "source_files": [os.path.basename(f) for f in file_paths],
            "target_languages": list(config.target_languages.values()),
            "dnt_terms": config.dnt_terms,
            "termbase": config.termbase,
            "language_batch_sizes": language_batch_sizes,
            "aggressiveness": config.aggressiveness,
        }

        # Write ai_config.json directly to artifacts directory
        artifacts_dir = os.path.join(batch_dir, "artifacts")
        os.makedirs(artifacts_dir, exist_ok=True)
        manifest_path = os.path.join(artifacts_dir, "ai_config.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, ensure_ascii=False, indent=2)
        logger.info("Wrote AI config to artifacts: ai_config.json")
    except Exception as e:
        logger.warning("Failed to write AI config manifest: %s", e)

    # Artifacts directory already created above

    # Create originals directory and copy source files for evaluation
    originals_dir = os.path.join(batch_dir, "originals")
    os.makedirs(originals_dir, exist_ok=True)

    # Copy source files to originals directory for evaluation pairing
    for file_path in file_paths:
        # try:
        #     source_filename = os.path.basename(file_path)
        #     dest_path = os.path.join(originals_dir, source_filename)
        #     shutil.copy2(file_path, dest_path)
        #     logger.info("Copied source file to originals: %s", source_filename)
        # except Exception as e:
        #     logger.warning("Failed to copy source file %s: %s", file_path, e)

        try:
            shutil.copy2(file_path, os.path.join(originals_dir, os.path.basename(file_path)))
            logger.info("Copied source file to originals: %s", os.path.basename(file_path))
        except Exception as e:
            logger.warning("Failed to copy source file %s: %s", file_path, e)

    # Per-language artifacts are now handled by the evaluation system
    # The core translation focuses only on translation, not artifact creation

    # Batch-level artifacts are now handled by the evaluation system
    # The core translation focuses only on translation, not artifact creation

    # # Print summary
    # logger.info(" === Translation Summary ===")
    # logger.info("Files processed: %s", len(file_paths))
    # logger.info("Languages processed: %s", len(config.target_languages))
    # logger.info("Total translation operations: %s", total_operations)
    # logger.info("Successful translations: %s", successful_translations)
    # logger.info("Failed translations: %s", total_operations - successful_translations)
    # logger.info("==========================")
    #
    # # Remove file handler to avoid duplicate logging
    # logger.removeHandler(file_handler)

    # Run SRT fixer (post-eval, batch-wide)
    logger.info("Running SRT fixer (post-eval, batch-wide)...")
    try:

        # Temporarily attach file handler to fixer's logger
        fixer_logger = logging.getLogger("srt_translator.core.translator.fixer")
        fixer_logger.addHandler(file_handler)

        fixer = SRTFixer(log_file, batch_dir)
        fixer.scan_and_fix_placeholders(batch_dir=Path(batch_dir), dnt_terms=config.dnt_terms, dry_run=False)

        # Remove file handler from fixer's logger
        fixer_logger.removeHandler(file_handler)
        logger.info("SRT fixer completed successfully.")
    except Exception as e:
        logger.error("Failed to run SRT fixer: %s", e)
    # except Exception as e:
    #     logger.error("Failed to run SRT fixer: %s", e)
    #
    # logger.info("SRT fixer completed.")

    # Print summary,Compact readable summary at end of log.
    logger.info(" === Translation Summary ===")
    logger.info("Files processed: %s", len(file_paths))
    logger.info("Languages processed: %s", len(config.target_languages))
    logger.info("Total translation operations: %s", total_operations)
    logger.info("Successful translations: %s", successful_translations)
    logger.info("Failed translations: %s", total_operations - successful_translations)
    logger.info("==========================")

    # Each batch run logs only once, cleanly.
    logger.removeHandler(file_handler)

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
