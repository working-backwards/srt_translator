# srt_translator/prompts/detection.py
"""Prompt builders for language detection."""


def build_language_detection_prompt(text: str) -> str:
    """Build the language detection prompt.

    Args:
        text: Sample text to detect the language of (pre-trimmed by caller).

    Returns:
        Fully-formatted user prompt string.
    """
    return f"""
Detect the primary source language of TEXT and answer in JSON only.
If multiple languages are present, set "mixed": true and choose the dominant one.

Output JSON:
{{
  "detected_code": "<IETF BCP-47 guess, e.g., en, es, zh-Hans, pt-BR>",
  "confidence": 0.0,
  "mixed": false
}}

TEXT:
{text}""".strip()
