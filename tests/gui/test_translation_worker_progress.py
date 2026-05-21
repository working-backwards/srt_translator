"""Unit tests for the worker's Tier 2 progress enrichment.

`TranslationWorker.emit_retry_status` is a thin wrapper around the
`retry_status` signal, but it has one piece of real logic: when the core
emits a Tier 2 escalation message ("Connection interrupted — retrying every
Ns…"), the worker appends a second line "N of M languages translated so far."
so the user knows how much progress is banked.

These tests pin that behavior, plus the off-by-one fix for `_total_languages`
when same-source filtering would otherwise leave a stale unfiltered count.
"""

from unittest.mock import MagicMock

import pytest

from srt_translator.gui.workers.translation_worker import TranslationWorker


@pytest.fixture
def worker(qapp):
    """Construct a worker with 5 target languages and a stubbed signal."""
    w = TranslationWorker(
        api_key="sk-test",
        selected_files=["/tmp/in.srt"],
        target_languages={
            "Spanish": "es",
            "French": "fr",
            "German": "de",
            "Italian": "it",
            "Japanese": "ja",
        },
    )
    # Replace the Qt signal with a Mock so we can capture every emission
    # without spinning the event loop.
    w.retry_status = MagicMock()
    return w


def test_message_passes_through_unchanged(worker):
    """A Tier 1 message ('Connection issue, retrying in 5s…') must NOT get
    the progress suffix appended — the suffix is reserved for Tier 2."""
    worker._completed_languages = 2
    worker.emit_retry_status("Connection issue, retrying in 5s (attempt 1/5)...")

    worker.retry_status.emit.assert_called_once_with("Connection issue, retrying in 5s (attempt 1/5)...")


def test_message_gets_progress_suffix(worker):
    """A Tier 2 message ('Connection interrupted — retrying every Ns…') must
    have the progress line appended so the user sees 'N of M languages
    translated so far.'"""
    worker._completed_languages = 2
    worker.emit_retry_status("Connection interrupted — retrying every 30s (attempt 4/5)...")

    emitted = worker.retry_status.emit.call_args.args[0]
    assert "Connection interrupted — retrying every 30s (attempt 4/5)..." in emitted
    assert "2 of 5 languages translated so far." in emitted


def test_empty_message_is_forwarded_as_clear(worker):
    """The empty-string convention is used to clear the banner on success;
    the worker must forward it as-is and not append progress info."""
    worker._completed_languages = 3
    worker.emit_retry_status("")

    worker.retry_status.emit.assert_called_once_with("")


def test_progress_reflects_languages_completed(worker):
    """The 'N of M' count should track the on_language_done callback."""
    # Simulate 3 successful languages
    worker._on_language_done()
    worker._on_language_done()
    worker._on_language_done()

    worker.emit_retry_status("Connection interrupted — retrying every 30s (attempt 4/5)...")
    emitted = worker.retry_status.emit.call_args.args[0]
    assert "3 of 5 languages translated so far." in emitted


def test_progress_does_nothing_when_total_unknown(qapp):
    """If the worker was constructed with no target languages (edge case —
    e.g. retry-failed-languages called with empty set), the progress
    enrichment must not run."""
    w = TranslationWorker(
        api_key="sk-test",
        selected_files=["/tmp/in.srt"],
        target_languages={},
    )
    w.retry_status = MagicMock()

    w.emit_retry_status("Connection interrupted — retrying every 30s (attempt 4/5)...")

    # Suffix should not be appended when _total_languages is 0
    emitted = w.retry_status.emit.call_args.args[0]
    assert "languages translated so far" not in emitted


def test_total_languages_initialised_from_target_set(qapp):
    """The off-by-one fix's invariant: _total_languages reflects the number
    of targets passed in at construction time. The worker's run() updates
    this after same-source filtering, but the __init__ value is the baseline."""
    w = TranslationWorker(
        api_key="sk-test",
        selected_files=["/tmp/in.srt"],
        target_languages={"Spanish": "es", "French": "fr", "German": "de"},
    )

    assert w._total_languages == 3
    assert w._completed_languages == 0


# --------------------------------------------------------------------------- #
# Cancel mechanism — request_stop / is_stopped form the contract that
# core.main.translate_srt_files polls via the `stop_check` kwarg.
# --------------------------------------------------------------------------- #


def test_worker_is_stopped_initial_state_is_false(worker):
    """A freshly-constructed worker must not report stopped — the user has
    not clicked Cancel yet."""
    assert worker.is_stopped() is False


def test_worker_request_stop_sets_is_stopped_to_true(worker):
    """request_stop() is the canonical way Cancel propagates from the GUI
    thread to the worker thread; it must flip is_stopped() to True."""
    worker.request_stop()
    assert worker.is_stopped() is True


def test_worker_request_stop_is_idempotent(worker):
    """Calling request_stop multiple times (e.g. user clicks Cancel twice
    or closeEvent also calls it) must not raise or reset the flag."""
    worker.request_stop()
    worker.request_stop()
    worker.request_stop()
    assert worker.is_stopped() is True


def test_worker_is_stopped_is_callable_as_stop_check(worker):
    """`is_stopped` is passed directly to `translate_srt_files` as the
    `stop_check` callback. It must accept no arguments and return a bool."""
    # Should not require any arguments
    result = worker.is_stopped()
    assert isinstance(result, bool)

    worker.request_stop()
    assert worker.is_stopped() is True


def test_on_language_done_increments_completed_counter(worker):
    """The callback core fires after each successful language must increment
    _completed_languages by exactly 1 each call."""
    assert worker._completed_languages == 0

    worker._on_language_done()
    assert worker._completed_languages == 1

    worker._on_language_done()
    assert worker._completed_languages == 2


# --------------------------------------------------------------------------- #
# Retry-status signal contract for downstream consumers.
# --------------------------------------------------------------------------- #


def test_retry_status_signal_carries_string(worker):
    """Downstream connects QLabel.setText() to this signal — it must always
    emit a str (never None, never bytes)."""
    worker.emit_retry_status("Connection issue, retrying in 5s (attempt 1/5)...")
    worker.retry_status.emit.assert_called_once()
    payload = worker.retry_status.emit.call_args.args[0]
    assert isinstance(payload, str)


def test_multiple_emissions_are_independent(worker):
    """Each call to emit_retry_status must produce one independent emission;
    state from a prior call must not leak into the next."""
    worker._completed_languages = 1
    worker.emit_retry_status("Connection issue, retrying in 5s (attempt 1/5)...")

    worker._completed_languages = 3
    worker.emit_retry_status("Connection interrupted — retrying every 30s (attempt 4/5)...")

    assert worker.retry_status.emit.call_count == 2
    second_payload = worker.retry_status.emit.call_args_list[1].args[0]
    assert "3 of 5 languages translated so far." in second_payload
