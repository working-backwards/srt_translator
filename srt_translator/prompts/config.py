# srt_translator/prompts/config.py
"""Prompt builders for AI configuration generation (DNT, termbase, top-up)."""

from __future__ import annotations

import json


def build_dnt_extraction_prompt(content: str) -> str:
    """Build the DNT (Do Not Translate) terms extraction prompt.

    Args:
        content: Clean transcript text from SRT files.

    Returns:
        User prompt string.
    """
    return f"""
You are analyzing educational video transcript content to identify terms that should NOT be translated and should remain in the original language.

TASK: From the transcript, extract terms that should be excluded from translation and kept in the original language.

INCLUDE:
• Proper names (people, organizations, institutions)
• Product or software names mentioned in the transcript
• Acronyms, abbreviations, or technical codes that would be confusing or incorrect if translated
• Units, version numbers, model names, or similar specifications
• Words that are culturally fixed or trademarked
• Any other terms that would sound unnatural or be misleading if translated

DO NOT INCLUDE:
• Common nouns or verbs that are expected to be translated
• Educational concepts that have clear equivalents in other languages
• General phrases or filler words

CONTEXT:
This is for subtitling and educational translation. Be conservative — only include terms that should clearly remain in the original language across all target languages.

TRANSCRIPT:
{content}

OUTPUT:
Return ONLY a JSON array of strings. No explanations, no markdown.

EXAMPLE FORMAT:
["Vivaldi", "API", "MIDI", "Adobe Premiere", "GPU", "NASA"]
"""


def build_two_pass_termbase_prompt(
    *,
    lang_name: str,
    lang_code: str,
    content: str,
    dnt_terms: list[str] | None = None,
    soft_lo: int | None = None,
    soft_hi: int | None = None,
    source_language: dict[str, object] | None = None,
) -> str:
    """Build the two-pass termbase generation prompt.

    This is the most complex prompt in the codebase. It includes conditional
    source-language hint and soft-alignment blocks.

    Args:
        lang_name: Human-readable target language name (e.g. "Spanish").
        lang_code: ISO language code (e.g. "es", "zh-Hans").
        content: Transcript text to analyze.
        dnt_terms: List of Do Not Translate terms to exclude.
        soft_lo: Minimum target term count (optional).
        soft_hi: Maximum target term count (optional).
        source_language: Source language metadata dict with keys
            normalized_code, detected_code, normalized_name (optional).

    Returns:
        User prompt string.
    """
    dnt_set = {t.lower().strip() for t in (dnt_terms or [])}

    # ---- Source-language hint (if GUI already detected it) ----
    src_hint = ""
    if source_language:
        src_code = str(source_language.get("normalized_code") or source_language.get("detected_code") or "").strip()
        src_name = str(source_language.get("normalized_name") or "").strip()
        if src_code:
            pretty = f"{src_code}" + (f" · {src_name}" if src_name else "")
            src_hint = (
                f"\nSOURCE LANGUAGE: {pretty}\n"
                '- In pass1_terms and pass2_terms, the "term" MUST be the EXACT surface form '
                "from the transcript in the SOURCE language. NEVER translate these terms.\n"
                f'- In "termbase", map from the SOURCE term ➜ {lang_name} translation.\n'
            )

    # soft alignment + concrete pass targets (optional)
    soft_block = ""
    pass1_goal = pass2_goal = None
    if soft_lo and soft_hi and soft_lo < soft_hi:
        target_total = int(round((soft_lo + soft_hi) / 2))
        pass1_goal = max(8, int(round(target_total * 0.7)))
        pass2_goal = max(4, max(target_total - pass1_goal, 0))
        soft_block = f"""
TERM COUNT ALIGNMENT (soft):
Aim to return a TOTAL of {soft_lo}–{soft_hi} items **in the "extracted_terms" array** for this language.
- If you do **not** set "exhausted": true, you **must** return at least {soft_lo} and at most {soft_hi}.
- Do **not** pad with low-value items just to hit the range; ensure each item is legitimate and useful.
- Each item must include a non-empty "term" and "reason".
- If the transcript genuinely lacks further legitimate candidates (not model fatigue), return fewer and set "exhausted": true and an "exhaustion_reason".""".strip()

    return f"""
You are building a bilingual termbase for target language: {lang_name} ({lang_code}).
The transcript's source language has already been detected elsewhere. Do NOT detect it here.
{src_hint}

REQUIREMENT: Return a total of {soft_lo}–{soft_hi} terms across Pass 1 + Pass 2, unless the content is genuinely exhausted.
If you cannot legitimately reach {soft_lo}, set "exhausted": true and provide "exhaustion_reason".
Otherwise, "exhausted": false.

Pass 1: topic-critical terms; Pass 2: confusable or easy-to-mistranslate items.

Hard-exclude any terms present in DNT. Use culturally appropriate, subtitle-friendly translations.

{soft_block if soft_block else ""}

1. Carefully analyze the transcript in the provided text.

2. PASS 1: Extract the topic-critical source-language terms most likely to cause confusion or mistranslation{f" (aim ≈{pass1_goal})" if pass1_goal else ""}. These should meet one or more of the following criteria:

   INCLUDE if they:
   - **Appear in the transcript** (surface forms from the source language; do NOT translate here)
   - **Remain in the source language** for pass lists; translation only belongs in the "termbase" mapping
   - Are **multi-word, domain-specific noun phrases** and proper names
   - Could be misunderstood or mistranslated due to ambiguity, abstraction, cultural specificity, or figurative language
   - Are important for learners to grasp — even if they appear only once
   - Would benefit from a standardized, subtitle-friendly translation to avoid confusion

   AVOID if they:
   - Are obvious, literal, or easily translatable without risk of confusion
   - Are purely stylistic idioms or colorful language with little instructional value
   - Are listed in DNT_TERMS (do not extract any terms that appear in the DNT_TERMS list)
   - Are **generic single-word terms** unless they appear in ≥3 distinct subtitle lines
   - Are inferred companies, brands, roles, or frameworks that aren't in the transcript

3. PASS 2: Identify additional source-language words or phrases{f" (aim ≈{pass2_goal})" if pass2_goal else ""} that are likely to be:
   - mistranslated,
   - interpreted too literally,
   - or misunderstood without context.

   These may include single words, figurative language, verbs or idioms with a special usage, or phrases that learners might take the wrong way in another culture or language.
   Pay special attention to single words that could be confused with similar words (e.g., "thrash" vs "trash").
   Only include these if their mistranslation could cause confusion or reduce learner understanding.
   Do not include merely colorful or stylistic phrases.

   **IMPORTANT**: Limit generic single-word terms (e.g., metrics, feedback, engagement, innovation, framework, alignment, goals) to at most **2 total** across both passes, **unless** the single word appears in ≥3 distinct subtitle lines. If a generic single has a longer, more specific variant also present (e.g., 'agile product development' vs 'agile'), **choose the longer phrase** and drop the generic.

   ➤ Generate a coherent list. If you cannot find enough legitimate candidates, return fewer and set "exhausted": true and "exhaustion_reason". **Do not pad** with broad synonyms.

Return JSON with:
- "pass1_terms": [{{"term": "...","reason":"..."}}]
- "pass2_terms": [{{"term": "...","reason":"..."}}]
- "termbase": {{"<SOURCE term>": "<{lang_name} translation>", ...}}
- "exhausted": boolean
- "exhaustion_reason": string|null

OUTPUT (JSON only; no markdown, no commentary):
{{
  "exhausted": false,
  "exhaustion_reason": null,
  "pass1_terms": [
    {{"term": "<SRC term 1>", "reason": "<Why risky when translating into {lang_name}>"}}
  ],
  "pass2_terms": [
    {{"term": "<SRC term 2>", "reason": "<Why risky when translating into {lang_name}>"}}
  ],
  "termbase": {{
    "<SRC term 1>": "<{lang_name} term 1>",
    "<SRC term 2>": "<{lang_name} term 2>"
  }}
}}

IMPORTANT: In the "reason" field, be specific about why the term is risky:
- For Pass 1: "key business concept", "technical framework", "strategic term", etc.
- For Pass 2: "confusable with similar words", "hard to translate", "ambiguous meaning", "literal vs figurative", etc.

TRANSLATION RULES
- Provide 1–4 word, natural, subtitle‑friendly {lang_name} equivalents.
- If no exact equivalent, use the most natural localized term (not a long definition).
- Preserve proper names; do not translate trademarks.
- Do NOT include any DNT terms (they were excluded from selection).
- Do NOT add new terms in the \"termbase\" that are not present (verbatim) as SOURCE terms
  in pass1_terms or pass2_terms.

DNT_TERMS (JSON array):
{json.dumps(sorted(list(dnt_set)), ensure_ascii=False)}

TEXT (Transcript):
{content}
""".strip()


