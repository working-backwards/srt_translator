import json
import math
import re
from collections import defaultdict
from typing import List

REPETITIVE_RE = re.compile(r"\b(\w+)(?:\s+\1){6,}\b", re.IGNORECASE)


def estimate_tokens(text: str) -> int:
    """Crude token estimate (~4 chars/token). Replace with client usage if available."""
    if not text:
        return 0
    return max(1, math.ceil(len(text) / 4))


def has_repetitive_loop(text: str) -> bool:
    if not text:
        return False
    return bool(REPETITIVE_RE.search(text))


class MalformedProbeBudget:
    """Allow at most one probe per (file, lang)."""

    def __init__(self):
        self._seen = defaultdict(int)

    def allow(self, file_base: str, lang: str) -> bool:
        key = (file_base, lang)
        if self._seen[key] >= 1:
            return False
        self._seen[key] += 1
        return True


def probe_malformed_json(
    *,
    logger,
    budget: MalformedProbeBudget,
    file_base: str,
    lang: str,
    batch_ids: List[int],
    raw_excerpt: str,
    hint_class: str = "unknown",
) -> None:
    """One-time advisory probe; never alters control flow. Logs a structured explanation if a small LLM is available on logger."""
    try:
        if not budget.allow(file_base, lang):
            return
        # If a small LLM handle is exposed on the logger, use it; otherwise log a stub line.
        llm_small = getattr(logger, "llm_small", None)
        if llm_small is None:
            logger.info(
                "Malformed JSON probe skipped (no small LLM). hint_class=%s (file=%s lang=%s ids=%s) excerpt=%s",
                hint_class,
                file_base,
                lang,
                batch_ids,
                (raw_excerpt or "")[:120].replace("\n", " "),
            )
            return
        system = (
            "You are a linter for model outputs. Answer with ONE JSON object only: "
            '{"class":"","cause":"","recommendation":"","can_retry":true}. '
            'class ∈ {"prose","json_single_quotes","schema_mismatch","truncation","encoding","repetitive_token_loop","unknown"}. '
            "cause≤160, recommendation≤120."
        )
        user = (
            f"Context: We asked a translator to return JSON with exactly N items: "
            f'{{"items":[{{"id":<int>,"tgt":"<string>"}}]}} (N=?). '
            f"Language: {lang}\n"
            f'Invalid output excerpt (first 300 chars):\n{(raw_excerpt or "")[:300]}\n'
            f"Hint class: {hint_class}\n"
            "Question: What failed (class), concise cause, one-line recommendation, and whether retrying the same prompt is advisable? "
            "Return JSON ONLY as specified."
        )
        diag_raw = llm_small(
            system=system,
            user=user,
            temperature=0,
            max_tokens=120,
            timeout_s=5,
            response_format="json",
        )
        try:
            diag = json.loads(diag_raw) if isinstance(diag_raw, str) else diag_raw
        except Exception:
            diag = {
                "class": "unknown",
                "cause": "probe returned non-JSON",
                "recommendation": "n/a",
                "can_retry": False,
            }
        logger.info(
            "Malformed JSON probe (file=%s, lang=%s, ids=%s): class=%s cause=%s rec=%s can_retry=%s",
            file_base,
            lang,
            batch_ids[:6],
            diag.get("class"),
            diag.get("cause"),
            diag.get("recommendation"),
            diag.get("can_retry"),
        )
    except Exception as e:
        logger.debug("Probe failed: %s", e)
