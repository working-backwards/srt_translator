import logging
import os
from datetime import datetime, timezone
from typing import Dict, List


from srt_core.config.settings import (
    FIX_AGGRESSIVENESS,
    SOURCE_DIR,
    TARGET_LANGUAGES,
    DNT_TERMS,
    TERMBASE,
)
from srt_core.config.translation_config import (
    TranslationConfig,
    build_config_from_parameters,
)
from srt_core.config.config_resolver import ConfigResolver
from srt_core.translator.fixer import SRTFixer
from srt_core.translator.translator import SRTTranslator
from srt_core.utils.logging_setup import setup_logging

# Do not configure logging at import time. The caller (GUI worker or CLI entrypoint)
# is responsible for initializing logging via setup_logging().


def translate_srt_files(
    file_paths=None,
    target_languages=None,
    dnt_terms=None,
    termbase=None,
    api_key=None,
    config: TranslationConfig = None,
):
    """Translate SRT files. If config is provided, use it. Otherwise, use individual parameters or fall back to global settings."""

    # If TranslationConfig is provided, use it
    if config is not None:
        translation_config = config
    else:
        # Build configuration from parameters or fall back to global settings
        if target_languages is None:
            target_languages = TARGET_LANGUAGES

        if dnt_terms is None:
            dnt_terms = DNT_TERMS

        if termbase is None:
            termbase = TERMBASE

        translation_config = build_config_from_parameters(
            target_languages=target_languages,
            dnt_terms=dnt_terms,
            termbase=termbase,
            api_key=api_key,
        )

    if file_paths is None:
        if not os.path.exists(SOURCE_DIR):
            print(f"Source directory {SOURCE_DIR} does not exist.")
            return {
                "success": False,
                "total_files": 0,
                "completed": 0,
                "failed": 0,
                "skipped": 0,
                "error_details": ["Source directory does not exist"],
            }
        file_paths = [
            os.path.join(SOURCE_DIR, f)
            for f in os.listdir(SOURCE_DIR)
            if f.endswith(".srt")
        ]

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

    print(f"Batch folder: {batch_dir}")
    print(f"Log file: {log_file}")
    print(f"Translating with batch size: {translation_config.batch_size}")

    # Create translator with configuration
    translator = SRTTranslator(
        dnt_terms=translation_config.dnt_terms,
        termbase=translation_config.termbase,
        api_key=translation_config.api_key,
        logger=translation_config.logger,
        allow_global_termbase_fallback=translation_config.mode
        == "CLI",  # GUI: no fallback; CLI: allow
        model_name=translation_config.model_name,
        batch_size=translation_config.batch_size,
    )

    # Log configuration debug info using the new debug_log_config method
    SRTTranslator.debug_log_config(translation_config, full_termbase=True)

    summary = {
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
                summary["error_details"].append(f"{filename} ({lang_name}): {e}")
                print(f"Error translating {filename} to {lang_name}: {e}")

        # Run fixer after each SRT file is complete
        if FIX_AGGRESSIVENESS > 0 and current_file_translations:
            logging.info(f"Running automatic fixes for {filename}...")
            fixer = SRTFixer(log_file, batch_dir)
            fixer.parse_log_file()
            fixer.fix_specific_srt_files(
                current_file_translations, aggressiveness=FIX_AGGRESSIVENESS
            )
            fixer.report_status()

    # Set unique languages count
    summary["unique_languages"] = len(translation_config.target_languages)

    # Print summary
    logging.info("\n=== Translation Summary ===")
    logging.info(f"Files processed: {summary['total_files']}")
    logging.info(f"Languages processed: {summary['unique_languages']}")
    logging.info(f"Total translation operations: {summary['total_operations']}")
    logging.info(f"Successful translations: {summary['successes']}")
    logging.info(f"Skipped (empty/corrupt): {summary['skipped']}")
    logging.info(f"Errors: {summary['errors']}")
    if summary["error_details"]:
        logging.info("Error details:")
        for detail in summary["error_details"]:
            logging.info(f"  - {detail}")
    logging.info("==========================\n")

    # Build minimal manifest (Option B)
    try:
        # Use mode from config
        mode = translation_config.mode

        # App version from pyproject.toml (best effort)
        app_version = "1.0.0"
        try:
            pyproject_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "pyproject.toml"
            )
            with open(pyproject_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("version = "):
                        app_version = line.split("=", 1)[1].strip().strip('"')
                        break
        except Exception:
            pass

        # Times
        started_at_local = ts_local.replace(microsecond=0).isoformat()
        finished_local_dt = datetime.now().astimezone()
        finished_at_local = finished_local_dt.replace(microsecond=0).isoformat()
        started_at_utc = (
            ts_local.astimezone(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )
        finished_at_utc = (
            finished_local_dt.astimezone(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )

        # Inputs relative paths
        inputs: List[Dict[str, object]] = []
        for input_filepath in file_paths:
            try:
                size = os.path.getsize(input_filepath)
            except OSError:
                size = None
            rel_path = os.path.relpath(input_filepath, batch_dir)
            inputs.append({"path": rel_path, "size": size})

        # Outputs mapping by code preserving casing from languages.json
        outputs: Dict[str, List[str]] = {}
        for lang_name, lang_code in translation_config.target_languages.items():
            outputs.setdefault(lang_code, [])
        for out_path in translated_files:
            rel_out = os.path.relpath(out_path, batch_dir)
            # infer code from parent directory (uppercase folder); map back to manifest code by scanning
            lang_upper = os.path.basename(os.path.dirname(out_path))
            # Find matching code by case-insensitive compare to uppercase
            match_code = None
            for code in translation_config.target_languages.values():
                if code.upper() == lang_upper:
                    match_code = code
                    break
            if match_code is None:
                match_code = lang_upper  # fallback
            outputs.setdefault(match_code, []).append(rel_out)

        manifest = {
            "schema_version": "1.0",
            "batch_id": ts_str,
            "started_at_local": started_at_local,
            "finished_at_local": finished_at_local,
            "started_at_utc": started_at_utc,
            "finished_at_utc": finished_at_utc,
            "mode": mode,
            "app_version": app_version,
            "target_languages": list(translation_config.target_languages.values()),
            "inputs": inputs,
            "outputs": outputs,
            "log_file": os.path.relpath(log_file, batch_dir),
            "termbase_file": "termbase.json",
            "dnt_terms_file": "dnt_terms.json",
            "paths_are_relative_to_batch_dir": True,
        }

        tmp_path = os.path.join(batch_dir, "manifest.tmp.json")
        final_path = os.path.join(batch_dir, "manifest.json")
        import json

        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, final_path)
        logging.info(f"Manifest written: {os.path.relpath(final_path, batch_dir)}")

        # Write termbase and DNT terms to the same output directory
        try:
            # Debug logging to see what data we have
            logging.info(
                f"Writing configuration files - Termbase keys: {list(translation_config.termbase.keys()) if translation_config.termbase else 'None'}"
            )
            logging.info(
                f"Writing configuration files - DNT terms count: {len(translation_config.dnt_terms) if translation_config.dnt_terms else 0}"
            )
            if translation_config.dnt_terms:
                logging.info(
                    f"Writing configuration files - DNT terms sample: {translation_config.dnt_terms[:5]}"
                )

            # termbase.json
            termbase_tmp = os.path.join(batch_dir, "termbase.tmp.json")
            termbase_path = os.path.join(batch_dir, "termbase.json")
            with open(termbase_tmp, "w", encoding="utf-8") as f:
                json.dump(translation_config.termbase, f, ensure_ascii=False, indent=2)
            os.replace(termbase_tmp, termbase_path)
            logging.info(
                f"Termbase written: {os.path.relpath(termbase_path, batch_dir)}"
            )

            # dnt_terms.json
            dnt_tmp = os.path.join(batch_dir, "dnt_terms.tmp.json")
            dnt_terms_path = os.path.join(batch_dir, "dnt_terms.json")
            dnt_terms_data = {
                "description": "List of terms that should not be translated (Do Not Translate)",
                "terms": translation_config.dnt_terms,
            }
            with open(dnt_tmp, "w", encoding="utf-8") as f:
                json.dump(dnt_terms_data, f, ensure_ascii=False, indent=2)
            os.replace(dnt_tmp, dnt_terms_path)
            logging.info(
                f"DNT terms written: {os.path.relpath(dnt_terms_path, batch_dir)}"
            )

        except Exception as e:
            logging.warning(f"Failed to write termbase or DNT terms: {e}")

        logging.info(f"Batch folder: {batch_dir}")
    except Exception as e:
        logging.warning(f"Failed to write manifest: {e}")

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


if __name__ == "__main__":
    # For CLI mode, use ConfigResolver to get configuration
    try:
        config = ConfigResolver.get_translation_config_for_cli()
        translate_srt_files(config=config)
    except Exception as e:
        print(f"Error: {e}")
        exit(1)
