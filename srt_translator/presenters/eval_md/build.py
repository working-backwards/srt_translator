from __future__ import annotations

import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)

_REQUIRED = {"decision", "totals", "kpis", "file_status", "lexicons"}


def _load(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"{path.name} not found at: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    missing = sorted(_REQUIRED - data.keys())
    if missing:
        raise ValueError(f"{path.name} missing required keys: {', '.join(missing)}")
    return data


def build_eval_md(report_v1_path: Path, out_path: Path | None = None) -> Path:
    """Render Markdown report from compiled report_v1.json."""
    data = _load(report_v1_path)
    if out_path is None:
        out_path = report_v1_path.with_name("eval_report.md")

    decision = data["decision"]
    icon = {"pass": "✅", "review": "⚠️", "fix": "❌"}.get(decision.get("level", ""), "⚠️")

    lines: list[str] = []
    # Banner
    lines.append(f"# {icon} {decision.get('summary', '')}".rstrip())
    lines.append("")
    lines.append("## What to do next")
    checklist = decision.get("checklist", [])
    if checklist:
        for step in checklist:
            lines.append(f"- {step}")
    else:
        lines.append("- (no actions)")

    # KPI strip
    lines.append("")
    lines.append("## KPI Summary")
    kpis = data.get("kpis", {})
    for k in [
        "files_total",
        "languages_total",
        "issues_total",
        "dnt_terms",
        "termbase_languages",
        "coverage_languages",
        "coverage_terms",
    ]:
        if k in kpis:
            lines.append(f"- **{k}**: {kpis[k]}")

    # Per-file status
    lines.append("")
    lines.append("## File Status")
    lines.append("")
    lines.append("| File | Lang | Status | Issues |")
    lines.append("|---|---|:---:|:---:|")
    for row in data.get("file_status", []):
        lines.append(f"| {row['file']} | {row['lang']} | {row['status']} | {row['issues']} |")

    # DNT + Termbase
    lines.append("")
    lines.append("## Lexicons")
    lex = data.get("lexicons", {})
    dnt = lex.get("dnt", [])
    tb = lex.get("termbase", {})
    lines.append("")
    lines.append("### DNT Terms")
    if dnt:
        for term in dnt:
            lines.append(f"- {term}")
    else:
        lines.append("_None_")

    lines.append("")
    lines.append("### Termbases")
    if tb:
        for lang in sorted(tb.keys()):
            lines.append(f"- **{lang}**: {len(tb[lang])} terms")
    else:
        lines.append("_None_")

    # Issues (errors + warnings)
    issues = data.get("issues", {})
    if issues:
        lines.append("")
        lines.append("## Punch List")
        # Errors first, then warnings
        for lvl in ("errors", "warnings"):
            items = issues.get(lvl, [])
            if not items:
                continue
            lines.append(f"### {lvl.title()}")
            for it in items:
                lines.append(
                    f"- **{it['file']} ({it['lang']}) — cue {it['cue_id']} — {it['type']}**"
                )
                if it.get("description"):
                    lines.append(f"  - {it['description']}")
                if it.get("suggested_check"):
                    lines.append(f"  - _Suggested check:_ {it['suggested_check']}")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log.info("Wrote eval_report.md: %s", out_path)
    return out_path
