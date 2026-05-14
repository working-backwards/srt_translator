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

from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    NotFoundError,
    OpenAI,
    PermissionDeniedError,
    RateLimitError,
)

# OpenAI client
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionDeveloperMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionToolMessageParam,
    ChatCompletionUserMessageParam,
)

from srt_translator.config.model_config_loader import build_call_params
from srt_translator.core.config.language_config import LanguageConfig
from srt_translator.core.constants import (
    DEFAULT_TEMPERATURE,
    DIAG_MAX_PROBE_BATCH_IDS,
    DIAG_MAX_SOURCE_ITEMS,
    DIAG_RESPONSE_PREVIEW_CHARS,
    MAX_BATCH_SIZE,
    MAX_COMPLETION_TOKENS_DIAGNOSTIC,
    MAX_COMPLETION_TOKENS_FALLBACK,
    MAX_COMPLETION_TOKENS_TRANSLATION_BATCH,
    MAX_CONSECUTIVE_DECODE_FAILURES,
    MAX_JSON_RETRIES_PER_SEGMENT,
    MAX_SPLIT_DEPTH,
    MAX_TRANSLATION_TOKEN_RATIO,
    MICRO_BACKOFF_BASE,
    MICRO_BACKOFF_CAP,
    MIN_TRANSLATION_TOKEN_RATIO,
    OVERSIZE_RESPONSE_MULTIPLIER,
    STRICT_RETRY_FREQUENCY_PENALTY,
    STRICT_RETRY_TOKEN_CAP,
    STRICT_RETRY_TOKEN_FLOOR,
    STRICT_RETRY_TOKEN_MULTIPLIER,
    TRANSLATION_CONNECTION_RETRY_BASE_S,
    TRANSLATION_CONNECTION_RETRY_CAP_S,
    TRANSLATION_MAX_CONNECTION_RETRIES,
)
from srt_translator.core.retry import compute_retry_delay, parse_retry_after
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
from srt_translator.prompts.diagnostics import build_oversize_diagnostic_system_prompt
from srt_translator.prompts.translation import (
    build_placeholder_fixer_prompt,
    build_single_string_fallback_prompt,
    build_translation_prompt,
)

# Token caps: use MAX_COMPLETION_TOKENS_TRANSLATION_BATCH (4096) for any call that returns
# JSON with multiple subtitles (main batch, placeholder-fixer). Using a small cap (e.g. 120)
# truncates the response and produces empty subtitles. Use the smaller constants
# (DIAGNOSTIC, FALLBACK) or strict-retry computed cap only for single-answer or retry paths.

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
    for i, (src, tgt) in enumerate(zip(src_items, tgt_items, strict=True)):
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


def _is_invalid_translation(text: str, src: str | None = None) -> bool:
    if not text:
        return True
    t = text.strip()
    if not t:
        return True
    if re.fullmatch(r"[\W\d_]+", t):
        # Punctuation/digit-only output is usually a model failure (collapsed
        # placeholder, dropped content). Exception: when the source itself is
        # punctuation/digit-only (isolated year, dollar amount, ellipsis,
        # chapter marker), returning it unchanged IS the correct translation.
        # Strict identity match — partial matches still count as failures.
        if src is not None and t == src.strip():
            return False
        return True
    return False


# ---------------------------
# Stage 1A Helper Methods (stay in translator.py)
# ---------------------------


def _load_and_parse_file(input_filepath: str) -> list[Subtitle]:
    """Load and parse SRT file into subtitle objects."""
    for encoding in ("utf-8", "utf-16", "iso-8859-1"):
        try:
            with open(input_filepath, encoding=encoding) as f:
                src_text = f.read()
            break
        except (UnicodeDecodeError, UnicodeError):
            continue
    else:
        raise UnicodeDecodeError(
            "multi",
            b"",
            0,
            1,
            f"Failed to decode {input_filepath} with utf-8, utf-16, or iso-8859-1",
        )
    src_subs = parse_srt(src_text)
    if not src_subs:
        raise ValueError("Empty or invalid SRT: no subtitle blocks found.")
    return src_subs


