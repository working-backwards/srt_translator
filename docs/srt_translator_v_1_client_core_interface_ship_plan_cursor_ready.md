# SRT Translator v1 — Public API & Ship Plan (final)

**Audience:** you (maintainer), future contributors

**v1 goals**

- One batch at a time (single‑use `Translator` per run)
- Clients (GUI/CLI) **collect config**, core **translates & fixes**
- Progress is **logging‑only** (CLI → stdout/file, GUI → `QueueHandler/QueueListener`)
- **No hung detection** in v1
- Keep current CLI workflow (`INPUT_DIRECTORY` from `.env` → enumerate files)

---

## 1) Public API façade (what GUI & CLI import)

Expose a tiny, stable surface so clients never touch `srt_translator.core.*` internals.

**New file: **``

```python
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Dict, Any
import logging

from srt_translator.core.config.models import TranslationConfig
from srt_translator.core.main import translate_srt_files  # (file_paths, config)

@dataclass(frozen=True)
class TranslationConfiguration:
    # v1: explicit files only; no directory input
    files: Iterable[Path] | None = None
    output_dir: Path = Path("translated_srt_files")
    target_languages: Dict[str, str] | None = None
    # DNT may be a GUI list or the CLI's bracketed CSV string from .env
    dnt_terms: list[str] | str | None = None
    # Termbase is typically a dict loaded from TERMBASE_PATH; core also accepts JSON string
    termbase: Dict[str, Dict[str, str]] | str | None = None
    openai_model: str = "gpt-4o-mini"
    batch_size: int = 5
    aggressiveness: float = 0.75
    log_mode: str = "Standard"
    api_key: Optional[str] = None
    mode: str = "GUI"  # or "CLI"

class Translator:
    """One-batch-per-instance translator façade."""
    def __init__(self, config: TranslationConfiguration):
        self._config = config
        self._ran = False
        self._log = logging.getLogger("srt_translator")

    def run(self) -> Dict[str, Any]:
        if self._ran:
            raise RuntimeError("Translator.run() is single-use; create a new instance for another batch")
        self._ran = True
        if not self._config.files:
            raise ValueError("TranslationConfiguration.files is required in v1")

        raw: Dict[str, Any] = {
            "api_key": self._config.api_key,
            "output_directory": str(self._config.output_dir),
            "target_languages": self._config.target_languages,
            "dnt_terms": self._config.dnt_terms,
            "termbase": self._config.termbase or {},
            "openai_model": self._config.openai_model,
            "batch_size": self._config.batch_size,
            "aggressiveness": self._config.aggressiveness,
            "log_mode": self._config.log_mode,
        }
        core_cfg = TranslationConfig.from_raw(raw, mode=(self._config.mode if self._config.mode in ("GUI","CLI") else "GUI"))
        files = [str(p) for p in self._config.files]
        return translate_srt_files(file_paths=files, config=core_cfg)
```

**Type expectations & parsing (v1)**\*

- Pass native **int/float** for `batch_size`/`aggressiveness`.
- `dnt_terms`: GUI list **or** `.env` bracketed CSV string (e.g., `[AWS,S3,Lambda]`). Core normalizes both.
- `target_languages`: dict **or** JSON string. Core normalizes.
- `termbase`: dict **or** JSON string (CLI loads from `TERMBASE_PATH`). Core normalizes.

---

## 2) GUI: stream logs via `QueueHandler/QueueListener`

- Add `srt_translator/gui/logging_bridge.py` (NonBlockingQueueHandler, CallbackHandler, `make_gui_logging_pipeline`).
- In `gui/workers/translation_worker.py`, start bridge at the beginning of `run()` and stop in `finally:`; append log lines to the UI via a Qt signal.
- No heartbeat/idle logic in v1.

---

## 3) CLI: keep your current `.env`-driven workflow

- No new flags. CLI reads `.env` (with **OS env taking precedence for **``), enumerates `INPUT_DIRECTORY/*.srt` → `files=[Path(...), ...]`, builds the façade config, and calls `Translator(cfg).run()`.

**Example **``

```
TARGET_LANGUAGES={"Spanish": "es",  "Chinese (Simplified)": "zh-Hans", "English": "en"}
DNT_TERMS=["Amazon", "Jeff Bezos", "Colin Bryar", "Bill Carr", "Prime Video", "Amazon Music", "OP1", "OP2", "FPA", "ROI", "CS reps", "iOS", "Fire TV", "Roku", "Sony", "LG", "Q4", "PRFAQ", "RO"]
INPUT_DIRECTORY=original_captions
OUTPUT_DIRECTORY=translated_srt_files
OPENAI_MODEL=gpt-4o-mini
AGGRESSIVENESS=0.75
BATCH_SIZE=5
TERMBASE_PATH=termbase.json
```

---

## 4) What we’re **not** doing in v1

- No heartbeat logs / “hung” UI state
- No message bus / custom DTOs
- No concurrency (one batch per client)
- No new CLI flags (source dir remains in `.env`)

---

## 5) Step-by-step to ship

**Commit A — GUI logging bridge**

1. Add `srt_translator/gui/logging_bridge.py`.
2. In `translation_worker.py`, wrap the run with `start_logging_bridge()` / `stop_logging_bridge()` and append log lines to the text box.

**Commit A.5 — Fix CLI config loader to read INPUT_DIRECTORY**

1. In `cli/config_loader.py`, add `INPUT_DIRECTORY` to the returned config:
   ```python
   return {
       # ... existing fields ...
       "input_directory": env_file.get("INPUT_DIRECTORY", "original_captions"),  # ← Add this
   }
   ```

2. In `cli/app.py`, replace hardcoded source directory:
   ```python
   # Before: input_dir = os.getenv("INPUT_DIRECTORY", "original_captions")
   # After: 
   input_dir = raw_config.get("input_directory", "original_captions")
   ```

**Commit B — Public façade & decouple GUI from **``

1. Add `srt_translator/api.py` (above).
2. Replace GUI imports of `srt_translator.core.*` with `from srt_translator.api import TranslationConfiguration, Translator`.
3. Build `TranslationConfiguration(files=[...], ...)`; call `Translator(cfg).run()`.

**Commit C — CLI uses the façade (no behavior change)**

1. In `cli/app.py`, replace `core.*` imports with `from srt_translator.api import TranslationConfiguration, Translator`.
2. Enumerate `INPUT_DIRECTORY` → `files=[...]`, build the façade config, call `Translator(cfg).run()`.

**Commit F — Core always runs the fixer; remove GUI fixer references**

1. **srt_translator/core/main.py** — run fixer after translation
2. **srt_translator/gui/workers/translation_worker.py** — remove GUI fixer import & call

*We intentionally keep the core entry as **`translate_srt_files(file_paths, config)`** to preserve separation of concerns: ****files = what****, ****config = how****.*

## 6) QA checklist

- GUI and CLI both process a sample set; logs match.
- Cancellation leaves no partial outputs (core should use atomic rename `.partial → .srt`).
- Errors surface in logs; GUI shows the same lines.
- A second run with a new `Translator` instance works cleanly.
- CLI enumerates files from `INPUT_DIRECTORY` and passes them via the façade.

