import logging
import os
from datetime import datetime

from srt_core.config.language_config import language_config
from srt_core.config.settings import (
    BATCH_SIZE,
    FIX_AGGRESSIVENESS,
    LOG_DIRECTORY,
    OUTPUT_BASE_DIR,
    SOURCE_DIR,
    SOURCE_LANG,
    TARGET_LANGUAGES,
    DNT_TERMS,
    TERMBASE,
)
from srt_core.config.translation_config import TranslationConfig, build_config_from_parameters
from srt_core.config.config_resolver import ConfigResolver
from srt_core.translator.fixer import SRTFixer
from srt_core.translator.translator import SRTTranslator

# Do not configure logging at import time. The caller (GUI worker or CLI entrypoint)
# is responsible for initializing logging via setup_logging().


def translate_srt_files(
    file_paths=None, 
    target_languages=None, 
    dnt_terms=None, 
    termbase=None, 
    api_key=None,
    config: TranslationConfig = None
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
            source_lang=SOURCE_LANG,
            api_key=api_key
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

    # Ensure translation logs directory exists
    os.makedirs(LOG_DIRECTORY, exist_ok=True)

    # Create a timestamped log file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(LOG_DIRECTORY, f"translation_issues_{timestamp}.log")

    print(f"Log file created at: {log_file}")
    print(f"Translating with batch size: {BATCH_SIZE}")

    # Create translator with configuration
    translator = SRTTranslator(
        source_lang=translation_config.source_lang,
        dnt_terms=translation_config.dnt_terms,
        termbase=translation_config.termbase,
        api_key=translation_config.api_key,
        logger=translation_config.logger
    )

    # Log language configuration information
    logging.info(f"Source language: {translation_config.source_lang}")
    logging.info(f"Target languages: {len(translation_config.target_languages)} languages configured")
    if len(translation_config.target_languages) <= 10:
        logging.info(f"Languages: {', '.join(translation_config.target_languages.keys())}")
    else:
        popular_langs = language_config.get_popular_languages()
        logging.info(f"Popular languages: {', '.join(popular_langs)}")
        logging.info(f"Total available languages: {len(translation_config.target_languages)}")
    
    # Log configuration information
    logging.info(f"DNT terms count: {len(translation_config.dnt_terms)}")
    logging.info(f"Termbase languages: {list(translation_config.termbase.keys())}")

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
            output_filepath = os.path.join(
                OUTPUT_BASE_DIR,
                lang_code.upper(),  # Convert language code to uppercase for folder name
                new_filename,
            )

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
            fixer = SRTFixer(log_file, OUTPUT_BASE_DIR)
            fixer.parse_log_file()
            fixer.fix_specific_srt_files(current_file_translations, aggressiveness=FIX_AGGRESSIVENESS)
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

    # Return results for GUI integration
    return {
        "success": summary["errors"] == 0,
        "total_files": summary["total_files"],
        "completed": summary["successes"],
        "failed": summary["errors"],
        "skipped": summary["skipped"],
        "error_details": summary["error_details"],
    }


if __name__ == "__main__":
    # For CLI mode, use ConfigResolver to get configuration
    try:
        config = ConfigResolver.get_translation_config_for_cli()
        translate_srt_files(config=config)
    except Exception as e:
        print(f"Error: {e}")
        exit(1)
