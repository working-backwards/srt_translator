#!/usr/bin/env python3
"""
Main module for SRT Translator.
Provides the core translation functionality for both CLI and GUI interfaces.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path

from openai import APIConnectionError, AuthenticationError, PermissionDeniedError, RateLimitError

from srt_translator import __version__
from srt_translator.core.config.language_config import LanguageConfig
from srt_translator.core.config.models import SummaryDict, TranslationConfig
from srt_translator.core.translator.fixer import SRTFixer
from srt_translator.core.translator.translator import SRTTranslator

# Do not configure logging at import time. The caller (GUI worker or CLI entrypoint)
# is responsible for initializing logging via setup_logging().


def translate_srt_files(
    file_paths: list[str],
    config: TranslationConfig,
    retry_status_callback=None,
    stop_check=None,
    on_language_done=None,
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

    # Always logs to file + INFO-level messages appear in log file.
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

    try:
        logger.info("Batch folder: %s", batch_dir)
        logger.info("Log file: %s", log_file)
        logger.info("Translating with per-language batch sizes from injected policies")

        # Stage 3: the core must not read languages.json directly.
        # Language policy is injected by GUI/CLI loaders via config.language_policies.

        language_config = LanguageConfig(config.language_policies)

        # clear errors if codes() missing.
        num_langs = len(language_config.codes())
        logger.info("Language policy injected (languages=%d)", num_langs)

        # === Same-language guard: drop targets that match detected source ===
        # Note: We do NOT mutate the caller's config object (it's frozen).
        # Instead, we compute active_target_languages for this run and use that throughout.
        source_lang = getattr(config, "source_language", None)
        source_code = None

        if source_lang is not None and isinstance(source_lang, dict):
            source_code = (source_lang.get("normalized_code") or source_lang.get("detected_code") or "").strip()

        # Compute the active target languages for this run without mutating config
        if source_code:
            # Compare case-insensitively against requested target codes
            keep = {
                name: code
                for name, code in config.target_languages.items()
                if (code or "").strip().lower() != source_code.lower()
            }
            if len(keep) != len(config.target_languages):
                logger.warning(
                    "Dropping target identical to detected source (%s); %s target(s) removed.",
                    source_code,
                    len(config.target_languages) - len(keep),
                )
            active_target_languages = keep
        else:
            active_target_languages = config.target_languages

        if source_lang and isinstance(source_lang, dict) and source_lang.get("mixed"):
            logger.warning("Detected mixed-language source; proceeding with dominant language.")

        # Process each target language
        successful_translations = 0
        total_operations = 0

        successful_languages = []
        failed_languages = []
        cancelled = False

        for lang_name, lang_code in active_target_languages.items():
            if stop_check is not None and stop_check():
                logger.info("Translation cancelled by user before language: %s", lang_name)
                cancelled = True
                break

            if not lang_code:
                logger.warning("Skipping language '%s' with empty code", lang_name)
                continue

            total_operations += 1
            logger.info(
                "translated by %s / %s - %s → %s",
                total_operations,
                len(active_target_languages),
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
                    translation_model_name=config.translation_model_name,
                    batch_size=batch_size_for_lang,
                    logger=logger,
                    error_policy=config.error_policy,  # Pass error policy
                    language_config=language_config,  # Pass language configuration
                    tone=config.tone,  # Pass tone setting
                    retry_status_callback=retry_status_callback,
                    stop_check=stop_check,
                )
                logger.info(
                    "Language run: %s (%s) batch_size=%d cps_cap=%s apostrophe_allowed=%s tone=%s",
                    lang_name,
                    lang_code,
                    batch_size_for_lang,
                    language_config.get_cps_cap(lang_code),
                    language_config.allows_placeholder_apostrophe(lang_code),
                    config.tone,
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
                successful_languages.append({"language": lang_name, "code": lang_code, "status": "success"})
                logger.info("Successfully translated to %s", lang_name)
                if on_language_done is not None:
                    try:
                        on_language_done()
                    except Exception:
                        logger.exception("on_language_done callback raised; ignoring")

            except (AuthenticationError, PermissionDeniedError):
                logger.error(
                    "Authentication failed for %s.",
                    lang_name,
                )
                raise

            except RuntimeError as e:
                if "Invalid translation model" in str(e):
                    logger.error("Fatal model configuration error for %s: %s", lang_name, e)
                    raise
                logger.error(
                    "Translation failed for %s: %s",
                    lang_name,
                    e,
                )
                failed_languages.append(
                    {
                        "language": lang_name,
                        "code": lang_code,
                        "error_type": type(e).__name__,
                        "message": str(e),
                        "retryable": True,
                    }
                )
                continue

            except RateLimitError as e:
                detail = str(e).lower()
                if "insufficient_quota" in detail or "quota" in detail or "billing" in detail:
                    logger.error(
                        "OpenAI quota exhausted for %s: %s",
                        lang_name,
                        e,
                    )
                    raise

                # Soft/transient throttling → track per-language failure
                logger.error(
                    "Rate limit while translating to %s: %s",
                    lang_name,
                    e,
                )

                failed_languages.append(
                    {
                        "language": lang_name,
                        "code": lang_code,
                        "error_type": type(e).__name__,
                        "message": str(e),
                    }
                )
                continue

            except APIConnectionError as e:
                logger.error(
                    "Internet connection lost for %s: %s",
                    lang_name,
                    e,
                )
                raise

            except Exception as e:
                logger.error("Failed to translate to %s: %s", lang_name, e)
                failed_languages.append(
                    {
                        "language": lang_name,
                        "code": lang_code,
                        "error_type": type(e).__name__,
                        "message": str(e),
                    }
                )
                continue

        # Write AI config manifest
        try:
            # Collect the actual batch sizes used for each language
            language_batch_sizes = {}
            for _lang_name, lang_code in active_target_languages.items():
                # Record batch size for each processed language
                if lang_code:
                    try:
                        language_batch_sizes[lang_code] = language_config.get_target_batch_size(lang_code)
                    except Exception:
                        language_batch_sizes[lang_code] = 5

            manifest_data = {
                "version": __version__,
                "timestamp": ts_str,
                "mode": config.mode,
                "source_files": [os.path.basename(f) for f in file_paths],
                "target_languages": list(active_target_languages.values()),
                # Convert immutable config containers to JSON-friendly types:
                # - dnt_terms: tuple -> list (json.dump can't serialize tuple directly)
                # - termbase: MappingProxyType (nested) -> dict of dicts
                "dnt_terms": list(config.dnt_terms),
                "termbase": {lang: dict(entries) for lang, entries in config.termbase.items()},
                # Persist source language so evaluation is reproducible from
                # artifacts alone. Shape matches what TranslationConfig holds
                # (detected_code/normalized_code/normalized_name keys); the
                # eval reader at runner.py:_extract_source_language unpacks
                # those keys back into {code, name}.
                "source_language": dict(config.source_language) if config.source_language else {},
                "language_batch_sizes": language_batch_sizes,
                "temperature": config.temperature,
                "tone": config.tone,
                "translation_model_name": config.translation_model_name,
            }

            # Write ai_config.json directly to artifacts directory
            artifacts_dir = os.path.join(batch_dir, "artifacts")
            os.makedirs(artifacts_dir, exist_ok=True)
            manifest_path = os.path.join(artifacts_dir, "ai_config.json")
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest_data, f, ensure_ascii=False, indent=2)

            with open(os.path.join(artifacts_dir, "dnt.json"), "w", encoding="utf-8") as f:
                json.dump(list(config.dnt_terms), f, ensure_ascii=False, indent=2)

            with open(os.path.join(artifacts_dir, "termbase.json"), "w", encoding="utf-8") as f:
                json.dump(
                    {lang: dict(entries) for lang, entries in config.termbase.items()},
                    f,
                    ensure_ascii=False,
                    indent=2,
                )

            logger.info("Wrote artifacts: ai_config.json, dnt.json, termbase.json")

        except Exception as e:
            logger.warning("Failed to write AI config manifest: %s", e)

        # Artifacts directory already created above

        # Create originals directory and copy source files for evaluation
        originals_dir = os.path.join(batch_dir, "originals")
        os.makedirs(originals_dir, exist_ok=True)

        # Copy source files to originals directory for evaluation pairing
        for file_path in file_paths:
            try:
                import shutil

                shutil.copy2(file_path, os.path.join(originals_dir, os.path.basename(file_path)))
                logger.info("Copied source file to originals: %s", os.path.basename(file_path))
            except Exception as e:
                logger.warning("Failed to copy source file %s: %s", file_path, e)

        # Per-language artifacts are now handled by the evaluation system
        # The core translation focuses only on translation, not artifact creation

        # Batch-level artifacts are now handled by the evaluation system
        # The core translation focuses only on translation, not artifact creation

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

        # Print summary - compact readable summary at end of log.
        logger.info(" === Translation Summary ===")
        logger.info("Files processed: %s", len(file_paths))
        logger.info("Languages processed: %s", len(active_target_languages))
        logger.info("Total translation operations: %s", total_operations)
        logger.info("Successful translations: %s", successful_translations)
        logger.info("Failed translations: %s", total_operations - successful_translations)
        logger.info("==========================")
    finally:
        # Each batch run logs only once, cleanly.
        logger.removeHandler(file_handler)
        file_handler.close()

    # Return summary of translation results with batch directory
    return {
        "total_files": len(file_paths),
        "unique_languages": len(active_target_languages),
        "total_operations": total_operations,
        "successes": successful_translations,
        "skipped": 0,
        "errors": total_operations - successful_translations,
        "error_details": [],
        "successful_languages": successful_languages,
        "failed_languages": failed_languages,
        "batch_directory": batch_dir,  # Include batch directory for evaluation
        "cancelled": cancelled,
    }
