# srt_translator/core/translator/translator.py
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple, Set

# Core imports
from srt_translator.core.config.language_config import LanguageConfig
from srt_translator.core.translator.subtitle_formatter import format_subtitle_text
from srt_translator.core.translator.term_handler import TermHandler



# OpenAI client
from openai import OpenAI

# ---------------------------
# Fallback functions (if imports fail)
# ---------------------------

def _safe_format_subtitle_text(
    text: str,
    start_s: float,
    end_s: float,
    lang_code: str,
    cps_soft: int,
    cps_hard: int,
    allow_overshoot_pct: float = 0.10,
) -> str:
    """
    Safe fallback for subtitle formatting if the main formatter is unavailable.
    Simple wrapper with basic line wrapping and CPS enforcement.
    """
    try:
        return format_subtitle_text(
            text, start_s, end_s, lang_code, cps_soft, cps_hard, allow_overshoot_pct
        )
    except Exception:
        # Very basic fallback: wrap to ~42 chars/line and trim if > hard cap
        duration = max(0.001, end_s - start_s)
        cap = int(cps_hard * duration * (1.0 + allow_overshoot_pct))
        clean = " ".join(text.split())
        if len(clean) > cap:
            clean = clean[:cap].rstrip()

        # naive 2-line wrap
        if len(clean) <= 42:
            return clean
        mid = clean.rfind(" ", 0, min(len(clean), 42))
        if mid == -1:
            mid = 42
        return clean[:mid].rstrip() + "\n" + clean[mid:].lstrip()



# ---------------------------
# Data models
# ---------------------------

@dataclass
class Subtitle:
    idx: int
    start: str  # "HH:MM:SS,mmm"
    end: str    # "HH:MM:SS,mmm"
    text: str

@dataclass
class TranslationConfiguration:
    target_languages: Dict[str, str]                  # {"Spanish":"es", ...}
    dnt_terms: List[str]
    termbase: Dict[str, Dict[str, str]]               # {"es": {"term": "term"}, "zh-hans": {...}}
    batch_size: int
    aggressiveness: float
    api_key: str
    model_name: str = "gpt-4o-mini"
    error_policy: str = "STRICT"                      # "STRICT" | "BOUNDED" | "DEV"
    mode: str = "GUI"                                 # "GUI" | "CLI"

# ---------------------------
# Utilities
# ---------------------------

SRT_BLOCK_RE = re.compile(
    r"^\s*(\d+)\s*\n"                                 # index
    r"(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*"
    r"(\d{2}:\d{2}:\d{2},\d{3})\s*\n"
    r"(.*?)(?=\n{2,}|\Z)",                            # text
    re.DOTALL | re.MULTILINE,
)

TIME_RE = re.compile(r"(?P<h>\d{2}):(?P<m>\d{2}):(?P<s>\d{2}),(?P<ms>\d{3})")

PH_RE = re.compile(r"__DNT_TERM_(\d+)__")

def _parse_time_to_seconds(ts: str) -> float:
    m = TIME_RE.match(ts)
    if not m:
        return 0.0
    h = int(m.group("h")); m_ = int(m.group("m")); s = int(m.group("s")); ms = int(m.group("ms"))
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
    parts: List[str] = []
    for i, sub in enumerate(subs, start=1):
        parts.append(str(i))
        parts.append(f"{sub.start} --> {sub.end}")
        parts.append(sub.text.strip())
        parts.append("")  # blank line
    return "\n".join(parts).rstrip() + "\n"

