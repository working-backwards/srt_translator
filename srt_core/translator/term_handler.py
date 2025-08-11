#!/usr/bin/env python3
"""
Term handler for the SRT Translator.
"""

import logging
import re

from srt_core.config.settings import DNT_TERMS


class TermHandler:
    """
    Handles DNT (Do Not Translate) terms by replacing them with placeholders.

    This prevents the AI from translating important terms like company names,
    technical terms, or proper nouns that should remain in the original language.
    """

    def __init__(self, dnt_terms=None):
        # Use provided DNT terms or fall back to environment variable for backward compatibility
        if dnt_terms is not None:
            self.dnt_terms = sorted(dnt_terms, key=len, reverse=True)
        else:
            # Fall back to environment variable for backward compatibility
            self.dnt_terms = sorted(DNT_TERMS, key=len, reverse=True)

    def replace_dnt_terms(self, text):
        """
        Replace DNT terms with numbered placeholders before translation.

        This method scans the text for DNT terms and replaces them with unique
        placeholders (e.g., "__DNT_TERM_0__", "__DNT_TERM_1__") to prevent
        the AI from translating them.

        Args:
            text: The text to process for DNT terms

        Returns:
            tuple: (processed_text, term_map) where term_map maps placeholders to original terms
        """
        term_map = {}
        placeholder_count = 0

        # Process each DNT term (longest first to avoid partial matches)
        for term in self.dnt_terms:
            # Create regex pattern with word boundaries to match whole words only
            pattern = r"\b{}\b".format(re.escape(term))

            def replace_term(match):
                """Replace matched term with unique placeholder"""
                nonlocal placeholder_count
                placeholder = f"__DNT_TERM_{placeholder_count}__"
                term_map[placeholder] = match.group(0)  # Store original term
                placeholder_count += 1
                return placeholder

            # Replace all occurrences of this term with placeholders
            text = re.sub(pattern, replace_term, text)

        return text, term_map

    def restore_dnt_terms(
        self,
        text,
        term_map,
        filename,
        subtitle_number=None,
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
        """
        Get surrounding context for a term in text.

        This method extracts the words around a DNT term to help determine
        if the term's position changed significantly during translation.

        Args:
            text: The text to search in
            term: The term to find context for
            context_words: Number of words to include before and after the term

        Returns:
            String containing the context words, or None if term not found
        """
        try:
            words = text.split()
            for i, word in enumerate(words):
                if term in word:
                    # Extract words before and after the term
                    start = max(0, i - context_words)
                    end = min(len(words), i + context_words + 1)
                    return " ".join(words[start:end])
        except Exception as e:
            logging.error(f"Error getting context: {e}")
        return None

    def check_context_similarity(self, original_context, translated_context):
        """
        Check if the position of a DNT term is similar in original vs translated text.

        This method helps detect if a DNT term moved to a completely different
        position during translation (e.g., from beginning to end of sentence),
        which might indicate a translation error.

        Args:
            original_context: Context words around the term in original text
            translated_context: Context words around the term in translated text

        Returns:
            True if positions are similar, False if position changed significantly
        """
        orig_words = original_context.split()
        trans_words = translated_context.split()

        # Find the position of the DNT term in both contexts
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
            # Check for extreme position changes (beginning to end or vice versa)
            if (orig_pos == 0 and trans_pos == len(trans_words) - 1) or (
                trans_pos == 0 and orig_pos == len(orig_words) - 1
            ):
                return False

            # Calculate relative position shift (as percentage of sentence length)
            max_allowed_shift = min(3, len(orig_words) // 2)
            position_shift = abs(
                orig_pos / len(orig_words) - trans_pos / len(trans_words)
            )

            # Return True if position shift is within acceptable range
            return position_shift < (max_allowed_shift / len(orig_words))

        return False
