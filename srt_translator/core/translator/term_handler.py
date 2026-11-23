#!/usr/bin/env python3
"""
Term handler for the SRT Translator.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping
from typing import Any

# Public, stable placeholder regex — Fixer depends on this exact shape.
PH_RE = re.compile(r"__DNT_TERM_(\d+)__", re.UNICODE)


def _dedup_preserve_order(items: list[str]) -> list[str]:
    seen = set()
    out: list[str] = []
    for x in items or []:
        if not x:
            continue
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def _compile_word_safe_pattern(term: str) -> re.Pattern:
    """
    Compile a regex that matches `term` as a token without
    splitting inside longer words. Works for mixed scripts.
    Strategy: (?<!\\w)term(?!\\w) with term escaped.
    """
    return re.compile(rf"(?<!\w){re.escape(term)}(?!\w)", re.UNICODE)


def ensure_flat_termbase(termbase: Mapping[str, Any] | None) -> dict[str, str]:
    """Validate one language's termbase and return a plain-dict copy.

    The translator works on a single language's entries, ``{source_term: target_term}``.
    ``TranslationConfig`` stores them as read-only ``MappingProxyType`` objects, so any
    ``Mapping`` is accepted. A nested ``{language: {source: target}}`` mapping is rejected:
    it is the configuration shape, not the translator's, and passing it used to merge
    every language's entries into one table.

    Raises:
        TypeError: if ``termbase`` is not a mapping, a value is itself a mapping, or an
            entry is not a string.
    """
    if termbase is None:
        return {}
    if not isinstance(termbase, Mapping):
        raise TypeError(f"termbase must be a mapping of source term to target term, got {type(termbase).__name__}")
    flat: dict[str, str] = {}
    for source, target in termbase.items():
        if isinstance(target, Mapping):
            raise TypeError(
                "termbase must be a flat {source: target} mapping for one language; "
                f"got a nested mapping under {source!r}. Pass config.termbase.get(lang_code, {{}})."
            )
        if not isinstance(source, str) or not isinstance(target, str):
            raise TypeError(f"termbase entries must be strings, got {source!r}: {target!r}")
        flat[source] = target
    return flat


class TermHandler:
    """
    Central place for termbase find-and-replace and DNT placeholders, for ONE language.
    - Takes that language's flat termbase {source_term: target_term}.
    - apply_all(): replaces termbase terms with their target strings, then DNT terms
      with placeholders (term -> __DNT_TERM_i__), before translation.
    - restore_all(): restores DNT placeholders after translation.
    - Exposes `placeholder_regex` so other modules (Fixer/logs) can detect them.
    The prompt glossary is built separately (translator.build_termbase_block).
    """

    def __init__(
        self,
        dnt_terms: list[str] | None = None,
        termbase: Mapping[str, str] | None = None,
        lang_code: str | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.logger = logger or logging.getLogger(__name__)
        self.lang_code = (lang_code or "").lower()
        # One language's entries: {source_term: target_term}
        self.termbase: dict[str, str] = ensure_flat_termbase(termbase)
        self.term_map: dict[str, str] = dict(self.termbase)
        self.termbase_patterns: list[tuple[re.Pattern, str]] = []
        for term, replacement in sorted(self.term_map.items(), key=lambda x: len(x[0]), reverse=True):
            pat = re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)
            self.termbase_patterns.append((pat, replacement))

        # Build stable placeholder map once per file/language

        self._ordered_terms: list[str] = _dedup_preserve_order(dnt_terms or [])
        # Expose dnt_terms for backward compatibility with core/main.py
        self.dnt_terms = self._ordered_terms
        self.placeholder_map: dict[str, str] = {term: f"__DNT_TERM_{i}__" for i, term in enumerate(self._ordered_terms)}
        # Precompile exact patterns for speed and correctness
        self.dnt_patterns: list[tuple[re.Pattern, str, str]] = []
        # Sort longest-first to avoid partial/overlapping replacement issues.
        for term in sorted(self._ordered_terms, key=len, reverse=True):
            pat = _compile_word_safe_pattern(term)
            ph = self.placeholder_map[term]
            self.dnt_patterns.append((pat, term, ph))

        self.logger.debug(
            "TermHandler initialized (lang=%s): %d DNT terms, %d TB entries",
            self.lang_code,
            len(self._ordered_terms),
            len(self.termbase),
        )

    # Expose for Fixer & logs
    @property
    def placeholder_regex(self) -> re.Pattern:
        return PH_RE

    def build_placeholder_map(self, new_terms: list[str] | None = None) -> dict[str, str]:
        """
        Optional: rebuild the map if calling code wants to override terms.
        Returns the active map for convenience.
        """
        if new_terms is None:
            return self.placeholder_map
        self._ordered_terms = _dedup_preserve_order(new_terms)
        self.placeholder_map = {t: f"__DNT_TERM_{i}__" for i, t in enumerate(self._ordered_terms)}
        self.dnt_patterns.clear()
        for term in sorted(self._ordered_terms, key=len, reverse=True):
            self.dnt_patterns.append((_compile_word_safe_pattern(term), term, self.placeholder_map[term]))
        self.logger.debug("Rebuilt DNT placeholder map: %d terms", len(self._ordered_terms))
        return self.placeholder_map

    def apply_dnt_placeholders(self, text: str) -> str:
        """
        Replace DNT terms in `text` with placeholders.
        Longest-first; token-safe; preserves punctuation/spacing.
        """

        if not text or not self.dnt_patterns:
            return text

        def _sub_once(s: str, pat: re.Pattern, ph: str) -> str:
            return pat.sub(ph, s)

        out = text
        for pat, term, ph in self.dnt_patterns:
            # Only apply placeholder if the term is in text
            if term in out:
                new_out = _sub_once(out, pat, ph)
                if new_out != out:
                    self.logger.debug("Applied DNT placeholder: '%s' → %s", term, ph)
                    out = new_out
        return out

    def restore_dnt_placeholders(self, text: str) -> str:
        """
        Restore placeholders back to original DNT terms in `text`.
        """

        if not text or not self.placeholder_map:
            return text

        # Reverse mapping: placeholder -> term
        rev = {ph: term for term, ph in self.placeholder_map.items()}
        # Fast path: if no placeholders, return early
        if not PH_RE.search(text or ""):
            return text

        def _restore(m: re.Match) -> str:
            full = m.group(0)
            # Map full placeholder token back to term if we have it
            return rev.get(full, full)

        restored = PH_RE.sub(_restore, text)
        if restored != text:
            self.logger.debug("Restored DNT placeholders in translated text")
        return restored

    def apply_termbase(self, text: str) -> str:
        """
        Replace termbase keys in source text before translation.
        """
        if not text:
            return text

        out = text
        for pat, replacement in self.termbase_patterns:
            out = pat.sub(replacement, out)
        return out

    def apply_all(self, text: str) -> str:
        """Apply termbase substitutions then DNT placeholders (correct order)."""
        termbase_substituted = self.apply_termbase(text)
        return self.apply_dnt_placeholders(termbase_substituted)

    def restore_all(self, text: str) -> str:
        """Restore DNT placeholders in translated text.

        Termbase substitutions are not re-applied to model output: the find-and-replace
        runs on the source before translation, so the model already sees the preferred
        target strings.
        """
        return self.restore_dnt_placeholders(text)

    # Optional artifacts/metrics helpers
    def placeholder_count(self) -> int:
        return len(self.placeholder_map)

    def placeholder_report(self) -> list[tuple[int, str, str]]:
        """
        Returns list of (idx, term, placeholder) for logging/artifacts.
        """
        return [(i, term, self.placeholder_map[term]) for i, term in enumerate(self._ordered_terms)]

    def get_effective_dnt(self) -> list[str]:
        """Get the effective DNT terms (after precedence rules applied)"""
        return self._ordered_terms.copy()
