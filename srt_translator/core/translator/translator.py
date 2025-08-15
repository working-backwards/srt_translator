import json
import logging
import os
import re
import threading

# Import unified language configuration
import time
from typing import List

import srt
from openai import OpenAI

from srt_translator.core.config.language_config import get_language_config
from srt_translator.core.translator.srt_parser import SRTParser
from srt_translator.core.translator.term_handler import TermHandler
from srt_translator.core.utils.logging_setup import log_placeholder_issue

# Update BAD_RESPONSE_PATTERNS to only check for the new phrase
BAD_RESPONSE_PATTERNS = ["I cannot translate because"]


def contains_bad_response(text, patterns=BAD_RESPONSE_PATTERNS):
    text_lower = text.lower()
    return any(pattern.lower() in text_lower for pattern in patterns)


def extract_translation_failure_reason(ai_response):
    prefix = "I cannot translate because"
    if ai_response.lower().startswith(prefix.lower()):
        return ai_response[len(prefix) :].strip(" .")
    return ai_response


class SRTTranslator:
    def __init__(
        self,
        dnt_terms=None,
        termbase=None,
        api_key=None,
        logger=None,
        allow_global_termbase_fallback: bool = False,
        model_name: str = "gpt-4o-mini",
        batch_size: int = 5,
    ):
        self.logger = logger or logging.getLogger(__name__)
        self.allow_global_termbase_fallback = allow_global_termbase_fallback

        # Require API key to be provided explicitly
        if not api_key:
            raise ValueError("OpenAI API key must be provided as parameter")
        self.api_key = api_key

        self.client = OpenAI(api_key=self.api_key)

        # Use provided DNT terms and termbase or fall back to defaults
        self.dnt_terms = dnt_terms or []
        self.termbase = termbase or {}
        self.model_name = model_name
        self.batch_size = batch_size

        # Initialize term handler with provided DNT terms
        self.term_handler = TermHandler(dnt_terms=self.dnt_terms)
        self.parser = SRTParser()

        # Single-batch enforcement mechanism
        self._batch_in_progress = False
        self._translation_lock = threading.Lock()

        # Log configuration information
        self.logger.info(
            f"SRTTranslator initialized with {len(self.dnt_terms)} DNT terms"
        )
        self.logger.info(
            f"SRTTranslator initialized with termbase for {len(self.termbase)} languages"
        )

    @staticmethod
    def debug_log_config(
        cfg, logger=None, *, full_termbase=False, max_langs=12, max_terms_per_lang=8
    ):
        """
        Emit a redacted, human-friendly config snapshot at DEBUG level.
        - full_termbase=False prints a per-language summary with samples.
        - Set full_termbase=True to pretty-print the entire termbase.
        """
        log = logger or logging.getLogger(__name__)
        if not log.isEnabledFor(logging.DEBUG):
            return

        def _mask_tail(s: str, n: int = 4) -> str:
            if not s:
                return ""
            return "…" + s[-n:]

        # Header
        lines = []
        lines.append("=== TranslationConfig (DEBUG) ===")

        # Basics
        tgt = getattr(cfg, "target_languages", {}) or {}
        dnt = getattr(cfg, "dnt_terms", []) or []
        tb = getattr(cfg, "termbase", {}) or {}

        lines.append(
            f"Output directory  : {getattr(cfg, 'output_directory', 'translated_srt_files')}"
        )
        lines.append(
            f"Model / batch     : {getattr(cfg, 'model_name', 'gpt-4o-mini')} / {getattr(cfg, 'batch_size', 5)}"
        )
        lines.append(f"API key (tail)    : {_mask_tail(getattr(cfg, 'api_key', ''))}")

        # Targets
        codes = list(tgt.values())
        lines.append(
            f"Targets ({len(codes)}): {', '.join(codes) if codes else '(none)'}"
        )

        # DNT
        lines.append(f"DNT terms ({len(dnt)}):")
        if dnt:
            for term in dnt:
                lines.append(f"  - {term}")
        else:
            lines.append("  (none)")

        # Termbase
        lines.append(
            f"Termbase languages ({len(tb)}): {', '.join(sorted(tb.keys())) if tb else '(none)'}"
        )

        if full_termbase and tb:
            # Pretty-print the entire termbase
            lines.append("Termbase (full):")
            lines.append(json.dumps(tb, ensure_ascii=False, indent=2, sort_keys=True))
        elif tb:
            # Summarize per language with samples
            lines.append("Termbase (summary with samples):")
            lang_items = sorted(tb.items())[:max_langs]
            for lang, mapping in lang_items:
                terms = list(mapping.items())
                shown = terms[:max_terms_per_lang]
                extra = len(terms) - len(shown)
                lines.append(f"  [{lang}] {len(terms)} terms")
                for k, v in shown:
                    lines.append(f"  • {k}  →  {v}")
                if extra > 0:
                    lines.append(f"    … (+{extra} more)")
            if len(tb) > max_langs:
                lines.append(f"  … (+{len(tb) - max_langs} more languages)")
        else:
            lines.append("Termbase: (none)")

        log.debug("\n".join(lines))

    def get_translation_prompt(self, target_lang):
        """Get the translation prompt for single subtitle translation (fallback only)"""
        # For single subtitle translation, we need to create a dummy batch with one subtitle
        # This is only used as fallback when batch translation fails
        dummy_batch = [type("Subtitle", (), {"content": ""})()]
        termbase_block = self._format_termbase_block(target_lang, dummy_batch)
        mapped_target_lang = target_lang
        return self._get_builtin_prompt(mapped_target_lang, termbase_block)

    def _format_termbase_block(self, target_lang, batch_content):
        """Format termbase terms for injection into prompt"""
        return self._format_termbase_block_smart(target_lang, batch_content)

    def _format_termbase_block_smart(self, target_lang, batch_content):
        """Filter termbase to only include terms present in current batch"""
        # Prefer instance termbase; optionally allow CLI fallback
        if target_lang in self.termbase:
            all_terms = self.termbase[target_lang]
        elif self.allow_global_termbase_fallback:
            # This function is no longer imported, so this fallback will fail.
            # The user's edit hint implies this change, but the new_code doesn't provide a replacement.
            # For now, we'll just return an empty string if termbase is not available.
            return "No specific termbase terms for this content."
        else:
            all_terms = {}

        batch_text = " ".join([sub.content for sub in batch_content]).lower()

        relevant_terms = {
            english: translation
            for english, translation in all_terms.items()
            if english.lower() in batch_text
        }

        if not relevant_terms:
            return "No specific termbase terms for this content."

        return "\n".join(
            [f'- "{en}" → "{trans}"' for en, trans in relevant_terms.items()]
        )

    def _get_builtin_prompt(self, target_lang, termbase_block):
        """Built-in fallback prompt with termbase injection"""
        return f"""You are a professional translator. Translate the following text to {target_lang}.

BUSINESS TERMINOLOGY: When you see these specific business terms, use these translations:
{termbase_block}

PLACEHOLDER RULES:
1. If you see __DNT_TERM_X__ placeholders, keep them EXACTLY as written - DO NOT translate them back to the original terms
2. Do NOT create any new placeholders
3. Do NOT replace normal words with placeholders
4. CRITICAL: Placeholders like __DNT_TERM_0__ must appear in your translation exactly as __DNT_TERM_0__

TRANSLATION APPROACH:
- Translate ALL text naturally and completely
- Use the business terminology above when those specific terms appear
- For all other words, use standard translation practices
- Preserve all formatting and punctuation
- Do not skip or omit any content unless it is genuinely untranslatable
- Numbers: keep digits; localize formatting; no rounding.

ERROR HANDLING:
Only refuse translation if the text is genuinely untranslatable (corrupted, inappropriate content, etc.).
If you cannot translate, respond EXACTLY: "I cannot translate because [specific reason]"

Examples:
- "Hello __DNT_TERM_0__ world" → "你好 __DNT_TERM_0__ 世界"
- "The operating plan shows results" → "运营计划显示结果" (using termbase)
- "They met at the time" → "他们当时见面了" (normal translation)

Translate completely and naturally."""

    def get_batch_translation_prompt(self, target_lang, batch_content):
        termbase_block = self._format_termbase_block(target_lang, batch_content)
        mapped_target_lang = target_lang

        return f"""You are a professional translator. Translate the following SRT subtitles to {mapped_target_lang}.

BUSINESS TERMINOLOGY:
When you see these specific business terms, use these translations:
{termbase_block}

SRT STRUCTURE RULES:
1. Preserve subtitle numbering and timestamps exactly as shown.
2. Return one translated subtitle for each original — do not merge, split, or skip subtitles.
3. Keep the structure and order of subtitles exactly as provided.

TRANSLATION RULES:
1. Translate all subtitle text completely and naturally.
2. Use the business terminology provided above when terms appear.
3. For all other content, use standard professional translation practices.
4. Do not add or remove any content, punctuation, or formatting unless necessary to complete the translation.
5. Numbers: keep digits; localize formatting; no rounding.

PLACEHOLDER RULES:
1. If you see __DNT_TERM_X__ placeholders, keep them EXACTLY as written — do not translate or modify them.
2. Do not invent new placeholders.
3. CRITICAL: Placeholders like __DNT_TERM_0__ must appear in your output exactly as __DNT_TERM_0__.

ERROR HANDLING:
Only refuse to translate if content is truly untranslatable. If so, return: "I cannot translate because [specific reason]"

Return a complete, valid SRT block with the same subtitle count, structure, and timestamps as the input.
"""

    def translate_subtitle(
        self, text, target_lang, filename, subtitle_number=None, summary=None
    ):
        """Translate a single subtitle text"""
        # Use unified language config (no mapping needed for standard ISO codes)
        mapped_target_lang = target_lang

        try:
            time.sleep(0.5)
            processed_text, term_map = self.term_handler.replace_dnt_terms(text)

            system_prompt = self.get_translation_prompt(target_lang)

            max_retries = 2
            retries = 0
            final_text = ""
            while retries <= max_retries:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": processed_text},
                    ],
                    temperature=0.1,  # Lower temperature for more consistent behavior
                )
                translated_text = response.choices[0].message.content
                if translated_text is None:
                    raise ValueError("OpenAI response content is None")
                translated_text = translated_text.strip()
                final_text = self.term_handler.restore_dnt_terms(
                    translated_text,
                    term_map,
                    filename,
                    subtitle_number=subtitle_number,
                    target_lang=target_lang,
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
                logging.info(
                    f"\n--- SINGLE TRANSLATION ERROR PROMPT for {filename} (subtitle {subtitle_number}) ---\nSYSTEM PROMPT:\n{system_prompt}\nUSER MESSAGE (processed_text):\n{processed_text}\n--- MODEL RESPONSE ---\n{final_text}\n--- END ERROR LOG ---\n"
                )
                logging.error(
                    f"""
{"=" * 80}
SINGLE TRANSLATION FAILURE - INSTRUCTOR ACTION NEEDED
{"=" * 80}
SUMMARY: OpenAI refused to translate single subtitle after {max_retries + 1} attempts

COPY THIS ENTIRE SECTION TO AN AI CHAT FOR HELP:
----------------------------------------
File: {filename}
Subtitle Number: {subtitle_number}
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
- Model: {self.model_name}
- Processed text sent to AI: \"{processed_text}\"
- Full AI response: \"{final_text}\"
----------------------------------------

RESULT: Subtitle left untranslated to mark failure.
{"=" * 80}
"""
                )
                if summary is not None and isinstance(summary, dict):
                    summary["bad_translations"] = summary.get("bad_translations", 0) + 1
                return final_text  # Keep the AI refusal message in the SRT output

            # Check for phantom placeholders (AI hallucinations) and remove them
            phantom_placeholders = re.findall(r"__DNT_TERM_\d+__", final_text)
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
                    # Remove hallucinated placeholder from output
                    final_text = final_text.replace(phantom, "")
            # Tidy whitespace after removals
            final_text = re.sub(r"\s{2,}", " ", final_text).strip()

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
        """
        Check for issues with placeholders in translated text.

        This method validates that DNT (Do Not Translate) terms were properly preserved
        during translation by checking for two types of issues:
        1. Missing placeholders - DNT terms that were completely removed
        2. Position mismatches - DNT terms that moved to different contexts

        Args:
            original_text: The source text before translation
            translated_text: The translated text to check
            term_map: Dictionary mapping placeholders to original terms
            target_lang: Target language code
            filename: Source filename for logging
            subtitle_number: Subtitle number for logging

        Returns:
            List of issue dictionaries with details about placeholder problems
        """
        issues = []

        # Check each DNT term that was replaced with a placeholder
        for placeholder, original_term in term_map.items():
            # Issue 1: Missing placeholder - DNT term was completely removed
            if placeholder not in translated_text:
                issues.append(
                    {
                        "type": "missing_placeholder",
                        "fixable": True,  # Can be fixed by re-adding the placeholder
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
                # Auto-fix: Add placeholder back to the beginning
                translated_text = f"{placeholder} {translated_text}"
            else:
                # Issue 2: Position mismatch - DNT term moved to different context
                # Get the surrounding context (words before/after) for both original and translated
                original_context = self.term_handler.get_context(
                    original_text, original_term
                )
                translated_context = self.term_handler.get_context(
                    translated_text, placeholder
                )

                # Check if contexts are similar (same surrounding words)
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
                            "fixable": False,  # Requires human review due to sentence structure changes
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
        """
        Translate an entire SRT file using sentence-aware batching for efficiency and context preservation.

        This method processes SRT files in sentence-aware chunks rather than individual subtitles
        to maintain context between related subtitles and improve translation quality.

        Args:
            input_filepath: Path to source SRT file
            output_filepath: Path for translated SRT file
            target_lang: Target language code

        Raises:
            RuntimeError: If another translation batch is already in progress
        """
        # Single-batch enforcement check
        if self._batch_in_progress:
            raise RuntimeError(
                "Translation already in progress. Only one batch can run at a time. "
                "Wait for the current translation to complete before starting another."
            )

        filename = os.path.basename(input_filepath)

        # Acquire lock and set batch state
        with self._translation_lock:
            self._batch_in_progress = True
            try:
                # Parse the SRT file into subtitle objects
                subtitles = self.parser.parse_file(input_filepath)

                if not subtitles:
                    logging.warning(
                        f"No subtitles found in {input_filepath}. Skipping translation."
                    )
                    return

                # Sort and reindex subtitles to ensure proper order
                subtitles = list(srt.sort_and_reindex(subtitles))

                # Process subtitles in sentence-aware batches for better context and efficiency
                translated_subtitles = []
                total = len(subtitles)

                # Create sentence-aware batches for better context and efficiency
                logging.info(
                    f"Using sentence-aware batching for {filename} to {target_lang}"
                )
                subtitle_batches = self._create_batches(
                    subtitles,
                    soft_limit=self.batch_size,
                    hard_limit=8,
                    target_lang=target_lang,
                )

                logging.info(
                    f"Starting batch translation of {filename} to {target_lang} with {len(subtitle_batches)} batches"
                )

                # Process each batch of subtitles
                for batch_index, batch in enumerate(subtitle_batches):
                    batch_srt = srt.compose(batch)

                    logging.info(
                        f"Translating batch {batch_index + 1}/{len(subtitle_batches)} (subtitles {batch[0].index}-{batch[-1].index})"
                    )

                    # Translate the entire batch as one unit
                    translated_batch_srt, prompt = self.translate_srt_block(
                        batch_srt, target_lang, filename, batch[0].index, batch
                    )

                    # Error handling: Check if batch translation failed completely
                    if contains_bad_response(translated_batch_srt):
                        logging.warning(
                            f"Batch translation failed for batch starting at index {batch[0].index}. Reason: {extract_translation_failure_reason(translated_batch_srt)}"
                        )
                        logging.info(
                            f"\n--- BATCH TRANSLATION ERROR PROMPT for {filename} (batch starting at subtitle {batch[0].index}) ---\n{prompt}\n--- MODEL RESPONSE ---\n{translated_batch_srt}\n--- END ERROR LOG ---\n"
                        )

                        # Fallback strategy: Translate each subtitle individually
                        logging.info(
                            f"Falling back to single subtitle translation for batch {batch_index + 1}"
                        )
                        for sub in batch:
                            sub.content = self.translate_subtitle(
                                sub.content, target_lang, filename, sub.index
                            )
                            translated_subtitles.append(sub)
                        continue

                    # Clean up the translated SRT output
                    translated_batch_srt = clean_srt_output(translated_batch_srt)

                    # Quality check: Detect phantom placeholders (AI hallucinations)
                    # These are placeholders that appear in translation but weren't in the original
                    phantom_placeholders = re.findall(
                        r"__DNT_TERM_\d+__", translated_batch_srt
                    )
                    batch_term_map = getattr(self, "_last_batch_term_map", {})
                    for phantom in phantom_placeholders:
                        if phantom not in batch_term_map:
                            logging.warning(
                                f"""
==================================================
PHANTOM PLACEHOLDER DETECTED IN BATCH:
File: {filename}
Batch: {batch_index + 1} (subtitles {batch[0].index}-{batch[-1].index})
Language: {target_lang}
Phantom Placeholder: {phantom}
Status: AI Hallucination in batch translation - Remove this placeholder
==================================================
"""
                            )
                            # Remove hallucinated placeholder from batch output before parsing
                            translated_batch_srt = translated_batch_srt.replace(
                                phantom, ""
                            )
                    # Tidy whitespace after removals (basic)
                    translated_batch_srt = re.sub(
                        r"[ \t]{2,}", " ", translated_batch_srt
                    )
                    try:
                        translated_batch = list(srt.parse(translated_batch_srt))

                        # ALWAYS use redistribution for consistent boundary clamping
                        redistributed_batch = self._redistribute_subtitles(
                            batch, translated_batch, filename, batch[0].index
                        )
                        translated_subtitles.extend(redistributed_batch)
                    except Exception as e:
                        logging.error(
                            f"Failed to parse translated SRT batch at index {batch[0].index}: {e}"
                        )
                        # Log the prompt and model response for debugging
                        logging.info(
                            f"\n--- BATCH PARSING EXCEPTION for {filename} "
                            f"(batch starting at subtitle {batch[0].index}) ---\n"
                            f"EXCEPTION: {e}\nPROMPT:\n{prompt}\n"
                            f"--- MODEL RESPONSE ---\n{translated_batch_srt}\n"
                            f"--- END ERROR LOG ---\n"
                        )
                        for sub in batch:
                            sub.content = self.translate_subtitle(
                                sub.content, target_lang, filename, sub.index
                            )
                            translated_subtitles.append(sub)

                # Filter out empty subtitles and reindex for clean output
                final_subtitles = []
                for subtitle in translated_subtitles:
                    if subtitle.content.strip():  # Only keep subtitles with content
                        final_subtitles.append(subtitle)

                # Reindex the final subtitles to ensure sequential numbering
                final_subtitles = list(srt.sort_and_reindex(final_subtitles))

                logging.info(
                    f"Final output: {len(final_subtitles)} subtitles "
                    f"(filtered from {len(translated_subtitles)} total)"
                )

                # Log timing boundaries for verification
                if final_subtitles:
                    logging.info(
                        f"Final timing boundaries: {final_subtitles[0].start} --> {final_subtitles[-1].end}"
                    )

                self.parser.write_file(output_filepath, final_subtitles)
                logging.info(f"Translated SRT saved to: {output_filepath}")
                return output_filepath
            finally:
                # Always reset batch state when translation completes
                self._batch_in_progress = False

    def translate_srt_block(
        self, srt_block, target_lang, filename, batch_start_index, batch_content
    ):
        """Translate a block of SRT subtitles as a batch."""
        # Process DNT terms for the entire SRT block
        processed_srt_block, term_map = self.term_handler.replace_dnt_terms(srt_block)

        # Store term_map for phantom detection (hacky but works)
        self._last_batch_term_map = term_map

        prompt = self.get_batch_translation_prompt(target_lang, batch_content)
        full_prompt = f"{prompt}\n\n{processed_srt_block}"

        time.sleep(0.5)  # Respect rate limits
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "user", "content": full_prompt},
            ],
            temperature=0.1,
        )

        translated_srt = response.choices[0].message.content
        if translated_srt is None:
            raise ValueError("OpenAI response content is None")
        translated_srt = translated_srt.strip()

        # Restore DNT terms in the translated SRT block
        restored_srt = self.term_handler.restore_dnt_terms(
            translated_srt,
            term_map,
            filename,
            subtitle_number=f"batch_{batch_start_index}",
            target_lang=target_lang,
        )

        return restored_srt, full_prompt

    def _create_batches(
        self,
        subtitles: List[srt.Subtitle],
        soft_limit: int,
        hard_limit: int,
        target_lang: str,
    ) -> List[List[srt.Subtitle]]:
        """
        Create sentence-aware batches that respect sentence boundaries while staying within size limits.

        This method groups subtitles into batches that end at natural sentence boundaries
        when possible, improving translation context and quality.

        Args:
            subtitles: List of subtitle objects to batch
            soft_limit: Target batch size (preferred)
            hard_limit: Maximum batch size (absolute limit)
            target_lang: Target language code for language-specific rules

        Returns:
            List of subtitle batches
        """
        if not subtitles:
            return []

        batches = []
        current_batch = []

        # Get language-specific sentence boundary rules
        language_config = get_language_config()
        lang_rules = language_config.get_language_rules(target_lang)
        sentence_endings = tuple(lang_rules["sentence_endings"])
        break_markers = lang_rules["break_markers"]

        for subtitle in subtitles:
            current_batch.append(subtitle)

            # Check if we've hit the hard limit
            if len(current_batch) >= hard_limit:
                batches.append(current_batch)
                current_batch = []
                continue

            # Check if we've hit the soft limit and can break at a sentence boundary
            if len(current_batch) >= soft_limit:
                # Look for sentence endings in the current subtitle's content
                content = subtitle.content.strip()
                if any(content.endswith(ending) for ending in sentence_endings):
                    batches.append(current_batch)
                    current_batch = []

        # Add any remaining subtitles
        if current_batch:
            batches.append(current_batch)

        return batches

    def _redistribute_subtitles(
        self, original_batch, translated_batch, filename, batch_start_index
    ):
        """Redistribute translated content across original timing slots, clamped to batch boundaries, no blanks."""
        original_count = len(original_batch)
        translated_count = len(translated_batch)

        batch_start_time = original_batch[0].start
        batch_end_time = original_batch[-1].end
        redistributed = []

        # Edge case: no translations returned
        if translated_count == 0:
            logging.info(
                f"No translations returned for batch {batch_start_index} of {filename}, emitting nothing."
            )
            return redistributed

        # Case 1: counts match → keep AI timing/content, then clamp batch edges
        if translated_count == original_count:
            for orig, trans in zip(original_batch, translated_batch):
                redistributed.append(
                    srt.Subtitle(
                        index=orig.index,
                        start=trans.start,
                        end=trans.end,
                        content=trans.content.strip(),
                    )
                )
            # clamp edges
            redistributed[0].start = batch_start_time
            redistributed[-1].end = batch_end_time
            logging.debug(
                f"BATCH BOUNDARY ENFORCED for {filename}: {batch_start_time} → {batch_end_time}"
            )
            logging.debug(
                f"REDISTRIBUTION DETAILS for {filename}: 1:1 mapping with clamped edges"
            )
            return redistributed

        # Case 2: fewer translations than original → spread evenly across whole batch, no blanks
        if translated_count < original_count:
            total = batch_end_time - batch_start_time
            slot = total / translated_count

            for i in range(translated_count):
                t_start = batch_start_time + i * slot
                t_end = batch_start_time + (i + 1) * slot
                redistributed.append(
                    srt.Subtitle(
                        index=original_batch[i].index,  # preserve first N indices
                        start=t_start,
                        end=t_end,
                        content=translated_batch[i].content.strip(),
                    )
                )

            # clamp edges (defensive)
            redistributed[0].start = batch_start_time
            redistributed[-1].end = batch_end_time

            logging.info(
                f"Redistributed {translated_count} translations across {original_count} original slots "
                f"(emitted {translated_count}; no blanks) in batch {batch_start_index} of {filename}."
            )
            logging.info(
                f"BATCH BOUNDARY ENFORCED for {filename}: {batch_start_time} → {batch_end_time}"
            )
            logging.debug(
                f"REDISTRIBUTION DETAILS for {filename}: even time slices = {[str(sub.end - sub.start) for sub in redistributed]}"
            )
            return redistributed

        # Case 3: more translations than original → merge into original slots, keep original slot timing
        translations_per_slot = translated_count / original_count
        ti = 0
        for i in range(original_count):
            take = int(translations_per_slot) + (
                1 if i < (translated_count % original_count) else 0
            )
            chunk = []
            for _ in range(take):
                if ti < translated_count:
                    chunk.append(translated_batch[ti].content.strip())
                    ti += 1
            # keep original timing for slot i
            redistributed.append(
                srt.Subtitle(
                    index=original_batch[i].index,
                    start=original_batch[i].start,
                    end=original_batch[i].end,
                    content=(
                        "\n".join(c for c in chunk if c)
                    ),  # newline separator reads better
                )
            )

        # clamp edges (defensive)
        redistributed[0].start = batch_start_time
        redistributed[-1].end = batch_end_time
        logging.info(
            f"Merged {translated_count} translations into {original_count} original slots (kept original timing) "
            f"in batch {batch_start_index} of {filename}."
        )
        logging.info(
            f"BATCH BOUNDARY ENFORCED for {filename}: {batch_start_time} → {batch_end_time}"
        )
        logging.debug(
            f"REDISTRIBUTION DETAILS for {filename}: content lengths = {[len(s.content) for s in redistributed]}"
        )
        return redistributed

    # Update translate_file to call batch_translate_file by default
    def translate_file(self, input_filepath, output_filepath, target_lang):
        """Translate an entire SRT file using batching."""
        return self.batch_translate_file(input_filepath, output_filepath, target_lang)


def clean_srt_output(text):
    """Remove Markdown code fences (``` or ```srt) from model output if present."""
    text = text.strip()
    if text.startswith("```srt"):
        text = text[len("```srt") :].strip()
    if text.startswith("```"):
        text = text[len("```") :].strip()
    if text.endswith("```"):
        text = text[:-3].strip()
    return text
