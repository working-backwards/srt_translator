import os
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)  # Enable DEBUG-level logging for the whole app

from dotenv import load_dotenv

from srt_app.config.settings import SOURCE_DIR, OUTPUT_BASE_DIR, TARGET_LANGUAGES, SOURCE_LANG, \
    FIX_AGGRESSIVENESS, LOG_DIRECTORY
from srt_app.translator.fixer import SRTFixer
from srt_app.translator.translator import SRTTranslator

load_dotenv()


def batch_translate_srt_files():
    """Batch translate all SRT files in the source directory using batching for efficiency and context."""
    if not os.path.exists(SOURCE_DIR):
        print(f"Source directory {SOURCE_DIR} does not exist.")
        return

    # Ensure translation logs directory exists
    os.makedirs(LOG_DIRECTORY, exist_ok=True)

    # Create a timestamped log file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(LOG_DIRECTORY, f"translation_issues_{timestamp}.log")

    from srt_app.config.settings import BATCH_SIZE
    print(f"Log file created at: {log_file}")
    print(f"Translating with batch size: {BATCH_SIZE}")

    translator = SRTTranslator(source_lang=SOURCE_LANG)

    summary = {
        "total_files": 0,
        "total_languages": 0,
        "successes": 0,
        "skipped": 0,
        "errors": 0,
        "error_details": []
    }

    for filename in os.listdir(SOURCE_DIR):
        if filename.endswith('.srt'):
            input_filepath = os.path.join(SOURCE_DIR, filename)
            summary["total_files"] += 1

            for lang_name, lang_code in TARGET_LANGUAGES.items():
                summary["total_languages"] += 1
                file_base, file_ext = os.path.splitext(filename)
                new_filename = f"{file_base} - {lang_code}{file_ext}"
                output_filepath = os.path.join(
                    OUTPUT_BASE_DIR,
                    lang_code,
                    new_filename
                )

                try:
                    result = translator.translate_file(
                        input_filepath=input_filepath,
                        output_filepath=output_filepath,
                        target_lang=lang_name
                    )
                    if result is None:
                        summary["skipped"] += 1
                    else:
                        summary["successes"] += 1
                except Exception as e:
                    summary["errors"] += 1
                    summary["error_details"].append(
                        f"{filename} ({lang_name}): {e}"
                    )
                    print(f"Error translating {filename} to {lang_name}: {e}")

    # Perform fixes based on the aggressiveness level
    fixer = SRTFixer(log_file, OUTPUT_BASE_DIR)
    fixer.parse_log_file()

    if FIX_AGGRESSIVENESS > 0:
        fixer.fix_srt_files(aggressiveness=FIX_AGGRESSIVENESS)

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


if __name__ == '__main__':
    batch_translate_srt_files()
