# srt_translator/prompts/__init__.py
"""Centralized AI prompt builders for srt_translator."""

from srt_translator.prompts.config import (
    build_dnt_extraction_prompt,
    build_single_language_termbase_prompt,
    build_top_up_extraction_prompt,
    build_two_pass_termbase_prompt,
)
from srt_translator.prompts.detection import build_language_detection_prompt
from srt_translator.prompts.diagnostics import (
    build_malformed_json_probe,
    build_oversize_diagnostic_system_prompt,
    build_oversize_probe_question,
)
from srt_translator.prompts.translation import (
    build_placeholder_fixer_prompt,
    build_single_string_fallback_prompt,
    build_translation_prompt,
)

__all__ = [
    "build_dnt_extraction_prompt",
    "build_language_detection_prompt",
    "build_malformed_json_probe",
    "build_oversize_diagnostic_system_prompt",
    "build_oversize_probe_question",
    "build_placeholder_fixer_prompt",
    "build_single_language_termbase_prompt",
    "build_single_string_fallback_prompt",
    "build_top_up_extraction_prompt",
    "build_translation_prompt",
    "build_two_pass_termbase_prompt",
]
