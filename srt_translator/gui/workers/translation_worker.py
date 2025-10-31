#!/usr/bin/env python3
"""
Translation Worker for the SRT Translator GUI.
"""

import io
import logging
import threading
import time
import uuid
from collections import deque
from contextlib import redirect_stdout
from pathlib import Path

from PySide6.QtCore import QObject
from PySide6.QtCore import Signal as pyqtSignal

from srt_translator.config import load_language_catalog
from srt_translator.core.config.models import TranslationConfig

# Evaluation imports (config-gated)
from srt_translator.eval.runner import run_batch_evaluation

# (Fixer now runs in core automatically)
# Stream core logs into the GUI box safely
from srt_translator.gui.logging_bridge import make_gui_logging_pipeline
from srt_translator.gui.settings_manager import SettingsManager


def _load_language_policies(selected_codes: list[str]) -> dict:
    """Return packaged language catalog (read-only)."""
    raw = load_language_catalog()
    if "languages" not in raw:
        raise RuntimeError("languages.json missing 'languages' key")
    defaults = raw.get("policy_defaults", {})
    langs = raw["languages"]
    missing = {}
    for code in selected_codes:
        entry = langs.get(code, {})
        need = []
        for k in (
            "target_batch_size",
            "max_batch_size",
            "allow_placeholder_apostrophe",
        ):
            if k not in entry and k not in defaults:
                need.append(k)
        if "cps_cap" not in entry:
            need.append("cps_cap")
        if need:
            missing[code] = need
    if missing:
        raise RuntimeError(f"languages.json missing required keys for GUI run: {missing}")
    return raw


