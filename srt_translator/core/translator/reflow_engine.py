"""
Reflow engine for distributing translated utterance text into original subtitle windows.
"""

import re
from typing import List
from .models import Utterance
from .language_config import LanguageConfig


class ReflowEngine:
    """Splits translated utterances into chunks that fit each subtitle's reading capacity."""
    
    def __init__(self, language_config: LanguageConfig):
        self.language_config = language_config
    
    def reflow_to_subtitles(self, u: Utterance, tgt_text: str, lang: str) -> List[str]:
        """Split the translated utterance into chunks that fit each subtitle's reading capacity."""
        soft, hard = self.language_config.get_cps_caps(lang)
        budgets = [soft * max(0.001, (s.end_ms - s.start_ms)/1000.0) for s in u.subtitles]
        hard_caps = [hard * max(0.001, (s.end_ms - s.start_ms)/1000.0) for s in u.subtitles]
        
        # Simple character scanner tokenization (ship default)
        tokens = self._tokenize_for_reflow_simple(tgt_text, lang)
        
        chunks: List[str] = []
        buf: List[str] = []
        j = 0
        
        def flush():
            """Flush current buffer to chunks."""
            nonlocal buf
            chunk = "".join(buf).strip()
            chunks.append(chunk)
            buf = []
        
        for t in tokens:
            if j >= len(budgets):
                break
            
            nxt = "".join(buf + [t])
            if len(nxt) <= budgets[j] or len(nxt) <= hard_caps[j]:
                buf.append(t)
            else:
                flush()
                j += 1
                if j >= len(budgets):
                    break
                buf = [t] if len(t) <= hard_caps[j] else []
        
        if buf and j < len(budgets):
            flush()
        
        # If we produced fewer chunks than subtitles in this utterance, repeat the last chunk to fill remaining
        while len(chunks) < len(u.subtitles):
            chunks.append(chunks[-1] if chunks else "")
        
        # If more, trim (rare: over-aggressive splits)
        if len(chunks) > len(u.subtitles):
            chunks = chunks[:len(u.subtitles)]
        
        return chunks
    
    def _tokenize_for_reflow_simple(self, text: str, lang: str) -> List[str]:
        """
        Simple, robust character scanner (ship default):
          - Group consecutive ASCII letters/digits (allow -_/.: inside for S-Team, API, 3.5, PRFAQ)
          - Treat each CJK char as a token
          - Emit punctuation/whitespace as separate tokens
          - Never split tokens that look like numbers/units/DNT terms
        """
        tokens = []
        i = 0
        
        while i < len(text):
            # Group consecutive ASCII letters/digits (allow -_/.: inside)
            if text[i].isalnum() or text[i] in '-_/.:':
                start = i
                while i < len(text) and (text[i].isalnum() or text[i] in '-_/.:'):
                    i += 1
                tokens.append(text[start:i])
                continue
            
            # Single CJK char
            if re.match(r"[\u4E00-\u9FFF]", text[i]):
                tokens.append(text[i])
                i += 1
                continue
            
            # Whitespace or punctuation
            tokens.append(text[i])
            i += 1
        
        return tokens
    
    def _tokenize_for_reflow_regex(self, text: str, lang: str) -> List[str]:
        """
        Regex-based tokenizer (dev-only experiment flag).
        More complex but potentially more accurate for edge cases.
        """
        # Fallback: split into reasonable chunks while preserving punctuation
        parts: List[str] = []
        i = 0
        
        while i < len(text):
            m = re.match(r"[A-Za-z0-9]+", text[i:])
            if m:
                parts.append(m.group(0))
                i += len(m.group(0))
                continue
            
            # single CJK char
            if re.match(r"[\u4E00-\u9FFF]", text[i]):
                parts.append(text[i])
                i += 1
                continue
            
            # whitespace or punctuation
            parts.append(text[i])
            i += 1
        
        return parts
