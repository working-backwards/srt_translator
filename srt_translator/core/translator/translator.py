# srt_translator/core/translator/translator.py
from __future__ import annotations

import json
import logging
import math
import os
import random
import re
import time
from collections import deque
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from re import Match, Pattern
from typing import (
    Any,
    TypeAlias,
    cast,
)

# OpenAI client
from openai import OpenAI
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionDeveloperMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionToolMessageParam,
    ChatCompletionUserMessageParam,
)

# Core imports
from srt_translator.core.config.language_config import LanguageConfig

# Helper imports
from srt_translator.core.translator._helpers import (
    _create_batches_with_logging,
    _handle_mid_batch_empty_retries,
    _is_invalid_translation,
    _translate_batch_and_extract,
)
from srt_translator.core.translator.diagnostics import (
    MalformedProbeBudget,
    build_oversize_probe_question,
    estimate_tokens,
    looks_like_repetitive_loop,
    probe_malformed_json_with_translator,
    snip,
)
from srt_translator.core.translator.subtitle_formatter import format_subtitle_text
from srt_translator.core.translator.term_handler import TermHandler
from srt_translator.core.utils.log_types import LoggerLike

# ---------------------------
# Data models
# ---------------------------


@dataclass
class Subtitle:
    idx: int
    start: str  # "HH:MM:SS,mmm"
    end: str  # "HH:MM:SS,mmm"
    text: str


# ---------------------------
# Utilities
# ---------------------------


TIME_RE: Pattern[str] = re.compile(r"(?P<h>\d{2}):(?P<m>\d{2}):(?P<s>\d{2}),(?P<ms>\d{3})")

PH_RE: Pattern[str] = re.compile(r"__DNT_TERM_(\d+)__")
# Detector (Stage 1): placeholder immediately followed by apostrophe (straight or curly)
TR_PLACEHOLDER_APOS_RE: Pattern[str] = re.compile(r"__DNT_TERM_\d+__['']")

# Union type for OpenAI chat message params (for mypy)
ChatMsg: TypeAlias = (
    ChatCompletionDeveloperMessageParam
    | ChatCompletionSystemMessageParam
    | ChatCompletionUserMessageParam
    | ChatCompletionAssistantMessageParam
    | ChatCompletionToolMessageParam
)


def _parse_time_to_seconds(ts: str) -> float:
    m = TIME_RE.match(ts)
    if not m:
        return 0.0
    h = int(m.group("h"))
    m_ = int(m.group("m"))
    s = int(m.group("s"))
    ms = int(m.group("ms"))
    return h * 3600 + m_ * 60 + s + ms / 1000.0


def parse_srt(text: str) -> list[Subtitle]:
    """
    Parse SRT content into Subtitle objects.
    Handles empty cues correctly by stopping at blank lines or next index.
    """
    subs: list[Subtitle] = []

    # Split into blocks by double newlines
    blocks = re.split(r"\r?\n\r?\n", text.strip())

    for block in blocks:
        if not block.strip():
            continue

        lines = block.strip().split("\n")
        if len(lines) < 2:
            continue

        try:
            # First line should be index
            idx = int(lines[0].strip())

            # Second line should be timing
            timing_match = re.match(r"(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})", lines[1])
            if not timing_match:
                continue

            start, end = timing_match.groups()

            # Remaining lines are text (may be empty)
            body = "\n".join(lines[2:]).strip() if len(lines) > 2 else ""

            subs.append(Subtitle(idx=idx, start=start, end=end, text=body))

        except (ValueError, IndexError) as exc:
            # Skip malformed blocks; log once per block for visibility at debug level.
            # This preserves resiliency without hiding systematic formatting issues.
            logging.getLogger(__name__).debug("Skipping malformed SRT block: %s", exc)
            continue

    return subs


def render_srt(subs: Sequence[Subtitle]) -> str:
    """
    Render target SRT using original timings.
    IMPORTANT: We ALWAYS emit a block—even if the translated text is empty.
    This preserves 1:1 cue parity and timings, allowing the evaluator to
    surface true 'Missing translation' instead of silently shifting indices.
    """
    parts: list[str] = []
    for i, sub in enumerate(subs, start=1):
        translated = (sub.text or "").strip()
        parts.append(str(i))
        parts.append(f"{sub.start} --> {sub.end}")
        parts.append(translated if translated else "")
        parts.append("")  # blank line
    return "\n".join(parts).rstrip() + "\n"


def build_termbase_block(termbase: dict[str, dict[str, str]], lang_code: str) -> str:
    lang = lang_code.lower()
    if not termbase or lang not in termbase:
        return "(none)"
    pairs = termbase[lang]
    if not pairs:
        return "(none)"
    # Render as "source → target" lines
    lines = [f"- {src} → {tgt}" for src, tgt in pairs.items()]
    return "\n".join(lines)


# DNT placeholder validation helpers
def _extract_ph_ids(text: str, ph_regex: Pattern[str]) -> set[str]:
    return set(ph_regex.findall(text or ""))


def validate_placeholders_pair(
    src_items: list[str],
    tgt_items: list[str],
    ph_regex: Pattern[str],
) -> dict[int, dict[str, set[str]]]:
    issues: dict[int, dict[str, set[str]]] = {}
    for i, (src, tgt) in enumerate(zip(src_items, tgt_items, strict=False)):
        src_ids = _extract_ph_ids(src, ph_regex)
        tgt_ids = _extract_ph_ids(tgt, ph_regex)
        invented = tgt_ids - src_ids
        missing = src_ids - tgt_ids
        if invented or missing:
            issues[i] = {"invented": invented, "missing": missing}
    return issues


