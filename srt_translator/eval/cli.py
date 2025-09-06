# srt_translator/eval/cli.py
from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Optional

from srt_translator.eval.runner import run_batch_evaluation


def _setup_logging(verbosity: int) -> logging.Logger:
    level = logging.WARNING
    if verbosity == 1:
        level = logging.INFO
    elif verbosity >= 2:
        level = logging.DEBUG

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    return logging.getLogger("srt_translator")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="st-eval",
        description=(
            "Re-run the evaluator on a completed translation batch. "
            "Rewrites evaluator artifacts under artifacts/<lang>/… "
            "and leaves translator outputs untouched."
        ),
    )
    parser.add_argument(
        "--batch-root",
        dest="batch_root",
        default=".",
        help="Path to the batch directory (default: current directory).",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase verbosity (-v=INFO, -vv=DEBUG).",
    )
    args = parser.parse_args(argv)

    log = _setup_logging(args.verbose)
    batch_root = Path(args.batch_root).resolve()

    if not batch_root.exists():
        log.error("Batch root does not exist: %s", batch_root)
        return 2
    if not (batch_root / "artifacts" / "ai_config.json").exists():
        log.error("No ai_config.json in artifacts directory: %s", batch_root / "artifacts")
        return 2

    try:
        rollup = run_batch_evaluation(batch_root=batch_root, logger=log, language_config=None)
    except Exception:  # noqa: BLE001
        log.exception("Evaluation failed.")
        return 1

    if not rollup:
        log.error("No rollup produced; nothing to write.")
        return 3

    try:
        from srt_translator.eval.report import emit_all_reports

        artifacts_dir = batch_root / "artifacts"
        paths = emit_all_reports(artifacts_dir, rollup)
        log.info("Generated all reports: %s", paths)
    except Exception:  # noqa: BLE001
        log.exception("Failed writing evaluation report.")
        return 4

    log.info("Evaluation complete. Artifacts written under: %s", batch_root / "artifacts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
