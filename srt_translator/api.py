from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from srt_translator.core.config.models import TranslationConfig
from srt_translator.core.main import translate_srt_files  # (file_paths, config)


@dataclass(frozen=True)
class TranslationConfiguration:
    files: Iterable[Path] | None = None  # v1: required
    output_dir: Path = Path("translated_srt_files")
    target_languages: Dict[str, str] | None = None
    dnt_terms: list[str] | str | None = None  # GUI list or CLI bracketed CSV string
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
            raise RuntimeError(
                "Translator.run() is single-use; create a new instance for another batch"
            )
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
        core_cfg = TranslationConfig.from_raw(
            raw,
            mode=(self._config.mode if self._config.mode in ("GUI", "CLI") else "GUI"),
        )
        files = [str(p) for p in self._config.files]
        return translate_srt_files(file_paths=files, config=core_cfg)