def strip_invented_placeholders(text: str, invented_ids: set[str], ph_regex: Pattern[str]) -> str:
    if not invented_ids:
        return text

    def _sub(m: Match[str]) -> str:
        pid = m.group(1)
        return "" if pid in invented_ids else m.group(0)

    return ph_regex.sub(_sub, text or "")


# ---------------------------
# Stage 1A Helper Methods (stay in translator.py)
# ---------------------------


def _load_and_parse_file(input_filepath: str) -> list[Subtitle]:
    """Load and parse SRT file into subtitle objects."""
    with open(input_filepath, encoding="utf-8") as f:
        src_text = f.read()
    src_subs = parse_srt(src_text)
    if not src_subs:
        raise ValueError("Empty or invalid SRT: no subtitle blocks found.")
    return src_subs


def _format_and_append_subtitles(
    _self: SRTTranslator,
    batch: list[Subtitle],
    tgt_texts: list[str],
    target_lang: str,
    cps_cap: int | None,
    _file_logger: LoggerLike,
) -> list[Subtitle]:
    """Format subtitles with CPS and append to global list."""
    formatted_subs = []
    for s, tgt in zip(batch, tgt_texts, strict=False):
        start_s = _parse_time_to_seconds(s.start)
        end_s = _parse_time_to_seconds(s.end)
        formatted = format_subtitle_text(
            lang_code=target_lang.lower(),
            text=tgt,
            start_ms=int(start_s * 1000),  # Convert seconds to milliseconds
            end_ms=int(end_s * 1000),  # Convert seconds to milliseconds
            cps_cap=cps_cap or 20,  # Default to 20 if None
        )
        formatted_subs.append(Subtitle(idx=s.idx, start=s.start, end=s.end, text=formatted))
    return formatted_subs


# ---------------------------
# SRTTranslator
# ---------------------------