def _format_and_append_subtitles(
    batch: list[Subtitle],
    tgt_texts: list[str],
    target_lang: str,
    cps_cap: int | None,
) -> list[Subtitle]:
    """Format subtitles with CPS and append to global list."""
    formatted_subs = []
    for s, tgt in zip(batch, tgt_texts, strict=True):
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

class TranslationCancelledError(Exception):
    """Raised when translation is cancelled by user."""

class SRTTranslator:
    # Explicit attribute types to avoid "Cannot determine type of X"
    logger: LoggerLike
    term_handler: TermHandler

    # Expert configuration - modify these values as needed
    MAX_BATCH_SIZE = MAX_BATCH_SIZE  # Maximum subtitles per batch (safety cap)
    # Internal bounded shape-lock caps (not user-configurable)
    _MAX_SPLIT_DEPTH = MAX_SPLIT_DEPTH
    _MAX_JSON_RETRIES_PER_SEGMENT = MAX_JSON_RETRIES_PER_SEGMENT
    _MAX_CONSECUTIVE_DECODE_FAILURES = MAX_CONSECUTIVE_DECODE_FAILURES
    _MICRO_BACKOFF_BASE_S = MICRO_BACKOFF_BASE
    _MICRO_BACKOFF_CAP_S = MICRO_BACKOFF_CAP

    def __init__(
        self,
        *,
        dnt_terms: list[str],
        termbase: dict[str, dict[str, str]],
        api_key: str,
        logger: logging.Logger,  # Required - no fallback allowed
        allow_global_termbase_fallback: bool = False,
        translation_model_name: str,
        batch_size: int,
        error_policy: str = "STRICT",
        temperature: float | None = None,
        language_config: LanguageConfig,
        tone: str = "neutral",
        retry_status_callback=None,
        stop_check=None,
    ) -> None:
        if logger is None:
            raise ValueError("SRTTranslator requires an application logger (non-None).")

        self.dnt_terms = dnt_terms or []
        self.termbase = termbase or {}
        self.allow_global_termbase_fallback = allow_global_termbase_fallback
        self.translation_model_name = translation_model_name
        self.batch_size = min(MAX_BATCH_SIZE, max(1, int(batch_size)))
        self.error_policy = error_policy.upper()
        self.tone = tone.lower() if tone else "neutral"
        self.temperature = max(0.0, min(2.0, temperature if temperature is not None else DEFAULT_TEMPERATURE))

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

        self.client = OpenAI(api_key=api_key, timeout=120.0)

        # One-shot advisory probe budget per (file, lang)
        self._probe_budget = MalformedProbeBudget()
        # Probe budget: only ask the "why was it oversized?" question once per target language
        self._probe_budget_langs: set[str] = set()
        # Simple per-file/lang circuit breaker for repeated JSON failures
        self._consecutive_decode_failures = 0
        self._model_invalid = False
        self.retry_status_callback = retry_status_callback
        self.stop_check = stop_check

    def _strict_retry_kwargs(self, src_items: list[str]) -> dict[str, Any]:
        """
        Strict decoding for retries: cools repetition and caps length conservatively,
        but guarantees enough budget to close the JSON wrapper even for tiny inputs.
        Uses a computed cap (STRICT_RETRY_*), not the generic 120-token constant, so
        retries get enough tokens for valid JSON without allowing runaway length.
        """
        src_tok = sum(estimate_tokens(s or "") for s in src_items)
        cap = int(math.ceil(STRICT_RETRY_TOKEN_MULTIPLIER * max(1, src_tok)))
        floor = STRICT_RETRY_TOKEN_FLOOR  # <-- token floor: prevents cut-off JSON on very short cues
        max_completion_tokens = min(STRICT_RETRY_TOKEN_CAP, max(floor, cap))
        base = build_call_params(
            self.translation_model_name,
            max_completion_tokens=max_completion_tokens,
            temperature=self.temperature,
            frequency_penalty=STRICT_RETRY_FREQUENCY_PENALTY,
            presence_penalty=0.0,
        )
        # Optional: stop right after JSON; remove if provider doesn't support 'stop'
        base["stop"] = ["]}"]
        return base

    def _emit_retry_status(self, message: str) -> None:
        """Emit retry status to GUI if callback exists."""
        try:
            if self.retry_status_callback:
                self.retry_status_callback(message)
        except Exception:
            pass

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
            "run_id": getattr(self.logger, "extra", {}).get("run_id", "n/a"),
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
        for i, (src, tgt) in enumerate(zip(src_items, tgt_texts, strict=True)):
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
        target_lang = getattr(batch_logger, "extra", {}).get("lang", "unknown")
        if self.language_config.allows_placeholder_apostrophe(target_lang.lower()):
            # Normalize for detection only: treat "__...__'..." as "__...__"
            norm_tgts = [TR_PLACEHOLDER_APOS_RE.sub(lambda m: m.group(0)[:-1], t) for t in tgt_texts]
            ph_issues = validate_placeholders_pair(src_items, norm_tgts, self.term_handler.placeholder_regex)
            # Once-per-batch debug (observational only)
            seen = False
            for i, (_s_i, t_i) in enumerate(zip(src_items, tgt_texts, strict=True)):
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

            for i, (s_i, t_i) in enumerate(zip(src_items, tgt_texts, strict=True)):
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

        # Restore DNT placeholders and termbase substitutions
        tgt_texts = [self.term_handler.restore_all(t, target_lang) for t in tgt_texts]
        self.logger.debug("FINAL OUTPUT: %s", tgt_texts)
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

    def _create_batches_with_logging(
        self,
        src_subs: list[Subtitle],
        target_lang: str,
        file_logger: LoggerLike,
    ) -> list[list[Subtitle]]:
        """Create sentence-aware batches with logging setup."""
        batches = self._create_batches(
            subtitles=src_subs,
            target_size=int(self.batch_size),
            max_size=self.MAX_BATCH_SIZE,
            target_lang=target_lang,
        )

        file_logger.info(
            "Using sentence-aware batching for %s → %s (%d subtitles → %d batches; target=%d, max=%d)",
            os.path.basename(getattr(file_logger, "extra", {}).get("file", "unknown")),
            target_lang,
            len(src_subs),
            len(batches),
            self.batch_size,
            self.MAX_BATCH_SIZE,
        )
        return batches

    def _translate_batch_and_extract(
        self,
        src_items: list[str],
        batch_ids: list[int],
        target_lang: str,
        batch_logger: LoggerLike,
    ) -> list[str]:
        """Translate batch and extract target texts."""
        try:
            items = self._translate_with_simple_shape_lock(
                src_items,
                target_lang,
                self.termbase,
                batch_ids,
                logger=batch_logger,
            )
        except Exception:
            if self.logger.isEnabledFor(logging.DEBUG):
                self.logger.debug(
                    "Main batch translation failure - Payload sent (lang=%s, items=%d).",
                    target_lang,
                    len(src_items),
                )
            raise
        tgt_texts = [it.get("tgt", "") for it in items]
        return tgt_texts

    def _handle_mid_batch_empty_retries(
        self,
        batch: list[Subtitle],
        tgt_texts: list[str],
        target_lang: str,
        batch_logger: LoggerLike,
    ) -> list[str]:
        """Handle mid-batch empty translation retries."""
        for i, (_src_raw, tgt_raw) in enumerate(zip([s.text for s in batch], tgt_texts, strict=True)):
            if tgt_raw.strip():
                continue
            sid = batch[i].idx
            filled = False
            if i + 1 < len(batch):
                try:
                    batch_logger.debug(
                        "Empty target at idx=%s; attempting pair retry with next cue.",
                        sid,
                    )
                    pair_src = [
                        self.term_handler.apply_all(batch[i].text),
                        self.term_handler.apply_all(batch[i + 1].text),
                    ]

                    pair_ids = [batch[i].idx, batch[i + 1].idx]
                    pair_items = self._translate_batch_json(
                        src_items=pair_src,
                        target_lang=target_lang,
                        termbase=self.termbase,
                        batch_ids=pair_ids,
                        strict=True,
                    )
                    if isinstance(pair_items, list) and len(pair_items) >= 1:
                        candidate = pair_items[0].get("tgt", "")
                        if candidate and candidate.strip():
                            tgt_texts[i] = self.term_handler.restore_all(candidate, target_lang)
                            batch_logger.debug("Pair retry filled idx=%s successfully.", sid)
                            filled = True
                except Exception as ex:
                    # SANCTIONED DIAGNOSTICS HOOK: strict pair-retry failure
                    # Probes/logs may be added here (and ONLY here) with tests. Do not add probes elsewhere.
                    batch_logger.debug("Pair retry failed for idx=%s: %s", sid, ex)
            if not filled:
                if self.error_policy == "STRICT":
                    raise RuntimeError(f"Empty translation for subtitle idx={sid}")
                batch_logger.warning(
                    "Empty translation for subtitle idx=%s; leaving empty for evaluator.",
                    sid,
                )
        return tgt_texts

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
        batches = self._create_batches_with_logging(src_subs, target_lang, file_logger)
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
            if self.stop_check is not None and self.stop_check():
                file_logger.info(
                    "Translation cancelled during batch processing "
                    "(file=%s lang=%s batch=%s/%s)",
                    os.path.basename(input_filepath),
                    target_lang,
                    bi,
                    len(batches),
                )
                raise TranslationCancelledError("Translation cancelled by user")
            # Batch-scoped logger with correlation ids
            batch_logger = logging.LoggerAdapter(file_logger, {"batch": bi, "ids": [s.idx for s in batch]})

            # Handle deferred tail now, pairing with THIS batch's head via shape-lock
            if deferred_tail_retry is not None:
                if batch:
                    head = batch[0]
                    pair_src = [
                        deferred_tail_retry["source_text_with_placeholders"],
                        self.term_handler.apply_all(head.text),
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
                            fixed = self.term_handler.restore_all(fixed, target_lang)
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

            # Preprocess: apply termbase + DNT placeholders on a per-subtitle basis
            src_items = [self.term_handler.apply_all(s.text) for s in batch]

            # Log source items being sent to AI for troubleshooting
            file_logger.debug(
                "Sending batch %d/%d to AI (lang=%s):\n%s",
                bi,
                len(batches),
                target_lang,
                "\n".join([f"  {i}: {text}" for i, text in enumerate(src_items)]),
            )

            # 3) Translate batch and validate placeholders
            tgt_texts = self._translate_batch_and_extract(
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
            tgt_texts = self._handle_mid_batch_empty_retries(
                batch=batch,
                tgt_texts=tgt_texts,
                target_lang=target_lang,
                batch_logger=batch_logger,
            )

            # 4) Format and append subtitles
            formatted_subs = _format_and_append_subtitles(
                batch=batch,
                tgt_texts=tgt_texts,
                target_lang=target_lang,
                cps_cap=cps_cap,
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

        lang_hint = self.language_config.get_tone_hint(target_lang, self.tone)
        if lang_hint:
            self.logger.debug("Tone hint found for %s (%s): %s", target_lang, self.tone, lang_hint)
        else:
            self.logger.debug("No tone hint found for %s (%s)", target_lang, self.tone)

        system_prompt, user_prompt = build_translation_prompt(
            target_lang=target_lang,
            tone=self.tone,
            tone_hint=lang_hint,
            termbase_block=termbase_block,
            rendered_items=self._render_items_for_prompt(batch_ids, src_items),
            item_count=len(src_items),
            strict=strict,
            is_chinese=target_lang.lower().startswith("zh"),
        )

        # Prepare the messages payload for logging (typed for mypy)
        messages_payload: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        messages_typed = cast(Sequence[ChatMsg], messages_payload)

        # Use JSON mode if available; otherwise rely on instruction.
        if strict:
            kwargs = self._strict_retry_kwargs(src_items)
        else:
            # Main batch path: response is JSON for up to MAX_BATCH_SIZE subtitles. A small
            # token cap (e.g. 120) truncates the JSON and yields empty subtitles; use
            # MAX_COMPLETION_TOKENS_TRANSLATION_BATCH.
            kwargs = {
                "response_format": {"type": "json_object"},
                **build_call_params(
                    self.translation_model_name,
                    max_completion_tokens=MAX_COMPLETION_TOKENS_TRANSLATION_BATCH,
                    temperature=self.temperature,
                ),
            }
        resp = self.client.chat.completions.create(
            model=self.translation_model_name,
            messages=messages_typed,
            **kwargs,
        )
        content = (resp.choices[0].message.content or "").strip()

        # --- Oversize/repetition diagnostics (purely advisory; never changes flow) ---

        prompt_token_est = estimate_tokens(user_prompt)
        response_token_est = estimate_tokens(content or "")
        repetitive_loop = looks_like_repetitive_loop(content or "")

        # Heuristic: response wildly larger than prompt (>= 4x), or loop detected
        oversize = response_token_est >= OVERSIZE_RESPONSE_MULTIPLIER * prompt_token_est
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
                    src_excerpt: Sequence[str] = tuple(src_items[: min(len(src_items), DIAG_MAX_SOURCE_ITEMS)])
                    response_preview = content or ""
                    if len(response_preview) > DIAG_RESPONSE_PREVIEW_CHARS:
                        response_preview = response_preview[:DIAG_RESPONSE_PREVIEW_CHARS] + "…"

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
                    diag_params = {
                        "model": self.translation_model_name,
                        "messages": cast(
                            Sequence[ChatMsg],
                            [
                                {
                                    "role": "system",
                                    "content": build_oversize_diagnostic_system_prompt(),
                                },
                                {"role": "user", "content": question},
                            ],
                        ),
                        # Diagnostic probe: we only need a short explanation of oversize
                        # behaviour; small cap is sufficient.
                        **build_call_params(
                            self.translation_model_name,
                            max_completion_tokens=MAX_COMPLETION_TOKENS_DIAGNOSTIC,
                            temperature=self.temperature,
                        ),
                    }

                    response = self.client.chat.completions.create(**diag_params)
                    diag_text = (response.choices[0].message.content or "").strip()
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
            for i, (src, out) in enumerate(zip(src_items, norm, strict=True)):
                tgt = (out or {}).get("tgt", "")
                if not tgt:
                    continue
                if looks_like_repetitive_loop(tgt):
                    bad.append((i, "repetitive_loop"))
                    continue

                if estimate_tokens(tgt) < MIN_TRANSLATION_TOKEN_RATIO * max(1, estimate_tokens(src or "")):
                    bad.append((i, "under_ratio"))

                # 2.8× is conservative; adjust later per language if needed
                if estimate_tokens(tgt) >= MAX_TRANSLATION_TOKEN_RATIO * max(1, estimate_tokens(src or "")):
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
                    batch_ids=batch_ids[:DIAG_MAX_PROBE_BATCH_IDS],
                    raw_excerpt=(content or "")[:DIAG_RESPONSE_PREVIEW_CHARS],
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
            self.logger.error("Translation model did not return JSON; cannot recover without shape lock.")
            raise RuntimeError("Translation failed: translation model did not return valid JSON format") from None

    def _translate_single_string_fallback(self, *, _src_text: str, target_lang: str) -> str:
        """
        Minimal escape hatch for repeated JSON truncation in size=1 strict retries.
        Returns ONLY a translated string; caller will wrap into JSON.
        """
        sys, usr = build_single_string_fallback_prompt(target_lang, _src_text)
        params = {
            "model": self.translation_model_name,
            "messages": cast(
                Sequence[ChatMsg],
                [
                    {"role": "system", "content": sys},
                    {"role": "user", "content": usr},
                ],
            ),
            # Fallback returns a single translated string only; small cap is enough.
            **build_call_params(
                self.translation_model_name,
                max_completion_tokens=MAX_COMPLETION_TOKENS_FALLBACK,
                temperature=self.temperature,
            ),
        }

        resp = self.client.chat.completions.create(**params)
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
        sys, prompt = build_placeholder_fixer_prompt(
            allowed_placeholders=allowed_placeholders,
            rendered_src=self._render_items_for_prompt(ids, src_items),
            rendered_tgt=self._render_items_for_prompt(ids, tgt_items),
        )

        # Prepare the messages payload for logging
        messages_payload = [
            {"role": "system", "content": sys},
            {"role": "user", "content": prompt},
        ]

        # Placeholder-fixer returns JSON for multiple items (same shape as main batch);
        # use MAX_COMPLETION_TOKENS_TRANSLATION_BATCH so the response is not truncated.
        params = {
            "model": self.translation_model_name,
            "messages": cast(Sequence[ChatMsg], messages_payload),
            "response_format": {"type": "json_object"},
            **build_call_params(
                self.translation_model_name,
                max_completion_tokens=MAX_COMPLETION_TOKENS_TRANSLATION_BATCH,
                temperature=self.temperature,
            ),
        }

        resp = self.client.chat.completions.create(**params)
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
        for i, t in zip(ids, texts, strict=True):
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
        transient_retry = 0

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

            # Fast-exit: if model was already flagged invalid, emit empties for all remaining work
            if self._model_invalid:
                while work_q:
                    s, e, _, _ = work_q.popleft()
                    for i, cue_id in enumerate(batch_ids[s:e], start=s):
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

                    if _is_invalid_translation(tgt, src=seg_src[offset]):
                        raise RuntimeError(f"Invalid translation at cue id={seg_ids[offset]}: {tgt!r}")
                    results[start + offset] = {
                        "id": obj.get("id"),
                        "tgt": obj.get("tgt", ""),
                    }
                self._consecutive_decode_failures = 0  # reset breaker on success
                transient_retry = 0
                self._emit_retry_status("")
                continue

            except NotFoundError as ex:
                self._model_invalid = True
                logger.error(
                    "Invalid translation model '%s': %s. Check the translator model name in your settings.",
                    self.translation_model_name,
                    ex,
                )
                raise RuntimeError(
                    f"Invalid translation model '{self.translation_model_name}'. Check the translator model name in your settings. "
                    f"Valid examples: gpt-4o-mini, gpt-4o, gpt-4.1-mini, gpt-5-mini"
                ) from ex

            except (AuthenticationError, PermissionDeniedError):
                logger.error("Authentication failed: API key or permissions invalid.")
                raise

            except (
                    APIConnectionError,
                    APITimeoutError,
                    RateLimitError,
            ) as ex:
                detail = str(ex).lower()

                if (
                        "insufficient_quota" in detail
                        or "quota" in detail
                        or "billing" in detail
                ):
                    raise
                transient_retry += 1
                if transient_retry > TRANSLATION_MAX_CONNECTION_RETRIES:
                    logger.error(
                        "Transient API retries exhausted after %s attempts: %s",
                        TRANSLATION_MAX_CONNECTION_RETRIES,
                        ex,
                    )
                    self._emit_retry_status("")
                    raise

                delay = compute_retry_delay(
                    transient_retry,
                    base=TRANSLATION_CONNECTION_RETRY_BASE_S,
                    cap=TRANSLATION_CONNECTION_RETRY_CAP_S,
                    retry_after=parse_retry_after(ex),
                    max_total=TRANSLATION_CONNECTION_RETRY_CAP_S * 2,
                )
                logger.warning(
                    "Transient API error. Retrying in %.1fs (attempt %s/%s): %s",
                    delay,
                    transient_retry,
                    TRANSLATION_MAX_CONNECTION_RETRIES,
                    ex,
                )
                if transient_retry >= 3:
                    status_msg = (
                        f"Connection interrupted — retrying every {int(delay)}s "
                        f"(attempt {transient_retry}/{TRANSLATION_MAX_CONNECTION_RETRIES})..."
                    )
                else:
                    status_msg = (
                        f"Connection issue, retrying in {int(delay)}s "
                        f"(attempt {transient_retry}/{TRANSLATION_MAX_CONNECTION_RETRIES})..."
                    )
                self._emit_retry_status(status_msg)
                time.sleep(delay)
                work_q.appendleft((start, end, depth, retries))
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
