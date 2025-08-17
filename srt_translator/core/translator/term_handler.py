#!/usr/bin/env python3
"""
Term handler for the SRT Translator.
"""

import logging
import re
import unicodedata
from typing import Dict, List, Set


class TermHandler:
    """
    Handles DNT (Do Not Translate) terms by replacing them with placeholders.

    This prevents the AI from translating important terms like company names,
    technical terms, or proper nouns that should remain in the original language.
    """

    def __init__(self, dnt_terms: List[str], termbase: Dict[str, str] = None):
        # DNT terms must be provided - no fallbacks to global settings
        if dnt_terms is None:
            raise ValueError(
                "dnt_terms must be provided. TermHandler cannot fall back to global settings."
            )

        # Normalize and filter DNT terms
        self.dnt_terms = self._normalize_dnt_terms(dnt_terms)
        
        # Store termbase if provided
        self.termbase = termbase or {}
        
        # Compile tolerant regex patterns for Latin keys
        self._compile_tolerant_patterns()

    def _normalize_dnt_terms(self, dnt_terms: List[str]) -> List[str]:
        """Normalize DNT terms for consistent matching (NFKC, lowercase)"""
        normalized_terms = []
        for term in dnt_terms:
            if term and term.strip():
                normalized = unicodedata.normalize("NFKC", term.lower().strip())
                normalized_terms.append(normalized)
        
        # Sort by length (longest first) to avoid partial matches
        return sorted(normalized_terms, key=len, reverse=True)

    def _compile_tolerant_patterns(self):
        """Compile regex patterns for tolerant matching of Latin keys"""
        self.tolerant_patterns = {}
        
        for term in self.dnt_terms:
            # Skip non-Latin terms (CJK, etc.)
            if not self._is_latin_text(term):
                continue
                
            # Create patterns for space/hyphen variations and possessives
            # First escape the term, then replace spaces/hyphens with regex pattern
            escaped_term = re.escape(term)
            base_term = escaped_term.replace('\\ ', r'[\s\-]+').replace('\\-', r'[\s\-]+')
            possessive_pattern = f"{base_term}['s]?"
            
            # Compile the pattern
            try:
                self.tolerant_patterns[term] = re.compile(possessive_pattern, re.IGNORECASE)
            except re.error:
                # Fallback to exact match if pattern compilation fails
                self.tolerant_patterns[term] = re.compile(re.escape(term), re.IGNORECASE)

    def _is_latin_text(self, text: str) -> bool:
        """Check if text contains primarily Latin characters"""
        latin_chars = sum(1 for c in text if unicodedata.category(c).startswith('L'))
        return latin_chars > len(text) * 0.5

    def _enforce_dnt_precedence(self, termbase: Dict[str, str]) -> Dict[str, str]:
        """Remove termbase keys that collide with DNT terms after normalization"""
        if not termbase:
            return {}
            
        # Normalize termbase keys
        normalized_tb = {}
        for key, value in termbase.items():
            if key and value:
                normalized_key = unicodedata.normalize("NFKC", key.lower().strip())
                normalized_tb[normalized_key] = value
        
        # Remove keys that collide with DNT terms
        filtered_tb = {}
        for key, value in normalized_tb.items():
            # Check if this key collides with any DNT term
            collision = False
            for dnt_term in self.dnt_terms:
                if key == dnt_term or key in dnt_term or dnt_term in key:
                    collision = True
                    logging.debug(f"Removing termbase key '{key}' due to DNT collision with '{dnt_term}'")
                    break
            
            if not collision:
                filtered_tb[key] = value
        
        if len(filtered_tb) != len(termbase):
            logging.info(f"Filtered termbase: {len(termbase)} -> {len(filtered_tb)} (removed DNT collisions)")
        
        return filtered_tb

    def relevant_termbase(self, text: str) -> Dict[str, str]:
        """Return only termbase entries that are present in the given text"""
        if not self.termbase or not text:
            return {}
        
        # Normalize text for matching
        normalized_text = unicodedata.normalize("NFKC", text.lower())
        
        # Find relevant termbase entries
        relevant_entries = {}
        for key, value in self.termbase.items():
            if key and key.lower() in normalized_text:
                relevant_entries[key] = value
        
        logging.debug(f"Relevant termbase: {len(self.termbase)} -> {len(relevant_entries)} entries")
        return relevant_entries

    def replace_dnt_terms(self, text: str) -> tuple[str, Dict[str, str]]:
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
        processed_text = text

        # Process each DNT term (longest first to avoid partial matches)
        for term in self.dnt_terms:
            # Use tolerant patterns for Latin terms, exact match for others
            if term in self.tolerant_patterns:
                pattern = self.tolerant_patterns[term]
            else:
                # For non-Latin terms (CJK, etc.), use exact substring matching
                pattern = re.compile(re.escape(term), re.IGNORECASE)

            def replace_term(match):
                """Replace matched term with unique placeholder"""
                nonlocal placeholder_count
                placeholder = f"__DNT_TERM_{placeholder_count}__"
                term_map[placeholder] = match.group(0)  # Store original term
                placeholder_count += 1
                return placeholder

            # Replace all occurrences of this term with placeholders
            processed_text = pattern.sub(replace_term, processed_text)

        return processed_text, term_map

    def get_filtered_termbase(self) -> Dict[str, str]:
        """Get termbase with DNT precedence enforced (collisions removed)"""
        return self._enforce_dnt_precedence(self.termbase)

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
            position_shift = abs(orig_pos / len(orig_words) - trans_pos / len(trans_words))

            # Return True if position shift is within acceptable range
            return position_shift < (max_allowed_shift / len(orig_words))

        return False
