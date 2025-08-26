#!/usr/bin/env python3
"""Unified GUI entry for SRT Translator (used by `srtx` and PyInstaller)."""
from __future__ import annotations
import argparse, logging, sys


def _setup_logging(debug: bool) -> None:
    """Dev-only debug: ignore `--debug` when frozen (packaged app)."""
    level = (
        logging.DEBUG if (debug and not getattr(sys, "frozen", False)) else logging.INFO
    )
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        force=True,
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="srtx", description="SRT Translator GUI")
    p.add_argument(
        "--debug", action="store_true", help="Enable debug logging (dev runs only)"
    )
    p.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__import__('srt_translator').__version__}",
    )
    args, _ = p.parse_known_args(argv)
    _setup_logging(args.debug)

    try:
        from PySide6.QtWidgets import QApplication
    except ImportError as e:
        raise SystemExit(
            "GUI deps missing. Try: pip install 'srt-translator[gui]'"
        ) from e

    from srt_translator.gui.main_window import SRTTranslatorMainWindow
    from srt_translator import __version__ as _ver

    app = QApplication(sys.argv)
    app.setApplicationName("SRT Translator")
    app.setApplicationVersion(_ver)
    win = SRTTranslatorMainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
