#!/usr/bin/env python3
"""
SRT parser for the SRT Translator.
"""

import logging
import os

import srt

# Get logger for this module
logger = logging.getLogger(__name__)


class SRTParser:
    """
    Parser for SRT subtitle files with robust encoding detection.

    SRT files can come in various encodings, so this parser tries multiple
    common encodings to handle files from different sources and regions.
    """

    @staticmethod
    def parse_file(filepath: str) -> list[srt.Subtitle]:
        """
        Parse an SRT file into a list of srt.Subtitle objects.

        This method handles the SRT file format which consists of:
        - Subtitle number (sequential)
        - Time range in format: HH:MM:SS,mmm --> HH:MM:SS,mmm
        - Subtitle text (one or more lines)
        - Blank line separator

        Args:
            filepath: Path to the SRT file to parse

        Returns:
            List of srt.Subtitle objects with timing and text information
        """
        # Try multiple encodings to handle files from different sources
        # SRT files can be saved with various encodings depending on the source
        encodings = ["utf-8", "utf-16", "iso-8859-1"]

        for enc in encodings:
            try:
                with open(filepath, encoding=enc) as file:
                    content = file.read()
                break  # Successfully read with this encoding
            except UnicodeDecodeError:
                # Try next encoding if this one fails
                continue
            except Exception as e:
                logger.error("Error reading %s: %s", filepath, e)
                return []
        else:
            # All encodings failed
            logger.error("Could not decode %s with supported encodings.", filepath)
            return []

        # Parse the SRT content into subtitle objects
        try:
            subtitles = list(srt.parse(content))
            return subtitles
        except Exception as e:
            logger.error("Error parsing SRT content in %s: %s", filepath, e)
            return []

    @staticmethod
    def write_file(filepath: str, subtitles: list[srt.Subtitle]):
        """
        Write a list of srt.Subtitle objects to an SRT file.

        Creates the output directory if it doesn't exist and writes
        the subtitles in standard SRT format with UTF-8 encoding.

        Args:
            filepath: Path where the SRT file should be written
            subtitles: List of srt.Subtitle objects to write
        """
        # Ensure the output directory exists
        dirpath = os.path.dirname(filepath) or "."
        os.makedirs(dirpath, exist_ok=True)

        try:
            # Convert subtitle objects back to SRT format
            srt_content = srt.compose(subtitles)

            # Write with UTF-8 encoding for maximum compatibility
            with open(filepath, "w", encoding="utf-8") as file:
                file.write(srt_content)
        except Exception as e:
            logger.error("Error writing %s: %s", filepath, e)
