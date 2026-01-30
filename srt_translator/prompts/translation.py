# srt_translator/prompts/translation.py
"""Prompt builders for translation, fallback, and placeholder fixing."""

from __future__ import annotations


def build_translation_prompt(
    *,
    target_lang: str,
    tone: str,
    tone_hint: str | None,
    termbase_block: str,
    rendered_items: str,
    item_count: int,
    strict: bool = False,
    is_chinese: bool = False,
) -> tuple[str, str]:
    """Build the main translation system + user prompts.

    Args:
        target_lang: Target language code (e.g. "zh-Hans").
        tone: Tone setting (e.g. "formal").
        tone_hint: Language-specific tone hint, or None.
        termbase_block: Pre-formatted termbase block string.
        rendered_items: Pre-rendered input items string.
        item_count: Number of source items in the batch.
        strict: Whether to add anti-repetition constraint.
        is_chinese: Whether target_lang is Chinese (for system-level tone hint).

    Returns:
        (system_prompt, user_prompt) tuple.
    """
    system_prompt = "You are a professional subtitle translator. Return valid JSON ONLY, never prose."
    if strict:
        system_prompt += (
            " Hard constraint: never repeat any single word/syllable/token more than 3 times consecutively;"
            " do not pad, chant, or fill with repeated fragments."
        )

    # Add tone-critical instruction to system prompt for languages with strong formality distinctions
    if tone_hint and is_chinese:
        # Chinese has critical 你/您 distinction - add to system prompt for higher priority
        system_prompt += f" CRITICAL for {target_lang}: {tone_hint}"

    # Build TONE and optional LANG_HINT section
    tone_section = f"TONE: {tone}\n"
    if tone_hint:
        tone_section += f"\nLANG_HINT ({target_lang}): {tone_hint}\n"

    # The translation rules here preserve the core behavior you've tuned:
    user_prompt = f"""Translate each item to {target_lang}. Keep 1:1 count and order.

IMPORTANT SUBTITLE TRANSLATION RULES (MUST FOLLOW):
- Each item is an independent subtitle fragment.
- DO NOT use context from previous or next items.
- DO NOT complete or rewrite broken sentences.
- If a sentence is cut off in the input, it MUST be cut off in the translation.
- If a sentence starts mid-thought, keep it mid-thought.
- Preserve meaning ONLY of the visible text in that item.
- Do NOT add or remove information.
- Do NOT improve grammar beyond what is necessary for understanding.
- Keep translation length close to the input (no expansion).

TERMINOLOGY:
Use these business term mappings when present (source → target). If "(none)", ignore:
{termbase_block}

DNT PLACEHOLDERS:
- If you see placeholders like __DNT_TERM_7__, keep them EXACTLY as written.
- Do not invent or drop placeholders.
- Never invent __DNT_TERM_n__ placeholders. Only preserve those already present in the input.

STRUCTURE:
- Return JSON ONLY as: {{"items":[{{"id":<int>,"tgt":"..."}}, ...]}}
- The "items" array MUST have exactly {item_count} objects.
- Use the provided ids 1:1 with the inputs below. Do not merge or split.
- Do not include SRT timestamps in the output. Only JSON.

STYLE:
- Natural, fluent translation.
- Numbers: keep digits; localize formatting where normal. No rounding.
- No added/removed content.

{tone_section}
INPUT ITEMS:
{rendered_items}
"""

    return system_prompt, user_prompt


def build_single_string_fallback_prompt(
    target_lang: str,
    src_text: str,
) -> tuple[str, str]:
    """Build the single-string fallback prompts (no JSON wrapper).

    Args:
        target_lang: Target language code.
        src_text: Source text to translate.

    Returns:
        (system_prompt, user_prompt) tuple.
    """
    sys = (
        "You are a professional subtitle translator. "
        "Reply with the translation ONLY—no JSON, no code, no quotes, no commentary."
    )
    usr = (
        f"Translate to {target_lang}.\n\n"
        "DNT PLACEHOLDERS:\n"
        "- If you see placeholders like __DNT_TERM_7__, keep them EXACTLY as written.\n"
        "- Do not invent or drop placeholders.\n\n"
        f"TEXT:\n{src_text}\n"
    )
    return sys, usr


def build_placeholder_fixer_prompt(
    *,
    allowed_placeholders: list[str],
    rendered_src: str,
    rendered_tgt: str,
) -> tuple[str, str]:
    """Build the placeholder fixer prompts.

    Args:
        allowed_placeholders: List of allowed placeholder strings.
        rendered_src: Pre-rendered source items string.
        rendered_tgt: Pre-rendered target items string.

    Returns:
        (system_prompt, user_prompt) tuple.
    """
    sys = "You are a strict placeholder fixer. Do not translate; only adjust placeholders."
    prompt = f"""Fix placeholders ONLY. Do not change wording except to:
- Remove any placeholders NOT in this allowed list: {allowed_placeholders}
- If a source item contains a placeholder, the same placeholder MUST appear in that target item.
- Keep the same number of items, same ids, same order.
- Return JSON ONLY: {{"items":[{{"id":<int>,"tgt":"..."}}, ...]}}

SOURCE ITEMS:
{rendered_src}

TARGET ITEMS (TO FIX):
{rendered_tgt}
"""
    return sys, prompt
