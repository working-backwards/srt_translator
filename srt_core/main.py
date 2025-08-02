import logging
import os
from datetime import datetime

from dotenv import load_dotenv

from srt_core.config.language_config import language_config
from srt_core.config.settings import (
    BATCH_SIZE,
    FIX_AGGRESSIVENESS,
    LOG_DIRECTORY,
    OUTPUT_BASE_DIR,
    SOURCE_DIR,
    SOURCE_LANG,
    TARGET_LANGUAGES,
)
from srt_core.translator.fixer import SRTFixer
from srt_core.translator.translator import SRTTranslator

load_dotenv()

logging.basicConfig(level=logging.INFO)  # Enable DEBUG-level logging for the whole app


def translate_srt_files(file_paths=None):
    """Translate SRT files. If file_paths is None, process all files in SOURCE_DIR."""
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

    translator = SRTTranslator(source_lang=SOURCE_LANG)

    # Log language configuration information
    logging.info(f"Source language: {SOURCE_LANG}")
    logging.info(f"Target languages: {len(TARGET_LANGUAGES)} languages configured")
    if len(TARGET_LANGUAGES) <= 10:
        logging.info(f"Languages: {', '.join(TARGET_LANGUAGES.keys())}")
    else:
        popular_langs = language_config.get_popular_languages()
        logging.info(f"Popular languages: {', '.join(popular_langs)}")
        logging.info(f"Total available languages: {len(TARGET_LANGUAGES)}")

    summary = {
        "total_files": 0,
        "total_languages": 0,
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

        for lang_name, lang_code in TARGET_LANGUAGES.items():
            summary["total_languages"] += 1
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
                    target_lang=lang_name,
                )
                if result is None:
                    summary["skipped"] += 1
                else:
                    summary["successes"] += 1
                    # Track successfully translated files
                    translated_files.append(output_filepath)
            except Exception as e:
                summary["errors"] += 1
                summary["error_details"].append(f"{filename} ({lang_name}): {e}")
                print(f"Error translating {filename} to {lang_name}: {e}")

    # Perform fixes only on files that were translated in this session
    fixer = SRTFixer(log_file, OUTPUT_BASE_DIR)
    fixer.parse_log_file()

    if FIX_AGGRESSIVENESS > 0 and translated_files:
        # Only fix files that were actually translated in this session
        fixer.fix_specific_srt_files(
            translated_files, aggressiveness=FIX_AGGRESSIVENESS
        )

    fixer.report_status()

    # Print summary
    logging.info("\n=== Translation Summary ===")
    logging.info(f"Files processed: {summary['total_files']}")
    logging.info(f"Languages processed: {summary['total_languages']}")
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
    translate_srt_files()
