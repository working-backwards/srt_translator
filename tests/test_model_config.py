from srt_translator.config.model_config_loader import (
    MODEL_CONFIG,
    build_call_params,
    get_max_inline_tokens,
)


def test_get_max_inline_tokens_gpt5_mini():
    assert get_max_inline_tokens("gpt-5-mini") == 250000


def test_get_max_inline_tokens_fallback_for_unknown_model():
    assert get_max_inline_tokens("unknown-model") == 12500


def test_build_call_params_omits_temperature_for_gpt5_mini():
    # Use a budget above REASONING_MODEL_COMPLETION_TOKEN_FLOOR so the floor
    # does not lift it; this test only cares that temperature is dropped.
    params = build_call_params("gpt-5-mini", max_completion_tokens=8000, temperature=0.75)
    assert "temperature" not in params
    assert params["max_completion_tokens"] == 8000


def test_build_call_params_includes_temperature_for_gpt4o_mini():
    params = build_call_params("gpt-4o-mini", max_completion_tokens=1000, temperature=0.75)
    assert params["temperature"] == 0.75


def test_build_call_params_omits_penalties_for_gpt5_mini():
    params = build_call_params(
        "gpt-5-mini",
        max_completion_tokens=1000,
        frequency_penalty=0.6,
        presence_penalty=0.0,
    )
    assert "frequency_penalty" not in params
    assert "presence_penalty" not in params


def test_build_call_params_includes_reasoning_effort_for_gpt5_mini():
    params = build_call_params("gpt-5-mini", max_completion_tokens=1000)
    assert params["reasoning_effort"] == "medium"


def test_build_call_params_no_reasoning_effort_for_gpt4o_mini():
    params = build_call_params("gpt-4o-mini", max_completion_tokens=1000)
    assert "reasoning_effort" not in params


def test_build_call_params_clamps_to_max_output_tokens_for_gpt4o_mini():
    params = build_call_params("gpt-4o-mini", max_completion_tokens=32000)
    assert params["max_completion_tokens"] == 16384


def test_build_call_params_does_not_clamp_for_gpt5_mini():
    params = build_call_params("gpt-5-mini", max_completion_tokens=32000)
    assert params["max_completion_tokens"] == 32000


def test_all_supported_models_have_required_fields():
    required = {
        "supports_temperature",
        "supports_sampling_penalties",
        "model_context_length",
        "max_output_tokens",
        "max_inline_tokens",
    }
    for model_name, config in MODEL_CONFIG.items():
        missing = required - config.keys()
        assert not missing, f"{model_name} missing fields: {missing}"


def test_build_call_params_lifts_tiny_budget_to_floor_for_reasoning_model():
    # Mirrors the bug: a small max_completion_tokens (here 120) on a reasoning
    # model would let internal reasoning exhaust the budget before any visible
    # output is emitted. The floor lifts it to a safe minimum.
    from srt_translator.core.constants import REASONING_MODEL_COMPLETION_TOKEN_FLOOR

    params = build_call_params("gpt-5-mini", max_completion_tokens=120)
    assert params["max_completion_tokens"] >= REASONING_MODEL_COMPLETION_TOKEN_FLOOR


def test_build_call_params_does_not_lift_already_sufficient_budget_for_reasoning_model():
    from srt_translator.core.constants import REASONING_MODEL_COMPLETION_TOKEN_FLOOR

    big = REASONING_MODEL_COMPLETION_TOKEN_FLOOR * 4
    params = build_call_params("gpt-5-mini", max_completion_tokens=big)
    assert params["max_completion_tokens"] == big


def test_build_call_params_floor_does_not_apply_to_non_reasoning_model():
    # Standard models do not consume budget on hidden reasoning, so a tiny
    # caller-supplied value must be respected.
    params = build_call_params("gpt-4o-mini", max_completion_tokens=120)
    assert params["max_completion_tokens"] == 120


def test_build_call_params_floor_clamps_to_max_output_tokens():
    # The floor must never exceed the model's published max_output_tokens.
    # If a reasoning model ever has a max_output_tokens lower than the floor,
    # build_call_params should still respect the API ceiling.
    cfg = MODEL_CONFIG["gpt-5-mini"]
    params = build_call_params("gpt-5-mini", max_completion_tokens=1)
    assert params["max_completion_tokens"] <= cfg["max_output_tokens"]
