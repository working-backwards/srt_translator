"""
Utterance segmentation logic for grouping subtitles into sentence-level chunks.
"""

import re
from typing import List
from .models import Subtitle, Utterance
from .language_config import LanguageConfig


class UtteranceSegmenter:
    """Groups adjacent subtitles that form one sentence/thought (utterance)."""
    
    def __init__(self, language_config: LanguageConfig):
        self.language_config = language_config
        self.max_span = 3  # cap: ≤ 3 subtitles per utterance
        self.gap_ms = 350  # default gap threshold; bounded 250-500 ms
    
    def segment_utterances(self, subs: List[Subtitle], lang_code: str) -> List[Utterance]:
        """Group adjacent subtitles that form one sentence/thought (utterance)."""
        if not subs:
            return []
        
        ends = self.language_config.get_sentence_endings(lang_code)
        max_s = self.language_config.get_max_utterance_s(lang_code)
        
        def ends_with_term_punct(txt: str) -> bool:
            """Check if text ends with terminal punctuation."""
            t = txt.strip()
            return bool(t) and (t[-1] in ends)
        
        utterances: List[Utterance] = []
        i = 0
        
        while i < len(subs):
            j = i
            dur = 0
            
            while j < len(subs):
                cur = subs[j]
                dur = (cur.end_ms - subs[i].start_ms) / 1000.0
                
                # Stop if terminal punctuation at end of current subtitle
                stop_here = ends_with_term_punct(cur.text)
                
                # Or duration would exceed max
                over_dur = dur > max_s
                
                # Or we've spanned too many subtitle blocks
                over_span = (j - i + 1) >= self.max_span
                
                if stop_here or over_dur or over_span:
                    break
                
                # Else consider merging if tight time gap and mid-sentence comma-ish end
                if j + 1 < len(subs):
                    gap = subs[j+1].start_ms - cur.end_ms
                    comma_like = bool(re.search(r"[,，，、；;:]\s*$", cur.text))
                    if gap <= self.gap_ms or comma_like:
                        j += 1
                        continue
                break
            
            span = subs[i:j+1]
            text_src = self._join_for_translation(span)
            utterances.append(Utterance(
                sub_start=i,
                sub_end=j,
                text_src=text_src,
                subtitles=span,
                lang_code=lang_code
            ))
            i = j + 1
        
        return utterances
    
    def _join_for_translation(self, span: List[Subtitle]) -> str:
        """Join subtitle texts into one utterance string (normalize spaces/newlines lightly)."""
        raw = " ".join(s.text.strip() for s in span if s.text is not None)
        # collapse internal whitespace
        raw = re.sub(r"\s+", " ", raw).strip()
        return raw
