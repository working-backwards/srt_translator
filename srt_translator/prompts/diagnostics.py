# srt_translator/prompts/diagnostics.py
"""Prompt builders for diagnostic probes (oversized/malformed responses)."""

from __future__ import annotations

from collections.abc import Sequence


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
    """Build the diagnostic question for oversized/repetitive translation output.

    Args:
        lang_code: Target language code.
        batch_ids: IDs of the batch items.
        source_items: Source text items (typically first 8).
        response_preview: Truncated response text.
        prompt_token_estimate: Estimated prompt token count.
        response_token_estimate: Estimated response token count.
        repetitive_loop_detected: Whether a repetitive loop was detected.

    Returns:
        User prompt string for the diagnostic call.
    """
    # Format the source items as a numbered list; keep it compact (max ~8 lines typical)
    src_lines: list[str] = []
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


def build_oversize_diagnostic_system_prompt() -> str:
    """Build the static system prompt for the oversized-response diagnostic assistant.

    Returns:
        System prompt string.
    """
    return (
        "You are a concise diagnostic assistant. "
        "Explain the likely reason for the prior translation model's oversized "
        "or repetitive output in 1–2 sentences. Do not produce translations."
    )


def build_malformed_json_probe(
    *,
    lang: str,
    file_base: str,
    batch_ids: list[int],
    hint_class: str,
    source_content: str,
    raw_excerpt: str | None,
    token_estimate: int,
    response_token_estimate: int,
    repetitive_loop_detected: bool,
) -> str:
    """Build the diagnostic probe question for malformed JSON responses.

    Args:
        lang: Target language code.
        file_base: Base filename being translated.
        batch_ids: IDs of the batch items.
        hint_class: Classification hint for the failure.
        source_content: Source text or fallback message.
        raw_excerpt: Raw response excerpt (may be None).
        token_estimate: Estimated token count for the original prompt.
        response_token_estimate: Estimated token count for the response.
        repetitive_loop_detected: Whether a repetitive loop was detected.

    Returns:
        User prompt string for the diagnostic call.
    """
    return (
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
        f"- Original prompt: ~{token_estimate} tokens\n"
        f"- Response received: ~{response_token_estimate} tokens\n"
        f"- Repetitive loop detected: {'YES' if repetitive_loop_detected else 'NO'}\n\n"
        f"QUESTION: Why did you generate such a malformed/large response? "
        f"Were you confused about the task, trying to be too detailed, "
        f"or did something else go wrong? Please explain briefly in 1-2 sentences."
    )