def chunk(seq: Sequence[Any], n: int) -> List[List[Any]]:
    return [list(seq[i:i+n]) for i in range(0, len(seq), n)]

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
    allowed_ids: Set[str],
    ph_regex: re.Pattern,
) -> Dict[int, Dict[str, Set[str]]]:
    issues: Dict[int, Dict[str, Set[str]]] = {}
    for i, (src, tgt) in enumerate(zip(src_items, tgt_items)):
        src_ids = _extract_ph_ids(src, ph_regex)
        tgt_ids = _extract_ph_ids(tgt, ph_regex)
        invented = {pid for pid in tgt_ids if pid not in allowed_ids}
        missing  = {pid for pid in src_ids if pid not in tgt_ids}
        if invented or missing:
            issues[i] = {"invented": invented, "missing": missing}
    return issues

def strip_invented_placeholders(text: str, invented_ids: Set[str], ph_regex: re.Pattern) -> str:
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
    HARD_BATCH_LIMIT = 8  # Maximum subtitles per batch (safety cap)
    
    def __init__(
        self,
        *,
        dnt_terms: List[str],
        termbase: Dict[str, Dict[str, str]],
        api_key: str,
        logger: logging.Logger,  # Required - no fallback allowed
        allow_global_termbase_fallback: bool = False,
        model_name: str = "gpt-4o-mini",
        batch_size: int = 5,
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
        self.logger = logger.logger if isinstance(logger, logging.LoggerAdapter) else logger
        self.logger = self.logger.getChild("core.translator")
        # If caller gave an adapter, re-wrap child with the same extra
        if isinstance(logger, logging.LoggerAdapter):
            self.logger = logging.LoggerAdapter(self.logger, logger.extra)
            
        self.language_config = language_config or LanguageConfig()

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

    # --- Sentence-aware batching (no utterances) ----------------------------
    def _create_batches(
        self,
        subtitles: List[Subtitle],
        soft_limit: int,
        hard_limit: int,
        target_lang: str,
    ) -> List[List[Subtitle]]:
        """
        Group consecutive subtitles into batches that prefer ending at a natural
        sentence boundary once the soft limit is reached, without exceeding
        the hard limit.  Each subtitle remains its own item (1:1 id mapping).
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

            # If we hit the hard cap, cut the batch immediately.
            if len(current) >= hard_limit:
                batches.append(current)
                current = []
                continue

            # If we've reached the soft target, prefer to break on a sentence end.
            if len(current) >= soft_limit:
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
        file_logger = logging.LoggerAdapter(self.logger, {
            "run_id": getattr(self.logger, "extra", {}).get("run_id", "n/a"),
            "file": os.path.basename(input_filepath),
            "lang": target_lang,
        })
        
        file_logger.info("Using subtitle-based translation system for %s → %s", os.path.basename(input_filepath), target_lang)

        # 1) Load and parse SRT
        with open(input_filepath, "r", encoding="utf-8") as f:
            src_text = f.read()
        src_subs = parse_srt(src_text)
        if not src_subs:
            raise ValueError("Empty or invalid SRT: no subtitle blocks found.")

        self.logger.info("Processing %d subtitles for %s", len(src_subs), os.path.basename(input_filepath))

        # 2) Sentence-aware batching (each subtitle stays its own item)
        batches = self._create_batches(
            subtitles=src_subs,
            soft_limit=int(self.batch_size),
            hard_limit=self.HARD_BATCH_LIMIT,
            target_lang=target_lang,
        )
        
        file_logger.info(
            "Using sentence-aware batching for %s → %s "
            "(%d subtitles → %d batches; "
            "soft=%d, hard=%d)",
            os.path.basename(input_filepath), target_lang, len(src_subs), len(batches), 
            self.batch_size, self.HARD_BATCH_LIMIT
        )
        all_tgt_subs: List[Subtitle] = []

        # Language rules
        cps_soft, cps_hard = self._get_cps_caps(target_lang)

        for bi, batch in enumerate(batches, start=1):
            file_logger.info("Processing %d subtitles in batch %d/%d", len(batch), bi, len(batches))

            # Preprocess: apply DNT placeholders on a per-subtitle basis
            src_items = [self.term_handler.apply_dnt_placeholders(s.text) for s in batch]

            # Call JSON batch
            items = self._translate_batch_json(
                src_items=src_items,
                target_lang=target_lang,
                termbase=self.termbase,
                batch_ids=[s.idx for s in batch],
            )

            # Validate count
            if len(items) != len(batch):
                file_logger.warning("JSON batch count mismatch: expected %d, got %d", len(batch), len(items))
                # Reformat pass (shape-only)
                items = self._reformat_items_to_shape(
                    raw_src=src_items,
                    raw_ids=[s.idx for s in batch],
                    raw_tgt_text="\n".join([it.get("tgt", "") for it in items]) if isinstance(items, list) else str(items),
                    expected_count=len(batch),
                )

            # Extract and validate placeholder usage
            tgt_texts = [it.get("tgt", "") for it in items]
            allowed_ph_ids = {m.group(1) for ph in self.term_handler.placeholder_map.keys() for m in [self.term_handler.placeholder_regex.search(ph)] if m}
            ph_issues = validate_placeholders_pair(src_items, tgt_texts, allowed_ph_ids, self.term_handler.placeholder_regex)

            if ph_issues:
                for idx, kinds in ph_issues.items():
                    inv = ",".join(sorted(kinds["invented"])) or "-"
                    mis = ",".join(sorted(kinds["missing"])) or "-"
                    file_logger.warning("Placeholder check (batch=%d, item=%d): invented=[%s] missing=[%s]", bi, idx, inv, mis)

                if self.error_policy == "STRICT":
                    fixed = self._reformat_fix_placeholders(
                        src_items=src_items,
                        tgt_items=tgt_texts,
                        ids=[s.idx for s in batch],
                        allowed_placeholders=sorted(self.term_handler.placeholder_map.keys()),
                    )
                    if fixed is None:
                        raise RuntimeError("Reformat failed: phantom/missing placeholders unresolved.")
                    tgt_texts = fixed
                elif self.error_policy in ("BOUNDED", "DEV"):
                    # Remove invented; warn about missing but do not invent content.
                    for i, kinds in ph_issues.items():
                        if kinds["invented"]:
                            tgt_texts[i] = strip_invented_placeholders(tgt_texts[i], kinds["invented"], self.term_handler.placeholder_regex)

            # Restore DNT placeholders to originals
            tgt_texts = [self.term_handler.restore_dnt_placeholders(t) for t in tgt_texts]

            # Empty guard (STRICT/BOUNDED behavior)
            for i, (src_raw, tgt_raw) in enumerate(zip([s.text for s in batch], tgt_texts)):
                if not tgt_raw.strip():
                    msg = f"Empty translation for subtitle idx={batch[i].idx}"
                    if self.error_policy == "STRICT":
                        raise RuntimeError(msg)
                    file_logger.warning("%s; falling back to source text (BOUNDED/DEV).", msg)
                    tgt_texts[i] = src_raw

            # Format per subtitle (CPS; line breaks)
            for s, tgt in zip(batch, tgt_texts):
                start_s = _parse_time_to_seconds(s.start)
                end_s = _parse_time_to_seconds(s.end)
                formatted = format_subtitle_text(
                    lang_code=target_lang.lower(),
                    text=tgt,
                    start_ms=int(start_s * 1000),  # Convert seconds to milliseconds
                    end_ms=int(end_s * 1000),      # Convert seconds to milliseconds
                    cps_soft=cps_soft,
                    cps_hard=cps_hard,
                    overshoot_pct=0.10,
                )
                all_tgt_subs.append(Subtitle(idx=s.idx, start=s.start, end=s.end, text=formatted))

        # 3) Render and write
        out_text = render_srt(all_tgt_subs)
        with open(output_filepath, "w", encoding="utf-8") as f:
            f.write(out_text)

        # Defer fixes to core.main; just log what we produced.
        if file_logger:
            file_logger.debug(
                "Translated %s → %s (lang=%s). Placeholder restoration will run in core.main Fixer pass.",
                os.path.basename(input_filepath), os.path.basename(output_filepath), target_lang
            )

        file_logger.info("Subtitle-based translation completed for %s", os.path.basename(input_filepath))
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
        # Use JSON mode if available; otherwise rely on instruction.
        resp = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            # Some clients support JSON mode; if your SDK doesn't, remove this line.
            response_format={"type": "json_object"},  # harmless if unsupported
        )
        content = (resp.choices[0].message.content or "").strip()

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
            return norm
        except Exception:
            # If the model ignored JSON mode, attempt a quick reformat pass.
            self.logger.warning("Model did not return JSON; attempting shape reformat.")
            items = self._reformat_items_to_shape(
                raw_src=src_items,
                raw_ids=batch_ids,
                raw_tgt_text=content,
                expected_count=len(src_items),
            )
            return items

    def _reformat_items_to_shape(
        self,
        *,
        raw_src: List[str],
        raw_ids: List[int],
        raw_tgt_text: str,
        expected_count: int,
    ) -> List[Dict[str, Any]]:
        """
        Shape-only pass: do not change wording, only produce the required
        JSON with exactly expected_count items and the given ids.
        """
        sys = "You are a text formatter. Do not translate; only reformat."
        prompt = f"""Reformat the given translations to valid JSON ONLY.

RULES:
- Keep wording EXACTLY the same as provided; do not translate or edit text.
- Return JSON ONLY as: {{"items":[{{"id":<int>,"tgt":"..."}}, ...]}}
- MUST have exactly {expected_count} items.
- Use ids in this order: {raw_ids}.
- Do not merge or split content across items; assign the nearest content to each id.

SOURCE ITEMS (id → source):
{self._render_items_for_prompt(raw_ids, raw_src)}

TRANSLATED TEXT (to reformat, do NOT translate):
{raw_tgt_text}
"""
        resp = self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "system", "content": sys},
                      {"role": "user", "content": prompt}],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        content = (resp.choices[0].message.content or "").strip()
        data = json.loads(content)
        items = data.get("items", [])
        if len(items) != expected_count:
            raise RuntimeError(f"Reformat still mismatched: expected {expected_count}, got {len(items)}")
        norm = []
        for oid, obj in zip(raw_ids, items):
            # force ids to expected order
            norm.append({"id": oid, "tgt": obj.get("tgt", "")})
        return norm

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
        resp = self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "system", "content": sys},
                      {"role": "user", "content": prompt}],
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
            return None

    # ---------- Helpers ----------

    def _get_cps_caps(self, lang_code: str) -> Tuple[int, int]:
        try:
            caps = self.language_config.get_cps_caps(lang_code)
            # Expecting (soft, hard). If your method returns a dict, adapt here.
            if isinstance(caps, (list, tuple)) and len(caps) == 2:
                return int(caps[0]), int(caps[1])
            if isinstance(caps, dict):
                return int(caps.get("cps_soft", 16)), int(caps.get("cps_hard", 18))
        except Exception:
            pass
        return (16, 18)  # sensible defaults

    @staticmethod
    def _render_items_for_prompt(ids: List[int], texts: List[str]) -> str:
        rows = []
        for i, t in zip(ids, texts):
            # One line per item; escape braces lightly for JSON-mode friendliness
            clean = t.replace("\n", " ").strip()
            rows.append(f"{i}) {clean}")
        return "\n".join(rows)

    @staticmethod
    def debug_log_config(cfg, logger: logging.Logger, *, full_termbase=False, max_langs=12, max_terms_per_lang=8):
        """
        Emit a redacted, human-friendly config snapshot at DEBUG level.
        - full_termbase=False prints a per-language summary with samples.
        - Set full_termbase=True to pretty-print the entire termbase.
        """
        if logger is None:
            raise ValueError("Logger is required for debug_log_config; no fallback allowed.")
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
