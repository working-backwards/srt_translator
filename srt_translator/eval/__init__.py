# srt_translator/eval/__init__.py
"""
Evaluation package for translated SRT files.

This package provides tools to evaluate translation quality, including:
- Single pair evaluation (tools.py)
- Batch evaluation orchestration (runner.py)
- Batch report generation (report.py)

All evaluation is config-gated by config/translation_rubric.yaml.
"""

from srt_translator.eval.report import write_batch_report
from srt_translator.eval.runner import run_batch_evaluation
from srt_translator.eval.tools import generate_eval

__all__ = ["generate_eval", "run_batch_evaluation", "write_batch_report"]