class TranslationWorker(QObject):
    """Worker object for running translations in background thread"""

    progress_updated = pyqtSignal(str)
    translation_completed = pyqtSignal(dict)
    translation_error = pyqtSignal(str)
    log_message = pyqtSignal(str)
    eval_report_ready = pyqtSignal(dict)  # All report paths

    def __init__(
        self,
        api_key: str,
        selected_files: list[str],
        target_languages: dict[str, str],
        settings_manager: SettingsManager | None = None,
        output_directory: str | None = None,
    ):
        super().__init__()
        self.api_key = api_key
        self.selected_files = selected_files
        self.target_languages = target_languages
        self.settings_manager = settings_manager
        self.output_directory = output_directory
        self.translation_successful = False
        self.log_file = None
        self.batch_dir = None
        self.translation_results = None
        self.session_id = str(uuid.uuid4())[:8]
        self.logger = logging.getLogger(f"translation.{self.session_id}")

        # Signal throttling for GUI responsiveness
        self._emit_lock = threading.Lock()
        self._emit_buf: deque[str] = deque(maxlen=500)  # Bound the buffer
        self._last_emit = 0.0
        self._stop = threading.Event()  # Cooperative stop flag
        # Logging bridge state
        # UNUSED solved: All below 3 variables are not used, can they be removed?

    def request_stop(self):
        """Request cooperative stop of the worker"""
        self._stop.set()

    def is_stopped(self):
        """Check if stop has been requested"""
        return self._stop.is_set()

    # === Logging bridge ===
    def _append_log_to_ui(self, text: str, _levelno: int, _extra: dict) -> None:
        self._throttled_emit(self.progress_updated, text)

    def _start_logging_bridge(self) -> None:
        try:
            self._log_logger, self._log_queue_handler, self._log_listener = make_gui_logging_pipeline(
                logger_name="srt_translator",
                name_prefix_filter=("srt_translator",),
                append_callback=self._append_log_to_ui,
                file_handler=None,  # core already writes logs to file
                queue_size=1000,
                level=logging.INFO,
            )
        except Exception:
            logging.getLogger("srt_translator").exception("Failed to start GUI logging bridge")

    def _stop_logging_bridge(self) -> None:
        try:
            if self._log_listener:
                self._log_listener.stop()
            if self._log_logger and self._log_queue_handler:
                self._log_logger.removeHandler(self._log_queue_handler)
        except Exception:
            logging.getLogger("srt_translator").exception("Failed to stop GUI logging bridge")
        finally:
            self._log_listener = self._log_queue_handler = self._log_logger = None

    def _throttled_emit(self, signal, message):
        """Emit signal with throttling to prevent GUI hammering"""
        batched = None
        with self._emit_lock:
            if not self._emit_buf or self._emit_buf[-1] != message:
                self._emit_buf.append(message)
            now = time.monotonic()
            if now - self._last_emit >= 0.25:  # 4 Hz throttle (250ms)
                batched = "\n".join(self._emit_buf)
                self._emit_buf.clear()
                self._last_emit = now
        if batched is not None:
            signal.emit(batched)

    def run(self):
        """Run the translation process"""
        self._start_logging_bridge()
        try:
            # Debug logging for target languages
            self.logger.info("TranslationWorker received target_languages: %s", self.target_languages)
            self.logger.info("Number of target languages: %s", len(self.target_languages))
            self.logger.info("Target language names: %s", list(self.target_languages.keys()))
            self.logger.info("Target language codes: %s", list(self.target_languages.values()))

            # Emit progress via signal (thread-safe, throttled)
            self._throttled_emit(
                self.progress_updated,
                f"Starting translation to {len(self.target_languages)} languages",
            )

            # Create session-specific logger that doesn't propagate to root
            session_logger = logging.getLogger(f"translation.session.{self.session_id}")
            session_logger.propagate = False

            # Debug logging
            self.logger.info(
                "Starting translation with %s files and %s languages",
                len(self.selected_files),
                len(self.target_languages),
            )
            self._throttled_emit(
                self.progress_updated,
                f"Starting translation with {len(self.selected_files)} files and "
                f"{len(self.target_languages)} languages",
            )

            # Build configuration from GUI settings manager

            try:
                lang_policies = _load_language_policies(list((self.target_languages or {}).values()))
            except Exception as e:
                self.logger.warning("Failed to load language policies, using defaults: %s", e)
                lang_policies = {}

            #  Build config regardless of whether the try/except succeeded or failed
            api_cfg = TranslationConfig(
                files=[Path(p) for p in self.selected_files],
                output_directory=Path(self.output_directory or "translated_srt_files"),
                target_languages=self.target_languages,
                model_name="gpt-4o-mini",
                aggressiveness=0.75,
                log_mode="Standard",
                api_key=self.api_key,
                mode="GUI",
                language_policies=lang_policies,
                dnt_terms=["Thi's"],  # e.g. list of "do-not-translate" terms
                termbase=None
            )

            self.logger.info(
                "Using configuration from settings manager: %s languages",
                len(api_cfg.target_languages),
            )

            if self.settings_manager:
                try:
                    dnt_terms, termbase, source_language = self.settings_manager.load_ai_config()
                    api_cfg.dnt_terms = dnt_terms
                    api_cfg.termbase = termbase
                    api_cfg.source_language = source_language
                    self.logger.info("DNT terms loaded: %s", len(api_cfg.dnt_terms))
                    self.logger.info("Termbase languages loaded: %s", len(api_cfg.termbase))
                    if api_cfg.termbase:
                        self.logger.info("Termbase languages: %s", list(api_cfg.termbase.keys()))
                except Exception as e:
                    self.logger.warning("Failed to load AI config from settings manager: %s", e)

            # Check for cooperative stop before starting translation
            if self.is_stopped():
                self.logger.info("Translation stopped by user request")
                return

            # Run translation and capture stdout
            output = io.StringIO()

            with redirect_stdout(output):
                from srt_translator.api import Translator as _GuiTranslator

                try:
                    results = _GuiTranslator(api_cfg).run()
                except Exception as e:
                    self.logger.error("Translation session failed: %s", e)
                    raise e

            # Remember returned paths for fixer and UI
            self.log_file = results.get("log_file") if results else None
            self.batch_dir = results.get("batch_dir") if results else None

            # Check again after translation
            if self.is_stopped():
                self.logger.info("Translation stopped by user request before completion")
                return

            # Capture stdout output and chunk if large
            stdout_output = output.getvalue().strip()
            if stdout_output:
                output_lines = stdout_output.split("\n")
                chunk_size = 10
                for i in range(0, len(output_lines), chunk_size):
                    chunk = output_lines[i: i + chunk_size]
                    part_num = (i // chunk_size) + 1
                    self._throttled_emit(
                        self.progress_updated,
                        f"Translation output{' (part ' + str(part_num) + ')' if len(output_lines) > chunk_size else ''}: "
                        + "\n".join(chunk),
                    )

            # Store results for potential fixer use
            self.translation_results = results

            # (Fixer runs in core automatically; nothing to do here)

            # Learn from this run: update adaptive popular languages
            try:
                if self.settings_manager and self.target_languages:
                    # Track usage for each selected target language code
                    for code in (self.target_languages or {}).values():
                        try:
                            self.settings_manager.track_language_usage(code)
                        except Exception as e:
                            self.logger.warning("Failed to track usage for language '%s': %s", code, e)
            except Exception:
                # Never fail the run due to usage tracking
                self.logger.exception("Adaptive language usage tracking failed")

            # Post-translation evaluation (config-gated)
            try:
                eval_logger = self.logger.getChild("eval")

                # Prefer an explicit batch root if your translation returns it
                batch_root = results.get("batch_directory")  # <— add this in your pipeline if possible
                if batch_root:
                    latest_batch = Path(batch_root)
                else:
                    # Fallback: derive from the known output_directory
                    out_dir = results.get("output_directory")
                    if not out_dir:
                        self.logger.warning("No output directory found for evaluation")
                        latest_batch = None
                    else:
                        parent = Path(out_dir)
                        candidates = [
                            d for d in parent.iterdir() if d.is_dir() and d.name.startswith("translation-batch-")
                        ]
                        # Choose by modification time to avoid lexicographic surprises
                        latest_batch = max(candidates, key=lambda d: d.stat().st_mtime) if candidates else None

                if latest_batch and latest_batch.exists():
                    self.logger.info("Running evaluation", extra={"batch": latest_batch.name})
                    rollup = run_batch_evaluation(
                        batch_root=latest_batch,
                        logger=eval_logger,
                        language_config=api_cfg,
                    )

                    if rollup:
                        # Resolve artifacts dir
                        artifacts_dir = latest_batch / "artifacts"
                        ai_config_path = artifacts_dir / "ai_config.json"

                        if not ai_config_path.exists():
                            # Fail fast: a single source of truth
                            raise FileNotFoundError(f"ai_config.json not found at: {ai_config_path}")

                        # Call the orchestrator
                        from srt_translator.eval.report import emit_all_reports

                        try:
                            paths = emit_all_reports(artifacts_dir, rollup)
                            self.logger.info("Generated all reports:")
                            for name, path in paths.items():
                                self.logger.info("  %s: %s", name, path.absolute())
                        except Exception as e:
                            self.logger.error("Failed to generate reports: %s", e)
                            raise

                        self.logger.info("Evaluation completed successfully")
                        # Update progress for GUI
                        self._throttled_emit(
                            self.progress_updated,
                            f"Evaluation completed successfully for batch: {latest_batch.name}",
                        )

                        # Emit signal with all report paths
                        self.eval_report_ready.emit({k: str(v) for k, v in paths.items()})
                    else:
                        self.logger.info("Evaluation skipped (no rubric found)")
                        self._throttled_emit(
                            self.progress_updated,
                            "Evaluation skipped (no rubric found)",
                        )
                else:
                    self.logger.warning("No batch directory found for evaluation")

            except Exception as e:
                self.logger.error("Evaluation failed", extra={"error": str(e)}, exc_info=True)
                # Don't fail the translation - evaluation is optional
                self._throttled_emit(
                    self.progress_updated,
                    f"Evaluation failed: {e} (translation completed successfully)",
                )

            # Emit completion via signal (thread-safe)
            self.translation_completed.emit(results)

        except Exception as e:
            error_msg = f"Translation failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            # Emit error via signal (thread-safe)
            self.translation_error.emit(error_msg)
        finally:
            self._stop_logging_bridge()

    def setup_ai_configuration(self):
        """Log AI configuration snapshot from settings (if available)."""
        if not self.settings_manager:
            self.logger.warning("No settings manager available for AI configuration")
            return

        try:
            dnt_terms, termbase, source_language = self.settings_manager.load_ai_config()
            self.logger.info("AI configuration (snapshot) loaded from settings")
            self.logger.info("DNT terms count: %s", len(dnt_terms))
            if termbase:
                self.logger.info("Termbase languages: %s", list(termbase.keys()))
            if source_language:
                code = source_language.get("code")
                name = source_language.get("name")
                self.logger.info("Source language: %s (%s)", name, code)

            # Note: The translation run receives the config directly; this is logging only.

        except Exception as e:
            self.logger.error("Error setting up AI configuration: %s", e)
            # Don't raise - this is not critical for translation

    # (no fixer here; core owns fixes)
