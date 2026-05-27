import json
from types import SimpleNamespace
from unittest.mock import MagicMock

from srt_translator.core.constants import (
    DEFAULT_DETECTION_MODEL,
    MAX_COMPLETION_TOKENS_LANGUAGE_DETECTION,
)
from srt_translator.core.services.language_detection import detect_source_language


def _fake_chat_returning(payload: dict):
    """Build a fake `chat` object that returns `payload` as a JSON string."""
    fake = MagicMock()
    fake.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)))]
    )
    return fake


def _fake_chat_returning_raw(raw: str):
    """Build a fake `chat` whose response.message.content is `raw` verbatim."""
    fake = MagicMock()
    fake.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=raw))]
    )
    return fake


def test_detect_source_language_uses_detection_constant_not_caller_model():
    """Regression test: detection must NOT take the caller's generation model.
    It always uses DEFAULT_DETECTION_MODEL so the detection call is independent
    of the user's generation/translation model choice.
    """
    fake = _fake_chat_returning({"detected_code": "en", "confidence": 0.99, "mixed": False})

    detect_source_language("Hello world.", chat=fake)

    fake.chat.completions.create.assert_called_once()
    kwargs = fake.chat.completions.create.call_args.kwargs
    assert kwargs["model"] == DEFAULT_DETECTION_MODEL


def test_detect_source_language_signature_does_not_accept_generation_model_name():
    """The old (pre-fix) signature took `generation_model_name` and `temperature`
    as required keyword args. The fix dropped them. This test will fail loudly
    if anyone reintroduces them.
    """
    import inspect

    sig = inspect.signature(detect_source_language)
    params = sig.parameters
    assert "generation_model_name" not in params
    assert "temperature" not in params


def test_detect_source_language_returns_normalized_code_on_success():
    fake = _fake_chat_returning({"detected_code": "en", "confidence": 0.92, "mixed": False})

    result = detect_source_language("Hello world.", chat=fake)

    assert result["detected_code"] == "en"
    assert result["confidence"] == 0.92
    assert result["mixed"] is False


def test_detect_source_language_handles_empty_input():
    fake = MagicMock()
    result = detect_source_language("", chat=fake)
    assert result["detected_code"] is None
    fake.chat.completions.create.assert_not_called()


def test_detect_source_language_handles_empty_model_response():
    """Reproduces the gpt-5-mini bug: when the model exhausts its budget on
    reasoning, message.content is empty. Detection must return all-None
    rather than crash.
    """
    fake = _fake_chat_returning_raw("")

    result = detect_source_language("Hello world.", chat=fake)

    assert result["detected_code"] is None
    assert result["normalized_code"] is None


def test_detect_source_language_handles_api_exception():
    fake = MagicMock()
    fake.chat.completions.create.side_effect = RuntimeError("network down")

    result = detect_source_language("Hello world.", chat=fake)

    assert result["detected_code"] is None
    assert result["confidence"] == 0.0


def test_detect_source_language_passes_detection_token_budget_and_json_mode():
    fake = _fake_chat_returning({"detected_code": "en", "confidence": 0.9, "mixed": False})

    detect_source_language("Hello world.", chat=fake)

    kwargs = fake.chat.completions.create.call_args.kwargs
    # DEFAULT_DETECTION_MODEL is non-reasoning, so build_call_params should
    # pass the constant through unchanged (clamped only if it exceeds the
    # model's max_output_tokens, which 256 will not).
    assert kwargs["max_completion_tokens"] == MAX_COMPLETION_TOKENS_LANGUAGE_DETECTION
    assert kwargs["response_format"] == {"type": "json_object"}
