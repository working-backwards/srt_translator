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
from dataclasses import dataclass, field

from openai import APIConnectionError, APITimeoutError, OpenAI, RateLimitError

from srt_translator.config.model_config_loader import (
    build_call_params,
    get_max_inline_tokens,
    get_model_config,
)
from srt_translator.core.config.language_config import LanguageConfig
from srt_translator.core.constants import (
    ANCHOR_TOLERANCE_FRACTION,
    ANCHOR_TOLERANCE_MIN,
    CHARS_PER_TOKEN,
    DEFAULT_GENERATION_MODEL,
    GENERATION_PER_LANGUAGE_RETRY_ATTEMPTS,
    GENERATION_PER_LANGUAGE_RETRY_BACKOFF_BASE_S,
    GENERATION_PER_LANGUAGE_RETRY_BACKOFF_CAP_S,
    JITTER_SLEEP_HIGH,
    JITTER_SLEEP_LOW,
    MAX_COMPLETION_TOKENS_DNT,
    MAX_COMPLETION_TOKENS_TERMBASE,
    MAX_COMPLETION_TOKENS_VALIDATE,
    MAX_GENERIC_SINGLETONS,
    MIN_ANCHOR_COVERAGE,
    MIN_ANCHOR_TERM_COUNT,
    MIN_GENERIC_SINGLETON_LINE_FREQ,
    MIN_TERMBASE_SIZE,
    SOFT_BAND_FLOOR_LONG,
    SOFT_BAND_FLOOR_MEDIUM,
    SOFT_BAND_FLOOR_SHORT,
    SOFT_BAND_HARD_CAP,
    SOFT_BAND_LONG,
    SOFT_BAND_MEDIUM,
    SOFT_BAND_SHORT,
    TERMBASE_FILL_CHUNK_SIZE,
    TOPUP_OVERSAMPLE_DIVISOR,
)
from srt_translator.core.retry import compute_retry_delay, parse_retry_after
from srt_translator.core.services.language_detection import detect_source_language
from srt_translator.core.terminology_utils import is_hard_preserve, is_numeric_like
from srt_translator.core.translator.srt_parser import SRTParser
from srt_translator.prompts.config import (
    build_dnt_extraction_prompt,
    build_single_language_termbase_prompt,
    build_top_up_extraction_prompt,
    build_two_pass_termbase_prompt,
)

# Batch-level AI config constants
_CHARS_PER_TOKEN = CHARS_PER_TOKEN  # rough heuristic: ~4 chars per token


@dataclass
class BatchAIConfig:
    dnt_terms: list[str]
    termbase: dict[str, dict[str, str]]  # lang -> {source_term: mapped_translation}
    source_language: dict[str, object] | None = None
    # Language codes the AI generation pipeline could not produce a termbase
    # for (after retries). Empty in the happy path. Surfaced to the GUI so
    # creators see partial failures instead of just the success count.
    failed_languages: list[str] = field(default_factory=list)


_RETRYABLE_OPENAI_ERRORS: tuple[type[Exception], ...] = (
    APITimeoutError,
    APIConnectionError,
    RateLimitError,
)


def _call_with_retry(
    create_fn,
    *,
    context: str,
    logger: logging.Logger,
    attempts: int = GENERATION_PER_LANGUAGE_RETRY_ATTEMPTS,
    base_backoff_s: float = GENERATION_PER_LANGUAGE_RETRY_BACKOFF_BASE_S,
    cap_backoff_s: float = GENERATION_PER_LANGUAGE_RETRY_BACKOFF_CAP_S,
    sleep_fn=time.sleep,
):
    """Call create_fn() with exponential backoff on transient OpenAI errors.

    Retries on APITimeoutError, APIConnectionError, RateLimitError up to
    `attempts` times. Other exceptions propagate immediately. After the
    final attempt, the last retryable exception is re-raised.

    Args:
        create_fn: Zero-arg callable that performs the API call.
        context: Human-readable identifier (e.g. language code) used in
            log messages so creators can see which call retried.
        logger: Logger to write WARNING-level retry notices to.
        attempts: Number of retries after the initial attempt.
        base_backoff_s: Backoff for retry 1; subsequent retries double up
            to `cap_backoff_s`.
        cap_backoff_s: Maximum backoff between retries.
        sleep_fn: Injected for tests so they don't actually sleep.

    Returns:
        Whatever create_fn returns on success.
    """
    for attempt in range(attempts + 1):
        try:
            return create_fn()
        except _RETRYABLE_OPENAI_ERRORS as ex:
            if isinstance(ex, RateLimitError):
                detail = str(ex).lower()
                if "insufficient_quota" in detail or "current quota" in detail:
                    raise
            if attempt == attempts:
                raise
            backoff = compute_retry_delay(
                attempt + 1,
                base=base_backoff_s,
                cap=cap_backoff_s,
                retry_after=parse_retry_after(ex),
            )
            logger.warning(
                "[%s] %s on attempt %d/%d; retrying in %.1fs: %s",
                context,
                type(ex).__name__,
                attempt + 1,
                attempts + 1,
                backoff,
                ex,
            )
            sleep_fn(backoff)


