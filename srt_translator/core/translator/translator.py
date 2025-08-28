# srt_translator/core/translator/translator.py
from __future__ import annotations

import json
import logging
import os
import re
import time
import random
from collections import deque
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple, Set

# Core imports
from srt_translator.core.config.language_config import LanguageConfig
from srt_translator.core.translator.subtitle_formatter import format_subtitle_text
from srt_translator.core.translator.term_handler import TermHandler
from srt_translator.core.translator.diagnostics import (
    estimate_tokens,
    has_repetitive_loop,
    MalformedProbeBudget,
    probe_malformed_json,
)


# OpenAI client
from openai import OpenAI

# ---------------------------
# Fallback functions (if imports fail)
# ---------------------------


# Fallback function removed - no longer needed with simplified CPS system


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

SRT_BLOCK_RE = re.compile(
    r"^\s*(\d+)\s*\n"  # index
    r"(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*"
    r"(\d{2}:\d{2}:\d{2},\d{3})\s*\n"
    r"(.*?)(?=\n{2,}|\Z)",  # text
    re.DOTALL | re.MULTILINE,
)

TIME_RE = re.compile(r"(?P<h>\d{2}):(?P<m>\d{2}):(?P<s>\d{2}),(?P<ms>\d{3})")

PH_RE = re.compile(r"__DNT_TERM_(\d+)__")
# Detector (Stage 1): placeholder immediately followed by apostrophe (straight or curly)
TR_PLACEHOLDER_APOS_RE = re.compile(r"__DNT_TERM_\d+__['']")


def _parse_time_to_seconds(ts: str) -> float:
    m = TIME_RE.match(ts)
    if not m:
        return 0.0
    h = int(m.group("h"))
    m_ = int(m.group("m"))
    s = int(m.group("s"))
    ms = int(m.group("ms"))
    return h * 3600 + m_ * 60 + s + ms / 1000.0


def parse_srt(text: str) -> List[Subtitle]:
    subs: List[Subtitle] = []
    for m in SRT_BLOCK_RE.finditer(text):
        idx = int(m.group(1))
        start = m.group(2)
        end = m.group(3)
        body = m.group(4).strip("\n")
        subs.append(Subtitle(idx=idx, start=start, end=end, text=body))
    return subs


def render_srt(subs: Sequence[Subtitle]) -> str:
    """
    Render target SRT using original timings.
    IMPORTANT: We ALWAYS emit a block—even if the translated text is empty.
    This preserves 1:1 cue parity and timings, allowing the evaluator to
    surface true 'Missing translation' instead of silently shifting indices.
    """
    parts: List[str] = []
    for i, sub in enumerate(subs, start=1):
        translated = (sub.text or "").strip()
        parts.append(str(i))
        parts.append(f"{sub.start} --> {sub.end}")
        parts.append(translated if translated else "")
        parts.append("")  # blank line
    return "\n".join(parts).rstrip() + "\n"


def chunk(seq: Sequence[Any], n: int) -> List[List[Any]]:
    return [list(seq[i : i + n]) for i in range(0, len(seq), n)]


def build_termbase_block(termbase: Dict[str, Dict[str, str]], lang_code: str) -> str:
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
def _extract_ph_ids(text: str, ph_regex: re.Pattern) -> Set[str]:
    return set(ph_regex.findall(text or ""))


def validate_placeholders_pair(
    src_items: List[str],
    tgt_items: List[str],
    ph_regex: re.Pattern,
) -> Dict[int, Dict[str, Set[str]]]:
    issues: Dict[int, Dict[str, Set[str]]] = {}
    for i, (src, tgt) in enumerate(zip(src_items, tgt_items)):
        src_ids = _extract_ph_ids(src, ph_regex)
        tgt_ids = _extract_ph_ids(tgt, ph_regex)
        invented = tgt_ids - src_ids
        missing = src_ids - tgt_ids
        if invented or missing:
            issues[i] = {"invented": invented, "missing": missing}
    return issues


