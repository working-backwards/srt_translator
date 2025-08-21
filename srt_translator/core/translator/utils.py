"""
Translation utilities for SRT file processing.
"""

import logging
import os
import srt
from typing import List, Any

from srt_translator.core.translator.models import InternalSubtitle


class TranslationUtils:
    """
    Utility functions for subtitle parsing, writing, and validation.
    
    Provides adapters between our InternalSubtitle format and the srt library's
    Subtitle format for file I/O operations.
    """
    
    def __init__(self, logger: logging.Logger = None):
        self.logger = logger or logging.getLogger(__name__)
    
    def parse_source_to_local_subtitles(self, parser, input_filepath: str) -> List[InternalSubtitle]:
        """
        Adapter over existing parser → produce local InternalSubtitle list with ms times.
        
        Converts srt library Subtitle objects to our InternalSubtitle format
        for internal processing.
        """
        subs = []
        try:
            parsed = parser.parse_file(input_filepath)
            
            for s in parsed:
                # Convert start/end times to milliseconds
                start_ms = int(s.start.total_seconds() * 1000)
                end_ms = int(s.end.total_seconds() * 1000)
                
                # Get text content (handle different attribute names)
                text = getattr(s, 'content', None) or getattr(s, 'text', '')
                
                subs.append(InternalSubtitle(
                    index=s.index,
                    start_ms=start_ms,
                    end_ms=end_ms,
                    text=text
                ))
        except Exception as e:
            self.logger.error(f"Failed to parse source file {input_filepath}: {e}")
            raise
        
        return subs
    
    def write_local_subtitles_to_srt(self, subs: List[InternalSubtitle], output_filepath: str, target_lang: str = None):
        """
        Write InternalSubtitle objects to SRT file format.
        
        Converts our InternalSubtitle objects to srt library Subtitle
        format for file writing.
        """
        try:
            # Map back into existing subtitle object format
            out_objs = []
            for s in subs:
                subtitle_obj = self._build_subtitle_like(s)
                out_objs.append(subtitle_obj)
            
            # Write using srt library
            with open(output_filepath, 'w', encoding='utf-8') as f:
                f.write(srt.compose(out_objs))
            
        except Exception as e:
            self.logger.error(f"Failed to write output file {output_filepath}: {e}")
            raise
    
    def _build_subtitle_like(self, subtitle: InternalSubtitle) -> Any:
        """
        Build srt.Subtitle objects for the writer.
        
        Creates srt library Subtitle objects from our InternalSubtitle format
        for output writing, maintaining compatibility with the existing SRT writer.
        """
        try:
            # Use the actual srt.Subtitle class for compatibility
            from srt import Subtitle
            
            # Convert ms back to time objects
            start_time = srt.srt_timestamp_to_timedelta(f"00:00:{subtitle.start_ms/1000:06.3f}")
            end_time = srt.srt_timestamp_to_timedelta(f"00:00:{subtitle.end_ms/1000:06.3f}")
            
            return Subtitle(
                index=subtitle.index,
                start=start_time,
                end=end_time,
                content=subtitle.text
            )
            
        except Exception as e:
            self.logger.error(f"Failed to build subtitle object: {e}")
            raise
    
    def validate_subtitle_structure(self, src_subs: List[InternalSubtitle], 
                                  tgt_subs: List[InternalSubtitle]) -> List[str]:
        """
        Validate subtitle structure integrity.
        
        Ensures that the target subtitle list maintains the same structure
        as the source, including count, indices, and timing.
        """
        errors = []
        
        # Check parity
        if len(tgt_subs) != len(src_subs):
            errors.append(f"Parity failure: src={len(src_subs)} vs tgt={len(tgt_subs)}")
        
        # Check for missing subtitles
        if any(s is None for s in tgt_subs):
            missing = [i+1 for i, s in enumerate(tgt_subs) if s is None]
            errors.append(f"Missing subtitles in target: {missing[:8]}{'...' if len(missing)>8 else ''}")
        
        # Check timing consistency
        for i, (src, tgt) in enumerate(zip(src_subs, tgt_subs)):
            if tgt is None:
                continue
                
            if tgt.start_ms != src.start_ms:
                errors.append(f"Start time mismatch at subtitle {i+1}: {src.start_ms} != {tgt.start_ms}")
            
            if tgt.end_ms != src.end_ms:
                errors.append(f"End time mismatch at subtitle {i+1}: {src.end_ms} != {tgt.end_ms}")
            
            if tgt.index != src.index:
                errors.append(f"Index mismatch at subtitle {i+1}: {src.index} != {tgt.index}")
        
        return errors
    
    def log_warning(self, msg: str):
        """Safe warning logging."""
        if self.logger:
            self.logger.warning(msg)
        else:
            try:
                print(f"[WARN] {msg}")
            except Exception:
                pass