def _build_pass_assignment(
    response_pass1: list,
    response_pass2: list,
) -> dict[str, str]:
    """Build a term-lower -> 'pass1' | 'pass2' lookup from the model's response.

    Used so the local term-validation loop can preserve the model's own
    pass categorization instead of re-deriving it from the `reason` text.
    Re-derivation by English-keyword matching (the previous approach) silently
    failed when the model wrote reasons in the target language — for example
    a zh-Hans run came back with reasons in Chinese, so no English keyword
    matched and every term collapsed into Pass 1 in the diagnostic logs.

    On duplicate terms (same surface form in both arrays), Pass 2 wins —
    "confusable" is the more specific category, so if the model thought a
    term was confusable it should be reported as such.
    """
    assignment: dict[str, str] = {}
    for it in response_pass1 or []:
        if isinstance(it, dict):
            term = (it.get("term") or "").strip().lower()
            if term:
                assignment[term] = "pass1"
    for it in response_pass2 or []:
        if isinstance(it, dict):
            term = (it.get("term") or "").strip().lower()
            if term:
                assignment[term] = "pass2"
    return assignment


def _filter_termbase_response(
    tb: object,
    allowed_terms: list[dict],
    dnt_set: set[str],
) -> tuple[dict[str, str], dict[str, int]]:
    """Filter the raw termbase dict from a model response.

    Drops entries that are:
      - empty (no key or value)
      - DNT collisions (key matches a do-not-translate term)
      - self-references (source key equal to target value, case-insensitive)
      - unknown keys (key not present in allowed_terms)
      - case-only duplicates of an already-kept key

    Surviving keys are normalized to the canonical surface form from
    allowed_terms (the first-encountered casing in cleaned_terms). This
    matters because the downstream post-fill step does a case-sensitive
    `tb_dict.get(src_term)` against cleaned_terms — without normalization,
    `cleaned_terms=["fulfillment center"]` plus model-returned
    `tb={"Fulfillment center": ...}` would miss the lookup, post-fill would
    generate a fresh translation for "fulfillment center", and the saved
    JSON would end up with both case variants pointing at the same concept.

    The self-reference and unknown-key filters defend against malformed model
    output where the source key is in the target language (e.g. Japanese
    `2ピザチーム` → `2ピザチーム` for a Japanese-target call). Such entries
    are dead weight: they never match English source text.

    The case-duplicate filter defends against the model emitting the same
    surface form in multiple casings within its own tb response. Termbase
    lookup at translation time uses `re.IGNORECASE`, so case variants are
    functionally one entry — only the first-iterated regex pattern matches;
    the rest are dead. Worse, when the model emits conflicting translations
    across the case variants, all but one are silently orphaned.

    Args:
        tb: The raw termbase value from the model response. Expected to be a
            dict, but typed as object so callers can pass through whatever
            json.loads returned.
        allowed_terms: List of {"term": str, ...} dicts representing the
            canonical kept set of source terms. The caller should pass the
            post-cap, post-prune `cleaned_terms` list — passing the full
            uncapped pass1+pass2 response bypasses the size band the
            anchor mechanism is enforcing. If empty, the unknown-key filter
            is skipped and key normalization is also skipped (no canonical
            reference to normalize toward).
        dnt_set: Set of lowercased DNT terms.

    Returns:
        (filtered_dict, drop_counts) where drop_counts has integer keys
        "dnt_collision", "self_reference", "unknown_key", "case_duplicate".
    """
    filtered: dict[str, str] = {}
    drops = {"dnt_collision": 0, "self_reference": 0, "unknown_key": 0, "case_duplicate": 0}

    if not isinstance(tb, dict):
        return filtered, drops

    # Build lower -> canonical surface form from allowed_terms (first wins,
    # matching cleaned_terms's own first-seen-wins dedup).
    lower_to_surface: dict[str, str] = {}
    for t in allowed_terms:
        if isinstance(t, dict):
            term = str(t.get("term", "")).strip()
            if term:
                lower_to_surface.setdefault(term.lower(), term)

    seen_lower: set[str] = set()
    for k, v in tb.items():
        if not k or not v:
            continue
        k_clean = str(k).strip()
        v_clean = str(v).strip()
        if not k_clean or not v_clean:
            continue
        k_lower = k_clean.lower()
        if k_lower in dnt_set:
            drops["dnt_collision"] += 1
            continue
        if k_lower == v_clean.lower():
            drops["self_reference"] += 1
            continue
        if lower_to_surface and k_lower not in lower_to_surface:
            drops["unknown_key"] += 1
            continue
        if k_lower in seen_lower:
            drops["case_duplicate"] += 1
            continue
        seen_lower.add(k_lower)
        # Normalize to canonical surface form so post-fill's case-sensitive
        # lookup against cleaned_terms succeeds. Falls back to the model's
        # casing when allowed_terms is empty (no canonical reference).
        surface = lower_to_surface.get(k_lower, k_clean)
        filtered[surface] = v_clean

    return filtered, drops


