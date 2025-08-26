# srt_translator/eval/report.py
"""
Batch evaluation report generator for translated SRT files.

This module generates comprehensive batch-level evaluation reports that provide:
1. Language roll-up summary with pass/fail counts
2. Per-language detailed tables with status and metrics
3. Links to all evaluation artifacts for detailed review

The report format is designed to be creator-friendly and provide quick insights
into translation quality across all languages in a batch.

Key Features:
- Batch-level summary with language roll-up
- Per-language status tables with CPS thresholds
- Direct links to evaluation artifacts (CSV/MD files)
- Clear status indicators with emojis
- Consistent formatting matching the evaluation guide
"""

from __future__ import annotations
from pathlib import Path
from typing import Dict, Any

# Report template constants
HDR = """# Translation Evaluation Report

**Note on terminology:** Each numbered block is a *subtitle (aka cue)*.
**CPS (characters per second):** visible characters ÷ duration (sec).

Batch: {batch}
Target languages: {n}

---
"""

ROLLUP = """## Language roll-up (quick scan)

| Language | Files (ok / warn / fail) | Notable signals |
|---|---:|---|
"""

PER_LANG = """
---
## {lang}

**Caps used:** soft={soft} CPS, hard={hard} CPS

| Original file | Status | Key metrics | Where to review |
|---|---|---|---|
"""


def _status(s: str | None) -> str:
    """
    Convert evaluation status to human-readable emoji format.

    Args:
        s: Status string from evaluation results

    Returns:
        Formatted status with emoji and description
    """
    s = (s or "").upper()
    if s.startswith("PASS"):
        return "✅ Ready"
    if "WARN" in s or s.startswith("READY WITH"):
        return "⚠️ Ready w/ warnings"
    if s.startswith("FAIL") or s.startswith("NOT READY"):
        return "❌ Not ready"
    return "—"


def _counts(files):
    """
    Count files by status category.

    Args:
        files: List of file evaluation results

    Returns:
        Tuple of (ok_count, warn_count, fail_count)
    """
    ok = warn = fail = 0
    for f in files:
        st = (f.get("status") or "").upper()
        if st.startswith("PASS"):
            ok += 1
        elif "WARN" in st or st.startswith("READY WITH"):
            warn += 1
        elif st.startswith("FAIL") or st.startswith("NOT READY"):
            fail += 1
        else:
            # Unknown status treated as warning for visibility
            warn += 1
    return ok, warn, fail


def write_batch_report(batch_root: Path, rollup: Dict[str, Any], logger) -> Path:
    """
    Generate and write a comprehensive batch evaluation report.

    This function creates a batch-level eval_report.md that provides:
    1. Overall batch summary with language count
    2. Language roll-up table showing pass/fail statistics
    3. Per-language sections with CPS thresholds and file statuses
    4. Direct links to all evaluation artifacts for detailed review

    Args:
        batch_root: Path to the translation batch directory
        rollup: Evaluation results rollup from run_batch_evaluation
        logger: Injected logger for report generation logging

    Returns:
        Path to the generated eval_report.md file

    The report is written to batch_root/eval_report.md and provides
    a comprehensive overview of translation quality across all languages.
    """
    log = logger.getChild("report")
    out = []

    # Write report header with batch information
    out.append(
        HDR.format(
            batch=rollup.get("batch_label", batch_root.name),
            n=len(rollup.get("languages", {})),
        )
    )

    # Generate language roll-up table
    out.append(ROLLUP)
    for lang, entry in rollup.get("languages", {}).items():
        ok, warn, fail = _counts(entry.get("files", []))

        # Determine notable signals for quick scanning
        signals = []
        if warn:
            signals.append("CPS tail or terminology")
        if fail:
            signals.append("numbers or untranslated")

        out.append(f"| {lang} | {ok} / {warn} / {fail} | {', '.join(signals)} |")

    # Generate per-language detailed sections
    for lang, entry in rollup.get("languages", {}).items():
        out.append(
            PER_LANG.format(
                lang=lang, soft=entry.get("cps_soft"), hard=entry.get("cps_hard")
            )
        )

        # Add file-level status table
        for f in entry.get("files", []):
            base = f"artifacts/{lang}"

            # Generate links to all evaluation artifacts
            links = ", ".join(
                [
                    f"`{base}/eval_summary_{lang}_*.md`",
                    f"`{base}/cps_{lang}_*.csv`",
                    f"`{base}/timing_{lang}_*.csv`",
                    f"`{base}/number_mismatch_{lang}_*.csv`",
                    f"`{base}/source_fragments_{lang}_*.csv`",
                ]
            )

            out.append(
                f"| {f.get('source_file')} | {_status(f.get('status'))} | {f.get('notes') or ''} | {links} |"
            )

    # Write the complete report to file
    out_path = batch_root / "eval_report.md"
    out_path.write_text("\n".join(out), encoding="utf-8")

    log.info(
        "Wrote eval_report.md",
        extra={
            "path": str(out_path),
            "batch_label": rollup.get("batch_label", "unknown"),
            "n_languages": len(rollup.get("languages", {})),
        },
    )

    return out_path
