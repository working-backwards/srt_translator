"""
Utility functions and adapters for the refactored translation system.
"""

import logging
from typing import List, Any
from .models import Subtitle


class TranslationUtils:
    """Utility functions for subtitle parsing, writing, and validation."""
    
    def __init__(self, logger: logging.Logger = None):
        self.logger = logger or logging.getLogger(__name__)
    
    def parse_source_to_local_subtitles(self, parser, input_filepath: str) -> List[Subtitle]:
        """Adapter over existing parser → produce local Subtitle list with ms times."""
        subs = []
        try:
            parsed = parser.parse_file(input_filepath)
            
            for s in parsed:
                # Convert start/end times to milliseconds
                start_ms = int(s.start.total_seconds() * 1000)
                end_ms = int(s.end.total_seconds() * 1000)
                
                # Get text content (handle different attribute names)
                text = getattr(s, 'content', None) or getattr(s, 'text', '')
                
                subs.append(Subtitle(
                    index=s.index,
                    start_ms=start_ms,
                    end_ms=end_ms,
                    text=text
                ))
        except Exception as e:
            self.logger.error(f"Failed to parse source file {input_filepath}: {e}")
            raise
        
        return subs
    
    def write_local_subtitles_to_srt(self, parser, subs: List[Subtitle], output_filepath: str):
        """Adapter back to existing writer; uses source times; only text changes."""
        try:
            # Map back into existing subtitle object format
            out_objs = []
            for s in subs:
                subtitle_obj = self._build_subtitle_like(parser, s)
                out_objs.append(subtitle_obj)
            
            parser.write_file(output_filepath, out_objs)
            
        except Exception as e:
            self.logger.error(f"Failed to write output file {output_filepath}: {e}")
            raise
    
    def _build_subtitle_like(self, parser, subtitle: Subtitle) -> Any:
        """Build whatever the writer expects."""
        try:
            # Try to use existing build method if available
            if hasattr(parser, 'build_subtitle'):
                return parser.build_subtitle(
                    index=subtitle.index,
                    start_ms=subtitle.start_ms,
                    end_ms=subtitle.end_ms,
                    content=subtitle.text
                )
            
            # Fallback: create a simple object with required attributes
            class SimpleSubtitle:
                def __init__(self, index, start, end, content):
                    self.index = index
                    self.start = start
                    self.end = end
                    self.content = content
            
            # Convert ms back to time objects if needed
            from srt import Subtitle as SRTSubtitle
            start_time = SRTSubtitle.parse_time(f"00:00:{subtitle.start_ms/1000:06.3f}")
            end_time = SRTSubtitle.parse_time(f"00:00:{subtitle.end_ms/1000:06.3f}")
            
            return SimpleSubtitle(
                index=subtitle.index,
                start=start_time,
                end=end_time,
                content=subtitle.text
            )
            
        except Exception as e:
            self.logger.error(f"Failed to build subtitle object: {e}")
            raise
    
    def validate_subtitle_structure(self, src_subs: List[Subtitle], 
                                  tgt_subs: List[Subtitle]) -> List[str]:
        """Validate subtitle structure integrity."""
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