class SRTTranslator:
    # Explicit attribute types to avoid "Cannot determine type of X"
    logger: LoggerLike
    term_handler: TermHandler

    # Expert configuration - modify these values as needed
    MAX_BATCH_SIZE = 8  # Maximum subtitles per batch (safety cap)
    # Internal bounded shape-lock caps (not user-configurable)
    _MAX_SPLIT_DEPTH = 3
    _MAX_JSON_RETRIES_PER_SEGMENT = 2
    _MAX_CONSECUTIVE_DECODE_FAILURES = 8
    _MICRO_BACKOFF_BASE_S = 0.25
    _MICRO_BACKOFF_CAP_S = 1.0

    def __init__(
        self,
        *,
        dnt_terms: list[str],
        termbase: dict[str, dict[str, str]],
        api_key: str,
        logger: logging.Logger,  # Required - no fallback allowed
        allow_global_termbase_fallback: bool = False,
        model_name: str = "gpt-4o-mini",
        batch_size: int,
        error_policy: str = "STRICT",
        language_config: LanguageConfig,
        tone: str = "neutral",
    ) -> None:
        if logger is None:
            raise ValueError("SRTTranslator requires an application logger (non-None).")

        self.dnt_terms = dnt_terms or []
        self.termbase = termbase or {}
        self.allow_global_termbase_fallback = allow_global_termbase_fallback
        self.model_name = model_name
        self.batch_size = max(1, int(batch_size))
        self.error_policy = error_policy.upper()
        self.tone = tone.lower() if tone else "neutral"

        # Log the tone setting for debugging
        if isinstance(logger, logging.LoggerAdapter):
            logger.logger.debug("SRTTranslator initialized with tone: '%s'", self.tone)
        else:
            logger.debug("SRTTranslator initialized with tone: '%s'", self.tone)

        # Make a namespaced child for clarity in logs
        if isinstance(logger, logging.LoggerAdapter):
            self.logger = logger.logger.getChild("core.translator")
        else:
            self.logger = logger.getChild("core.translator")

        # If caller gave an adapter, re-wrap child with the same extra
        if isinstance(logger, logging.LoggerAdapter):
            self.logger = logging.LoggerAdapter(self.logger, logger.extra)

        if language_config is None:
            raise ValueError("SRTTranslator requires a LanguageConfig (non-None).")
        self.language_config = language_config

        # Initialize TermHandler for DNT and termbase management
        self.term_handler = TermHandler(
            dnt_terms=self.dnt_terms,
            termbase=self.termbase,
            lang_code=None,  # Will be set per file/lang
            logger=self.logger,
        )

        if OpenAI is None:
            raise RuntimeError("OpenAI client not available; install/openai and configure API key.")

        self.client = OpenAI(api_key=api_key)

        # One-shot advisory probe budget per (file, lang)
        self._probe_budget = MalformedProbeBudget()
        # Probe budget: only ask the "why was it oversized?" question once per target language
        self._probe_budget_langs: set[str] = set()
        # Simple per-file/lang circuit breaker for repeated JSON failures
        self._consecutive_decode_failures = 0

    def _strict_retry_kwargs(self, src_items: list[str]) -> dict[str, Any]:
        """
        Strict decoding for retries: cools repetition and caps length conservatively,
        but guarantees enough budget to close the JSON wrapper even for tiny inputs.
        """
        src_tok = sum(estimate_tokens(s or "") for s in src_items)
        cap = int(math.ceil(2.4 * max(1, src_tok)))
        floor = 120  # <-- token floor: prevents cut-off JSON on very short cues
        max_tokens = min(900, max(floor, cap))
        return {
            "temperature": 0,
            "frequency_penalty": 0.6,  # discourage loops like "ek ek ek…"
            "presence_penalty": 0.0,
            "max_tokens": max_tokens,
            # Optional: stop right after JSON; remove if provider doesn't support 'stop'
            "stop": ["]}"],
        }

    def _setup_file_logging(
        self: SRTTranslator, input_filepath: str, target_lang: str
    ) -> logging.LoggerAdapter[logging.Logger]:
        """Setup file-scoped logging with file/lang context."""

        # Ensure we pass a real `logging.Logger` to LoggerAdapter (not a LoggerAdapter / Protocol)
        if isinstance(self.logger, logging.LoggerAdapter):
            base_logger: logging.Logger = self.logger.logger
        else:
            base_logger = cast(logging.Logger, self.logger)

        extra: Mapping[str, object] = {
            "run_id": getattr(getattr(self.logger, "extra", {}), "get", lambda *_: "n/a")("run_id", "n/a"),
            "file": os.path.basename(input_filepath),
            "lang": target_lang,
        }

        # Parameterize the adapter so MyPy knows its type argument
        file_logger: logging.LoggerAdapter[logging.Logger] = logging.LoggerAdapter(base_logger, extra)
        return file_logger

    def _validate_and_repair_placeholders(
        self,
        src_items: list[str],
        tgt_texts: list[str],
        batch_ids: list[int],
        batch_logger: LoggerLike,
    ) -> list[str]:
        """Validate and repair placeholder integrity."""
        # Log input/output for troubleshooting placeholder issues
        for i, (src, tgt) in enumerate(zip(src_items, tgt_texts, strict=False)):
            # Use the regex pattern directly to avoid logging violations
            src_placeholders = PH_RE.findall(src)
            tgt_placeholders = PH_RE.findall(tgt)
            if src_placeholders or tgt_placeholders:
                batch_logger.debug(
                    "Placeholder comparison (item=%d):\n"
                    "  Source: %s\n"
                    "  Target: %s\n"
                    "  Source placeholders: %s\n"
                    "  Target placeholders: %s",
                    i,
                    src,
                    tgt,
                    src_placeholders,
                    tgt_placeholders,
                )

        # Policy-aware placeholder validation for apostrophes after placeholders
        target_lang = getattr(getattr(batch_logger, "extra", {}), "get", lambda *_: "unknown")("lang", "unknown")
        if self.language_config.allows_placeholder_apostrophe(target_lang.lower()):
            # Normalize for detection only: treat "__...__'..." as "__...__"
            norm_tgts = [TR_PLACEHOLDER_APOS_RE.sub(lambda m: m.group(0)[:-1], t) for t in tgt_texts]
            ph_issues = validate_placeholders_pair(src_items, norm_tgts, self.term_handler.placeholder_regex)
            # Once-per-batch debug (observational only)
            seen = False
            for i, (_s_i, t_i) in enumerate(zip(src_items, tgt_texts, strict=False)):
                if TR_PLACEHOLDER_APOS_RE.search(t_i) and not seen:
                    batch_logger.debug(
                        "Apostrophe after placeholder observed (allowed for %s, item=%d).",
                        target_lang,
                        i,
                    )
                    seen = True
                    break
        else:
            ph_issues = validate_placeholders_pair(src_items, tgt_texts, self.term_handler.placeholder_regex)
            # Stage 1: language-agnostic detector (observational logging only, once per batch)
            seen = False

            for i, (s_i, t_i) in enumerate(zip(src_items, tgt_texts, strict=False)):
                if TR_PLACEHOLDER_APOS_RE.search(t_i) and not seen:
                    batch_logger.debug(
                        "Observed apostrophe immediately after placeholder (item=%d, lang=%s). Source≈%s | Target≈%s",
                        i,
                        target_lang,
                        snip(s_i),
                        snip(t_i),
                    )
                    seen = True
                    break

        # Run drift repair BEFORE mutating targets (e.g., before stripping invented tokens),
        # so we can split on the actual placeholder token (e.g., __DNT_TERM_12__).
        tgt_texts = self._repair_adjacent_placeholder_drift(
            _src_items=src_items,
            tgt_items=tgt_texts,
            ph_issues=ph_issues,
            batch_ids=batch_ids,
            logger=batch_logger,
        )

        if ph_issues:
            for idx, kinds in ph_issues.items():
                inv = ",".join(sorted(kinds["invented"])) or "-"
                mis = ",".join(sorted(kinds["missing"])) or "-"
                batch_logger.warning(
                    "Placeholder check (item=%d): invented=[%s] missing=[%s]",
                    idx,
                    inv,
                    mis,
                )

            if self.error_policy == "STRICT":
                fixed = self._reformat_fix_placeholders(
                    src_items=src_items,
                    tgt_items=tgt_texts,
                    ids=batch_ids,
                    allowed_placeholders=sorted(self.term_handler.placeholder_map.keys()),
                )
                if fixed is None:
                    raise RuntimeError("Reformat failed: phantom/missing placeholders unresolved.")
                tgt_texts = fixed
            elif self.error_policy in ("BOUNDED", "DEV"):
                # After repair, remove any remaining invented tokens; warn about missing but do not invent content.
                for i, kinds in ph_issues.items():
                    if kinds["invented"]:
                        tgt_texts[i] = strip_invented_placeholders(
                            tgt_texts[i],
                            kinds["invented"],
                            self.term_handler.placeholder_regex,
                        )

        # Restore DNT placeholders to originals
        tgt_texts = [self.term_handler.restore_dnt_placeholders(t) for t in tgt_texts]

        tgt_texts = [self.term_handler.restore_termbase(t, target_lang) for t in tgt_texts]
        return tgt_texts

    # --- Sentence-aware batching ----------------------------
    def _create_batches(
        self,
        subtitles: list[Subtitle],
        target_size: int,
        max_size: int,
        target_lang: str,
    ) -> list[list[Subtitle]]:
        """
        Group consecutive subtitles into batches that prefer ending at a natural
        sentence boundary once the target size is reached, without exceeding
        the maximum size.  Each subtitle remains its own item (1:1 id mapping).
        """
        if not subtitles:
            return []

        batches: list[list[Subtitle]] = []
        current: list[Subtitle] = []

        # Pull language-specific rules from the injected language_config, if present.
        # Falls back to a generic set if not available.
        sentence_endings = (".", "!", "?", "…")
        try:
            if self.language_config:
                rules = self.language_config.get_language_rules(target_lang) or {}
                if isinstance(rules.get("sentence_endings"), list):
                    sentence_endings = tuple(rules["sentence_endings"])
        except (AttributeError, TypeError, KeyError) as exc:
            # Fallback to defaults; log at debug so we can diagnose config shape issues.
            self.logger.debug(
                "No language-specific sentence_endings for %s (%s: %s)",
                target_lang,
                type(exc).__name__,
                exc,
            )

        for sub in subtitles:
            current.append(sub)

            # If we hit the maximum cap, cut the batch immediately.
            if len(current) >= max_size:
                batches.append(current)
                current = []
                continue

            # If we've reached the target size, prefer to break on a sentence end.
            if len(current) >= target_size:
                text = (sub.text or "").strip()
                if any(text.endswith(end) for end in sentence_endings):
                    batches.append(current)
                    current = []

        if current:
            batches.append(current)

        return batches

    # ---------- Stage 1A Helper Methods ----------

    # ---------- Public API ----------

    def translate_file(
        self,
        *,
        input_filepath: str,
        output_filepath: str,
        target_lang: str,
    ) -> None:
        # Reset consecutive failure counter for this file/lang run
        self._consecutive_decode_failures = 0

        # 1) Setup file logging and load/parse SRT
        file_logger = self._setup_file_logging(input_filepath, target_lang)
        file_logger.info(
            "Using subtitle-based translation system for %s → %s",
            os.path.basename(input_filepath),
            target_lang,
        )

        src_subs = _load_and_parse_file(input_filepath)
        self.logger.info(
            "Processing %d subtitles for %s",
            len(src_subs),
            os.path.basename(input_filepath),
        )

        # 2) Create batches with logging
        batches = _create_batches_with_logging(self, src_subs, target_lang, file_logger)
        all_tgt_subs: list[Subtitle] = []

        # === Cross-batch pair-retry state ===================================
        # If the *last* cue of a batch returns empty, we cannot repair it inside
        # the same batch (no "next" cue available). We defer a one-shot pair-retry
        # to the start of the next loop iteration, when the head of the next batch
        # is available. We then patch the fixed text back into all_translated_texts.
        #
        # We keep at most one deferred retry at a time; it is resolved immediately
        # on the next batch. This preserves both invariants:
        #   - 1:1 cue parity with source
        #   - original timings unchanged
        deferred_tail_retry: dict[str, Any] | None = None

        # Language CPS cap
        cps_cap = self.language_config.get_cps_cap(target_lang)

        for bi, batch in enumerate(batches, start=1):
            # Batch-scoped logger with correlation ids
            batch_logger = logging.LoggerAdapter(file_logger, {"batch": bi, "ids": [s.idx for s in batch]})

            # Handle deferred tail now, pairing with THIS batch's head via shape-lock
            if deferred_tail_retry is not None:
                if batch:
                    head = batch[0]
                    pair_src = [
                        deferred_tail_retry["source_text_with_placeholders"],
                        self.term_handler.apply_dnt_placeholders(self.term_handler.apply_termbase(head.text)),
                    ]
                    pair_ids = [deferred_tail_retry["cue_index"], head.idx]
                    batch_logger.debug(
                        "Empty target at idx=%s; pair retry across batch boundary (pair_ids=%s).",
                        deferred_tail_retry["cue_index"],
                        pair_ids,
                    )
                    try:
                        pair_tgts = self._translate_with_simple_shape_lock(
                            pair_src,
                            target_lang,
                            self.termbase,
                            pair_ids,
                            logger=batch_logger,
                        )
                        fixed = pair_tgts[0].get("text", "") if pair_tgts else ""
                        if fixed:
                            # Restore DNT placeholders first
                            fixed = self.term_handler.restore_dnt_placeholders(fixed)
                            # Then restore termbase for the target language
                            fixed = self.term_handler.restore_termbase(fixed, target_lang)
                        if fixed.strip():
                            all_tgt_subs[deferred_tail_retry["out_index"]].text = fixed
                            batch_logger.debug(
                                "Pair retry filled idx=%s successfully.",
                                deferred_tail_retry["cue_index"],
                            )
                        else:
                            batch_logger.error(
                                "Empty translation for subtitle idx=%s; leaving empty for evaluator.",
                                deferred_tail_retry["cue_index"],
                            )
                    except Exception as ex:
                        batch_logger.debug(
                            "Pair retry failed for idx=%s: %s",
                            deferred_tail_retry["cue_index"],
                            ex,
                        )
                        batch_logger.warning(
                            "Empty translation for subtitle idx=%s; leaving empty for evaluator.",
                            deferred_tail_retry["cue_index"],
                        )
                    finally:
                        deferred_tail_retry = None
                else:
                    batch_logger.warning(
                        "Empty translation for subtitle idx=%s at end-of-file; leaving empty for evaluator.",
                        deferred_tail_retry["cue_index"],
                    )
                    deferred_tail_retry = None

            # One-line heartbeat for creators (keep at INFO)
            batch_logger.info(
                "Batch %d/%d: processing %d subtitles (file=%s ids=%s)",
                bi,
                len(batches),
                len(batch),
                os.path.basename(input_filepath),
                [s.idx for s in batch],
            )

            # Preprocess: apply DNT placeholders on a per-subtitle basis
            src_items = [
                self.term_handler.apply_dnt_placeholders(self.term_handler.apply_termbase(s.text)) for s in batch
            ]

            # Log source items being sent to AI for troubleshooting
            file_logger.debug(
                "Sending batch %d/%d to AI (lang=%s):\n%s",
                bi,
                len(batches),
                target_lang,
                "\n".join([f"  {i}: {text}" for i, text in enumerate(src_items)]),
            )

            # 3) Translate batch and validate placeholders
            tgt_texts = _translate_batch_and_extract(
                self,
                src_items=src_items,
                batch_ids=[s.idx for s in batch],
                target_lang=target_lang,
                batch_logger=batch_logger,
            )

            tgt_texts = self._validate_and_repair_placeholders(
                src_items=src_items,
                tgt_texts=tgt_texts,
                batch_ids=[s.idx for s in batch],
                batch_logger=batch_logger,
            )

            # 3a) Handle mid-batch empty retries
            tgt_texts = _handle_mid_batch_empty_retries(
                self,
                batch=batch,
                tgt_texts=tgt_texts,
                target_lang=target_lang,
                batch_logger=batch_logger,
            )

            # 4) Format and append subtitles
            formatted_subs = _format_and_append_subtitles(
                self,
                batch=batch,
                tgt_texts=tgt_texts,
                target_lang=target_lang,
                cps_cap=cps_cap,
                _file_logger=file_logger,
            )
            all_tgt_subs.extend(formatted_subs)

        # 3) Render and write
        out_text = render_srt(all_tgt_subs)
        with open(output_filepath, "w", encoding="utf-8") as f:
            f.write(out_text)

        # Defer fixes to core.main; just log what we produced.
        if file_logger:
            file_logger.debug(
                "Translated %s → %s (lang=%s). Placeholder restoration will run in core.main Fixer pass.",
                os.path.basename(input_filepath),
                os.path.basename(output_filepath),
                target_lang,
            )

        file_logger.info(
            "Subtitle-based translation completed for %s",
            os.path.basename(input_filepath),
        )

    # ---------- Core calls ----------

    def _translate_batch_json(
        self,
        *,
        src_items: list[str],
        target_lang: str,
        termbase: dict[str, dict[str, str]],
        batch_ids: list[int],
        strict: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Ask for JSON ONLY: {"items":[{"id":<int>,"tgt":"..."}]}
        One item per input, same order and ids.
        """
        termbase_block = build_termbase_block(termbase, target_lang)
        mapped_target_lang = target_lang

        system_prompt = "You are a professional subtitle translator. Return valid JSON ONLY, never prose."
        if strict:
            system_prompt += (
                " Hard constraint: never repeat any single word/syllable/token more than 3 times consecutively;"
                " do not pad, chant, or fill with repeated fragments."
            )

        # Add tone-critical instruction to system prompt for languages with strong formality distinctions
        lang_hint = self.language_config.get_tone_hint(target_lang, self.tone)
        if lang_hint and target_lang.lower().startswith("zh"):
            # Chinese has critical 你/您 distinction - add to system prompt for higher priority
            system_prompt += f" CRITICAL for {target_lang}: {lang_hint}"

        # Build TONE and optional LANG_HINT section
        tone_section = f"TONE: {self.tone}\n"
        lang_hint = self.language_config.get_tone_hint(target_lang, self.tone)
        if lang_hint:
            tone_section += f"\nLANG_HINT ({target_lang}): {lang_hint}\n"
            self.logger.debug("Tone hint found for %s (%s): %s", target_lang, self.tone, lang_hint)
        else:
            self.logger.debug("No tone hint found for %s (%s)", target_lang, self.tone)

        # Log the complete tone section being inserted into prompt
        self.logger.debug("Prompt tone section for %s:\n%s", target_lang, tone_section.strip())

        # The translation rules here preserve the core behavior you've tuned:
        user_prompt = f"""Translate each item to {mapped_target_lang}. Keep 1:1 count and order.

TERMINOLOGY:
Use these business term mappings when present (source → target). If "(none)", ignore:
{termbase_block}

DNT PLACEHOLDERS:
- If you see placeholders like __DNT_TERM_7__, keep them EXACTLY as written.
- Do not invent or drop placeholders.
- Never invent __DNT_TERM_n__ placeholders. Only preserve those already present in the input.

STRUCTURE:
- Return JSON ONLY as: {{"items":[{{"id":<int>,"tgt":"..."}}, ...]}}
- The "items" array MUST have exactly {len(src_items)} objects.
- Use the provided ids 1:1 with the inputs below. Do not merge or split.
- Do not include SRT timestamps in the output. Only JSON.

STYLE:
- Natural, fluent translation.
- Numbers: keep digits; localize formatting where normal. No rounding.
- No added/removed content.

{tone_section}
INPUT ITEMS:
{self._render_items_for_prompt(batch_ids, src_items)}
"""

        # Prepare the messages payload for logging (typed for mypy)
        messages_payload: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        messages_typed = cast(Sequence[ChatMsg], messages_payload)

        # Use JSON mode if available; otherwise rely on instruction.
        kwargs = (
            self._strict_retry_kwargs(src_items)
            if strict
            else {"temperature": 0.1, "response_format": {"type": "json_object"}}
        )
        resp = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages_typed,
            **kwargs,
        )
        content = (resp.choices[0].message.content or "").strip()

        # --- Oversize/repetition diagnostics (purely advisory; never changes flow) ---

        prompt_token_est = estimate_tokens(user_prompt)
        response_token_est = estimate_tokens(content or "")
        repetitive_loop = looks_like_repetitive_loop(content or "")

        # Heuristic: response wildly larger than prompt (>= 4x), or loop detected
        oversize = response_token_est >= 4 * prompt_token_est
        if oversize or repetitive_loop:
            self.logger.debug(
                "Diag: token_est prompt=%d, response=%d, total≈%d (chars: prompt=%d, response=%d)",
                prompt_token_est,
                response_token_est,
                prompt_token_est + response_token_est,
                len(user_prompt or ""),
                len(content or ""),
            )

            # Ask the AI *once per language* why it might have done this.
            if target_lang not in self._probe_budget_langs:
                self._probe_budget_langs.add(target_lang)
                try:
                    # Build a concise source excerpt and response preview for the question
                    # Limit source items to the same number we asked the model to translate.
                    src_excerpt: Sequence[str] = tuple(src_items[: min(len(src_items), 8)])
                    response_preview = content or ""
                    if len(response_preview) > 500:
                        response_preview = response_preview[:500] + "…"

                    question = build_oversize_probe_question(
                        lang_code=target_lang,
                        batch_ids=batch_ids,
                        source_items=src_excerpt,
                        response_preview=response_preview,
                        prompt_token_estimate=prompt_token_est,
                        response_token_estimate=response_token_est,
                        repetitive_loop_detected=repetitive_loop,
                    )

                    self.logger.info(
                        "Probing AI for oversized/malformed response (lang=%s, ids=%s)",
                        target_lang,
                        batch_ids,
                    )
                    diag_resp = self.client.chat.completions.create(
                        model=self.model_name,
                        messages=cast(
                            Sequence[ChatMsg],
                            [
                                {
                                    "role": "system",
                                    "content": (
                                        "You are a concise diagnostic assistant. "
                                        "Explain the likely reason for the prior translation model's oversized "
                                        "or repetitive output in 1–2 sentences. Do not produce translations."
                                    ),
                                },
                                {"role": "user", "content": question},
                            ],
                        ),
                        temperature=0,
                        max_tokens=160,
                    )
                    diag_text = (diag_resp.choices[0].message.content or "").strip()
                    self.logger.debug(
                        "AI diagnostic explanation (lang=%s, ids=%s): %s",
                        target_lang,
                        batch_ids,
                        snip(diag_text, 400),
                    )
                except Exception as probe_ex:
                    self.logger.debug(
                        "AI diagnostic probe failed (lang=%s, ids=%s): %s",
                        target_lang,
                        batch_ids,
                        probe_ex,
                    )

        # Log the raw AI response for troubleshooting
        self.logger.debug(
            "AI response for batch (lang=%s, items=%d):\n%s",
            target_lang,
            len(src_items),
            content,
        )

        try:
            data = json.loads(content)
            items = data.get("items", [])
            # Normalize ids to int; ensure shape
            norm = []
            for obj in items:
                oid = obj.get("id")
                if isinstance(oid, str) and oid.isdigit():
                    oid = int(oid)
                norm.append({"id": oid, "tgt": obj.get("tgt", "")})

            # Log the parsed items for verification
            self.logger.debug(
                "Parsed %d items from AI response: %s",
                len(norm),
                [
                    {
                        "id": item["id"],
                        "tgt": (item["tgt"][:50] + "..." if len(item["tgt"]) > 50 else item["tgt"]),
                    }
                    for item in norm
                ],
            )

            # Lightweight degeneracy check per item (advisory; retry paths already exist)
            bad = []
            for i, (src, out) in enumerate(zip(src_items, norm, strict=False)):
                tgt = (out or {}).get("tgt", "")
                if not tgt:
                    continue
                if looks_like_repetitive_loop(tgt):
                    bad.append((i, "repetitive_loop"))
                    continue

                if estimate_tokens(tgt) < 0.3 * max(1, estimate_tokens(src or "")):
                    bad.append((i, "under_ratio"))

                # 2.8× is conservative; adjust later per language if needed
                if estimate_tokens(tgt) >= 2.8 * max(1, estimate_tokens(src or "")):
                    bad.append((i, "oversize_ratio"))
            if bad:
                self.logger.debug(
                    "Degenerate outputs detected (lang=%s, ids=%s, bad=%s)",
                    target_lang,
                    batch_ids,
                    bad,
                )

            # (Removed) legacy logger-based oversize probe; translator already ran a direct probe above.

            return norm
        except Exception:
            if self.logger.isEnabledFor(logging.DEBUG):
                self.logger.debug(
                    "Translation failure - payload and raw response captured for DEBUG (lang=%s, items=%d).",
                    target_lang,
                    len(src_items),
                )
            # Diagnostics: token estimates + repetition hint + one-time probe
            try:
                payload_text = f"System: {system_prompt}\nUser: {user_prompt}"
                prompt_tokens = estimate_tokens(payload_text)
                response_tokens = estimate_tokens(content or "")
                self.logger.debug(
                    "Diag: token_est prompt=%d, response=%d, total≈%d (chars: prompt=%d, response=%d)",
                    prompt_tokens,
                    response_tokens,
                    prompt_tokens + response_tokens,
                    len(payload_text),
                    len(content or ""),
                )
                hint_class = "repetitive_token_loop" if looks_like_repetitive_loop(content or "") else "unknown"
                file_base = "?"
                if isinstance(self.logger, logging.LoggerAdapter):
                    try:
                        extra_map = cast(Mapping[str, object], getattr(self.logger, "extra", {}))
                        file_base = str(extra_map.get("file", "?"))
                    except Exception:
                        file_base = "?"
                # Call the AI probe to understand what went wrong
                source_text = "\n".join([f"{i + 1}) {src}" for i, src in enumerate(src_items)])
                probe_malformed_json_with_translator(
                    translator=self,
                    budget=self._probe_budget,
                    file_base=file_base,
                    lang=target_lang,
                    batch_ids=batch_ids[:8],
                    raw_excerpt=(content or "")[:500],
                    hint_class=hint_class,
                    source_text=source_text,
                )
            except Exception as diag_ex:
                self.logger.debug("Diagnostics capture skipped: %s", diag_ex)

            # LAST-CHANCE FALLBACK:
            # If strict retry still produced malformed/partial JSON and there is only ONE item,
            # ask once for a plain string and wrap it into the expected JSON structure.
            if len(src_items) == 1:
                try:
                    self.logger.debug(
                        "Attempting plain-string fallback for single item (lang=%s, id=%s).",
                        target_lang,
                        (batch_ids[0] if batch_ids else "?"),
                    )
                    fallback_txt = self._translate_single_string_fallback(
                        _src_text=src_items[0],
                        target_lang=target_lang,
                    )
                    wrapped = [{"id": (batch_ids[0] if batch_ids else 1), "tgt": fallback_txt}]
                    return wrapped
                except Exception as _fallback_ex:
                    self.logger.debug("Plain-string fallback failed: %s", _fallback_ex)

            # Otherwise, let shape-lock handle it as before.
            self.logger.error("Model did not return JSON; cannot recover without shape lock.")
            raise RuntimeError("Translation failed: model did not return valid JSON format") from None

    def _translate_single_string_fallback(self, *, _src_text: str, target_lang: str) -> str:
        """
        Minimal escape hatch for repeated JSON truncation in size=1 strict retries.
        Returns ONLY a translated string; caller will wrap into JSON.
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
            "TEXT:\n{src_text}\n"
        )
        resp = self.client.chat.completions.create(
            model=self.model_name,
            messages=cast(
                Sequence[ChatMsg],
                [
                    {"role": "system", "content": sys},
                    {"role": "user", "content": usr},
                ],
            ),
            temperature=0.0,
            max_tokens=256,
        )
        out = (resp.choices[0].message.content or "").strip()
        # Be defensive about accidental quoting
        if (out.startswith('"') and out.endswith('"')) or (out.startswith("'") and out.endswith("'")):
            out = out[1:-1].strip()
        return out

    def _reformat_fix_placeholders(
        self,
        *,
        src_items: list[str],
        tgt_items: list[str],
        ids: list[int],
        allowed_placeholders: list[str],
    ) -> list[str] | None:
        """
        Ask model to remove invented placeholders and restore any missing ones
        that appear in the corresponding source item.
        """
        sys = "You are a strict placeholder fixer. Do not translate; only adjust placeholders."
        prompt = f"""Fix placeholders ONLY. Do not change wording except to:
- Remove any placeholders NOT in this allowed list: {allowed_placeholders}
- If a source item contains a placeholder, the same placeholder MUST appear in that target item.
- Keep the same number of items, same ids, same order.
- Return JSON ONLY: {{"items":[{{"id":<int>,"tgt":"..."}}, ...]}}

SOURCE ITEMS:
{self._render_items_for_prompt(ids, src_items)}

TARGET ITEMS (TO FIX):
{self._render_items_for_prompt(ids, tgt_items)}
"""

        # Prepare the messages payload for logging
        messages_payload = [
            {"role": "system", "content": sys},
            {"role": "user", "content": prompt},
        ]

        resp = self.client.chat.completions.create(
            model=self.model_name,
            messages=cast(Sequence[ChatMsg], messages_payload),
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        content = (resp.choices[0].message.content or "").strip()
        try:
            data = json.loads(content)
            items = data.get("items", [])
            if len(items) != len(ids):
                return None
            return [obj.get("tgt", "") for obj in items]
        except Exception:
            # Log the payload sent to translator and the response received when failure occurs
            self.logger.info(
                "Placeholder fix failure - Payload sent to translator:\nSystem: %s\nUser: %s",
                sys,
                prompt,
            )
            self.logger.info(
                "Placeholder fix failure - Raw response received from translator:\n%s",
                content,
            )
            return None

    # ---------- Helpers ----------

    # Removed: no backward compatibility; single cps_cap is required in config.

    @staticmethod
    def _render_items_for_prompt(ids: list[int], texts: list[str]) -> str:
        rows = []
        for i, t in zip(ids, texts, strict=False):
            clean = (t or "").replace("\n", " ").replace("{", "{{").replace("}", "}}").strip()
            rows.append(f"{i}) {clean}")
        return "\n".join(rows)

    # ---------- Adjacent placeholder drift repair ----------
    def _repair_adjacent_placeholder_drift(
        self,
        *,
        _src_items: list[str],
        tgt_items: list[str],
        ph_issues: dict[int, dict[str, set[str]]],
        batch_ids: list[int],
        logger: LoggerLike,
    ) -> list[str]:
        """
        If item i 'invented' a placeholder that item i+1 'missed', and i+1 is empty,
        the model likely under-ran and merged content forward. Split item i at the
        first occurrence of that placeholder token and move the tail to item i+1.
        This preserves cue parity and original timings. Runs BEFORE placeholder restore.
        """
        if not tgt_items or not ph_issues:
            return tgt_items

        out = list(tgt_items)
        n = len(out)

        for i in range(n - 1):
            issues_i = ph_issues.get(i)
            issues_next = ph_issues.get(i + 1)
            if not issues_i or not issues_next:
                continue

            invented_here = issues_i.get("invented", set())
            missing_next = issues_next.get("missing", set())
            if not invented_here or not missing_next:
                continue

            leaked = sorted(invented_here.intersection(missing_next))
            if not leaked:
                continue

            # Only repair when the next slot is effectively empty.
            if out[i + 1].strip():
                continue

            pid = leaked[0]
            token = f"__DNT_TERM_{pid}__"
            text_i = out[i]
            pos = text_i.find(token)
            if pos < 0:
                # Cannot locate token; skip to avoid heuristic, non-deterministic splits.
                logger.debug(
                    "adjacent-repair: token %s not found in item %d (id=%s); skipping",
                    token,
                    i,
                    batch_ids[i] if i < len(batch_ids) else "?",
                )
                continue

            head = text_i[:pos].rstrip()
            tail = text_i[pos:].lstrip()
            if not tail:
                continue

            out[i] = head
            out[i + 1] = tail

            logger.debug(
                "adjacent-repair: moved tail starting with %s from id=%s to id=%s",
                token,
                batch_ids[i] if i < len(batch_ids) else "?",
                batch_ids[i + 1] if (i + 1) < len(batch_ids) else "?",
            )

        return out

    def _translate_with_simple_shape_lock(
        self,
        src_items: list[str],
        target_lang: str,
        termbase: dict[str, dict[str, str]],
        batch_ids: list[int],
        logger: LoggerLike,
        strict: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Bounded, iterative shape-lock:
        - Try the full batch once.
        - On decode/shape failure, split into halves up to _MAX_SPLIT_DEPTH.
        - For single-item segments, allow up to _MAX_JSON_RETRIES_PER_SEGMENT micro-retries
          with tiny exponential backoff.
        - Hard-stop via a simple per-run circuit breaker to avoid infinite loops.
        Always returns a list of length == len(src_items), emitting empty targets for
        unrecoverable cues (the evaluator will flag them).
        """
        total = len(src_items)
        if total == 0:
            return []

        results: list[dict[str, Any] | None] = [None] * total

        # Queue holds (start, end, depth, retries)
        work_q: deque[tuple[int, int, int, int]] = deque()
        work_q.append((0, total, 0, 0))

        # Guard maximum iterations to ensure termination
        max_iterations = total * (self._MAX_SPLIT_DEPTH + 1) * (self._MAX_JSON_RETRIES_PER_SEGMENT + 1) + 10
        iterations = 0

        while work_q:
            iterations += 1
            if iterations > max_iterations:
                logger.error(
                    "Shape-lock guard tripped; emitting empties for remaining %d item(s).",
                    sum(e - s for s, e, _, _ in work_q),
                )
                # Emit empties for all remaining pieces
                while work_q:
                    start, end, _, _ = work_q.popleft()
                    seg_ids = batch_ids[start:end]
                    for i, cue_id in enumerate(seg_ids, start=start):
                        results[i] = {"id": cue_id, "tgt": ""}
                break

            start, end, depth, retries = work_q.popleft()
            seg_src = src_items[start:end]
            seg_ids = batch_ids[start:end]

            try:
                items = self._translate_batch_json(
                    src_items=seg_src,
                    target_lang=target_lang,
                    termbase=termbase,
                    batch_ids=seg_ids,
                    strict=strict,
                )
                if len(items) != len(seg_src):
                    raise RuntimeError(f"Count mismatch: expected {len(seg_src)} got {len(items)}")

                # Success: place into results
                for offset, obj in enumerate(items):
                    tgt = (obj.get("tgt") or "").strip()

                    if _is_invalid_translation(tgt):
                        raise RuntimeError(f"Invalid translation at cue id={seg_ids[offset]}: {tgt!r}")
                    results[start + offset] = {
                        "id": obj.get("id"),
                        "tgt": obj.get("tgt", ""),
                    }
                self._consecutive_decode_failures = 0  # reset breaker on success
                continue

            except Exception as ex:
                self._consecutive_decode_failures += 1
                logger.info(
                    "Shape-lock failure (size=%d depth=%d retries=%d): %s",
                    len(seg_src),
                    depth,
                    retries,
                    ex,
                )

                # Circuit breaker: too many failures in a row → emit empties and stop
                if self._consecutive_decode_failures >= self._MAX_CONSECUTIVE_DECODE_FAILURES:
                    logger.error(
                        "Circuit breaker hit after %d consecutive failures; emitting empties for remaining segments.",
                        self._consecutive_decode_failures,
                    )
                    # Current segment empties
                    for i, cue_id in enumerate(seg_ids, start=start):
                        results[i] = {"id": cue_id, "tgt": ""}
                    # Remaining queue segments empties
                    while work_q:
                        s2, e2, _, _ = work_q.popleft()
                        for i2, cue_id in enumerate(batch_ids[s2:e2], start=s2):
                            results[i2] = {"id": cue_id, "tgt": ""}
                    break

                seg_len = len(seg_src)
                if seg_len == 1:
                    # Single item micro-retry with tiny backoff, capped
                    if retries < self._MAX_JSON_RETRIES_PER_SEGMENT:
                        backoff = min(
                            self._MICRO_BACKOFF_CAP_S,
                            self._MICRO_BACKOFF_BASE_S * (2**retries),
                        )
                        # jitter ±50ms
                        time.sleep(
                            max(0.0, backoff + random.uniform(-0.05, 0.05))  # nosec B311
                        )
                        work_q.appendleft((start, end, depth, retries + 1))
                    else:
                        logger.warning(
                            "Giving up on cue id=%s after %d retries; leaving empty.",
                            seg_ids[0],
                            retries,
                        )
                        results[start] = {"id": seg_ids[0], "tgt": ""}
                    continue

                # Split into halves if depth budget remains; otherwise fall back to singles
                if depth < self._MAX_SPLIT_DEPTH:
                    mid = start + (seg_len // 2)
                    # Process left first to preserve natural order in logging
                    work_q.appendleft((mid, end, depth + 1, 0))
                    work_q.appendleft((start, mid, depth + 1, 0))
                else:
                    # Enqueue each item singly with fresh retry budget
                    for i in range(end - 1, start - 1, -1):
                        work_q.appendleft((i, i + 1, depth, 0))

        # Ensure all slots are filled
        for i, val in enumerate(results):
            if val is None:
                results[i] = {"id": batch_ids[i], "tgt": ""}
        return results  # type: ignore[return-value]