class AIConfigGenerator:
    """Generates AI-powered translation configurations from SRT content"""

    def __init__(
        self,
        api_key: str,
        language_config: LanguageConfig,
        generation_model_name: str | None = None,
        temperature: float | None = None,
    ):
        """Initialize the AI config generator with OpenAI API key and language configuration"""
        if language_config is None:
            raise ValueError("LanguageConfig is required for AIConfigGenerator")
        self.api_key = api_key
        self.client = OpenAI(api_key=api_key, timeout=120.0)
        self.logger = logging.getLogger("srt_translator.gui.ai_config")
        # GUI-only generation model selection for AI config generation is intentionally
        # isolated from CLI/env to avoid cross-mode confusion
        self.temperature = temperature
        self.generation_model_name = generation_model_name or DEFAULT_GENERATION_MODEL

        # GUI-local approximation for characters per token to guide truncation.
        # Keep GUI/CLI separation: do not read from env.
        self.CHARS_PER_TOKEN = CHARS_PER_TOKEN

        # Language configuration for script validation
        self._lang_cfg = language_config

        # Configuration constants
        self.MAX_INLINE_TOKENS = get_max_inline_tokens(self.generation_model_name)

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
            prompt = build_dnt_extraction_prompt(content)

            self.logger.info("Temperature: %s", self.temperature)
            params = {
                "model": self.generation_model_name,
                "messages": [{"role": "user", "content": prompt}],
                **build_call_params(
                    self.generation_model_name,
                    max_completion_tokens=MAX_COMPLETION_TOKENS_DNT,
                    temperature=self.temperature,
                ),
            }

            response = self.client.chat.completions.create(**params)

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
    ) -> tuple[dict[str, dict[str, str]], list[str]]:
        """
        Generate a termbase per target language using a per‑language TWO‑PASS approach:
          Pass 1: ~20 topic‑critical & likely‑risky source‑language terms
          Pass 2: ~10 confusable / hard‑to‑translate source‑language terms
        Then translate those to the target language. DNT takes precedence; any term
        present in DNT is excluded from selection and filtered out if it slips through.

        Returns:
          (termbase, failed_languages) — termbase maps lang_code -> {source: target},
          failed_languages lists the codes that did not produce a termbase (after
          retries). A language can fail because its API call kept timing out, the
          model returned an empty result, or any other exception bubbled up from
          generate_language_termbase_two_pass. Surfacing this list lets the GUI
          show partial-failure summaries rather than silently dropping languages.
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
                return {}, []

            dnt_set = {term.lower().strip() for term in (dnt_terms or [])}
            termbase: dict[str, dict[str, str]] = {}
            failed_languages: list[str] = []

            # --- soft alignment anchor (first successful TB) ---
            anchor_count: int | None = None
            # derive a simple size floor from transcript size (tokens ≈ chars/4)
            approx_tokens = max(1, len(content) // self.CHARS_PER_TOKEN)
            if approx_tokens <= 400:
                size_floor = SOFT_BAND_FLOOR_SHORT
            elif approx_tokens <= 2000:
                size_floor = SOFT_BAND_FLOOR_MEDIUM
            else:
                size_floor = SOFT_BAND_FLOOR_LONG

            # default soft band BEFORE we have an anchor (content-scaled)
            # this helps the first few languages aim for a healthy size
            def _default_soft_band(tokens: int) -> tuple[int, int]:
                if tokens <= 600:
                    return SOFT_BAND_SHORT
                if tokens <= 2000:
                    return SOFT_BAND_MEDIUM
                # long content
                return SOFT_BAND_LONG

            default_lo, default_hi = _default_soft_band(approx_tokens)

            self.logger.info("Per‑language TWO‑PASS extraction + translation (source‑language agnostic)")
            for lang_code in valid_languages:
                lang_name = self._lang_cfg.get_language_name(lang_code)
                if not lang_name:
                    self.logger.warning("Could not get language name for %s, skipping", lang_code)
                    failed_languages.append(lang_code)
                    continue
                try:
                    # compute soft band (clamped to defaults)
                    if anchor_count:
                        tol = max(ANCHOR_TOLERANCE_MIN, round(anchor_count * ANCHOR_TOLERANCE_FRACTION))
                        soft_lo = max(default_lo, min(default_hi, max(MIN_ANCHOR_TERM_COUNT, anchor_count - tol)))
                        soft_hi = max(soft_lo, min(default_hi, min(SOFT_BAND_HARD_CAP, anchor_count + tol)))
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
                        time.sleep(random.uniform(JITTER_SLEEP_LOW, JITTER_SLEEP_HIGH))  # nosec B311

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
                        failed_languages.append(lang_code)
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
                        if size >= max(size_floor, MIN_ANCHOR_TERM_COUNT) and coverage >= MIN_ANCHOR_COVERAGE:
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
                    failed_languages.append(lang_code)
                    continue

            self.logger.info("Generated termbase for %s languages (per‑language two‑pass)", len(termbase))
            if failed_languages:
                self.logger.warning(
                    "AI termbase generation failed for %d of %d languages: %s",
                    len(failed_languages),
                    len(valid_languages),
                    ", ".join(sorted(failed_languages)),
                )
            return termbase, failed_languages
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

        prompt = build_two_pass_termbase_prompt(
            lang_name=lang_name,
            lang_code=lang_code,
            content=content,
            dnt_terms=dnt_terms,
            soft_lo=soft_lo,
            soft_hi=soft_hi,
            source_language=source_language,
        )

        try:
            params = {
                "model": self.generation_model_name,
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
                **build_call_params(
                    self.generation_model_name,
                    max_completion_tokens=MAX_COMPLETION_TOKENS_VALIDATE,
                    temperature=self.temperature,
                ),
            }

            response = _call_with_retry(
                lambda: self.client.chat.completions.create(**params),
                context=lang_code,
                logger=self.logger,
            )
            raw = (response.choices[0].message.content or "").strip()
            data = json.loads(raw)
            exhausted = bool(data.get("exhausted") or False)
            exhaustion_reason = data.get("exhaustion_reason")
            response_pass1 = data.get("pass1_terms", []) or []
            response_pass2 = data.get("pass2_terms", []) or []
            extracted = response_pass1 + response_pass2
            tb = data.get("termbase", {}) or {}
            # Capture the model's own pass assignment now, before the local
            # `pass1_terms` / `pass2_terms` accumulators below shadow these
            # names. Used in place of English-keyword matching on the reason
            # text, which silently miscategorizes when the model writes
            # reasons in the target language.
            _response_pass_assignment = _build_pass_assignment(response_pass1, response_pass2)

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
                singles_keep = [t for t in singles if count_distinct_lines(t, lines) >= MIN_GENERIC_SINGLETON_LINE_FREQ]
                singles_budget = max(0, MAX_GENERIC_SINGLETONS - len(singles_keep))
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

                # Debug: log a few reasons to see what the AI is actually writing
                if len(cleaned_terms) < 3:
                    self.logger.debug("Sample reason for '%s': '%s'", term, reason)

                # Categorize using the model's own pass assignment from the
                # response. Default to pass1 if the term isn't in either
                # response array (e.g. terms added later by the top-up path,
                # which doesn't carry pass info).
                if _response_pass_assignment.get(term.lower()) == "pass2":
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
                ask_low = needed + max(
                    ANCHOR_TOLERANCE_MIN, needed // TOPUP_OVERSAMPLE_DIVISOR
                )  # e.g., need 3 -> ask 4 or 5
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

            # Filter the raw termbase response. Validate against cleaned_terms,
            # not the model's full pass1+pass2 response — otherwise terms the
            # cap dropped or prune_generics removed would still leak into the
            # saved tb_dict. (Observed leak: zh-Hans returning ~49 entries
            # under a soft_hi of ~30 because the model over-generated and the
            # filter validated against the uncapped extracted list.)
            tb_dict, _tb_drops = _filter_termbase_response(tb, cleaned_terms, dnt_set)
            if any(_tb_drops.values()):
                self.logger.warning(
                    "[%s] Dropped %d malformed termbase entries from model response: "
                    "%d DNT collisions, %d self-references, %d unknown keys (not in cleaned terms), "
                    "%d case-only duplicates",
                    lang_code,
                    sum(_tb_drops.values()),
                    _tb_drops["dnt_collision"],
                    _tb_drops["self_reference"],
                    _tb_drops["unknown_key"],
                    _tb_drops["case_duplicate"],
                )

            # --- ensure translations exist for ALL cleaned terms ---
            src_terms = [t["term"] for t in cleaned_terms]
            missing_src = [s for s in src_terms if not tb_dict.get(s)]
            if missing_src:
                merged = {}
                for i in range(0, len(missing_src), TERMBASE_FILL_CHUNK_SIZE):
                    chunk = missing_src[i : i + TERMBASE_FILL_CHUNK_SIZE]
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
            if len(cleaned_terms) < MIN_TERMBASE_SIZE:  # Minimum reasonable size
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

            prompt = build_single_language_termbase_prompt(lang_name, term_list)

            params = {
                "model": self.generation_model_name,
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
                **build_call_params(
                    self.generation_model_name,
                    max_completion_tokens=MAX_COMPLETION_TOKENS_TERMBASE,
                    temperature=self.temperature,
                ),
            }

            response = self.client.chat.completions.create(**params)
            result_text = (response.choices[0].message.content or "").strip()
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

    def generate_batch_ai_config(
        self,
        source_file_paths: list[str],
        target_lang_codes: list[str],
        token_cap: int | None = None,
    ) -> BatchAIConfig:
        """
        Build ONE batch-level DNT list and ONE termbase (per target language)
        by sampling up to ~12,500 tokens (~50k chars) from the selected source SRTs.
        """

        generation_model_name = self.generation_model_name

        generation_model_config = get_model_config(generation_model_name)

        if not generation_model_config:
            raise ValueError(f"Generation model config not found for {generation_model_name}")

        TOKEN_CAP = generation_model_config["model_context_length"]

        CHAR_CAP = TOKEN_CAP * _CHARS_PER_TOKEN

        self.logger.info("Generation model selected: %s", generation_model_name)
        self.logger.info("Generation model context length (tokens): %s", TOKEN_CAP)
        self.logger.info("Calculated character cap: %s", CHAR_CAP)

        if not source_file_paths:
            raise ValueError("No source files provided for AI config generation.")

        # 1) Read & parse SRTs, concatenate subtitle text up to char budget
        if token_cap is None:
            token_cap = TOKEN_CAP
        char_budget = token_cap * _CHARS_PER_TOKEN
        sampler = []
        total = 0
        parser = SRTParser()

        for path in source_file_paths:
            try:
                subs = parser.parse_file(path)
            except Exception:
                # Fallback: read raw text if parsing fails
                with open(path, encoding="utf-8", errors="replace") as f:
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

        # 2) Detect source language. Detection uses DEFAULT_DETECTION_MODEL
        # (not the user's generation model) — see language_detection.py.
        source_lang = detect_source_language(
            transcript_sample,
            chat=self.client,
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
        termbase_by_lang, failed_languages = self.generate_termbase(
            transcript_sample,
            target_lang_codes,
            dnt_terms=dnt_terms,
            source_language=source_lang,
        )
        self.logger.info("Generated termbase for %s languages (batch-level)", len(termbase_by_lang))

        return BatchAIConfig(
            dnt_terms=dnt_terms,
            termbase=termbase_by_lang,
            source_language=source_lang,
            failed_languages=failed_languages,
        )

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
        prompt = build_top_up_extraction_prompt(
            lang_name=lang_name,
            content=content,
            needed=needed,
            needed_hi=needed_hi,
            existing_terms=existing_terms,
            dnt_terms=dnt_terms,
        )
        try:
            params = {
                "model": self.generation_model_name,
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
                **build_call_params(
                    self.generation_model_name,
                    max_completion_tokens=MAX_COMPLETION_TOKENS_TERMBASE,
                    temperature=self.temperature,
                ),
            }

            response = self.client.chat.completions.create(**params)
            raw = (response.choices[0].message.content or "").strip()
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
