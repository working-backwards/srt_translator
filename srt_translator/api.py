from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from srt_translator.core.config.models import TranslationConfig


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
    # NEW: pass-through from GUI/CLI detection (Batch-level, optional)
    source_language: Optional[Dict[str, object]] = None

    def _build_core_config(self) -> TranslationConfig:
        """Build the core TranslationConfig from this facade configuration."""
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
            # NEW: forward to core model
            "source_language": self._config.source_language,
        }
        core_cfg = TranslationConfig.from_raw(
            raw,
            mode=(self._config.mode if self._config.mode in ("GUI", "CLI") else "GUI"),
        )
        return core_cfg

    def run(self) -> Dict[str, Any]:
        """Run the translation with the current configuration and return summary."""
        core_cfg = self._build_core_config()
        from srt_translator.core.main import translate_srt_files

        if not self.files:
            raise ValueError("No files specified for translation")

        return translate_srt_files(
            file_paths=[str(f) for f in self.files],
            config=core_cfg,
        )

    @property
    def _config(self) -> "TranslationConfiguration":
        return self


class Translator:
    """Facade class for running translations from GUI/CLI."""

    def __init__(self, config: TranslationConfiguration):
        self.config = config

    def run(self) -> Dict[str, Any]:
        """Run the translation and return results."""
        try:
            # Run the translation and get summary
            summary = self.config.run()

            # Return results in format expected by GUI
            return {
                "status": "success",
                "message": "Translation completed successfully",
                "completed": summary["successes"],
                "failed": summary["errors"],
                "total_files": summary["total_files"],
                "output_directory": str(
                    self.config.output_dir
                ),  # Include actual output directory
            }
        except Exception as e:
            logging.error(f"Translation failed: {e}")
            raise
