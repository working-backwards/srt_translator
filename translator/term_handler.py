# translator/term_handler.py

import re
import logging
from ..config.settings import EXCLUDED_TERMS

class TermHandler:
    def __init__(self):
        self.excluded_terms = sorted(EXCLUDED_TERMS, key=len, reverse=True)

    def replace_excluded_terms(self, text):
        """Replace excluded terms with placeholders"""
        term_map = {}
        placeholder_count = 0
        
        for term in self.excluded_terms:
            pattern = r'\b{}\b'.format(re.escape(term))
            
            def replace_term(match):
                nonlocal placeholder_count
                placeholder = f"__EXCLUDED_TERM_{placeholder_count}__"
                term_map[placeholder] = match.group(0)
                placeholder_count += 1
                return placeholder
            
            text = re.sub(pattern, replace_term, text)
        
        return text, term_map

    def restore_excluded_terms(self, text, term_map, filename):
        """Restore excluded terms from placeholders"""
        restored_text = text
        for placeholder, original_term in term_map.items():
            if placeholder not in restored_text:
                logging.error(
                    f"\nTERM RESTORATION FAILED:"
                    f"\nFile: {filename}"
                    f"\nPlaceholder: {placeholder}"
                    f"\nOriginal Term: {original_term}"
                    f"\nText: {text}"
                    f"\n{'='*50}"
                )
            restored_text = restored_text.replace(placeholder, original_term)
        return restored_text

    def get_context(self, text, term, context_words=2):
        """Get surrounding context for a term in text"""
        try:
            words = text.split()
            for i, word in enumerate(words):
                if term in word:
                    start = max(0, i - context_words)
                    end = min(len(words), i + context_words + 1)
                    return ' '.join(words[start:end])
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
            if '__EXCLUDED_TERM_' in word:
                orig_pos = i
                break
                
        for i, word in enumerate(trans_words):
            if '__EXCLUDED_TERM_' in word:
                trans_pos = i
                break

        if orig_pos is not None and trans_pos is not None:
            if (orig_pos == 0 and trans_pos == len(trans_words) - 1) or \
               (trans_pos == 0 and orig_pos == len(orig_words) - 1):
                return False
                
            max_allowed_shift = min(3, len(orig_words) // 2)
            position_shift = abs(orig_pos / len(orig_words) - trans_pos / len(trans_words))
            
            return position_shift < (max_allowed_shift / len(orig_words))
            
        return False