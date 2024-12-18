# main.py

import os
from config.settings import SOURCE_DIR, OUTPUT_BASE_DIR, TARGET_LANGUAGES, SOURCE_LANG
from translator.translator import SRTTranslator

def batch_translate_srt_files():
    """Batch translate all SRT files in the source directory"""
    if not os.path.exists(SOURCE_DIR):
        print(f"Source directory {SOURCE_DIR} does not exist.")
        return
    
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
                    translator.translate_file(
                        input_filepath=input_filepath, 
                        output_filepath=output_filepath,
                        target_lang=lang_name
                    )
                except Exception as e:
                    print(f"Error translating {filename} to {lang_name}: {e}")

if __name__ == '__main__':
    batch_translate_srt_files()