def build_single_language_termbase_prompt(
    lang_name: str,
    term_list: list[str],
) -> str:
    """Build the single-language termbase translation prompt.

    Args:
        lang_name: Human-readable target language name.
        term_list: List of source-language term strings to translate.

    Returns:
        User prompt string.
    """
    return f"""
You translate a source-language term list into {lang_name} for subtitle use.

Return JSON only: {{"<SRC term>": "<{lang_name} term>", ...}}

Rules:
- 1-4 words per entry; concise and subtitle-friendly
- If no exact equivalent, give the most natural localized term (not a long definition)
- Preserve capitalization of proper names. Don't translate trademarks
- Do NOT include any DNT term (they're already excluded from the input)
- Do NOT add terms, do NOT skip terms

INPUT TERMS (JSON array of strings; these are source-language surface forms):
{json.dumps(term_list, ensure_ascii=False)}

Return valid JSON only. No explanations or markdown.
"""


def build_top_up_extraction_prompt(
    *,
    lang_name: str,
    content: str,
    needed: int,
    needed_hi: int | None,
    existing_terms: list[str],
    dnt_terms: list[str] | None = None,
) -> str:
    """Build the terminology top-up extraction prompt.

    Args:
        lang_name: Human-readable target language name.
        content: Transcript text to analyze.
        needed: Minimum number of new terms required.
        needed_hi: Maximum range for new terms (defaults to needed).
        existing_terms: Terms already extracted (to exclude).
        dnt_terms: Do Not Translate terms (to exclude).

    Returns:
        User prompt string.
    """
    dnt_set = {t.lower().strip() for t in (dnt_terms or [])}
    needed_hi = needed_hi or needed
    return f"""
You are assisting with a small top-up of terminology extraction for translation into {lang_name}.

REQUIREMENT: Return AT LEAST {needed} NEW, UNIQUE terms not in existing_terms (after DNT filtering).
If you can, return {needed} to {needed_hi} to allow for dedupe, but never include duplicates.

Provide NEW source-language terms that:
- are legitimate per the same selection rules,
- are NOT in EXISTING_TERMS and NOT in DNT_TERMS,
- include a concise "reason".

Output only:
{{"pass1_terms":[{{"term":"<SRC term>","reason":"<short reason>"}}]}}

EXISTING_TERMS (JSON): {json.dumps(sorted(existing_terms), ensure_ascii=False)}
DNT_TERMS (JSON): {json.dumps(sorted(list(dnt_set)), ensure_ascii=False)}
TEXT:
{content}
""".strip()