def strip_invented_placeholders(
    text: str, invented_ids: Set[str], ph_regex: re.Pattern
) -> str:
    if not invented_ids:
        return text

    def _sub(m):
        pid = m.group(1)
        return "" if pid in invented_ids else m.group(0)

    return ph_regex.sub(_sub, text or "")


# ---------------------------
# SRTTranslator
# ---------------------------


class SRTTranslator:
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
        dnt_terms: List[str],
        termbase: Dict[str, Dict[str, str]],
        api_key: str,
        logger: logging.Logger,  # Required - no fallback allowed
        allow_global_termbase_fallback: bool = False,
        model_name: str = "gpt-4o-mini",
        batch_size: int,
        error_policy: str = "STRICT",
        language_config: Optional[LanguageConfig] = None,
    ) -> None:
        if logger is None:
            raise ValueError("SRTTranslator requires an application logger (non-None).")

        self.dnt_terms = dnt_terms or []
        self.termbase = termbase or {}
        self.allow_global_termbase_fallback = allow_global_termbase_fallback
        self.model_name = model_name
        self.batch_size = max(1, int(batch_size))
        self.error_policy = error_policy.upper()

        # Make a namespaced child for clarity in logs
        self.logger = (
            logger.logger if isinstance(logger, logging.LoggerAdapter) else logger
        )
        self.logger = self.logger.getChild("core.translator")

        # If caller gave an adapter, re-wrap child with the same extra
        if isinstance(logger, logging.LoggerAdapter):
            self.logger = logging.LoggerAdapter(self.logger, logger.extra)

        self.language_config = language_config or LanguageConfig({"languages": {}})

        # Initialize TermHandler for DNT and termbase management
        self.term_handler = TermHandler(
            dnt_terms=self.dnt_terms,
            termbase=self.termbase,
            lang_code=None,  # Will be set per file/lang
            logger=self.logger,
        )

        if OpenAI is None:
            raise RuntimeError(
                "OpenAI client not available; install/openai and configure API key."
            )

        self.client = OpenAI(api_key=api_key)

        # One-shot advisory probe budget per (file, lang)
        self._probe_budget = MalformedProbeBudget()
        # Simple per-file/lang circuit breaker for repeated JSON failures
        self._consecutive_decode_failures = 0

    # --- Sentence-aware batching ----------------------------
    def _create_batches(
        self,
        subtitles: List[Subtitle],
        target_size: int,
        max_size: int,
        target_lang: str,
    ) -> List[List[Subtitle]]:
        """
        Group consecutive subtitles into batches that prefer ending at a natural
        sentence boundary once the target size is reached, without exceeding
        the maximum size.  Each subtitle remains its own item (1:1 id mapping).
        """
        if not subtitles:
            return []

        batches: List[List[Subtitle]] = []
        current: List[Subtitle] = []

        # Pull language-specific rules from the injected language_config, if present.
        # Falls back to a generic set if not available.
        sentence_endings = (".", "!", "?", "…")
        try:
            if self.language_config:
                rules = self.language_config.get_language_rules(target_lang) or {}
                if isinstance(rules.get("sentence_endings"), list):
                    sentence_endings = tuple(rules["sentence_endings"])  # type: ignore[assignment]
        except Exception:
            # Be permissive; logging is handled by the caller
            pass

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

    # ---------- Public API ----------

    def translate_file(
        self,
        *,
        input_filepath: str,
        output_filepath: str,
        target_lang: str,
    ) -> None:
        # Per-call context (add file/lang without reconfiguring handlers)
        file_logger = logging.LoggerAdapter(
            self.logger,
            {
                "run_id": getattr(self.logger, "extra", {}).get("run_id", "n/a"),
                "file": os.path.basename(input_filepath),
                "lang": target_lang,
            },
        )

        # Reset consecutive failure counter for this file/lang run
        self._consecutive_decode_failures = 0

        file_logger.info(
            "Using subtitle-based translation system for %s → %s",
            os.path.basename(input_filepath),
            target_lang,
        )

        # 1) Load and parse SRT
        with open(input_filepath, "r", encoding="utf-8") as f:
            src_text = f.read()
        src_subs = parse_srt(src_text)
        if not src_subs:
            raise ValueError("Empty or invalid SRT: no subtitle blocks found.")

        self.logger.info(
            "Processing %d subtitles for %s",
            len(src_subs),
            os.path.basename(input_filepath),
        )

        # 2) Sentence-aware batching (each subtitle stays its own item)
        batches = self._create_batches(
            subtitles=src_subs,
            target_size=int(self.batch_size),
            max_size=self.MAX_BATCH_SIZE,
            target_lang=target_lang,
        )

        file_logger.info(
            "Using sentence-aware batching for %s → %s "
            "(%d subtitles → %d batches; "
            "target=%d, max=%d)",
            os.path.basename(input_filepath),
            target_lang,
            len(src_subs),
            len(batches),
            self.batch_size,
            self.MAX_BATCH_SIZE,
        )
        all_tgt_subs: List[Subtitle] = []

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
        deferred_tail_retry: Optional[Dict[str, Any]] = None

        # Language CPS cap
        cps_cap = self.language_config.get_cps_cap(target_lang)

        for bi, batch in enumerate(batches, start=1):
            # Batch-scoped logger with correlation ids
            batch_logger = logging.LoggerAdapter(
                file_logger, {"batch": bi, "ids": [s.idx for s in batch]}
            )

            # Handle deferred tail now, pairing with THIS batch's head via shape-lock
            if deferred_tail_retry is not None:
                if batch:
                    head = batch[0]
                    pair_src = [
                        deferred_tail_retry["source_text_with_placeholders"],
                        self.term_handler.apply_dnt_placeholders(head.text),
                    ]
                    pair_ids = [deferred_tail_retry["cue_index"], head.idx]
                    batch_logger.info(
                        "Empty target at idx=%s; attempting pair retry with next cue across batch boundary (pair_ids=%s).",
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
                        fixed = self.term_handler.restore_dnt_placeholders(
                            pair_tgts[0] if pair_tgts else ""
                        )
                        if fixed.strip():
                            all_tgt_subs[deferred_tail_retry["out_index"]].text = fixed
                            batch_logger.info(
                                "Pair retry filled idx=%s successfully.",
                                deferred_tail_retry["cue_index"],
                            )
                        else:
                            batch_logger.error(
                                "Empty translation for subtitle idx=%s; leaving empty for evaluator.",
                                deferred_tail_retry["cue_index"],
                            )
                    except Exception as ex:
                        batch_logger.warning(
                            "Pair retry failed for idx=%s: %s",
                            deferred_tail_retry["cue_index"],
                            ex,
                        )
                        batch_logger.error(
                            "Empty translation for subtitle idx=%s; leaving empty for evaluator.",
                            deferred_tail_retry["cue_index"],
                        )
                    finally:
                        deferred_tail_retry = None
                else:
                    batch_logger.error(
                        "Empty translation for subtitle idx=%s at end-of-file; leaving empty for evaluator.",
                        deferred_tail_retry["cue_index"],
                    )
                    deferred_tail_retry = None

            # One-line context banner
            batch_logger.info(
                "Batch context: file=%s batch=%d/%d ids=%s",
                os.path.basename(input_filepath),
                bi,
                len(batches),
                [s.idx for s in batch],
            )
            batch_logger.info(
                "Processing %d subtitles in batch %d/%d", len(batch), bi, len(batches)
            )

            # Preprocess: apply DNT placeholders on a per-subtitle basis
            src_items = [
                self.term_handler.apply_dnt_placeholders(s.text) for s in batch
            ]

            # Log source items being sent to AI for troubleshooting
            file_logger.debug(
                "Sending batch %d/%d to AI (lang=%s):\n%s",
                bi,
                len(batches),
                target_lang,
                "\n".join([f"  {i}: {text}" for i, text in enumerate(src_items)]),
            )

            # Shape-locked translate: one call in the happy path; on mismatch, split halves and retry once.
            try:
                items = self._translate_with_simple_shape_lock(
                    src_items,
                    target_lang,
                    self.termbase,
                    [s.idx for s in batch],
                    logger=batch_logger,
                )
            except Exception as ex:
                # Log the payload that was sent to the translator when failure occurs
                self.logger.info(
                    "Main batch translation failure - Payload sent to translator (lang=%s, items=%d):\nSystem: You are a professional subtitle translator. Return valid JSON ONLY, never prose.\nUser: Translate each item to %s. Keep 1:1 count and order...",
                    target_lang,
                    len(src_items),
                    target_lang,
                )
                raise  # Re-raise the exception to maintain the original behavior

            # Extract and validate placeholder usage
            tgt_texts = [it.get("tgt", "") for it in items]

            # Log input/output for troubleshooting placeholder issues
            for i, (src, tgt) in enumerate(zip(src_items, tgt_texts)):
                # Use the regex pattern directly to avoid logging violations
                src_placeholders = PH_RE.findall(src)
                tgt_placeholders = PH_RE.findall(tgt)
                if src_placeholders or tgt_placeholders:
                    file_logger.info(
                        "Placeholder comparison (batch=%d, item=%d):\n"
                        "  Source: %s\n"
                        "  Target: %s\n"
                        "  Source placeholders: %s\n"
                        "  Target placeholders: %s",
                        bi,
                        i,
                        src,
                        tgt,
                        src_placeholders,
                        tgt_placeholders,
                    )

            # Policy-aware placeholder validation for apostrophes after placeholders
            if self.language_config.allows_placeholder_apostrophe(target_lang.lower()):
                # Normalize for detection only: treat "__...__'..." as "__...__"
                norm_tgts = [
                    TR_PLACEHOLDER_APOS_RE.sub(lambda m: m.group(0)[:-1], t)
                    for t in tgt_texts
                ]
                ph_issues = validate_placeholders_pair(
                    src_items, norm_tgts, self.term_handler.placeholder_regex
                )
                # Once-per-batch info (less noisy when allowed)
                seen = False
                for i, (s_i, t_i) in enumerate(zip(src_items, tgt_texts)):
                    if TR_PLACEHOLDER_APOS_RE.search(t_i) and not seen:
                        batch_logger.info(
                            "Apostrophe after placeholder observed (allowed for %s, item=%d).",
                            target_lang,
                            i,
                        )
                        seen = True
                        break
            else:
                ph_issues = validate_placeholders_pair(
                    src_items, tgt_texts, self.term_handler.placeholder_regex
                )
                # Stage 1: language-agnostic detector (observational logging only, once per batch)
                seen = False

                def _snip(s: str, n: int = 120) -> str:
                    return s if len(s) <= n else s[: n - 3] + "..."

                for i, (s_i, t_i) in enumerate(zip(src_items, tgt_texts)):
                    if TR_PLACEHOLDER_APOS_RE.search(t_i) and not seen:
                        batch_logger.info(
                            "Observed apostrophe immediately after placeholder (item=%d, lang=%s). Source≈%s | Target≈%s",
                            i,
                            target_lang,
                            _snip(s_i),
                            _snip(t_i),
                        )
                        seen = True
                        break

            # Run drift repair BEFORE mutating targets (e.g., before stripping invented tokens),
            # so we can split on the actual placeholder token (e.g., __DNT_TERM_12__).
            tgt_texts = self._repair_adjacent_placeholder_drift(
                src_items=src_items,
                tgt_items=tgt_texts,
                ph_issues=ph_issues,
                batch_ids=[s.idx for s in batch],
                logger=file_logger,
            )

            if ph_issues:
                for idx, kinds in ph_issues.items():
                    inv = ",".join(sorted(kinds["invented"])) or "-"
                    mis = ",".join(sorted(kinds["missing"])) or "-"
                    file_logger.warning(
                        "Placeholder check (batch=%d, item=%d): invented=[%s] missing=[%s]",
                        bi,
                        idx,
                        inv,
                        mis,
                    )

                if self.error_policy == "STRICT":
                    fixed = self._reformat_fix_placeholders(
                        src_items=src_items,
                        tgt_items=tgt_texts,
                        ids=[s.idx for s in batch],
                        allowed_placeholders=sorted(
                            self.term_handler.placeholder_map.keys()
                        ),
                    )
                    if fixed is None:
                        raise RuntimeError(
                            "Reformat failed: phantom/missing placeholders unresolved."
                        )
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
            tgt_texts = [
                self.term_handler.restore_dnt_placeholders(t) for t in tgt_texts
            ]

            # Empty guard — single pair-retry for mid-stream empty; no source fallback
            for i, (src_raw, tgt_raw) in enumerate(
                zip([s.text for s in batch], tgt_texts)
            ):
                if tgt_raw.strip():
                    continue
                sid = batch[i].idx
                filled = False
                # Try exactly one pair retry with the next cue when available
                if i + 1 < len(batch):
                    try:
                        file_logger.info(
                            "Empty target at idx=%s; attempting pair retry with next cue.",
                            sid,
                        )
                        pair_src = [
                            self.term_handler.apply_dnt_placeholders(batch[i].text),
                            self.term_handler.apply_dnt_placeholders(batch[i + 1].text),
                        ]
                        pair_ids = [batch[i].idx, batch[i + 1].idx]
                        pair_items = self._translate_with_simple_shape_lock(
                            pair_src,
                            target_lang,
                            self.termbase,
                            pair_ids,
                            logger=batch_logger,
                        )
                        if isinstance(pair_items, list) and len(pair_items) >= 1:
                            candidate = pair_items[0].get("tgt", "")
                            if candidate and candidate.strip():
                                tgt_texts[i] = (
                                    self.term_handler.restore_dnt_placeholders(
                                        candidate
                                    )
                                )
                                file_logger.info(
                                    "Pair retry filled idx=%s successfully.", sid
                                )
                                filled = True
                    except Exception as ex:
                        # Log the payload that was sent to the translator when failure occurs
                        self.logger.info(
                            "Pair retry failure - Payload sent to translator (lang=%s, items=%d):\nSystem: You are a professional subtitle translator. Return valid JSON ONLY, never prose.\nUser: Translate each item to %s. Keep 1:1 count and order...",
                            target_lang,
                            len(pair_src),
                            target_lang,
                        )
                        file_logger.warning("Pair retry failed for idx=%s: %s", sid, ex)
                if not filled:
                    if self.error_policy == "STRICT":
                        raise RuntimeError(f"Empty translation for subtitle idx={sid}")
                    # Leave empty in BOUNDED/DEV; evaluator will flag as Missing translation
                    file_logger.error(
                        "Empty translation for subtitle idx=%s; leaving empty for evaluator.",
                        sid,
                    )

            # Before we append, compute where the last item will land in the global list.
            # We need this to patch it later if we defer a cross-batch pair-retry.
            base_out_pos = len(all_tgt_subs)
            last_out_pos = base_out_pos + len(tgt_texts) - 1

            # If the last item is still empty, defer a cross-batch retry.
            # We only *record* the slot here; the actual retry happens after
            # the next batch is translated (so we can pair with its first cue).
            if tgt_texts and not tgt_texts[-1].strip():
                last_cue = batch[-1]
                if self.error_policy == "STRICT":
                    raise RuntimeError(
                        f"Empty translation for subtitle idx={last_cue.idx}"
                    )
                deferred_tail_retry = {
                    "cue_index": last_cue.idx,
                    "out_index": last_out_pos,
                    "source_text_with_placeholders": self.term_handler.apply_dnt_placeholders(
                        last_cue.text
                    ),
                }
                file_logger.info(
                    "Deferred cross-batch pair retry for end-of-batch empty at idx=%s.",
                    last_cue.idx,
                )

            # Format per subtitle (CPS; line breaks) and append to global list
            for s, tgt in zip(batch, tgt_texts):
                start_s = _parse_time_to_seconds(s.start)
                end_s = _parse_time_to_seconds(s.end)
                formatted = format_subtitle_text(
                    lang_code=target_lang.lower(),
                    text=tgt,
                    start_ms=int(start_s * 1000),  # Convert seconds to milliseconds
                    end_ms=int(end_s * 1000),  # Convert seconds to milliseconds
                    cps_cap=cps_cap,
                )
                all_tgt_subs.append(
                    Subtitle(idx=s.idx, start=s.start, end=s.end, text=formatted)
                )

            # Fulfill any deferred cross-batch pair-retry *now* that we have the next batch's head.
            if deferred_tail_retry is not None and batch:
                try:
                    first_cue = batch[0]
                    pair_src = [
                        deferred_tail_retry["source_text_with_placeholders"],
                        self.term_handler.apply_dnt_placeholders(first_cue.text),
                    ]
                    pair_ids = [deferred_tail_retry["cue_index"], first_cue.idx]
                    file_logger.info(
                        "Empty target at idx=%s; attempting pair retry with next cue across batch boundary.",
                        deferred_tail_retry["cue_index"],
                    )
                    pair_items = self._translate_batch_json(
                        src_items=pair_src,
                        target_lang=target_lang,
                        termbase=self.termbase,
                        batch_ids=pair_ids,
                    )
                    if isinstance(pair_items, list) and len(pair_items) >= 1:
                        candidate = pair_items[0].get("tgt", "")
                        if candidate and candidate.strip():
                            fixed = self.term_handler.restore_dnt_placeholders(
                                candidate
                            )
                            # Patch the fixed text back into the global list
                            all_tgt_subs[deferred_tail_retry["out_index"]].text = fixed
                            file_logger.info(
                                "Pair retry filled idx=%s successfully.",
                                deferred_tail_retry["cue_index"],
                            )
                        else:
                            file_logger.error(
                                "Empty translation for subtitle idx=%s; leaving empty for evaluator.",
                                deferred_tail_retry["cue_index"],
                            )
                    else:
                        file_logger.error(
                            "Empty translation for subtitle idx=%s; leaving empty for evaluator.",
                            deferred_tail_retry["cue_index"],
                        )
                except Exception as ex:
                    # Log the payload that was sent to the translator when failure occurs
                    self.logger.info(
                        "Cross-batch pair retry failure - Payload sent to translator (lang=%s, items=%d):\nSystem: You are a professional subtitle translator. Return valid JSON ONLY, never prose.\nUser: Translate each item to %s. Keep 1:1 count and order...",
                        target_lang,
                        len(pair_src),
                        target_lang,
                    )
                    file_logger.warning(
                        "Pair retry failed for idx=%s: %s",
                        deferred_tail_retry["cue_index"],
                        ex,
                    )
                    file_logger.error(
                        "Empty translation for subtitle idx=%s; leaving empty for evaluator.",
                        deferred_tail_retry["cue_index"],
                    )
                finally:
                    # Clear the deferred slot. If the *current* batch's tail is also empty,
                    # we will have just set a new deferred entry above; that will be handled
                    # on the next loop iteration.
                    deferred_tail_retry = None

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
        return True

    # ---------- Core calls ----------

    def _translate_batch_json(
        self,
        *,
        src_items: List[str],
        target_lang: str,
        termbase: Dict[str, Dict[str, str]],
        batch_ids: List[int],
    ) -> List[Dict[str, Any]]:
        """
        Ask for JSON ONLY: {"items":[{"id":<int>,"tgt":"..."}]}
        One item per input, same order and ids.
        """
        termbase_block = build_termbase_block(termbase, target_lang)
        mapped_target_lang = target_lang

        system_prompt = (
            "You are a professional subtitle translator. "
            "Return valid JSON ONLY, never prose."
        )

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

INPUT ITEMS:
{self._render_items_for_prompt(batch_ids, src_items)}
"""

        # Prepare the messages payload for logging
        messages_payload = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        # Use JSON mode if available; otherwise rely on instruction.
        resp = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages_payload,
            temperature=0.1,
            # Some clients support JSON mode; if your SDK doesn't, remove this line.
            response_format={"type": "json_object"},  # harmless if unsupported
        )
        content = (resp.choices[0].message.content or "").strip()

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
                        "tgt": (
                            item["tgt"][:50] + "..."
                            if len(item["tgt"]) > 50
                            else item["tgt"]
                        ),
                    }
                    for item in norm
                ],
            )

            return norm
        except Exception:
            # Log the payload sent to translator and the response received when failure occurs
            self.logger.info(
                "Translation failure - Payload sent to translator (lang=%s, items=%d):\nSystem: %s\nUser: %s",
                target_lang,
                len(src_items),
                system_prompt,
                user_prompt,
            )
            self.logger.info(
                "Translation failure - Raw response received from translator:\n%s",
                content,
            )
            # Diagnostics: token estimates + repetition hint + one-time probe
            try:
                payload_text = f"System: {system_prompt}\nUser: {user_prompt}"
                prompt_tokens = estimate_tokens(payload_text)
                response_tokens = estimate_tokens(content or "")
                self.logger.info(
                    "Diag: token_est prompt=%d, response=%d, total≈%d (chars: prompt=%d, response=%d)",
                    prompt_tokens,
                    response_tokens,
                    prompt_tokens + response_tokens,
                    len(payload_text),
                    len(content or ""),
                )
                hint_class = (
                    "repetitive_token_loop"
                    if has_repetitive_loop(content or "")
                    else "unknown"
                )
                file_base = "?"
                if isinstance(self.logger, logging.LoggerAdapter):
                    try:
                        file_base = self.logger.extra.get("file", "?")  # type: ignore[attr-defined]
                    except Exception:
                        file_base = "?"
                probe_malformed_json(
                    logger=self.logger,
                    budget=self._probe_budget,
                    file_base=file_base,
                    lang=target_lang,
                    batch_ids=batch_ids[:8],
                    raw_excerpt=(content or "")[:300],
                    hint_class=hint_class,
                )
            except Exception as diag_ex:
                self.logger.debug("Diagnostics capture skipped: %s", diag_ex)

            # If the model ignored JSON mode, we cannot recover - fail fast
            self.logger.error(
                "Model did not return JSON; cannot recover without shape lock."
            )
            raise RuntimeError(
                "Translation failed: model did not return valid JSON format"
            )

    def _reformat_fix_placeholders(
        self,
        *,
        src_items: List[str],
        tgt_items: List[str],
        ids: List[int],
        allowed_placeholders: List[str],
    ) -> Optional[List[str]]:
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
            messages=messages_payload,
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
    def _render_items_for_prompt(ids: List[int], texts: List[str]) -> str:
        rows = []
        for i, t in zip(ids, texts):
            # One line per item; escape braces lightly for JSON-mode friendliness
            clean = t.replace("\n", " ").strip()
            rows.append(f"{i}) {clean}")
        return "\n".join(rows)

    @staticmethod
    def debug_log_config(
        cfg,
        logger: logging.Logger,
        *,
        full_termbase=False,
        max_langs=12,
        max_terms_per_lang=8,
    ):
        """
        Emit a redacted, human-friendly config snapshot at DEBUG level.
        - full_termbase=False prints a per-language summary with samples.
        - Set full_termbase=True to pretty-print the entire termbase.
        """
        if logger is None:
            raise ValueError(
                "Logger is required for debug_log_config; no fallback allowed."
            )
        log = logger
        if not log.isEnabledFor(logging.DEBUG):
            return

        def _mask_tail(s: str, n: int = 4) -> str:
            if not s:
                return ""
            return "…" + s[-n:]

        # Header
        lines = []
        lines.append("=== TranslationConfig (DEBUG) ===")

        # Basics
        tgt = getattr(cfg, "target_languages", {}) or {}
        dnt = getattr(cfg, "dnt_terms", []) or []
        tb = getattr(cfg, "termbase", {}) or {}

        lines.append(
            f"Output directory  : {getattr(cfg, 'output_directory', 'translated_srt_files')}"
        )
        lines.append(
            f"Model / batch     : {getattr(cfg, 'model_name', 'gpt-4o-mini')} / {getattr(cfg, 'batch_size', 5)}"
        )
        lines.append(f"API key (tail)    : {_mask_tail(getattr(cfg, 'api_key', ''))}")

        # Targets
        codes = list(tgt.values())
        lines.append(
            f"Targets ({len(codes)}): {', '.join(codes) if codes else '(none)'}"
        )

        # DNT
        lines.append(f"DNT terms ({len(dnt)}):")
        if dnt:
            for term in dnt:
                lines.append(f"  - {term}")
        else:
            lines.append("  (none)")

        # Termbase
        lines.append(
            f"Termbase languages ({len(tb)}): {', '.join(sorted(tb.keys())) if tb else '(none)'}"
        )

        if full_termbase and tb:
            # Pretty-print the entire termbase
            lines.append("Termbase (full):")
            lines.append(json.dumps(tb, ensure_ascii=False, indent=2, sort_keys=True))
        elif tb:
            # Summarize per language with samples
            lines.append("Termbase (summary with samples):")
            lang_items = sorted(tb.items())[:max_langs]
            for lang, mapping in lang_items:
                terms = list(mapping.items())
                shown = terms[:max_terms_per_lang]
                extra = len(terms) - len(shown)
                lines.append(f"  [{lang}] {len(terms)} terms")
                for k, v in shown:
                    lines.append(f"  • {k}  →  {v}")
                if extra > 0:
                    lines.append(f"    … (+{extra} more)")
            if len(tb) > max_langs:
                lines.append(f"  … (+{len(tb) - max_langs} more languages)")
        else:
            lines.append("Termbase: (none)")

        log.debug("\n".join(lines))

    # ---------- Adjacent placeholder drift repair ----------
    def _repair_adjacent_placeholder_drift(
        self,
        *,
        src_items: List[str],
        tgt_items: List[str],
        ph_issues: Dict[int, Dict[str, Set[str]]],
        batch_ids: List[int],
        logger: logging.Logger,
    ) -> List[str]:
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

            logger.info(
                "adjacent-repair: moved tail starting with %s from id=%s to id=%s",
                token,
                batch_ids[i] if i < len(batch_ids) else "?",
                batch_ids[i + 1] if (i + 1) < len(batch_ids) else "?",
            )

        return out

    def _translate_with_simple_shape_lock(
        self,
        src_items: List[str],
        target_lang: str,
        termbase: Dict[str, Dict[str, str]],
        batch_ids: List[int],
        logger: logging.Logger,
    ) -> List[Dict[str, Any]]:
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

        results: List[Optional[Dict[str, Any]]] = [None] * total

        # Queue holds (start, end, depth, retries)
        work_q = deque()
        work_q.append((0, total, 0, 0))

        # Guard maximum iterations to ensure termination
        max_iterations = (
            total
            * (self._MAX_SPLIT_DEPTH + 1)
            * (self._MAX_JSON_RETRIES_PER_SEGMENT + 1)
            + 10
        )
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
                )
                if len(items) != len(seg_src):
                    raise RuntimeError(
                        f"Count mismatch: expected {len(seg_src)} got {len(items)}"
                    )

                # Success: place into results
                for offset, obj in enumerate(items):
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
                if (
                    self._consecutive_decode_failures
                    >= self._MAX_CONSECUTIVE_DECODE_FAILURES
                ):
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
                        time.sleep(max(0.0, backoff + random.uniform(-0.05, 0.05)))
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
