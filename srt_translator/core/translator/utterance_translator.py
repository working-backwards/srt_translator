"""
Utterance translation with batch processing and progressive fallback.
"""

import logging
from typing import List
from concurrent.futures import ThreadPoolExecutor
from .models import Utterance, TranslationConfig


class UtteranceTranslator:
    """Handles batch translation of utterances with progressive fallback."""
    
    def __init__(self, config: TranslationConfig, logger: logging.Logger = None):
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
    
    def translate_utterances_batch(self, utts: List[Utterance], target_lang: str, 
                                 translate_func) -> List[str]:
        """
        Quality-preserving batching. Default tries list-in/list-out call; 
        on mismatch, falls back per-utterance.
        """
        items = [u.text_src for u in utts]
        
        try:
            # Try batch translation first
            translated = translate_func(items, target_lang)
            if len(translated) == len(utts):
                return translated
        except Exception as e:
            self.logger.warning(f"Batch utterance translation failed; falling back per item: {e}")
        
        # Fallback to individual translation
        return [self._translate_utterance_fallback(u, target_lang, translate_func) for u in utts]
    
    def _translate_utterance_fallback(self, u: Utterance, target_lang: str, 
                                    translate_func) -> str:
        """Safe single-utterance call that preserves existing translator behavior."""
        try:
            # Use the provided translation function
            return translate_func(u.text_src, target_lang).strip()
        except Exception as e:
            self.logger.warning(f"Utterance fallback failed at span {u.sub_start}-{u.sub_end}: {e}")
            return u.text_src  # DEV-friendly; error policy gates catch issues later
    
    def progressive_fallback(self, utts: List[Utterance], target_lang: str, 
                           translate_func) -> List[str]:
        """Progressive fallback: try N → ceil(N/2) → ceil(N/4) → ... → 1."""
        batch_size = len(utts)
        
        while batch_size > 1:
            batch_size = max(1, (batch_size + 1) // 2)  # ceil(batch_size / 2)
            
            try:
                chunk = utts[:batch_size]
                translated = self.translate_utterances_batch(chunk, target_lang, translate_func)
                
                if len(translated) == len(chunk):
                    # Success with smaller batch, now handle remaining
                    result = translated
                    remaining = utts[batch_size:]
                    
                    for u in remaining:
                        result.append(self._translate_utterance_fallback(u, target_lang, translate_func))
                    
                    return result
            except Exception as e:
                self.logger.warning(f"Batch size {batch_size} failed: {e}")
                continue
        
        # Final fallback: single utterance translation
        return [self._translate_utterance_fallback(u, target_lang, translate_func) for u in utts]
    
    def translate_with_concurrency(self, utts: List[Utterance], target_lang: str, 
                                 translate_func, batch_size: int = 8) -> List[str]:
        """Translate utterances with optional concurrency."""
        if self.config.max_concurrency <= 1:
            # Sequential processing (default, safe)
            return self._translate_sequential(utts, target_lang, translate_func, batch_size)
        else:
            # Parallel processing for very long files
            return self._translate_parallel(utts, target_lang, translate_func, batch_size)
    
    def _translate_sequential(self, utts: List[Utterance], target_lang: str, 
                            translate_func, batch_size: int) -> List[str]:
        """Sequential batch processing."""
        translations = []
        
        for i in range(0, len(utts), batch_size):
            chunk = utts[i:i+batch_size]
            translated = self.translate_utterances_batch(chunk, target_lang, translate_func)
            
            if len(translated) != len(chunk):
                translated = self.progressive_fallback(chunk, target_lang, translate_func)
            
            translations.extend(translated)
        
        return translations
    
    def _translate_parallel(self, utts: List[Utterance], target_lang: str, 
                          translate_func, batch_size: int) -> List[str]:
        """Parallel batch processing using ThreadPoolExecutor."""
        translations = [None] * len(utts)  # Pre-allocate result list
        
        with ThreadPoolExecutor(max_workers=self.config.max_concurrency) as executor:
            batch_futures = []
            
            for i in range(0, len(utts), batch_size):
                chunk = utts[i:i+batch_size]
                future = executor.submit(self.translate_utterances_batch, chunk, target_lang, translate_func)
                batch_futures.append((i, chunk, future))
            
            for i, chunk, future in batch_futures:
                try:
                    translated = future.result()
                    
                    if len(translated) != len(chunk):
                        translated = self.progressive_fallback(chunk, target_lang, translate_func)
                    
                    # Place results in correct positions
                    for j, text in enumerate(translated):
                        translations[i + j] = text
                        
                except Exception as e:
                    self.logger.warning(f"Batch {i//batch_size + 1} failed: {e}")
                    translated = self.progressive_fallback(chunk, target_lang, translate_func)
                    
                    for j, text in enumerate(translated):
                        translations[i + j] = text
        
        return translations
