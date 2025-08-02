import logging
import re
from typing import Dict, List

from srt_core.config.settings import DNT_TERMS


class TermHandler:
    def __init__(self):
        self.dnt_terms = sorted(DNT_TERMS, key=len, reverse=True)

    def replace_dnt_terms(self, text):
        """Replace DNT terms with placeholders"""
        term_map = {}
        placeholder_count = 0

        for term in self.dnt_terms:
            pattern = r"\b{}\b".format(re.escape(term))

            def replace_term(match):
                nonlocal placeholder_count
                placeholder = f"__DNT_TERM_{placeholder_count}__"
                term_map[placeholder] = match.group(0)
                placeholder_count += 1
                return placeholder

            text = re.sub(pattern, replace_term, text)

        return text, term_map

    def restore_dnt_terms(
        self,
        text,
        term_map,
        filename,
        subtitle_number=None,
        source_lang=None,
        target_lang=None,
    ):
        """Restore DNT terms from placeholders"""
        restored_text = text

        # Only process placeholders that are actually in the text
        for placeholder, original_term in term_map.items():
            if placeholder in restored_text:
                restored_text = restored_text.replace(placeholder, original_term)
            # Silently skip placeholders that weren't used in this text
            # This is normal behavior - not all DNT terms appear in every subtitle

        return restored_text

    def get_context(self, text, term, context_words=2):
        """Get surrounding context for a term in text"""
        try:
            words = text.split()
            for i, word in enumerate(words):
                if term in word:
                    start = max(0, i - context_words)
                    end = min(len(words), i + context_words + 1)
                    return " ".join(words[start:end])
        except Exception as e:
            logging.error(f"Error getting context: {e}")
        return None

    def check_context_similarity(self, original_context, translated_context):
        """Check if contexts are similar in terms of position"""
        orig_words = original_context.split()
        trans_words = translated_context.split()

        orig_pos = None
        trans_pos = None

        for i, word in enumerate(orig_words):
            if "__DNT_TERM_" in word:
                orig_pos = i
                break

        for i, word in enumerate(trans_words):
            if "__DNT_TERM_" in word:
                trans_pos = i
                break

        if orig_pos is not None and trans_pos is not None:
            if (orig_pos == 0 and trans_pos == len(trans_words) - 1) or (
                trans_pos == 0 and orig_pos == len(orig_words) - 1
            ):
                return False

            max_allowed_shift = min(3, len(orig_words) // 2)
            position_shift = abs(
                orig_pos / len(orig_words) - trans_pos / len(trans_words)
            )

            return position_shift < (max_allowed_shift / len(orig_words))

        return False
