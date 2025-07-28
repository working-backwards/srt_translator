import logging
import os
import re
import time
import srt

from dotenv import load_dotenv
from openai import OpenAI

from srt_core.config.settings import LANGUAGE_MAP, OPENAI_MODEL, get_glossary_terms, BATCH_SIZE
from srt_core.translator.srt_parser import SRTParser
from srt_core.translator.term_handler import TermHandler
from srt_core.utils.logging_setup import log_placeholder_issue, setup_logging


# Update BAD_RESPONSE_PATTERNS to only check for the new phrase
BAD_RESPONSE_PATTERNS = [
    "I cannot translate because"
]

def contains_bad_response(text, patterns=BAD_RESPONSE_PATTERNS):
    text_lower = text.lower()
    return any(pattern.lower() in text_lower for pattern in patterns)

def extract_translation_failure_reason(ai_response):
    prefix = "I cannot translate because"
    if ai_response.lower().startswith(prefix.lower()):
        return ai_response[len(prefix):].strip(" .")
    return ai_response

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

BUSINESS TERMINOLOGY: When you see these specific business terms, use these translations:
{glossary_block}

PLACEHOLDER RULES:
1. If you see __EXCLUDED_TERM_X__ placeholders, keep them EXACTLY as written - DO NOT translate them back to the original terms
2. Do NOT create any new placeholders
3. Do NOT replace normal words with placeholders
4. CRITICAL: Placeholders like __EXCLUDED_TERM_0__ must appear in your translation exactly as __EXCLUDED_TERM_0__

TRANSLATION APPROACH:
- Translate ALL text naturally and completely
- Use the business terminology above when those specific terms appear
- For all other words, use standard translation practices
- Preserve all formatting and punctuation
- Do not skip or omit any content unless it is genuinely untranslatable

ERROR HANDLING:
Only refuse translation if the text is genuinely untranslatable (corrupted, inappropriate content, etc.).
If you cannot translate, respond EXACTLY: "I cannot translate because [specific reason]"

Examples:
- "Hello __EXCLUDED_TERM_0__ world" → "你好 __EXCLUDED_TERM_0__ 世界"
- "The operating plan shows results" → "运营计划显示结果" (using glossary)
- "They met at the time" → "他们当时见面了" (normal translation)

Translate completely and naturally."""

    def get_batch_translation_prompt(self, source_lang, target_lang):
        """Get the batch translation prompt with glossary integration"""
        glossary_block = self._format_glossary_block(target_lang)
        mapped_target_lang = LANGUAGE_MAP.get(target_lang, target_lang)
        return f"""You are a professional translator. Translate the following SRT subtitles from {source_lang} to {mapped_target_lang}.

BUSINESS TERMINOLOGY: When you see these specific business terms, use these translations:
{glossary_block}

SRT TRANSLATION RULES:
1. Preserve SRT structure, numbering, and timestamps exactly
2. Translate ALL subtitle text content completely
3. Use business terminology above for those specific terms
4. For all other text, translate normally using standard practices
5. Do not skip or omit any subtitle content unless it is genuinely untranslatable

PLACEHOLDER RULES:
1. If you see __EXCLUDED_TERM_X__ placeholders, keep them EXACTLY as written - DO NOT translate them back to the original terms
2. Do NOT create any new placeholders
3. Do NOT replace normal words with placeholders
4. CRITICAL: Placeholders like __EXCLUDED_TERM_0__ must appear in your translation exactly as __EXCLUDED_TERM_0__

ERROR HANDLING:
Only refuse if content is genuinely untranslatable. Otherwise, translate everything.
If you must refuse, respond EXACTLY: "I cannot translate because [specific reason]"

Return a complete, valid SRT block with all content translated. Do not change subtitle numbering or timestamps."""

    def translate_subtitle(self, text, target_lang, filename, subtitle_number=None, summary=None):
        """Translate a single subtitle text"""
        mapped_target_lang = LANGUAGE_MAP.get(target_lang, target_lang)

        try:
            time.sleep(0.5)
            processed_text, term_map = self.term_handler.replace_excluded_terms(text)

            system_prompt = self.get_translation_prompt(self.source_lang, target_lang)

            max_retries = 2
            retries = 0
            final_text = ""
            while retries <= max_retries:
                response = self.client.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": processed_text},
                    ],
                    temperature=0.1,  # Lower temperature for more consistent behavior
                )
                translated_text = response.choices[0].message.content.strip()
                final_text = self.term_handler.restore_excluded_terms(
                    translated_text, term_map, filename, subtitle_number=subtitle_number, source_lang=self.source_lang, target_lang=target_lang
                )
                if not contains_bad_response(final_text):
                    break
                logging.warning(
                    f"Translation refused at index {subtitle_number} in file {filename}. "
                    f"Retrying (attempt {retries + 1}/{max_retries + 1}). "
                    f"Reason: '{extract_translation_failure_reason(final_text)}'"
                )
                retries += 1
            if contains_bad_response(final_text):
                failure_reason = extract_translation_failure_reason(final_text)
                # Log the prompt and model response for debugging
                logging.info(f"\n--- SINGLE TRANSLATION ERROR PROMPT for {filename} (subtitle {subtitle_number}) ---\nSYSTEM PROMPT:\n{system_prompt}\nUSER MESSAGE (processed_text):\n{processed_text}\n--- MODEL RESPONSE ---\n{final_text}\n--- END ERROR LOG ---\n")
                logging.error(f"""
{'='*80}
SINGLE TRANSLATION FAILURE - INSTRUCTOR ACTION NEEDED
{'='*80}
SUMMARY: OpenAI refused to translate single subtitle after {max_retries + 1} attempts

