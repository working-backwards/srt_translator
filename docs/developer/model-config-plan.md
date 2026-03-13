# Model Configuration Architecture Plan

## Status: Plan complete — ready to implement
**Branch:** `feature/config-defaults-advanced-settings`
**Plan file:** `docs/developer/model-config-plan.md` (untracked, not yet committed)
**No code changes have been made yet.** All changes described below are pending.

---

## Why This Change Is Needed

### The generation / translation model split

The app uses two distinct OpenAI model roles with fundamentally different call profiles:

**Generation model** (DNT extraction + termbase generation, called **once per course**):

The model ingests as much of the course transcript as possible — up to the model's
`max_inline_tokens` cap — to produce a high-quality, coverage-rich termbase and DNT list.
The bottleneck is **input context**, not output length. With `gpt-4o-mini` (128 K context),
the transcript was capped at 12,500 tokens (~10,000 words, roughly 1.3 hours of course
content at a typical speaking pace). Switching to `gpt-5-mini` (400 K context) raises the
cap to 250,000 tokens (~200,000 words, roughly 27 hours), which covers virtually any
course in full. The cap is an application policy stored per-model in `model_config.json`
as `max_inline_tokens`; it does not equal the full context window, as headroom is reserved
for the system prompt, generation instructions, and output tokens.

**Translation model** (called **once per 5–8 cues**, many times per course):

Each call receives only 5–8 subtitle cues, the DNT list (~30 phrases), and the matching
subset of termbase entries — a small, bounded prompt. Context window size is irrelevant.
What matters is **cost and latency**, since this call runs dozens to hundreds of times per
course. `gpt-4o-mini` is the right fit.

### Problems the current code has

| Problem | Impact |
|---|---|
| `model_config.json` missing `max_output_tokens` | No guard against requesting more tokens than the model allows |
| `model_config.json` missing `supports_sampling_penalties` | `frequency_penalty` and `presence_penalty` sent unconditionally in `translator.py` strict-retry path, even for gpt-5-mini which rejects both |
| `model_config.json` missing `reasoning_effort` | gpt-5-mini's reasoning depth is uncontrolled; defaults to model's internal choice |
| Unsupported params guarded by scattered `if` checks at 11 call sites | Every new model capability change requires finding and updating all sites independently |
| `MAX_INLINE_TOKENS = 12500` is a single global constant | Changing `DEFAULT_GENERATION_MODEL` does not automatically scale the transcript budget |
| `SUPPORTED_MODELS` dict in `ai_config_section.py` duplicates `model_config.json` | Two places to update whenever a model is added |
| `settings_manager.py` hardcodes `"gpt-4o-mini"` as fallback strings | Changing `DEFAULT_GENERATION_MODEL` in `constants.py` silently does not propagate |
| `DEFAULT_GENERATION_MODEL` / `DEFAULT_TRANSLATION_MODEL` are swapped | Generation should use gpt-5-mini (large context); translation should use gpt-4o-mini (cost-efficient) |

---

## What Belongs Where

### `model_config.json` — model-intrinsic capabilities (what the OpenAI API enforces)

These are immutable facts about the model as published by OpenAI:

| Field | Meaning |
|---|---|
| `supports_temperature` | Whether the model accepts a `temperature` parameter |
| `supports_sampling_penalties` | Whether the model accepts `frequency_penalty` and `presence_penalty` |
| `model_context_length` | Max **input** tokens (context window ceiling from OpenAI) |
| `max_output_tokens` | Max **completion** tokens the API will return (OpenAI ceiling) |
| `max_inline_tokens` | Max transcript tokens to send inline for generation (app policy derived from context size) |
| `reasoning_effort` | Reasoning effort hint for reasoning models (`"low"` / `"medium"` / `"high"`); absent for standard models |

`max_inline_tokens` is technically an application policy, but it is *directly derived from
and coupled to* `model_context_length`. A model with 400 K context should get a different
cap than one with 128 K. Storing it per-model means changing `DEFAULT_GENERATION_MODEL`
automatically picks the right transcript budget with no other code changes.

`reasoning_effort` is only present for reasoning models (currently gpt-5-mini). Its
absence in a model entry means the parameter is not sent to the API.

### `constants.py` — application-level task budgets (what the app asks for)

These stay in `constants.py` because they are tunable engineering choices about task
complexity, not limits imposed by OpenAI:

