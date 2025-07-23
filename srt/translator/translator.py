import logging
import os
import re
import time

from dotenv import load_dotenv
from openai import OpenAI

from srt.config.settings import LANGUAGE_MAP, OPENAI_MODEL, get_glossary_terms, BATCH_SIZE
from srt.translator.srt_parser import SRTParser
from srt.translator.term_handler import TermHandler
from srt.utils.logging_setup import log_placeholder_issue, setup_logging


class SRTTranslator:
    def __init__(self, source_lang="EN"):
        load_dotenv()
        self.log_file = setup_logging()

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OpenAI API key must be set in the OPENAI_API_KEY environment variable"
            )

        self.client = OpenAI(api_key=api_key)
        self.source_lang = source_lang
        self.term_handler = TermHandler()
        self.parser = SRTParser()

    def get_translation_prompt(self, source_lang, target_lang):
        """Get the translation prompt with injected glossary from external file, environment, or use built-in default"""

        # Get glossary for this language
        glossary_block = self._format_glossary_block(target_lang)
        mapped_target_lang = LANGUAGE_MAP.get(target_lang, target_lang)

        # First try to load from external prompt file
        prompt_file_path = os.getenv(
            "TRANSLATION_PROMPT_FILE", "translation_prompt.txt"
        )
        if os.path.exists(prompt_file_path):
            try:
                with open(prompt_file_path, "r", encoding="utf-8") as f:
                    custom_prompt = f.read().strip()
                if custom_prompt:
                    return custom_prompt.format(
                        source_lang=source_lang,
                        target_lang=mapped_target_lang,
                        glossary_block=glossary_block,
                    )
            except Exception as e:
                logging.warning(
                    f"Error reading prompt file {prompt_file_path}: {e}. Using fallback."
                )

        # Fall back to environment variable (single line)
        custom_prompt = os.getenv("TRANSLATION_PROMPT")
        if custom_prompt:
            try:
                return custom_prompt.format(
                    source_lang=source_lang,
                    target_lang=mapped_target_lang,
                    glossary_block=glossary_block,
                )
            except KeyError as e:
                logging.warning(
                    f"Invalid template variable in TRANSLATION_PROMPT: {e}. Using built-in default."
                )

        # Built-in fallback with glossary injection
        return self._get_builtin_prompt(source_lang, mapped_target_lang, glossary_block)

    def _format_glossary_block(self, target_lang):
        """Format glossary terms for injection into prompt"""
        terms = get_glossary_terms(target_lang)
        if not terms:
            return "No specific glossary terms - use professional business terminology."

        glossary_lines = [
            f'- "{english}" → "{translation}"' for english, translation in terms.items()
        ]
        return "\n".join(glossary_lines)

    def _get_builtin_prompt(self, source_lang, target_lang, glossary_block):
        """Built-in fallback prompt with glossary injection"""
        return f"""You are a professional translator. Translate the following text from {source_lang} to {target_lang}.

IMPORTANT: Use these consistent translations for key business terms:
{glossary_block}

CRITICAL INSTRUCTIONS:
1. Do NOT create, add, or invent any placeholders like __EXCLUDED_TERM_X__
2. Only preserve placeholders that are ALREADY in the text (like __EXCLUDED_TERM_0__, __EXCLUDED_TERM_1__)
3. Use the glossary terms above for consistent translation of business concepts
4. If you see __EXCLUDED_TERM_X__ placeholders, keep them EXACTLY as written
5. Do NOT replace normal words like "the", "a", "an", etc. with placeholders
6. Only translate regular text - never modify or create placeholder patterns

Example:
- Input: "Hello __EXCLUDED_TERM_0__ world" → Output: "Hola __EXCLUDED_TERM_0__ mundo"
- Input: "The operating plan shows..." → Output: "El plan operativo muestra..." (using glossary)
- Input: "Hello the world" → Output: "Hola el mundo" (NOT "Hola __EXCLUDED_TERM_0__ mundo")

Preserve all formatting and translate naturally."""

    def translate_subtitle(self, text, target_lang, filename, subtitle_number=None):
        """Translate a single subtitle text"""
        mapped_target_lang = LANGUAGE_MAP.get(target_lang, target_lang)

        try:
            time.sleep(0.5)
            processed_text, term_map = self.term_handler.replace_excluded_terms(text)

            system_prompt = self.get_translation_prompt(self.source_lang, target_lang)

            response = self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": processed_text},
                ],
                temperature=0.1,  # Lower temperature for more consistent behavior
            )

            translated_text = response.choices[0].message.content.strip()

            # Check for phantom placeholders (AI hallucinations)
            phantom_placeholders = re.findall(r"__EXCLUDED_TERM_\d+__", translated_text)
            for phantom in phantom_placeholders:
                if phantom not in term_map:
                    logging.warning(
                        f"""
==================================================
PHANTOM PLACEHOLDER DETECTED:
File: {filename}
Subtitle Number: {subtitle_number}
Language: {target_lang}
Phantom Placeholder: {phantom}
Original Text: {text}
Translated Text: {translated_text}
Status: AI Hallucination - Remove this placeholder
==================================================
"""
                    )

            placeholder_issues = self._check_placeholder_issues(
                text, translated_text, term_map, target_lang, filename, subtitle_number
            )

            if placeholder_issues:
                for issue in placeholder_issues:
                    log_placeholder_issue(issue["type"], issue)

            final_text = self.term_handler.restore_excluded_terms(
                translated_text, term_map, filename
            )

            return final_text
        except Exception as e:
            logging.error(
                f"Translation error for file '{filename}', subtitle {subtitle_number}, text '{text}': {e}"
            )
            return text

    def _check_placeholder_issues(
        self,
        original_text,
        translated_text,
        term_map,
        target_lang,
        filename,
        subtitle_number=None,
    ):
        """Check for issues with placeholders in translated text"""
        issues = []

        for placeholder, original_term in term_map.items():
            if placeholder not in translated_text:
                issues.append(
                    {
                        "type": "missing_placeholder",
                        "fixable": True,  # This issue can likely be fixed by re-adding the placeholder
                        "reason_description": "The placeholder is missing in the translated text.",
                        "filename": filename,
                        "subtitle_number": subtitle_number,
                        "language": target_lang,
                        "placeholder": placeholder,
                        "original_term": original_term,
                        "original_text": original_text,
                        "translated_text": translated_text,
                    }
                )
                translated_text = f"{placeholder} {translated_text}"
            else:
                original_context = self.term_handler.get_context(
                    original_text, original_term
                )
                translated_context = self.term_handler.get_context(
                    translated_text, placeholder
                )

                if (
                    original_context
                    and translated_context
                    and not self.term_handler.check_context_similarity(
                        original_context, translated_context
                    )
                ):
                    issues.append(
                        {
                            "type": "position_mismatch",
                            "fixable": False,  # This issue usually requires human review
                            "reason_description": (
                                "The placeholder position in the translated text does not match its "
                                "original context, likely due to sentence structure changes."
                            ),
                            "filename": filename,
                            "subtitle_number": subtitle_number,
                            "language": target_lang,
                            "placeholder": placeholder,
                            "original_term": original_term,
                            "original_context": original_context,
                            "translated_context": translated_context,
                        }
                    )

        return issues

    def batch_translate_file(self, input_filepath, output_filepath, target_lang):
        """Translate an entire SRT file in batches for efficiency and context."""
        filename = os.path.basename(input_filepath)
        subtitles = self.parser.parse_file(input_filepath)

        if not subtitles:
            logging.warning(f"No subtitles found in {input_filepath}. Skipping translation.")
            return

        subtitles = list(srt.sort_and_reindex(subtitles))
        overlaps = list(srt.find_overlaps(subtitles))
        if overlaps:
            logging.warning(f"Overlapping subtitles detected in {input_filepath}.")

        batch_size = BATCH_SIZE
        translated_subtitles = []
        total = len(subtitles)

        for i in range(0, total, batch_size):
            batch = subtitles[i:i+batch_size]
            batch_srt = srt.compose(batch)
            translated_batch_srt = self.translate_srt_block(batch_srt, target_lang, filename, i)
            try:
                translated_batch = list(srt.parse(translated_batch_srt))
                if len(translated_batch) != len(batch):
                    logging.warning(
                        f"Batch at index {i} returned {len(translated_batch)} subtitles, expected {len(batch)}. Falling back to single translation."
                    )
                    for sub in batch:
                        sub.content = self.translate_subtitle(sub.content, target_lang, filename, sub.index)
                        translated_subtitles.append(sub)
                else:
                    for orig, trans in zip(batch, translated_batch):
                        orig.content = trans.content
                        translated_subtitles.append(orig)
            except Exception as e:
                logging.error(f"Failed to parse translated SRT batch at index {i}: {e}")
                for sub in batch:
                    sub.content = self.translate_subtitle(sub.content, target_lang, filename, sub.index)
                    translated_subtitles.append(sub)

        self.parser.write_file(output_filepath, translated_subtitles)
        logging.info(f"Translated SRT saved to: {output_filepath}")
        return output_filepath

    def translate_srt_block(self, srt_block, target_lang, filename, batch_start_index):
        """Translate a block of SRT subtitles as a batch."""
        prompt = (
            f"Translate the following SRT subtitles from {self.source_lang} to {target_lang}.\n"
            "Preserve the SRT structure, numbering, and timestamps exactly. Only translate the subtitle text.\n"
            "Return the result as a valid SRT block.\n\n"
            f"{srt_block}"
        )
        time.sleep(0.5)  # Respect rate limits
        response = self.client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": prompt},
            ],
            temperature=0.1,
        )
        return response.choices[0].message.content.strip()

    # Optionally, update translate_file to call batch_translate_file by default
    def translate_file(self, input_filepath, output_filepath, target_lang):
        """Translate an entire SRT file using batching."""
        return self.batch_translate_file(input_filepath, output_filepath, target_lang)
