# srt_translator/gui/logging_bridge.py
from __future__ import annotations

import logging
import queue
from collections.abc import Callable, Iterable
from logging.handlers import QueueHandler, QueueListener


class NamePrefixFilter(logging.Filter):
    def __init__(self, prefixes: Iterable[str]) -> None:
        super().__init__()
        self._p = tuple(prefixes)

    def filter(self, record: logging.LogRecord) -> bool:
        name = record.name or ""
        return name.startswith(self._p) if self._p else True


class NonBlockingQueueHandler(QueueHandler):
    """Never block producer; drop noisy INFO when full, keep ERROR+."""

    def enqueue(self, record: logging.LogRecord) -> None:
        q = self.queue  # type: ignore[attr-defined]
        try:
            q.put_nowait(record)
        except queue.Full:
            if record.levelno >= logging.ERROR:
                try:
                    q.get_nowait()
                except Exception as e:
                    # Queue operation failed, but don't break logging
                    print(f"Warning: Queue get failed: {e}")  # noqa: T201
                try:
                    q.put_nowait(record)
                except Exception as e:
                    # Queue operation failed, but don't break logging
                    print(f"Warning: Queue put failed: {e}")  # noqa: T201
            # else drop


class CallbackHandler(logging.Handler):
    """Send formatted records to a GUI callback."""

    def __init__(self, cb: Callable[[str, int, dict], None]) -> None:
        super().__init__()
        self._cb = cb

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            extra = {
                k: v
                for k, v in record.__dict__.items()
                if k
                not in {
                    "name",
                    "msg",
                    "args",
                    "levelname",
                    "levelno",
                    "pathname",
                    "filename",
                    "module",
                    "exc_info",
                    "exc_text",
                    "stack_info",
                    "lineno",
                    "funcName",
                    "created",
                    "msecs",
                    "relativeCreated",
                    "thread",
                    "threadName",
                    "processName",
                    "process",
                }
            }
            self._cb(msg, record.levelno, extra)
        except Exception as e:
            # Callback failed, but don't break logging
            print(f"Warning: Logging callback failed: {e}")  # noqa: T201


class SimpleFormatter(logging.Formatter):
    def __init__(self, fmt=None, datefmt=None):
        super().__init__(
            fmt or "%(asctime)s %(levelname)s  %(message)s",
            datefmt or "%Y-%m-%d %H:%M:%S",
        )


def make_gui_logging_pipeline(
    *,
    logger_name: str = "srt_translator",
    name_prefix_filter: Iterable[str] | None = ("srt_translator",),
    append_callback: Callable[[str, int, dict], None],
    file_handler: logging.Handler | None = None,
    queue_size: int = 1000,
    level: int = logging.INFO,
):
    """Attach a QueueHandler and start a QueueListener forwarding to UI callback (and optional file handler)."""
    log = logging.getLogger(logger_name)
    log.setLevel(level)
    q: queue.Queue[logging.LogRecord] = queue.Queue(maxsize=queue_size)
    qh = NonBlockingQueueHandler(q)
    qh.setLevel(level)
    if name_prefix_filter:
        qh.addFilter(NamePrefixFilter(name_prefix_filter))
    ui_handler = CallbackHandler(append_callback)
    ui_handler.setLevel(logging.INFO)
    ui_handler.setFormatter(SimpleFormatter())
    handlers = [ui_handler]
    if file_handler is not None:
        handlers.append(file_handler)
    listener = QueueListener(q, *handlers, respect_handler_level=True)
    if not any(isinstance(h, NonBlockingQueueHandler) for h in log.handlers):
        log.addHandler(qh)
    listener.start()
    return log, qh, listener
