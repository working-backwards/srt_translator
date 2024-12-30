import logging
import os
import time

from dotenv import load_dotenv
from openai import OpenAI

from src.config.settings import OPENAI_MODEL, LANGUAGE_MAP
from src.translator.srt_parser import SRTParser
from src.translator.term_handler import TermHandler
from src.utils.logging_setup import setup_logging, log_placeholder_issue


class SRTTranslator:
    def __init__(self, source_lang='EN'):
        load_dotenv()
        self.log_file = setup_logging()

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key must be set in the OPENAI_API_KEY environment variable")

        self.client = OpenAI(api_key=api_key)
        self.source_lang = source_lang
        self.term_handler = TermHandler()
        self.parser = SRTParser()

    def translate_subtitle(self, text, target_lang, filename):
        """Translate a single subtitle text"""
        mapped_target_lang = LANGUAGE_MAP.get(target_lang, target_lang)

        try:
            time.sleep(0.5)
            processed_text, term_map = self.term_handler.replace_excluded_terms(text)

            response = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": f"""You are a professional translator. Translate the following text from {self.source_lang} to {mapped_target_lang}.
                        Important: Do NOT translate any text between double underscores (e.g., __EXCLUDED_TERM_0__).
                        These are placeholders that must remain exactly as they are. Preserve all formatting."""
                    },
                    {
                        "role": "user",
                        "content": processed_text
                    }
                ],
                temperature=0.3
            )

            translated_text = response.choices[0].message.content.strip()
            placeholder_issues = self._check_placeholder_issues(
                text, translated_text, term_map, target_lang, filename
            )

            if placeholder_issues:
                for issue in placeholder_issues:
                    log_placeholder_issue(issue['type'], issue)

            final_text = self.term_handler.restore_excluded_terms(
                translated_text, term_map, filename
            )

            return final_text
        except Exception as e:
            logging.error(f"Translation error for file '{filename}', text '{text}': {e}")
            return text

    def _check_placeholder_issues(self, original_text, translated_text, term_map, target_lang, filename):
        """Check for issues with placeholders in translated text"""
        issues = []

        for placeholder, original_term in term_map.items():
            if placeholder not in translated_text:
                issues.append({
                    'type': 'missing_placeholder',
                    'fixable': True,  # This issue can likely be fixed by re-adding the placeholder
                    'reason_description': "The placeholder is missing in the translated text.",
                    'filename': filename,
                    'language': target_lang,
                    'placeholder': placeholder,
                    'original_term': original_term,
                    'original_text': original_text,
                    'translated_text': translated_text
                })
                translated_text = f"{placeholder} {translated_text}"
            else:
                original_context = self.term_handler.get_context(original_text, original_term)
                translated_context = self.term_handler.get_context(translated_text, placeholder)

                if (original_context and translated_context and
                        not self.term_handler.check_context_similarity(original_context, translated_context)):
                    issues.append({
                        'type': 'position_mismatch',
                        'fixable': False,  # This issue usually requires human review
                        'reason_description': ("The placeholder position in the translated text does not match its "
                                               "original context, likely due to sentence structure changes."),
                        'filename': filename,
                        'language': target_lang,
                        'placeholder': placeholder,
                        'original_term': original_term,
                        'original_context': original_context,
                        'translated_context': translated_context
                    })

        return issues

    def translate_file(self, input_filepath, output_filepath, target_lang):
        """Translate an entire SRT file"""
        filename = os.path.basename(input_filepath)
        subtitles = self.parser.parse_file(input_filepath)

        for subtitle in subtitles:
            subtitle['translated_text'] = self.translate_subtitle(
                subtitle['text'], target_lang, filename
            )

        # Ensure the output directory exists
        if not os.path.exists(os.path.dirname(output_filepath)):
            os.makedirs(os.path.dirname(output_filepath))

        self.parser.write_file(output_filepath, subtitles)
        logging.info(f"Translated SRT saved to: {output_filepath}")
        return output_filepath
