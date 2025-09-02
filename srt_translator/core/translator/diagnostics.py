import re
from collections import defaultdict
from typing import List, Optional, Sequence


# -- Token estimation (char-based, fast, deterministic) -----------------------
# We keep it dead-simple and deterministic for logging/diagnostics only.
def estimate_tokens_from_chars(char_count: int) -> int:
    # ≈4 chars/token is a common coarse heuristic; never returns 0 for non-empty.
    return 1 if char_count <= 0 else max(1, char_count // 4)


def estimate_tokens(text: str) -> int:
    return estimate_tokens_from_chars(len(text or ""))


# -- Repetition detector (catches "ek ek ek ..." and similar loops) -----------
_REPETITION_RE = re.compile(
    r"\b(\w{2,})\b(?:[\s,.;:!?]+?\1\b){20,}",
    re.IGNORECASE | re.UNICODE,
)


def looks_like_repetitive_loop(text: str) -> bool:
    if not text:
        return False
    return bool(_REPETITION_RE.search(text))


# -- Safe snipper for log lines ------------------------------------------------
def snip(text: str, limit: int = 400) -> str:
    if text is None:
        return ""
    t = text.replace("\n", " ").replace("\r", " ")
    return t if len(t) <= limit else t[:limit] + "…"


# -- Build a focused diagnostic question for the LLM ---------------------------
def build_oversize_probe_question(
    *,
    lang_code: str,
    batch_ids: Sequence[int],
    source_items: Sequence[str],
    response_preview: str,
    prompt_token_estimate: int,
    response_token_estimate: int,
    repetitive_loop_detected: bool,
) -> str:
    # Format the source items as a numbered list; keep it compact (max ~8 lines typical)
    src_lines: List[str] = []
    for i, s in enumerate(source_items, start=1):
        if s is None:
            continue
        src_lines.append(f"{i}) {s}")
    src_block = "\n".join(src_lines)

    loop_note = "YES" if repetitive_loop_detected else "NO"

    # Keep question direct and short; ask for 1–2 sentence reason only.
    # We do not ask for a fix; this is purely advisory logging.
    question = (
        "You are a diagnostic assistant. The last *translation* call produced an abnormally "
        "large output (and possibly repetitive text), which violated the expected response "
        "shape. Please explain briefly (1–2 sentences) why a translation model might do this."
        "\n\n"
        f"LANGUAGE: {lang_code}\n"
        f"BATCH IDs: {list(batch_ids)}\n"
        "\n"
        "SOURCE EXCERPT:\n"
        f"{src_block}\n"
        "\n"
        "RESPONSE EXCERPT (truncated):\n"
        f"{response_preview}\n"
        "\n"
        "TOKEN ESTIMATES:\n"
        f"- Prompt: ~{prompt_token_estimate} tokens\n"
        f"- Response: ~{response_token_estimate} tokens\n"
        f"- Repetitive loop detected: {loop_note}\n"
        "\n"
        "QUESTION: What likely caused the model to output an oversized/malformed translation "
        "response here (e.g., confusion about task, prompt/formatting, context length, or "
        "other failure mode)? Keep it concise."
    )
    return question


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


# NOTE: Legacy logger-based probes were removed. The translator invokes probes directly.


def probe_malformed_json_with_translator(
    *,
    translator,
    budget: MalformedProbeBudget,
    file_base: str,
    lang: str,
    batch_ids: List[int],
    raw_excerpt: str,
    hint_class: str = "unknown",
    source_text: Optional[str] = None,
) -> None:
    """Actually ask the AI what went wrong when JSON is malformed. Uses translator's OpenAI client directly."""
    try:
        if not budget.allow(file_base, lang):
            return

        # Log that we're about to ask the AI
        translator.logger.info(
            "Probing AI for malformed JSON explanation (file=%s, lang=%s, ids=%s)",
            file_base,
            lang,
            batch_ids[:6],
        )

        # Create the diagnostic probe question for the AI
        source_content = (
            source_text
            if source_text
            else f"[Source text for {len(batch_ids)} items - not available]"
        )
        probe_question = (
            f"You are a diagnostic AI that analyzes translation failures. "
            f"Explain why the AI translator failed in this specific case.\n\n"
            f"LANGUAGE: {lang}\n"
            f"FILE: {file_base}\n"
            f"BATCH IDs: {batch_ids[:8]}\n"
            f"HINT CLASS: {hint_class}\n\n"
            f"ORIGINAL TEXT ({len(batch_ids)} items):\n"
            f"{source_content}\n\n"
            f"RESPONSE RECEIVED (first 500 chars):\n"
            f"{raw_excerpt[:500] if raw_excerpt else 'None'}\n\n"
            f"TOKEN COUNTS:\n"
            f"- Original prompt: ~{estimate_tokens(raw_excerpt or '')} tokens\n"
            f"- Response received: ~{len(raw_excerpt or '') // 4} tokens\n"
            f"- Repetitive loop detected: {'YES' if looks_like_repetitive_loop(raw_excerpt or '') else 'NO'}\n\n"
            f"QUESTION: Why did you generate such a malformed/large response? "
            f"Were you confused about the task, trying to be too detailed, "
            f"or did something else go wrong? Please explain briefly in 1-2 sentences."
        )

        # Make direct AI call using the translator's OpenAI client
        try:
            translator.logger.info("Making AI probe call via translator's OpenAI client")
            diag_resp = translator.client.chat.completions.create(
                model=translator.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a concise diagnostic assistant. "
                            "Explain the likely reason for the prior translation model's failure "
                            "in 1–2 sentences. Do not produce translations."
                        ),
                    },
                    {"role": "user", "content": probe_question},
                ],
                temperature=0,
                max_tokens=200,
            )
            ai_explanation = (diag_resp.choices[0].message.content or "").strip()
            translator.logger.info("AI probe successful via translator's OpenAI client")
        except Exception as ai_ex:
            translator.logger.error("AI probe via translator's OpenAI client failed: %s", ai_ex)
            ai_explanation = None

        # Log the AI's explanation if we got one
        if ai_explanation:
            translator.logger.info(
                "AI explanation for malformed JSON: %s", snip(ai_explanation, 400)
            )
        else:
            translator.logger.warning("AI probe failed - logging question for manual review")
            translator.logger.info("AI probe question (manual review needed): %s", probe_question)

        # Always log the diagnostic summary
        diagnostic_summary = (
            f"MALFORMED JSON AI PROBE COMPLETED (file={file_base}, lang={lang}):\n"
            f"Hint class: {hint_class}\n"
            f"AI explanation: {ai_explanation or 'None (AI probe failed)'}\n"
            f"Raw excerpt length: {len(raw_excerpt or '')} chars\n"
            f"Token estimate: ~{estimate_tokens(raw_excerpt or '')} tokens\n"
            f"Repetitive loop: {'YES' if looks_like_repetitive_loop(raw_excerpt or '') else 'NO'}"
        )

        translator.logger.info(diagnostic_summary)

    except Exception as e:
        # If the probe itself fails, log the error properly
        error_msg = f"AI probe for malformed JSON failed: {e}"
        translator.logger.error(error_msg)

        # Try to log additional context about the failure
        try:
            translator.logger.error(
                "Probe failure context: file=%s, lang=%s, ids=%s",
                file_base,
                lang,
                batch_ids[:6],
            )
        except Exception as e:
            # Logging failed, but don't let it break the main flow
            print(f"Warning: Failed to log probe failure context: {e}")  # noqa: T201
