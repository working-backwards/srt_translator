import os
import srt
from typing import List

class SRTParser:
    @staticmethod
    def parse_file(filepath: str) -> List[srt.Subtitle]:
        """Parse an SRT file into a list of srt.Subtitle objects."""
        encodings = ['utf-8', 'utf-16', 'iso-8859-1']
        for enc in encodings:
            try:
                with open(filepath, "r", encoding=enc) as file:
                    content = file.read()
                break
            except UnicodeDecodeError:
                continue
            except Exception as e:
                print(f"Error reading {filepath}: {e}")
                return []
        else:
            print(f"Could not decode {filepath} with supported encodings.")
            return []

        try:
            subtitles = list(srt.parse(content))
            return subtitles
        except Exception as e:
            print(f"Error parsing SRT content in {filepath}: {e}")
            return []

    @staticmethod
    def write_file(filepath: str, subtitles: List[srt.Subtitle]):
        """Write a list of srt.Subtitle objects to an SRT file."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        try:
            srt_content = srt.compose(subtitles)
            with open(filepath, "w", encoding="utf-8") as file:
                file.write(srt_content)
        except Exception as e:
            print(f"Error writing {filepath}: {e}")
