#!/usr/bin/env python3
"""
Subtitle Structural Boundary Review Tool
Pre-processing step before translation.

SPEC-COMPLIANT VERSION
Implements dynamic structural boundary detection based on:
- Cue N end signals
- Cue N+1 completion signals
- Confidence category assignment
- Summary metrics
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List

TIME_RE = re.compile(r"(.*) --> (.*)")

DETERMINERS = {"a", "an", "the", "this", "that", "these", "those"}
PREPOSITIONS = {"of", "to", "in", "on", "for", "with", "at", "from"}
AUXILIARIES = {"will", "would", "could", "should", "can", "may", "might", "must"}
CONJUNCTIONS = {"and", "or", "but"}

ADJECTIVE_SUFFIXES = ("ful", "ous", "ive", "al", "able", "ible", "ant", "ent", "ic", "good")

TERMINAL_PUNCT = (".", "?", "!")


def parse_srt(path: Path):
    cues = []
    blocks = path.read_text(encoding="utf-8").strip().split("\n\n")

    for block in blocks:
        lines = block.splitlines()
        if len(lines) < 3:
            continue

        idx = lines[0]
        match = TIME_RE.match(lines[1])
        if not match:
            continue

        start, end = match.groups()
        text = " ".join(lines[2:]).strip()
        cues.append((idx, start, end, text))

    return cues


def last_word(text: str) -> str:
    words = text.strip().split()
    if not words:
        return ""
    return words[-1].lower().strip(",.:;-")


def first_word(text: str) -> str:
    words = text.strip().split()
    if not words:
        return ""
    return words[0].lower().strip(",.:;-")


def ends_with_terminal(text: str) -> bool:
    return text.strip().endswith(TERMINAL_PUNCT)


def looks_like_adjective(word: str) -> bool:
    return word.endswith(ADJECTIVE_SUFFIXES)


def detect_boundaries(file_name: str, cues):
    results = []
    metrics = {"Error": 0, "Warning": 0, "Info": 0, "checked": 0}

    for i in range(len(cues) - 1):
        a = cues[i]
        b = cues[i + 1]

        metrics["checked"] += 1

        text_a = a[3]
        text_b = b[3]

        if ends_with_terminal(text_a):
            continue

        lw = last_word(text_a)
        fw = first_word(text_b)

        end_signal = None
        start_signal = None

        if lw in DETERMINERS:
            end_signal = "determiner"
        elif lw in PREPOSITIONS:
            end_signal = "preposition"
        elif lw in AUXILIARIES:
            end_signal = "auxiliary"
        elif lw in CONJUNCTIONS:
            end_signal = "conjunction"
        elif looks_like_adjective(lw):
            end_signal = "adjective"


        if fw and fw[0].isalpha():
            start_signal = "continuation"

        reason = None
        level = None

        if end_signal in ("adjective", "determiner", "preposition") and start_signal:
            reason = f"Strong structural continuation ({end_signal} → completion)"
            level = "Error"

        elif end_signal == "conjunction":
            reason = "Possible list or clause continuation"
            level = "Warning"

        elif end_signal:
            reason = f"Weak continuation signal ({end_signal})"
            level = "Info"

        if level:
            metrics[level] += 1
            results.append((file_name, a, b, reason, level))

    return results, metrics


def generate_boundary_review(files: List[Path], output_path: Path):
    all_flags = []
    summary = {"Error": 0, "Warning": 0, "Info": 0, "checked": 0, "cues": 0}

    for file in files:
        cues = parse_srt(file)
        summary["cues"] += len(cues)

        flags, metrics = detect_boundaries(file.name, cues)

        summary["Error"] += metrics["Error"]
        summary["Warning"] += metrics["Warning"]
        summary["Info"] += metrics["Info"]
        summary["checked"] += metrics["checked"]

        all_flags.extend(flags)

    lines = ["# Subtitle Structural Boundary Review\n"]

    lines.append("## Summary Metrics\n")
    lines.append(f"- Total cues analyzed: {summary['cues']}")
    lines.append(f"- Total boundaries checked: {summary['checked']}")
    lines.append(f"- Error: {summary['Error']}")
    lines.append(f"- Warning: {summary['Warning']}")
    lines.append(f"- Info: {summary['Info']}\n")

    current_file = None

    for f in all_flags:
        file_name, a, b, reason, level = f

        if file_name != current_file:
            lines.append(f"\n## File: {file_name}\n")
            current_file = file_name

        lines.append(
f"""### Cue {a[0]} → {b[0]}

{a[1]} --> {a[2]}
{b[1]} --> {b[2]}

Text A: {a[3]}
Text B: {b[3]}

Reason: {reason}
Confidence: {level}
""")
    output_path.write_text("\n".join(lines), encoding="utf-8")
