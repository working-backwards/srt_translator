import os
from datetime import datetime

from config.settings import SOURCE_DIR, OUTPUT_BASE_DIR, TARGET_LANGUAGES, SOURCE_LANG, \
    FIX_AGGRESSIVENESS, LOG_DIRECTORY
from translator.fixer import SRTFixer
from translator.translator import SRTTranslator


def batch_translate_srt_files():
    """Batch translate all SRT files in the source directory"""
    if not os.path.exists(SOURCE_DIR):
        print(f"Source directory {SOURCE_DIR} does not exist.")
        return

    # Ensure translation logs directory exists
    os.makedirs(LOG_DIRECTORY, exist_ok=True)

    # Create a timestamped log file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(LOG_DIRECTORY, f"translation_issues_{timestamp}.log")

    print(f"Log file created at: {log_file}")

    translator = SRTTranslator(source_lang=SOURCE_LANG)

    for filename in os.listdir(SOURCE_DIR):
        if filename.endswith('.srt'):
            input_filepath = os.path.join(SOURCE_DIR, filename)

            for lang_name, lang_code in TARGET_LANGUAGES.items():
                file_base, file_ext = os.path.splitext(filename)
                new_filename = f"{file_base} - {lang_code}{file_ext}"
                output_filepath = os.path.join(
                    OUTPUT_BASE_DIR,
                    lang_code,
                    new_filename
                )

                try:
                    # Translate the file
                    translator.translate_file(
                        input_filepath=input_filepath,
                        output_filepath=output_filepath,
                        target_lang=lang_name
                    )
                except Exception as e:
                    print(f"Error translating {filename} to {lang_name}: {e}")

    # Perform fixes based on the aggressiveness level
    fixer = SRTFixer(log_file, OUTPUT_BASE_DIR)
    fixer.parse_log_file()

    if FIX_AGGRESSIVENESS > 0:
        fixer.fix_srt_files(aggressiveness=FIX_AGGRESSIVENESS)

    fixer.report_status()


if __name__ == '__main__':
    batch_translate_srt_files()