COPY THIS ENTIRE SECTION TO AN AI CHAT FOR HELP:
----------------------------------------
File: {filename}
Subtitle Number: {subtitle_number}
Source Language: {self.source_lang}
Target Language: {target_lang}

ORIGINAL TEXT:
\"{text}\"

AI REFUSAL MESSAGE:
\"{final_text}\"

EXTRACTED REASON:
\"{failure_reason}\"

QUESTION FOR AI CHAT:
\"I'm translating educational content about business operations. The AI translator
refused to translate the above subtitle. The original text is educational content
about Amazon's business practices. Why might the AI refuse this translation and
how can I modify the text to make it translatable while preserving the educational
value? Please suggest an alternative wording that would be acceptable.\"

TECHNICAL DETAILS:
- Translation attempts: {max_retries + 1}
- Model: {OPENAI_MODEL}
- Processed text sent to AI: \"{processed_text}\"
- Full AI response: \"{final_text}\"
----------------------------------------

RESULT: Subtitle left untranslated to mark failure.
{'='*80}
""")
                if summary is not None and isinstance(summary, dict):
                    summary["bad_translations"] = summary.get("bad_translations", 0) + 1
                return final_text  # Keep the AI refusal message in the SRT output

            # Check for phantom placeholders (AI hallucinations)
            phantom_placeholders = re.findall(r"__EXCLUDED_TERM_\d+__", final_text)
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
Translated Text: {final_text}
Status: AI Hallucination - Remove this placeholder
==================================================
"""
                    )

            placeholder_issues = self._check_placeholder_issues(
                text, final_text, term_map, target_lang, filename, subtitle_number
            )

            if placeholder_issues:
                for issue in placeholder_issues:
                    log_placeholder_issue(issue["type"], issue)

            # ADDED: Warn if a non-empty source subtitle becomes empty after translation
            if text.strip() and not final_text.strip():
                logging.warning(
                    f"Subtitle at index {subtitle_number} in file {filename} became empty after translation. "
                    f"Original: '{text}'"
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

        batch_size = BATCH_SIZE
        translated_subtitles = []
        total = len(subtitles)

        logging.info(f"Starting batch translation of {filename} to {target_lang} with batch size {batch_size}")

        for i in range(0, total, batch_size):
            batch = subtitles[i:i+batch_size]
            batch_srt = srt.compose(batch)
            
            logging.info(f"Translating batch {i//batch_size + 1}/{(total + batch_size - 1)//batch_size} (subtitles {i+1}-{min(i+batch_size, total)})")
            
            translated_batch_srt, prompt = self.translate_srt_block(batch_srt, target_lang, filename, i)
            
            # Check if the batch translation failed completely
            if contains_bad_response(translated_batch_srt):
                logging.warning(f"Batch translation failed for batch starting at index {i}. Reason: {extract_translation_failure_reason(translated_batch_srt)}")
                logging.info(f"\n--- BATCH TRANSLATION ERROR PROMPT for {filename} (batch starting at subtitle {i}) ---\n{prompt}\n--- MODEL RESPONSE ---\n{translated_batch_srt}\n--- END ERROR LOG ---\n")
                
                # Fall back to single subtitle translation for this batch
                logging.info(f"Falling back to single subtitle translation for batch {i//batch_size + 1}")
                for sub in batch:
                    sub.content = self.translate_subtitle(sub.content, target_lang, filename, sub.index)
                    translated_subtitles.append(sub)
                continue
            
            translated_batch_srt = clean_srt_output(translated_batch_srt)
            
            # Check for phantom placeholders in batch translation
            phantom_placeholders = re.findall(r"__EXCLUDED_TERM_\d+__", translated_batch_srt)
            batch_term_map = getattr(self, '_last_batch_term_map', {})
            for phantom in phantom_placeholders:
                if phantom not in batch_term_map:
                    logging.warning(
                        f"""
==================================================
PHANTOM PLACEHOLDER DETECTED IN BATCH:
File: {filename}
Batch: {i//batch_size + 1} (subtitles {i+1}-{min(i+batch_size, total)})
Language: {target_lang}
Phantom Placeholder: {phantom}
Status: AI Hallucination in batch translation - Remove this placeholder
==================================================
"""
                    )
            try:
                translated_batch = list(srt.parse(translated_batch_srt))
                if len(translated_batch) != len(batch):
                    # Log the redistribution instead of falling back
                    logging.info(
                        f"BATCH REDISTRIBUTION: File {filename}, Batch {i//batch_size + 1} "
                        f"(subtitles {i+1}-{min(i+batch_size, total)}): "
                        f"Original {len(batch)} subtitles  AI returned {len(translated_batch)} subtitles. "
                        f"Redistributing content across original timing slots."
                    )
                    # Redistribute translated content across original timing slots
                    redistributed_batch = self._redistribute_subtitles(batch, translated_batch, filename, i)
                    for orig, redistributed in zip(batch, redistributed_batch):
                        orig.content = redistributed.content
                        translated_subtitles.append(orig)
                else:
                    # Normal case: same count, direct mapping
                    for orig, trans in zip(batch, translated_batch):
                        orig.content = trans.content
                        translated_subtitles.append(orig)
            except Exception as e:
                logging.error(f"Failed to parse translated SRT batch at index {i}: {e}")
                # Log the prompt and model response for debugging
                logging.info(f"\n--- BATCH PARSING EXCEPTION for {filename} (batch starting at subtitle {i}) ---\nEXCEPTION: {e}\nPROMPT:\n{prompt}\n--- MODEL RESPONSE ---\n{translated_batch_srt}\n--- END ERROR LOG ---\n")
                for sub in batch:
                    sub.content = self.translate_subtitle(sub.content, target_lang, filename, sub.index)
                    translated_subtitles.append(sub)

        self.parser.write_file(output_filepath, translated_subtitles)
        logging.info(f"Translated SRT saved to: {output_filepath}")
        return output_filepath

    def translate_srt_block(self, srt_block, target_lang, filename, batch_start_index):
        """Translate a block of SRT subtitles as a batch."""
        # Process excluded terms for the entire SRT block
        processed_srt_block, term_map = self.term_handler.replace_excluded_terms(srt_block)
        
        # Store term_map for phantom detection (hacky but works)
        self._last_batch_term_map = term_map
        
        prompt = self.get_batch_translation_prompt(self.source_lang, target_lang)
        full_prompt = f"{prompt}\n\n{processed_srt_block}"
        
        time.sleep(0.5)  # Respect rate limits
        response = self.client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "user", "content": full_prompt},
            ],
            temperature=0.1,
        )
        
        translated_srt = response.choices[0].message.content.strip()
        
        # Restore excluded terms in the translated SRT block
        restored_srt = self.term_handler.restore_excluded_terms(
            translated_srt, term_map, filename, 
            subtitle_number=f"batch_{batch_start_index}", 
            source_lang=self.source_lang, 
            target_lang=target_lang
        )
        
        return restored_srt, full_prompt

    def _redistribute_subtitles(self, original_batch, translated_batch, filename, batch_start_index):
        """Redistribute translated content across original timing slots, optimizing for user experience."""
        original_count = len(original_batch)
        translated_count = len(translated_batch)
        redistributed = []

        if translated_count < original_count:
            # Assign each translation to a slot as usual
            for i in range(translated_count):
                new_subtitle = srt.Subtitle(
                    index=original_batch[i].index,
                    start=original_batch[i].start,
                    end=original_batch[i].end,
                    content=translated_batch[i].content
                )
                redistributed.append(new_subtitle)
            # If there are leftover slots, extend the last non-empty subtitle's end time
            if translated_count > 0:
                last_sub = redistributed[-1]
                last_sub.end = original_batch[-1].end  # Extend to end of last slot
                logging.info(f"Extended subtitle {last_sub.index} to cover empty slots at end in batch {batch_start_index} of {filename}.")
            # Log skipped empty slots
            if translated_count < original_count:
                logging.info(f"Skipped {original_count - translated_count} empty slot(s) at end of batch {batch_start_index} in {filename}.")
        else:
            # More translations than original slots: combine as before
            translations_per_slot = translated_count / original_count
            translation_index = 0
            for i in range(original_count):
                new_subtitle = srt.Subtitle(
                    index=original_batch[i].index,
                    start=original_batch[i].start,
                    end=original_batch[i].end,
                    content=""
                )
                slot_translations = int(translations_per_slot)
                if i < (translated_count % original_count):
                    slot_translations += 1
                combined_content = []
                for j in range(slot_translations):
                    if translation_index < translated_count:
                        combined_content.append(translated_batch[translation_index].content)
                        translation_index += 1
                new_subtitle.content = " ".join(combined_content)
                redistributed.append(new_subtitle)

        # Log the specific redistribution details
        logging.info(
            f"REDISTRIBUTION DETAILS for {filename}: "
            f"Mapped {translated_count} translations across {original_count} timing slots. "
            f"Content distribution: {[len(sub.content) for sub in redistributed]}"
        )
        return redistributed

    # Update translate_file to call batch_translate_file by default
    def translate_file(self, input_filepath, output_filepath, target_lang):
        """Translate an entire SRT file using batching."""
        return self.batch_translate_file(input_filepath, output_filepath, target_lang)


def clean_srt_output(text):
    """Remove Markdown code fences (``` or ```srt) from model output if present."""
    text = text.strip()
    if text.startswith('```srt'):
        text = text[len('```srt'):].strip()
    if text.startswith('```'):
        text = text[len('```'):].strip()
    if text.endswith('```'):
        text = text[:-3].strip()
    return text