| Constant | Value | Notes |
|---|---|---|
| `MAX_COMPLETION_TOKENS_DNT` | 32,000 (was 5,000) | Completion budget for DNT extraction; must cover reasoning tokens + visible output for gpt-5-mini |
| `MAX_COMPLETION_TOKENS_TERMBASE` | 48,000 (was 5,000) | Completion budget for termbase generation; deep reasoning over large transcript plus structured JSON output |
| `MAX_COMPLETION_TOKENS_VALIDATE` | 16,000 | Completion budget for termbase validation; checking existing work needs less reasoning |
| `MAX_COMPLETION_TOKENS_DIAGNOSTIC` | 160 | Output budget for diagnostic probes |
| `MAX_COMPLETION_TOKENS_FALLBACK` | 256 | Output budget for single-string fallback calls |
| `MAX_COMPLETION_TOKENS_TRANSLATION_BATCH` | 4,096 | **Required.** Token budget for main translation batch JSON and placeholder-fixer JSON. Do *not* use `MAX_COMPLETION_TOKENS` (120) for these paths or responses will be truncated and subtitles will be empty. |
| `DEFAULT_GENERATION_MODEL` | `"gpt-5-mini"` (was `"gpt-4o-mini"`) | Swapped |
| `DEFAULT_TRANSLATION_MODEL` | `"gpt-4o-mini"` (was `"gpt-5-mini"`) | Swapped |
| `DEFAULT_TEMPERATURE` | 0.75 | Unchanged |
| `DEFAULT_TONE` | `"neutral"` | Already exists; import in settings_manager |
| `AI_CONFIG_MAX_AGE_DAYS` | 30 (new) | Remove magic number from settings_manager |
| ~~`MAX_INLINE_TOKENS`~~ | *Deleted* | Replaced by per-model value in model_config.json |

---

## Verified OpenAI Model Specs

All values sourced directly from the OpenAI developer docs:

