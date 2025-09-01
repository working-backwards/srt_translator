"""
Helper functions for SRT translation processing.

These functions were moved verbatim from translator.py as part of Stage 3 refactoring.
Do not modify function names, signatures, bodies, or logging text.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, List, Tuple

if TYPE_CHECKING:
    from .translator import SRTTranslator  # type-only; no runtime import


def _create_batches_with_logging(
    self: "SRTTranslator",
    src_subs: List["Subtitle"],
    target_lang: str,
    file_logger: logging.LoggerAdapter,
) -> Tuple[List[List["Subtitle"]], logging.LoggerAdapter]:
    """Create sentence-aware batches with logging setup."""
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
        os.path.basename(getattr(file_logger, "extra", {}).get("file", "unknown")),
        target_lang,
        len(src_subs),
        len(batches),
        self.batch_size,
        self.MAX_BATCH_SIZE,
    )
    return batches, file_logger


def _translate_batch_and_extract(
    self: "SRTTranslator",
    src_items: List[str],
    batch_ids: List[int],
    target_lang: str,
    batch_logger: logging.LoggerAdapter,
) -> List[str]:
    """Translate batch and extract target texts."""
    # Shape-locked translate: one call in the happy path; on mismatch, split halves and retry once.
    try:
        items = self._translate_with_simple_shape_lock(
            src_items,
            target_lang,
            self.termbase,
            batch_ids,
            logger=batch_logger,
        )
    except Exception:
        # Only log payload details at DEBUG to avoid alarming content creators
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(
                "Main batch translation failure - Payload sent (lang=%s, items=%d).",
                target_lang,
                len(src_items),
            )
        raise  # Re-raise the exception to maintain the original behavior

    # Extract and validate placeholder usage
    tgt_texts = [it.get("tgt", "") for it in items]
    return tgt_texts


def _handle_mid_batch_empty_retries(
    self: "SRTTranslator",
    batch: List["Subtitle"],
    tgt_texts: List[str],
    target_lang: str,
    batch_logger: logging.LoggerAdapter,
) -> List[str]:
    """Handle mid-batch empty translation retries."""
    # Empty guard — single pair-retry for mid-stream empty; no source fallback
    for i, (_src_raw, tgt_raw) in enumerate(zip([s.text for s in batch], tgt_texts)):
        if tgt_raw.strip():
            continue
        sid = batch[i].idx
        filled = False
        # Try exactly one pair retry with the next cue when available
        if i + 1 < len(batch):
            try:
                batch_logger.debug(
                    "Empty target at idx=%s; attempting pair retry with next cue.",
                    sid,
                )
                pair_src = [
                    self.term_handler.apply_dnt_placeholders(batch[i].text),
                    self.term_handler.apply_dnt_placeholders(batch[i + 1].text),
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
                        tgt_texts[i] = self.term_handler.restore_dnt_placeholders(
                            candidate
                        )
                        batch_logger.debug(
                            "Pair retry filled idx=%s successfully.", sid
                        )
                        filled = True
            except Exception as ex:
                # SANCTIONED DIAGNOSTICS HOOK: strict pair-retry failure
                # Probes/logs may be added here (and ONLY here) with tests. Do not add probes elsewhere.
                batch_logger.debug("Pair retry failed for idx=%s: %s", sid, ex)
        if not filled:
            if self.error_policy == "STRICT":
                raise RuntimeError(f"Empty translation for subtitle idx={sid}")
            # Leave empty in BOUNDED/DEV; evaluator will flag as Missing translation
            batch_logger.warning(
                "Empty translation for subtitle idx=%s; leaving empty for evaluator.",
                sid,
            )
    return tgt_texts
