#!/usr/bin/env python3
"""
AI Configuration Generator for SRT Translator.
Generates DNT terms and termbase using OpenAI API.
"""

import json
import logging
import os
import random
import re
import time
import unicodedata
from dataclasses import dataclass

from openai import OpenAI

from srt_translator.core.config.language_config import LanguageConfig
from srt_translator.core.services.language_detection import detect_source_language
from srt_translator.core.terminology_utils import is_hard_preserve, is_numeric_like
from srt_translator.core.translator.srt_parser import SRTParser

# Batch-level AI config constants
_CHARS_PER_TOKEN = 4  # rough heuristic: ~4 chars per token
_TOKEN_CAP = 12_500
_CHAR_CAP = _TOKEN_CAP * _CHARS_PER_TOKEN  # ~50k chars


@dataclass
class BatchAIConfig:
    dnt_terms: list[str]
    termbase: dict[str, dict[str, str]]  # lang -> {source_term: mapped_translation}
    source_language: dict[str, object] | None = None


class AIConfigGenerator:
    """Generates AI-powered translation configurations from SRT content"""

    def __init__(self, api_key: str, language_config: LanguageConfig | None = None):
        """Initialize the AI config generator with OpenAI API key and language configuration"""
        if language_config is None:
            raise ValueError("LanguageConfig is required for AIConfigGenerator")
        self.api_key = api_key
        self.client = OpenAI(api_key=api_key)
        self.logger = logging.getLogger("srt_translator.gui.ai_config")
        # GUI-only model selection for AI config generation is intentionally
        # isolated from CLI/env to avoid cross-mode confusion
        self.DEFAULT_MODEL = "gpt-4o-mini"
        # GUI-local approximation for characters per token to guide truncation.
        # Keep GUI/CLI separation: do not read from env.
        self.CHARS_PER_TOKEN = 4

        # Language configuration for script validation
        self._lang_cfg = language_config

        # Configuration constants
        self.MAX_INLINE_TOKENS = 12500  # Precise token limit for inline content
        self.MAX_CONTENT_TOKENS = 100000  # Token limit for AI analysis (well within OpenAI's 128K limit)
        self.MAX_CONTENT_LENGTH = 400000  # Character limit as fallback (roughly 100K tokens)

    def get_supported_languages(self) -> list[str]:
        """Get all supported languages from unified configuration"""
        return self._lang_cfg.codes()

    def get_supported_language_names(self) -> list[str]:
        """Get all supported language names from unified configuration"""
        return list(self._lang_cfg.get_language_names().values())

    def extract_subtitle_content(self, srt_files: list[str]) -> str:
        """
        Extract text from SRT files, then truncate to the first MAX_INLINE_TOKENS tokens.

        Args:
            srt_files: List of paths to SRT files

        Returns:
            Clean text content limited to exactly MAX_INLINE_TOKENS tokens for safe AI processing
        """
        try:
            parser = SRTParser()
            all_text_chunks = []

            for file_path in srt_files:
                if not os.path.exists(file_path):
                    self.logger.warning("SRT file not found: %s", file_path)
                    continue

                # Parse SRT file and extract subtitle text
                subtitles = parser.parse_file(file_path)

                for subtitle in subtitles:
                    # Clean the subtitle text
                    clean_text = self._clean_subtitle_text(subtitle.content)
                    if clean_text:
                        all_text_chunks.append(clean_text)

            # Join all text
            combined_text = " ".join(all_text_chunks)
            # Normalize to NFC to reduce odd splits of composed characters/emoji
            combined_text = unicodedata.normalize("NFC", combined_text)

            # --- Safe character-based truncation (avoids tiktoken in packaged builds) ---
            # Approximate 1 token ≈ 4 characters and truncate at sentence boundaries
            approximate_chars = self.MAX_INLINE_TOKENS * self.CHARS_PER_TOKEN
            if len(combined_text) > approximate_chars:
                truncated_text = self._truncate_text_intelligently(combined_text, target_length=approximate_chars)
                self.logger.info(
                    "Transcript truncated to ~%s chars for safe analysis",
                    format(approximate_chars, ","),
                )
                return truncated_text

            # Under limit—return whole thing
            self.logger.info("Transcript size: %s chars (no truncation needed)", format(len(combined_text), ","))
            return combined_text

        except Exception as e:
            self.logger.error("Error extracting subtitle content: %s", e)
            # Provide a clearer message to the GUI layer
            raise RuntimeError(
                "Failed to prepare transcript content for AI analysis. Please verify your files and try again."
            ) from e

    def generate_dnt_terms(self, content: str) -> list[str]:
        """
        Generate list of terms that should stay in the original language

        Args:
            content: Clean text content from SRT files

        Returns:
            List of terms to exclude from translation
        """
        try:
            prompt = f"""
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

            response = self.client.chat.completions.create(
                model=self.DEFAULT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.3,
            )

            result_text = response.choices[0].message.content
            if result_text is None:
                raise ValueError("OpenAI response content is None")
            result_text = result_text.strip()
            dnt_raw = self._parse_dnt_terms_response(result_text) or []

            # Apply hard-preserve filtering to DNT terms
            dnt_terms = []
            for term in dnt_raw:
                if is_numeric_like(term):  # remove numeric/number-like
                    continue
                if is_hard_preserve(term):
                    dnt_terms.append(term)

            dnt_terms = sorted(set(dnt_terms), key=str.lower)
            self.logger.info(
                "Generated %s DNT terms, filtered to %s (hard-preserve only)",
                len(dnt_raw),
                len(dnt_terms),
            )

            return dnt_terms

        except Exception as e:
            self.logger.error("Error generating DNT terms: %s", e)
            raise

    def generate_termbase(
        self,
        content: str,
        target_languages: list[str],
        dnt_terms: list[str] | None = None,
        source_language: dict[str, object] | None = None,
    ) -> dict[str, dict[str, str]]:
        """
        Generate a termbase per target language using a per‑language TWO‑PASS approach:
          Pass 1: ~20 topic‑critical & likely‑risky source‑language terms
          Pass 2: ~10 confusable / hard‑to‑translate source‑language terms
        Then translate those to the target language. DNT takes precedence; any term
        present in DNT is excluded from selection and filtered out if it slips through.

        If a language's TB fails, it is skipped. TB is optional by design.
        """
        try:
            supported_languages = self.get_supported_languages()
            self.logger.info("Supported languages count: %s", len(supported_languages))

            valid_languages = [lang for lang in target_languages if lang in supported_languages]
            self.logger.info("Valid languages from input: %s", valid_languages)
            if not valid_languages:
                self.logger.warning("No valid target languages provided")
                self.logger.warning("Input languages: %s", target_languages)
                self.logger.warning("Supported languages sample: %s", supported_languages[:10])
                return {}

            dnt_set = {term.lower().strip() for term in (dnt_terms or [])}
            termbase: dict[str, dict[str, str]] = {}

            # --- soft alignment anchor (first successful TB) ---
            anchor_count: int | None = None
            # derive a simple size floor from transcript size (tokens ≈ chars/4)
            approx_tokens = max(1, len(content) // self.CHARS_PER_TOKEN)
            if approx_tokens <= 400:
                size_floor = 6
            elif approx_tokens <= 2000:
                size_floor = 10
            else:
                size_floor = 14

            # default soft band BEFORE we have an anchor (content-scaled)
            # this helps the first few languages aim for a healthy size
            def _default_soft_band(tokens: int) -> tuple[int, int]:
                if tokens <= 600:
                    return (8, 12)
                if tokens <= 2000:
                    return (16, 24)
                # long content
                return (20, 30)

            default_lo, default_hi = _default_soft_band(approx_tokens)

            self.logger.info("Per‑language TWO‑PASS extraction + translation (source‑language agnostic)")
            for lang_code in valid_languages:
                lang_name = self._lang_cfg.get_language_name(lang_code)
                if not lang_name:
                    self.logger.warning("Could not get language name for %s, skipping", lang_code)
                    continue
                try:
                    # compute soft band (clamped to defaults)
                    if anchor_count:
                        tol = max(2, round(anchor_count * 0.15))
                        soft_lo = max(default_lo, min(default_hi, max(8, anchor_count - tol)))
                        soft_hi = max(soft_lo, min(default_hi, min(40, anchor_count + tol)))
                    else:
                        soft_lo, soft_hi = default_lo, default_hi
                    if anchor_count is None:
                        self.logger.info(
                            "[%s] default_soft_range=%s-%s (no anchor yet)",
                            lang_code,
                            soft_lo,
                            soft_hi,
                        )
                    else:
                        self.logger.info(
                            "[%s] soft_range=%s-%s (anchor=%s)",
                            lang_code,
                            soft_lo,
                            soft_hi,
                            anchor_count,
                        )

                    # small jitter AFTER anchor to reduce order effects
                    if anchor_count is not None:
                        import random
                        import time

                        time.sleep(random.uniform(0.4, 1.1))  # nosec B311

                    tb_dict, extracted_terms = self.generate_language_termbase_two_pass(
                        content=content,
                        lang_code=lang_code,
                        lang_name=lang_name,
                        dnt_terms=list(dnt_set),
                        soft_lo=soft_lo,
                        soft_hi=soft_hi,
                        source_language=source_language,
                    )
                    if not tb_dict:
                        self.logger.warning("Empty termbase for %s; skipping", lang_code)
                        continue
                    # DNT wins: aggressively drop any collisions that slipped in.
                    cleaned = self._drop_dnt_from_termbase(tb_dict, dnt_set)
                    if cleaned:
                        termbase[lang_code] = cleaned
                        size = len(cleaned)
                        self.logger.info("TB[%s] %s terms (after DNT filtering)", lang_code, size)

                        # anchor may rise later, but never drop below default_soft_lo
                        extracted_n = max(1, len(extracted_terms))
                        coverage = size / extracted_n
                        if size >= max(size_floor, 8) and coverage >= 0.6:
                            candidate = max(size, default_lo)
                            if anchor_count is None:
                                anchor_count = candidate
                            else:
                                anchor_count = max(anchor_count, candidate)
                            self.logger.info(
                                "Anchored soft term count at %s (size_floor=%s, coverage=%s)",
                                anchor_count,
                                size_floor,
                                format(coverage, ".2f"),
                            )
                except Exception as e:
                    self.logger.error("Failed to generate termbase for %s: %s", lang_code, e)
                    continue

            self.logger.info("Generated termbase for %s languages (per‑language two‑pass)", len(termbase))
            return termbase
        except Exception as e:
            self.logger.error("Error generating termbase: %s", e)
            raise

    def generate_language_termbase_two_pass(
        self,
        content: str,
        lang_code: str,
        lang_name: str,
        dnt_terms: list[str] | None = None,
        max_terms: int = 30,
        soft_lo: int | None = None,
        soft_hi: int | None = None,
        source_language: dict[str, object] | None = None,
    ) -> tuple[dict[str, str], list[dict[str, str]]]:
        """
        Per‑language two‑pass extraction (source‑language agnostic) + translation in ONE call.
        Returns (termbase_dict, extracted_terms_list). extracted_terms are [{'term','reason'}, ...].
        DNT list is used to exclude/skip terms; any collisions are filtered after parsing as well.
        """
        dnt_set = {t.lower().strip() for t in (dnt_terms or [])}

        # ---- Source-language hint (if GUI already detected it) ----
        # We make the source/target roles explicit and non-optional to prevent
        # accidental target→source flips (observed for zh-Hans).
        src_hint = ""
        if source_language:
            src_code = str(source_language.get("normalized_code") or source_language.get("detected_code") or "").strip()
            src_name = str(source_language.get("normalized_name") or "").strip()
            if src_code:
                pretty = f"{src_code}" + (f" · {src_name}" if src_name else "")
                # Two hard rules:
                # 1) All items in pass1_terms/pass2_terms must be the *exact source-language surface forms*
                #    as they appear in the transcript (no translation, no romanization).
                # 2) "termbase" must map *SOURCE term* ➜ *{lang_name} translation*.
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
- If the transcript genuinely lacks further legitimate candidates (not model fatigue), return fewer and set "exhausted": true and an "exhaustion_reason".
""".strip()

        prompt = f"""
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

        try:
            response = self.client.chat.completions.create(
                model=self.DEFAULT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=5000,
                temperature=0.2,
                response_format={"type": "json_object"},
            )
            raw = (response.choices[0].message.content or "").strip()
            data = json.loads(raw)
            exhausted = bool(data.get("exhausted") or False)
            exhaustion_reason = data.get("exhaustion_reason")
            pass1_terms = data.get("pass1_terms", []) or []
            pass2_terms = data.get("pass2_terms", []) or []
            extracted = pass1_terms + pass2_terms
            tb = data.get("termbase", {}) or {}

            # Domain-agnostic post-filtering constants and functions
            GENERIC_SINGLETONS = {
                "metrics",
                "feedback",
                "engagement",
                "innovation",
                "framework",
                "alignment",
                "goals",
                "control",
                "execution",
                "insights",
                "initiative",
                "agile",
            }

            def appears_in_transcript(term: str, transcript: str) -> bool:
                # simple case/space/hyphen tolerant check
                canon = term.lower().replace("-", " ").strip()
                text = transcript.lower().replace("-", " ")
                return f" {canon} " in f" {text} "

            def count_distinct_lines(term: str, lines: list[str]) -> int:
                t = term.lower()
                return sum(1 for ln in lines if t in ln.lower())

            def dedupe_substrings(terms: list[str]) -> list[str]:
                terms_sorted = sorted(terms, key=lambda t: (-len(t), t.lower()))
                keep: list[str] = []
                for t in terms_sorted:
                    if not any(t.lower() in k.lower() and t.lower() != k.lower() for k in keep):
                        keep.append(t)
                return keep

            def prune_generics(terms: list[str], transcript: str, lines: list[str]) -> list[str]:
                # 1) drop terms not in transcript at all
                in_text = [t for t in terms if appears_in_transcript(t, transcript)]
                # 2) substring collapse (prefer longer phrases)
                collapsed = dedupe_substrings(in_text)
                # 3) cap generic singletons to 2 unless frequent (≥3 distinct lines)
                singles, others = [], []
                for t in collapsed:
                    if " " not in t and t.lower() in GENERIC_SINGLETONS:
                        singles.append(t)
                    else:
                        others.append(t)
                singles_keep = [t for t in singles if count_distinct_lines(t, lines) >= 3]
                singles_budget = max(0, 2 - len(singles_keep))
                singles_fill = [t for t in singles if t not in singles_keep][:singles_budget]
                return others + singles_keep + singles_fill

            # Basic validation + DNT filtering with pass analysis
            cleaned_terms: list[dict[str, str]] = []
            dnt_filtered_terms = []
            pass1_terms = []
            pass2_terms = []

            # Require non-empty reason and dedupe by case-insensitive key
            seen_terms = set()
            for it in extracted:
                if not isinstance(it, dict):
                    continue
                term = (it.get("term") or "").strip()
                reason = (it.get("reason") or "").strip()
                if not term or not reason:
                    continue

                # Check if term is in DNT list
                if term.lower() in dnt_set:
                    dnt_filtered_terms.append(term)
                    continue

                kl = term.lower()
                if kl in seen_terms:
                    continue
                seen_terms.add(kl)

                # Categorize by pass based on reason content
                reason_lower = reason.lower()
                # Debug: log a few reasons to see what the AI is actually writing
                if len(cleaned_terms) < 3:
                    self.logger.debug("Sample reason for '%s': '%s'", term, reason)

                if any(
                    keyword in reason_lower
                    for keyword in [
                        "confusable",
                        "near-homophone",
                        "orthography",
                        "mistranslate",
                        "over-literal",
                        "confused",
                        "similar",
                        "hard to translate",
                        "difficult",
                        "ambiguous",
                        "literal",
                        "misunderstood",
                    ]
                ):
                    pass2_terms.append({"term": term, "reason": reason})
                else:
                    pass1_terms.append({"term": term, "reason": reason})

                cleaned_terms.append({"term": term, "reason": reason})
                # keep a sane upper bound but prefer the prompt band
                effective_max = min(max_terms, soft_hi) if (soft_hi and soft_hi > 0) else max_terms
                if len(cleaned_terms) >= effective_max:
                    break

            def do_top_up(needed: int) -> int:
                # oversample to survive DNT/dedupe; clip later
                ask_low = needed + max(2, needed // 2)  # e.g., need 3 -> ask 4 or 5
                ask_high = ask_low + 2
                addl = self._top_up_extracted_terms(
                    content=content,
                    lang_code=lang_code,
                    lang_name=lang_name,
                    existing_terms=[t["term"] for t in cleaned_terms],
                    needed=ask_low,
                    needed_hi=ask_high,
                    dnt_terms=list(dnt_set),
                )
                added = 0
                for it in addl:
                    term = (it.get("term") or "").strip()
                    reason = (it.get("reason") or "").strip()
                    if not term or not reason:
                        continue
                    kl = term.lower()
                    if kl in seen_terms or kl in dnt_set:
                        continue
                    cleaned_terms.append({"term": term, "reason": reason})
                    seen_terms.add(kl)
                    added += 1
                    if soft_hi and len(cleaned_terms) >= soft_hi:
                        break
                return added

            if (soft_lo and len(cleaned_terms) < soft_lo) and not exhausted:
                missing = soft_lo - len(cleaned_terms)
                self.logger.info(
                    "[%s] %s < soft_lo(%s); requesting +%s top-up terms.",
                    lang_code,
                    len(cleaned_terms),
                    soft_lo,
                    missing,
                )
                added = do_top_up(missing)
                if (soft_lo and len(cleaned_terms) < soft_lo) and added > 0:
                    # still short, try one more time for the remainder
                    do_top_up(soft_lo - len(cleaned_terms))

            # Apply domain-agnostic post-filtering
            transcript_lines = content.split("\n")
            term_texts = [t["term"] for t in cleaned_terms]
            filtered_terms = prune_generics(term_texts, content, transcript_lines)

            # Rebuild cleaned_terms with filtered results
            filtered_cleaned_terms = []
            for term_text in filtered_terms:
                # Find the original term dict with this text
                for term_dict in cleaned_terms:
                    if term_dict["term"] == term_text:
                        filtered_cleaned_terms.append(term_dict)
                        break

            # Update cleaned_terms with filtered results
            cleaned_terms = filtered_cleaned_terms

            # Filter DNT collisions from TB keys
            tb_dict = {}
            if isinstance(tb, dict):
                for k, v in tb.items():
                    if not k or not v:
                        continue
                    if k.strip().lower() in dnt_set:
                        continue
                    tb_dict[k.strip()] = str(v).strip()

            # --- ensure translations exist for ALL cleaned terms ---
            src_terms = [t["term"] for t in cleaned_terms]
            missing_src = [s for s in src_terms if not tb_dict.get(s)]
            if missing_src:
                merged = {}
                CHUNK = 25
                for i in range(0, len(missing_src), CHUNK):
                    chunk = missing_src[i : i + CHUNK]
                    fill_map = (
                        self.generate_single_language_termbase(
                            terms=[{"term": s, "reason": ""} for s in chunk],
                            lang_code=lang_code,
                            lang_name=lang_name,
                        )
                        or {}
                    )
                    merged.update(fill_map)
                for s in missing_src:
                    tb_dict[s] = merged.get(s) or s
                self.logger.info(
                    "[%s] post-fill added %s translations; TB now %s",
                    lang_code,
                    len(missing_src),
                    len(tb_dict),
                )

            # Log detailed breakdown
            self.logger.info(
                "Termbase breakdown for %s: Pass 1 (topic-critical): %s, Pass 2 (confusable): %s, DNT filtered: %s, Total extracted: %s, Final TB entries: %s",
                lang_code,
                len(pass1_terms),
                len(pass2_terms),
                len(dnt_filtered_terms),
                len(cleaned_terms),
                len(tb_dict),
            )
            self.logger.info("[%s] exhausted=%s reason=%s", lang_code, exhausted, exhaustion_reason)

            # Log each term with its reason for detailed analysis
            if pass1_terms:
                self.logger.info("Pass 1 terms for %s:", lang_code)
                for term_info in pass1_terms:
                    self.logger.info("  Pass 1: '%s' - %s", term_info["term"], term_info["reason"])

            if pass2_terms:
                self.logger.info("Pass 2 terms for %s:", lang_code)
                for term_info in pass2_terms:
                    self.logger.info("  Pass 2: '%s' - %s", term_info["term"], term_info["reason"])

            if dnt_filtered_terms:
                self.logger.info(
                    "DNT filtered terms for %s: %s%s",
                    lang_code,
                    dnt_filtered_terms[:5],
                    "..." if len(dnt_filtered_terms) > 5 else "",
                )

            # Add size validation
            if len(cleaned_terms) < 5:  # Minimum reasonable size
                self.logger.warning("Very small termbase for %s: %s terms", lang_code, len(cleaned_terms))

            return tb_dict, cleaned_terms

        except json.JSONDecodeError as e:
            self.logger.error("Failed to parse AI response for %s: %s", lang_code, e)
            self.logger.debug("Raw response: %s", raw)
            return {}, []  # Return empty results instead of raising
        except Exception as e:
            self.logger.error("Error generating termbase for %s: %s", lang_code, e)
            return {}, []

    def _drop_dnt_from_termbase(self, tb: dict[str, str], dnt_set: set[str]) -> dict[str, str]:
        """Remove any entries whose source key collides with DNT (DNT > TB)."""
        if not tb:
            return {}
        out = {}
        for k, v in tb.items():
            if k and k.strip().lower() not in dnt_set and v:
                out[k.strip()] = v.strip()
        return out

    def _clean_subtitle_text(self, text: str) -> str:
        """Clean subtitle text by removing timestamps and formatting"""
        # Remove timestamp patterns like [00:00:00] or (00:00:00)
        text = re.sub(r"\[?\d{1,2}:\d{2}:\d{2}\]?", "", text)
        # Remove HTML tags
        text = re.sub(r"<[^>]+>", "", text)
        # Remove extra whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _norm(self, text: str) -> str:
        """Normalize text for consistent matching (NFKC, lowercase)"""
        return unicodedata.normalize("NFKC", text.lower().strip())

    def filter_dnt_terms(self, dnt_terms: list[str]) -> list[str]:
        """Filter DNT terms to exclude numeric and number-like items"""
        if not dnt_terms:
            return []

        filtered_terms = []
        for term in dnt_terms:
            if not term or not term.strip():
                continue

            # Skip pure numbers and number-like terms
            if is_numeric_like(term):
                self.logger.debug("Filtering out numeric DNT term: '%s'", term)
                continue

            filtered_terms.append(term)

        if len(filtered_terms) != len(dnt_terms):
            self.logger.info(
                "Filtered DNT terms: %s -> %s (removed numeric items)",
                len(dnt_terms),
                len(filtered_terms),
            )

        return filtered_terms

    def filter_dnt_terms_with_metadata(self, dnt_terms: list[str]) -> tuple[list[str], list[str]]:
        """
        Filter DNT terms and return both filtered terms and metadata about what was filtered out.

        Args:
            dnt_terms: List of DNT terms to filter

        Returns:
            Tuple of (filtered_terms, filtered_out_terms)
        """
        if not dnt_terms:
            return [], []

        filtered_terms = []
        filtered_out = []

        for term in dnt_terms:
            if not term or not term.strip():
                continue

            # Skip pure numbers and number-like terms
            if is_numeric_like(term):
                self.logger.debug("Filtering out numeric DNT term: '%s'", term)
                filtered_out.append(f"{term} (filtered: numeric/number-like)")
                continue

            filtered_terms.append(term)

        if len(filtered_terms) != len(dnt_terms):
            self.logger.info(
                "Filtered DNT terms: %s -> %s (removed numeric items)",
                len(dnt_terms),
                len(filtered_terms),
            )

        return filtered_terms, filtered_out

    def _truncate_text_intelligently(self, text: str, target_length: int) -> str:
        """Truncate text at sentence boundaries to stay within target length"""
        if len(text) <= target_length:
            return text

        # Find the last sentence boundary within the limit
        truncated = text[:target_length]

        # Look for sentence endings
        sentence_endings = [".", "!", "?"]
        last_sentence_end = -1

        for ending in sentence_endings:
            pos = truncated.rfind(ending)
            if pos > last_sentence_end:
                last_sentence_end = pos

        if last_sentence_end > 0:
            # Truncate at the last complete sentence
            return text[: last_sentence_end + 1]
        else:
            # Fall back to word boundary
            last_space = truncated.rfind(" ")
            if last_space > 0:
                return text[:last_space]
            else:
                return truncated

    def _parse_dnt_terms_response(self, response_text: str) -> list[str]:
        """Parse the AI response for DNT terms"""
        try:
            # Extract JSON array from response

            # Clean the response text
            cleaned = response_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]

            # Parse JSON
            terms = json.loads(cleaned)

            # Ensure it's a list and all items are strings
            if isinstance(terms, list):
                return [str(term).strip() for term in terms if term]
            else:
                self.logger.warning("AI response is not a list format")
                return []

        except Exception as e:
            self.logger.error("Error parsing DNT terms response: %s", e)
            self.logger.debug("Raw response: %s", response_text)
            return []

    def _parse_termbase_response(self, response_text: str) -> dict[str, str]:
        """Parse the AI response for termbase"""
        try:
            # Clean the response text
            cleaned = response_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]

            # Parse JSON
            termbase = json.loads(cleaned)

            # Ensure it's a dict and all values are strings
            if isinstance(termbase, dict):
                return {str(k).strip(): str(v).strip() for k, v in termbase.items() if k and v}
            else:
                self.logger.warning("AI response is not a dictionary format")
                return {}

        except Exception as e:
            self.logger.error("Error parsing termbase response: %s", e)
            self.logger.debug("Raw response: %s", response_text)
            return {}

    def generate_single_language_termbase(
        self,
        terms: list[dict[str, str]],
        lang_code: str,
        lang_name: str,
    ) -> dict[str, str]:
        """
        Generate termbase for a single target language.

        Args:
            terms: List of {"term": str, "reason": str} from extract_risk_terms
            lang_code: ISO language code (e.g., "es", "zh-Hans")
            lang_name: Human-readable language name (e.g., "Spanish", "Chinese (Simplified)")

        Returns:
            Dictionary mapping source-language terms to target language translations
        """
        try:
            # Convert terms to simple list for the prompt
            term_list = [item["term"] for item in terms]

            prompt = f"""
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

            response = self.client.chat.completions.create(
                model=self.DEFAULT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=3000,
                temperature=0.1,
                response_format={"type": "json_object"},
            )

            result_text = response.choices[0].message.content.strip()
            if not result_text:
                raise ValueError("Empty response from AI")

            # Parse the response
            try:
                translations = json.loads(result_text)

                # Validate that all input terms are present
                missing_terms = []
                result = {}

                for term in term_list:
                    if term in translations:
                        target = translations[term].strip()
                        if target:
                            result[term] = target
                        else:
                            # Empty translation - use source term and warn
                            result[term] = term
                            self.logger.warning(
                                "Empty translation for '%s' in %s, using source term",
                                term,
                                lang_code,
                            )
                    else:
                        missing_terms.append(term)
                        # Missing term - use source term and warn
                        result[term] = term
                        self.logger.warning("Missing translation for '%s' in %s, using source term", term, lang_code)

                if missing_terms:
                    self.logger.warning("Missing %s terms in %s: %s", len(missing_terms), lang_code, missing_terms)

                self.logger.info("Generated termbase for %s: %s terms", lang_code, len(result))
                return result

            except json.JSONDecodeError as e:
                self.logger.error("Failed to parse %s response as JSON: %s", lang_code, e)
                self.logger.debug("Raw response: %s", result_text)
                raise

        except Exception as e:
            self.logger.error("Error generating termbase for %s: %s", lang_code, e)
            raise

    def validate_api_key(self) -> bool:
        """Validate that the API key is working"""
        try:
            # Make a simple test call
            self.client.chat.completions.create(
                model=self.DEFAULT_MODEL,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5,
            )
            return True
        except Exception as e:
            error_msg = str(e).lower()
            if "invalid" in error_msg or "authentication" in error_msg:
                self.logger.error("Invalid API key - please check your key at platform.openai.com")
            elif "quota" in error_msg or "billing" in error_msg or "credits" in error_msg:
                self.logger.error("Insufficient API credits - please add credits to your OpenAI account")
            elif "rate" in error_msg:
                self.logger.error("Rate limit exceeded - please wait a moment and try again")
            elif "network" in error_msg or "connection" in error_msg:
                self.logger.error("Network connection issue - please check your internet connection")
            else:
                self.logger.error("API key validation failed: %s", e)
            return False

    def get_error_details(self, error: Exception) -> dict:
        """Get detailed error information for GUI display"""
        error_msg = str(error).lower()

        # Check for context length exceeded first (before "invalid" check)
        if (
            "context length" in error_msg
            or "maximum context length" in error_msg
            or "context_length_exceeded" in error_msg
        ):
            return {
                "type": "context_length_exceeded",
                "title": "Content Too Large for Analysis",
                "message": "The selected files contain too much text for the AI model to process at once",
                "suggestion": "Try selecting fewer files or use the content truncation feature",
            }
        elif "invalid" in error_msg and "authentication" in error_msg:
            return {
                "type": "invalid_api_key",
                "title": "Invalid API Key",
                "message": "Please check your API key at platform.openai.com",
                "suggestion": "Get your key at: platform.openai.com",
            }
        elif "quota" in error_msg or "billing" in error_msg or "credits" in error_msg:
            return {
                "type": "insufficient_credits",
                "title": "Insufficient API Credits",
                "message": "Please add credits to your OpenAI account",
                "suggestion": "Add credits at: platform.openai.com",
            }
        elif "rate" in error_msg:
            return {
                "type": "rate_limit",
                "title": "Rate Limit Exceeded",
                "message": "Please wait a moment and try again",
                "suggestion": "Wait 1-2 minutes before retrying",
            }
        elif "network" in error_msg or "connection" in error_msg:
            return {
                "type": "network_error",
                "title": "Network Connection Issue",
                "message": "Please check your internet connection",
                "suggestion": "Check your internet connection and try again",
            }
        elif "content" in error_msg and ("too small" in error_msg or "insufficient" in error_msg):
            return {
                "type": "insufficient_content",
                "title": "Insufficient Content for Analysis",
                "message": "Selected files contain very little text for analysis",
                "suggestion": "Try selecting larger files or more files from your course",
            }
        else:
            return {
                "type": "unknown_error",
                "title": "AI Configuration Failed",
                "message": f"An error occurred: {str(error)}",
                "suggestion": "Please check your settings and try again",
            }

    def generate_batch_ai_config(
        self,
        source_file_paths: list[str],
        target_lang_codes: list[str],
        token_cap: int = _TOKEN_CAP,
    ) -> BatchAIConfig:
        """
        Build ONE batch-level DNT list and ONE termbase (per target language)
        by sampling up to ~12,500 tokens (~50k chars) from the selected source SRTs.
        """
        if not source_file_paths:
            raise ValueError("No source files provided for AI config generation.")

        # 1) Read & parse SRTs, concatenate subtitle text up to char budget
        char_budget = token_cap * _CHARS_PER_TOKEN
        sampler = []
        total = 0
        parser = SRTParser()

        for path in source_file_paths:
            try:
                subs = parser.parse_file(path)
            except Exception:
                # Fallback: read raw text if parsing fails
                with open(path, encoding="utf-8", errors="ignore") as f:
                    raw = f.read()
                text_only = self._strip_srt_markup(raw)
                if total < char_budget:
                    take = text_only[: max(0, char_budget - total)]
                    sampler.append(take)
                    total += len(take)
                continue

            # join subtitle contents
            joined = "\n".join((s.content or "").strip() for s in subs if s.content)
            if not joined:
                continue
            if total < char_budget:
                take = joined[: max(0, char_budget - total)]
                sampler.append(take)
                total += len(take)
            if total >= char_budget:
                break

        transcript_sample = "\n".join(sampler)
        approx_tokens = len(transcript_sample) // _CHARS_PER_TOKEN
        self.logger.info(
            "Transcript sampled for AI config: ~%s tokens (~%s chars)",
            approx_tokens,
            len(transcript_sample),
        )

        # 2) Detect source language
        source_lang = detect_source_language(
            transcript_sample,
            chat=self.client,
            model=self.DEFAULT_MODEL,
            language_config=self._lang_cfg,
        )
        self.logger.info(
            "Detected source language: %s",
            source_lang.get("normalized_code") or source_lang.get("detected_code"),
        )

        # 3) Generate a SINGLE DNT list for the whole run
        dnt_terms = self.generate_dnt_terms(transcript_sample)
        self.logger.info("Generated %s DNT terms (batch-level)", len(dnt_terms))

        # 4) Generate termbase using the new two-stage pipeline
        termbase_by_lang = self.generate_termbase(
            transcript_sample,
            target_lang_codes,
            dnt_terms=dnt_terms,
            source_language=source_lang,
        )
        self.logger.info("Generated termbase for %s languages (batch-level)", len(termbase_by_lang))

        return BatchAIConfig(dnt_terms=dnt_terms, termbase=termbase_by_lang, source_language=source_lang)

    @staticmethod
    def _strip_srt_markup(raw: str) -> str:
        """Remove index/timestamps and keep visible text as a fallback sampler."""
        # kill timestamps 00:00:00,000 --> 00:00:00,000
        raw = re.sub(r"\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3}", "", raw)
        # kill pure index lines
        raw = re.sub(r"(?m)^\s*\d+\s*$", "", raw)
        return raw

    def _maybe_sleep_jitter(self, low: float = 0.5, high: float = 2.0) -> None:
        """Add a small random sleep to reduce AI fatigue."""
        sleep_time = random.uniform(low, high)  # nosec B311
        self.logger.debug("Sleeping for %s seconds to reduce AI fatigue.", format(sleep_time, ".2f"))
        time.sleep(sleep_time)

    def _top_up_extracted_terms(
        self,
        content: str,
        lang_code: str,
        lang_name: str,
        existing_terms: list[str],
        needed: int,
        needed_hi: int | None = None,
        dnt_terms: list[str] | None = None,
    ) -> list[dict[str, str]]:
        """
        One-shot request for EXACTLY `needed` NEW terms (not in existing_terms, not in DNT).
        Returns a list of {"term","reason"} (may be fewer than requested if genuinely exhausted).
        """
        dnt_set = {t.lower().strip() for t in (dnt_terms or [])}
        needed_hi = needed_hi or needed
        prompt = f"""
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
        try:
            resp = self.client.chat.completions.create(
                model=self.DEFAULT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=1400,
                response_format={"type": "json_object"},
            )
            raw = (resp.choices[0].message.content or "").strip()
            data = json.loads(raw)
            out = []
            for it in data.get("pass1_terms") or []:
                term = (it.get("term") or "").strip()
                reason = (it.get("reason") or "").strip()
                if not term or not reason:
                    continue
                tl = term.lower()
                if tl in dnt_set:
                    continue
                if tl in {t.lower() for t in existing_terms}:
                    continue
                out.append({"term": term, "reason": reason})
                if len(out) >= needed:
                    break
            return out
        except Exception as e:
            self.logger.warning("[%s] top-up failed: %s", lang_code, e)
            return []