| Model | Context Window | Max Output Tokens | Source |
|---|---|---|---|
| gpt-4o-mini | 128,000 | 16,384 | [OpenAI docs](https://developers.openai.com/api/docs/models/gpt-4o-mini) |
| gpt-4o | 128,000 | 16,384 | [OpenAI docs](https://developers.openai.com/api/docs/models/gpt-4o) |
| gpt-4.1-mini | 1,047,576 | 32,768 | [OpenAI docs](https://developers.openai.com/api/docs/models/gpt-4.1-mini) |
| gpt-5-mini | 400,000 | 128,000 | [OpenAI docs](https://developers.openai.com/api/docs/models/gpt-5-mini) |

**`max_inline_tokens` rationale** (prompt overhead ~5 K, output request ~12 K for standard
models):

| Model | Available for transcript | `max_inline_tokens` |
|---|---|---|
| gpt-4o-mini | 111,000 | 80,000 (72 % of available) |
| gpt-4o | 111,000 | 80,000 (72 % of available) |
| gpt-4.1-mini | ~1,030,000 | 500,000 (49 % of available) |
| gpt-5-mini | 383,000 | 250,000 (65 % of available) |

> **Reasoning token note (gpt-5-mini):** `max_completion_tokens` for reasoning models is a
> shared bucket consumed by both internal reasoning tokens (chain-of-thought, not returned)
> and visible output tokens. Reasoning tokens also occupy context window space *during*
> generation. The 150,000-token safety margin in `max_inline_tokens` for gpt-5-mini
> (250,000 vs. the 400,000 context window) accounts for prompt overhead, reasoning weight,
> and the "lost in the middle" degradation that can occur when approaching the context
> limit. If `max_completion_tokens` is set too low, the model may exhaust its budget on
> internal reasoning and return a truncated or empty response — see the token budget
> section below.

---

## File-by-File Changes

### 1. `srt_translator/config/model_config.json`

Add `supports_sampling_penalties`, `max_output_tokens`, `max_inline_tokens`, and
`reasoning_effort` (gpt-5-mini only):

```json
{
  "gpt-4o-mini": {
    "supports_temperature": true,
    "supports_sampling_penalties": true,
    "model_context_length": 128000,
    "max_output_tokens": 16384,
    "max_inline_tokens": 80000
  },
  "gpt-4o": {
    "supports_temperature": true,
    "supports_sampling_penalties": true,
    "model_context_length": 128000,
    "max_output_tokens": 16384,
    "max_inline_tokens": 80000
  },
  "gpt-4.1-mini": {
    "supports_temperature": true,
    "supports_sampling_penalties": true,
    "model_context_length": 1047576,
    "max_output_tokens": 32768,
    "max_inline_tokens": 500000
  },
  "gpt-5-mini": {
    "supports_temperature": false,
    "supports_sampling_penalties": false,
    "reasoning_effort": "medium",
    "model_context_length": 400000,
    "max_output_tokens": 128000,
    "max_inline_tokens": 250000
  }
}
```

### 2. `srt_translator/config/model_config_loader.py`

Replace the current minimal file with typed helpers plus a `build_call_params()` function
that centralizes all model-capability filtering. This eliminates the 11 scattered
`if self.model_config.get(...)` guards across `ai_config.py` and `translator.py`.

```python
import json
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / "model_config.json"

with open(CONFIG_FILE) as f:
    MODEL_CONFIG = json.load(f)


def get_model_config(model_name: str) -> dict:
    return MODEL_CONFIG.get(model_name, {})


def get_max_inline_tokens(model_name: str) -> int:
    """Max transcript tokens to send inline; falls back to the old constant value."""
    return get_model_config(model_name).get("max_inline_tokens", 12500)


def get_max_output_tokens(model_name: str) -> int:
    """API ceiling for completion tokens for the given model."""
    return get_model_config(model_name).get("max_output_tokens", 16384)


def build_call_params(
    model_name: str,
    *,
    max_completion_tokens: int,
    temperature: float | None = None,
    frequency_penalty: float | None = None,
    presence_penalty: float | None = None,
) -> dict:
    """Build the kwargs dict for client.chat.completions.create(),
    omitting parameters unsupported by the given model and injecting
    model-specific parameters (e.g. reasoning_effort for gpt-5-mini).

    max_completion_tokens is automatically clamped to the model's
    max_output_tokens ceiling so that callers can use large constants
    (sized for reasoning models) without causing API errors on standard
    models whose output ceiling is lower.

    Callers may freely add extra keys (e.g. 'stop', 'response_format')
    to the returned dict after the call.
    """
    cfg = get_model_config(model_name)
    safe_limit = min(max_completion_tokens, cfg.get("max_output_tokens", 16384))
    params: dict = {"max_completion_tokens": safe_limit}

    if cfg.get("supports_temperature", True) and temperature is not None:
        params["temperature"] = temperature

    if cfg.get("supports_sampling_penalties", True):
        if frequency_penalty is not None:
            params["frequency_penalty"] = frequency_penalty
        if presence_penalty is not None:
            params["presence_penalty"] = presence_penalty

    reasoning_effort = cfg.get("reasoning_effort")
    if reasoning_effort is not None:
        params["reasoning_effort"] = reasoning_effort

    return params
```

**Usage pattern at every call site:**

```python
kwargs = build_call_params(
    self.generation_model_name,
    max_completion_tokens=MAX_COMPLETION_TOKENS_DNT,
    temperature=self.temperature,
)
# Add any call-specific non-capability params:
# kwargs["stop"] = ["]}"]
# kwargs["response_format"] = {"type": "json_object"}
response = self.client.chat.completions.create(
    model=self.generation_model_name,
    messages=messages,
    **kwargs,
)
```

### 3. `srt_translator/core/constants.py`

- Swap `DEFAULT_GENERATION_MODEL` ↔ `DEFAULT_TRANSLATION_MODEL`
- Raise `MAX_COMPLETION_TOKENS_DNT` to 32,000
- Raise `MAX_COMPLETION_TOKENS_TERMBASE` to 48,000
- Add `AI_CONFIG_MAX_AGE_DAYS = 30`
- Add `MAX_COMPLETION_TOKENS_TRANSLATION_BATCH = 4096` (for main batch and placeholder-fixer; see post-implementation note below).
- **Delete** `MAX_INLINE_TOKENS = 12500`

### 4. `srt_translator/gui/ai_config.py`

Two changes:

**a) Replace `MAX_INLINE_TOKENS` constant with per-model lookup:**

```python
# Remove: from srt_translator.core.constants import MAX_INLINE_TOKENS
from srt_translator.config.model_config_loader import get_max_inline_tokens, build_call_params

# In __init__:
self.MAX_INLINE_TOKENS = get_max_inline_tokens(self.generation_model_name)
```

**b) Replace all 5 scattered capability guards with `build_call_params()`:**

Each of the 5 API call sites (DNT extraction, termbase generation ×2, validation,
language detection) currently has:

```python
params = {"model": ..., "messages": ..., "max_completion_tokens": N}
if self.model_config.get("supports_temperature", True):
    params["temperature"] = self.temperature
```

Becomes:

```python
params = {
    "model": self.generation_model_name,
    "messages": messages,
    **build_call_params(
        self.generation_model_name,
        max_completion_tokens=MAX_COMPLETION_TOKENS_DNT,
        temperature=self.temperature,
    ),
}
```

The `self.model_config` dict lookup and all individual guards are removed.

### 5. `srt_translator/gui/settings_manager.py`

Import and use constants instead of hardcoded strings:

```python
from srt_translator.core.constants import (
    DEFAULT_GENERATION_MODEL,
    DEFAULT_TEMPERATURE,
    DEFAULT_TONE,
    AI_CONFIG_MAX_AGE_DAYS,
)
```

Four methods to fix:

| Method | Hardcoded value | Replace with |
|---|---|---|
| `save_model_name` / `load_model_name` | `"gpt-4o-mini"` (×3) | `DEFAULT_GENERATION_MODEL` |
| `save_tone` / `load_tone` | `"neutral"` (×4) | `DEFAULT_TONE` |
| `save_aggressiveness` / `load_aggressiveness` | `0.75` (×2) | `DEFAULT_TEMPERATURE` (already exists in constants.py — do NOT add a separate `DEFAULT_AGGRESSIVENESS`) |
| `has_recent_ai_config` | `max_age_days: int = 30` | `max_age_days: int = AI_CONFIG_MAX_AGE_DAYS` |

> **Note on "aggressiveness" vs temperature:** The UI labels this control "aggressiveness"
> but it is the OpenAI `temperature` parameter. The stored value from
> `load_aggressiveness()` is passed directly as `temperature` to both the generation and
> translation API calls. `DEFAULT_TEMPERATURE = 0.75` in `constants.py` already covers
> this — no second constant is needed.
>
> **Behavioral consequence of the model swap:** Because `DEFAULT_GENERATION_MODEL` is now
> `gpt-5-mini` (which does not support `temperature`), the aggressiveness slider will be
> **hidden by default** for new users. The `supports_temperature` field in
> `model_config.json` drives this visibility via `agg_row_frame.setVisible(...)` in
> `ai_config_section.py`. Users who manually switch the generation model to `gpt-4o-mini`
> or `gpt-4.1-mini` will see the slider restored.

### 6. `srt_translator/gui/ui/ai_config_section.py`

- Remove `SUPPORTED_MODELS` dict; derive from `MODEL_CONFIG` (single source of truth)
- Replace `is_gpt5 = model_name.startswith("gpt-5")` heuristic with model config lookup

```python
from srt_translator.config.model_config_loader import MODEL_CONFIG, get_model_config

SUPPORTED_MODELS = list(MODEL_CONFIG.keys())

# In update_temperature_visibility:
cfg = get_model_config(model_name or "")
self.agg_row_frame.setVisible(cfg.get("supports_temperature", True))
```

Validation message in `validate_advanced_settings` should build the supported model list
dynamically from `SUPPORTED_MODELS` instead of hardcoding model names.

### 7. `srt_translator/core/translator/translator.py`

Replace all 5 scattered capability guards with `build_call_params()`.

The strict-retry path currently has:

```python
base = {
    "frequency_penalty": STRICT_RETRY_FREQUENCY_PENALTY,  # unguarded
    "presence_penalty": 0.0,                               # unguarded
    "max_completion_tokens": max_completion_tokens,
    "stop": ["]}"],
}
if self.model_config.get("supports_temperature", True):
    base["temperature"] = self.temperature
```

Becomes:

```python
base = build_call_params(
    self.translation_model_name,
    max_completion_tokens=max_completion_tokens,
    temperature=self.temperature,
    frequency_penalty=STRICT_RETRY_FREQUENCY_PENALTY,
    presence_penalty=0.0,
)
base["stop"] = ["]}"]   # not a capability flag — always include
```

The other 4 translation call sites follow the same pattern (omitting
`frequency_penalty`/`presence_penalty` where not applicable to the call type).

**Critical:** For the *main* batch path (non-strict) and for the placeholder-fixer path,
use `MAX_COMPLETION_TOKENS_TRANSLATION_BATCH` (4096), **not** `MAX_COMPLETION_TOKENS` (120).
Using 120 truncates the JSON response and produces empty subtitles.

### 8. `srt_translator/core/services/language_detection.py`

Replace the single capability guard with `build_call_params()` (1 call site).

---

## New Tests Required

### A. `tests/test_model_config.py` (new file)

```python
def test_get_max_inline_tokens_gpt5_mini():
    assert get_max_inline_tokens("gpt-5-mini") == 250000

def test_get_max_inline_tokens_fallback_for_unknown_model():
    assert get_max_inline_tokens("unknown-model") == 12500

def test_build_call_params_omits_temperature_for_gpt5_mini():
    params = build_call_params("gpt-5-mini", max_completion_tokens=1000,
                               temperature=0.75)
    assert "temperature" not in params
    assert params["max_completion_tokens"] == 1000

def test_build_call_params_includes_temperature_for_gpt4o_mini():
    params = build_call_params("gpt-4o-mini", max_completion_tokens=1000,
                               temperature=0.75)
    assert params["temperature"] == 0.75

def test_build_call_params_omits_penalties_for_gpt5_mini():
    params = build_call_params("gpt-5-mini", max_completion_tokens=1000,
                               frequency_penalty=0.6, presence_penalty=0.0)
    assert "frequency_penalty" not in params
    assert "presence_penalty" not in params

def test_build_call_params_includes_reasoning_effort_for_gpt5_mini():
    params = build_call_params("gpt-5-mini", max_completion_tokens=1000)
    assert params["reasoning_effort"] == "medium"

def test_build_call_params_no_reasoning_effort_for_gpt4o_mini():
    params = build_call_params("gpt-4o-mini", max_completion_tokens=1000)
    assert "reasoning_effort" not in params

def test_build_call_params_clamps_to_max_output_tokens_for_gpt4o_mini():
    # MAX_COMPLETION_TOKENS_DNT=32000 exceeds gpt-4o-mini's 16384 ceiling
    params = build_call_params("gpt-4o-mini", max_completion_tokens=32000)
    assert params["max_completion_tokens"] == 16384

def test_build_call_params_does_not_clamp_for_gpt5_mini():
    # 32000 is well within gpt-5-mini's 128000 ceiling
    params = build_call_params("gpt-5-mini", max_completion_tokens=32000)
    assert params["max_completion_tokens"] == 32000

def test_all_supported_models_have_required_fields():
    required = {"supports_temperature", "supports_sampling_penalties",
                "model_context_length", "max_output_tokens", "max_inline_tokens"}
    for model_name, config in MODEL_CONFIG.items():
        missing = required - config.keys()
        assert not missing, f"{model_name} missing fields: {missing}"
```

### B. `tests/test_ai_config_basic.py` (add to existing)

```python
def test_load_model_name_default_uses_constant():
    sm = SettingsManager(language_config)
    sm.settings.remove("model_name")
    assert sm.load_model_name() == DEFAULT_GENERATION_MODEL
```

### C. `tests/test_orchestrator_pipeline.py` or new file (add)

Verify that `build_call_params("gpt-5-mini", ...)` omits `frequency_penalty` and
`presence_penalty` and includes `reasoning_effort`, confirming the strict-retry path
would be safe if gpt-5-mini were used as the translation model.

---

## Order of Execution

1. `model_config.json` — foundation all runtime lookups depend on
2. `model_config_loader.py` — add `build_call_params()` and typed helpers
3. `constants.py` — swap defaults, raise budgets, add `AI_CONFIG_MAX_AGE_DAYS`, delete `MAX_INLINE_TOKENS`
4. `gui/ai_config.py` — use `get_max_inline_tokens()` + `build_call_params()` at all 5 call sites
5. `core/translator/translator.py` — replace 5 scattered guards with `build_call_params()`
6. `core/services/language_detection.py` — replace 1 guard with `build_call_params()`
7. `gui/settings_manager.py` — import and use constants
8. `gui/ui/ai_config_section.py` — remove `SUPPORTED_MODELS` dict, fix heuristic
9. Add tests (A, B, C above)

---

## Architecture / Isolation Check

- `TranslationConfig` is untouched structurally — only its `DEFAULT_TRANSLATION_MODEL`
  default value changes.
- `model_config_loader.py` lives in `srt_translator/config/`, which `translator.py`,
  `ai_config.py`, `language_detection.py`, and `main_window.py` already import.
  No new cross-layer dependency is introduced.
- `build_call_params()` is a pure function with no side effects — safe to call from both
  core and GUI layers.
- `MAX_INLINE_TOKENS` removal only affects `ai_config.py` (GUI generation layer). The core
  translator never used it.
- `settings_manager.py` and `ai_config_section.py` are GUI-only — zero risk to core.
- `test_import_barriers.py` continues to pass.

### Post-implementation fix: translation batch token cap

After wiring `build_call_params()` into the translator, the main batch path and the
placeholder-fixer path were incorrectly given `max_completion_tokens=MAX_COMPLETION_TOKENS`
(120). The main path had previously *not* set `max_completion_tokens`, so the API used
its default. With 120, the JSON for 5–8 subtitles was truncated, parsing failed, and
output was empty subtitles. **Fix:** Add `MAX_COMPLETION_TOKENS_TRANSLATION_BATCH = 4096`
in `constants.py` and use it in `translator.py` for (1) the non-strict batch path and
(2) the placeholder-fixer path. Leave `MAX_COMPLETION_TOKENS` (120) only for paths that
truly need a small cap (e.g. diagnostic/fallback).

---

## CLI Endpoint: Model Configuration & Documentation (Follow-Up Plan)

This section captures the **CLI-only** configuration and documentation changes that
build on the model config work above. These changes do **not** affect the GUI entry
point or the core translator; they only change how the CLI reads models from `.env`
and how that behavior is documented.

### CLI Audience & Scope

- CLI (`srtx-cli`) is for **developers who have cloned the repo** and can edit code.
- GUI (`srtx`) is for **creators** and remains opinionated:
  - GUI model selection stays in the GUI layer.
  - GUI users do **not** tweak models via `.env`.
- The goal is to give CLI users an explicit way to pick:
  - **Configuration model** (AI Config: DNT + termbase), and
  - **Translation model** (subtitle translation),
  without introducing multiple conflicting sources of truth or extra fallbacks.

### Current CLI Behavior (Before This Follow-Up)

- `.env` is loaded by `cli/config_loader.collect_cli_raw()` via `dotenv_values`.
- Relevant keys today:
  - `OPENAI_API_KEY` → required API key (OS env wins).
  - `OPENAI_MODEL` → used as `openai_model` and then normalized into
    `translation_model_name` in `TranslationConfig.from_raw()`.
  - `TARGET_LANGUAGES`, `INPUT_DIRECTORY`, `OUTPUT_DIRECTORY`, `DNT_TERMS`,
    `TERMBASE_PATH`, `AGGRESSIVENESS`, `LOG_MODE`, `TONE` → standard CLI knobs.
- `cli/app.py` also reads `TRANSLATION_MODEL_NAME` from **OS env** as a secondary,
  less discoverable override:

```python
env_translation_model = os.getenv("TRANSLATION_MODEL_NAME")
if env_translation_model:
    raw_config["translation_model_name"] = env_translation_model
```

- `TranslationConfig` has **only one model field**:
  - `translation_model_name: str = DEFAULT_TRANSLATION_MODEL`
  - There is **no separate field** for a configuration/generation model; that choice
    is made in the GUI pipeline and via `DEFAULT_GENERATION_MODEL` in `constants.py`.

### Design Decision: Keep CLI Simple and Explicit

Given the above and the project goals:

- **No new fallback layers**:
  - Avoid stacking more env vars or hidden overrides.
  - Prefer a single obvious source for each CLI knob.
- **CLI only exposes the translation model as a runtime knob**:
  - Configuration/generation model remains a **code-level default**:
    - `DEFAULT_GENERATION_MODEL` in `core/constants.py`, with per-model capabilities
      and budgets in `model_config.json`.
  - If a developer wants to experiment with a different generation model, they edit
    `DEFAULT_GENERATION_MODEL` and `model_config.json` in the repo and run tests.

### CLI Code Changes (Minimal, Explicit)

1. **Rename the CLI translation-model env var**

   - In `examples/env_example` and `cli/config_loader.collect_cli_raw()`:
     - **Rename** the translation model key from `OPENAI_MODEL` to
       `OPENAI_TRANSLATION_MODEL` to make its role explicit.
     - `collect_cli_raw()` should read:

```python
translation_model = env_file.get("OPENAI_TRANSLATION_MODEL")
```

     - And include it in the raw config as a dedicated field, e.g.:

```python
return {
    ...
    "translation_model_name": translation_model,
    ...
}
```

   - In `cli/app.py`:
     - **Remove** the `TRANSLATION_MODEL_NAME` OS-env override entirely to avoid
       multiple, conflicting paths for the same concept.
     - Rely solely on the `translation_model_name` coming from `collect_cli_raw()`
       (which in turn comes from `.env: OPENAI_TRANSLATION_MODEL`) or the default.

   - In `TranslationConfig.from_raw()`:

```python
translation_model_name = (
    raw.get("translation_model_name")
    or raw.get("model_name")
    or DEFAULT_TRANSLATION_MODEL
)
```

   - This keeps a single, explicit env entry for CLI (`OPENAI_TRANSLATION_MODEL`)
     and a single default from code (`DEFAULT_TRANSLATION_MODEL`), with no extra
     fallback env knobs.

2. **Do not add runtime overrides for the generation model in CLI**

   - The generation/configuration model is governed by:
     - `DEFAULT_GENERATION_MODEL` in `core/constants.py`, and
     - Per-model capabilities in `model_config.json`.
   - The CLI **does not** need `OPENAI_CONFIGURATION_MODEL` / `generation_model_name`
     at runtime; changing the generation model is a code/config change, not a CLI knob.

### `.env` Example Updates (CLI-Facing Only)

In `examples/env_example`, keep CLI configuration focused and explicit:

- Replace the comment and key around the translation model with:

```bash
# OpenAI model used by the CLI for subtitle translation.
# If unset, the CLI uses DEFAULT_TRANSLATION_MODEL from srt_translator/core/constants.py.
OPENAI_TRANSLATION_MODEL=gpt-4o-mini
```

- Do **not** introduce `OPENAI_CONFIGURATION_MODEL` (or similar) for the CLI. The
  configuration/generation model remains a code-level choice via
  `DEFAULT_GENERATION_MODEL` and `model_config.json`, and the CLI does not need
  to reference it.

### Documentation Changes for CLI Endpoint

- **Developer docs (`docs/developer/setup.md`)**:
  - Add a short "CLI Model Configuration" subsection:
    - Explain that:
      - The **generation model** (AI Config: DNT + termbase) is controlled by
        `DEFAULT_GENERATION_MODEL` and `model_config.json` (code-level change).
      - The **translation model** for CLI runs is controlled by:
        - `.env: OPENAI_MODEL`, or
        - The code default `DEFAULT_TRANSLATION_MODEL` if `OPENAI_MODEL` is not set.
  - Make explicit that **CLI users are expected to be developers** and can change the
    generation model by editing the repo config directly.

- **User guide (CLI usage page, when added)**:
  - For CLI commands, document:
    - `OPENAI_API_KEY` (required).
    - `OPENAI_MODEL` (optional translation model; default from code).
  - Do **not** mention:
    - GUI settings (sliders, advanced settings).
    - Runtime generation-model overrides.

### Impact on GUI and Core

- **GUI**:
  - Unaffected. GUI continues to:
    - Use `DEFAULT_GENERATION_MODEL` for AI config generation by default.
    - Let advanced users switch the generation model via GUI controls that read
      `model_config.json` and `MODEL_CONFIG`.
  - GUI does **not** read CLI `.env` variables for models.

- **Core translator**:
  - Unaffected structurally:
    - `TranslationConfig` still has a **single** `translation_model_name` field.
    - No new fields are added.
  - All capability handling still flows through:
    - `model_config.json` + `model_config_loader.build_call_params()`.

### Status of `TranslationConfig`

- `TranslationConfig` **already** supports:
  - A single `translation_model_name` defaulted from `DEFAULT_TRANSLATION_MODEL`.
  - No separate field for a "configuration/generation" model.
- The generation model choice is made:
  - In GUI code (`ai_config.py`) using `DEFAULT_GENERATION_MODEL` and
    `model_config.json`, **not** in `TranslationConfig`.
- This plan **does not change** `TranslationConfig`'s structure; it only clarifies
  and tightens how the CLI populates `translation_model_name` and how that is
  documented for developers.
