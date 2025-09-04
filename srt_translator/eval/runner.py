# srt_translator/eval/runner.py
from __future__ import annotations

import csv
import datetime
import json
import logging
import re
import shutil
from importlib.metadata import version as _pkg_version
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from srt_translator.core.config.language_config import LanguageConfig
from srt_translator.eval.tools import (
    classify_empty_target_rollup,
    generate_eval,
    normalize_for_empty_check,
    parse_srt,
    percentile,
)

BATCH_RE = re.compile(r"translation-batch-([^/\\]+)$")


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _rubric_path() -> Path:
    return _project_root() / "config" / "translation_rubric.yaml"


def _discover_batch_label(batch_root: Path) -> str:
    m = BATCH_RE.search(batch_root.as_posix())
    return m.group(1) if m else batch_root.name


def _find_originals_dir(batch_root: Path) -> Optional[Path]:
    base = batch_root / "originals"
    if not base.exists():
        return None
    subs = [d for d in base.iterdir() if d.is_dir()]
    if len(subs) == 1:
        return subs[0]
    if any(x.suffix.lower() == ".srt" for x in base.glob("*.srt")):
        return base
    return None


def _collect_language_dirs(batch_root: Path) -> List[Path]:
    out = []
    for p in batch_root.iterdir():
        if p.is_dir() and p.name not in ("originals", "artifacts", "config"):
            if any(True for _ in p.rglob("*.srt")):
                out.append(p)
    return sorted(out)


def _pair_by_contract(originals_dir: Path, lang_dir: Path, lang: str) -> List[Tuple[Path, Path]]:
    token = lang.replace("_", "-").upper()
    suffix = f" - {token}"
    source_map = {p.stem: p for p in originals_dir.rglob("*.srt")}
    pairs: List[Tuple[Path, Path]] = []
    for target in lang_dir.rglob("*.srt"):
        stem = target.stem
        if stem.endswith(suffix):
            base = stem[: -len(suffix)]
            source = source_map.get(base)
            if source:
                pairs.append((source, target))
    return pairs


def _caps_for(lang: str, rubric: dict) -> Tuple[int, int]:
    caps = rubric.get("caps", {})
    per = caps.get("per_language") or {}
    if lang in per:
        return int(per[lang]["cps_soft"]), int(per[lang]["cps_hard"])
    d = caps.get("defaults") or {}
    soft = int(d.get("cps_soft", 15))
    hard = int(d.get("cps_hard", 20))
    if soft >= hard:
        return (12, 15) if lang.lower().startswith("zh") else (15, 20)
    return (soft, hard)


# === Context helpers (evaluator owns context in v1.0) =======================
# We already have source_cues and target_cues in memory during evaluation.
# Add a small, boundary-safe ±2 window around a 1-based cue index.
def _ctx_window(cues, idx1: int, k: int = 2) -> list[tuple[int, str]]:
    lines: list[tuple[int, str]] = []
    if not cues or not isinstance(idx1, int) or idx1 <= 0:
        return lines
    n = len(cues)
    i0 = min(max(idx1 - 1, 0), n - 1)  # clamp to [0, n-1]
    lo = max(0, i0 - k)
    hi = min(n - 1, i0 + k)
    for j in range(lo, hi + 1):
        # cues[j].text is expected to be the raw text for that cue
        lines.append((j + 1, (cues[j].text or "")))
    return lines


def _attach_context_to_issues(issue_list: list[dict], source_cues, target_cues) -> None:
    # Mutates each issue dict in place, adding a "context" field:
    # {"source":[(n,text)...], "target":[(n,text)...]}
    if not issue_list:
        return
    for it in issue_list:
        idx = it.get("idx")
        if not isinstance(idx, int):
            continue
        it["context"] = {
            "source": _ctx_window(source_cues, idx, 2),
            "target": _ctx_window(target_cues, idx, 2),
        }


def _find_summary(candidates: List[Path]) -> Optional[Path]:
    for p in candidates:
        if p and p.exists():
            return p
    return None


def _copy_into_artifacts(src: Optional[Path], dest_dir: Path, logger) -> Optional[Path]:
    if not src:
        return None
    dest = dest_dir / src.name
    try:
        if src.resolve() != dest.resolve():
            shutil.copyfile(src, dest)
    except Exception as e:
        logger.warning(
            "Could not copy policy JSON into artifacts",
            extra={"src": str(src), "dest": str(dest), "error": str(e)},
        )
    return dest


def _get_language_info(code: str) -> Dict[str, str]:
    """Get language info using the language config abstraction."""
    try:
        # Load languages.json from project root
        project_root = _project_root()
        languages_file = project_root / "config" / "languages.json"
        if languages_file.exists():
            data = json.loads(languages_file.read_text(encoding="utf-8"))
            config = LanguageConfig(data)
            name = config.get_language_name(code)
            return {"name": name, "code": code}
    except Exception as e:
        # Fallback to code if language lookup fails
        print(f"Warning: Failed to load language info for {code}: {e}")  # noqa: T201
    return {"name": code, "code": code}


def _extract_dnt_terms(dnt_json: Dict[str, Any]) -> List[str]:
    """Accepts {'terms': [...]} or legacy {'dnt_terms': [...]}."""
    if not isinstance(dnt_json, dict):
        return []
    terms = dnt_json.get("terms") or dnt_json.get("dnt_terms")
    return terms if isinstance(terms, list) else []


def _extract_tb_map(tb_json: Dict[str, Any], lang: str) -> Dict[str, str]:
    """
    Accepts {'languages': {'az': {...}}} or legacy {'az': {...}}.
    Returns a target-side term map for the language, or {}.
    """
    if not isinstance(tb_json, dict):
        return {}
    lang_key = lang
    short = lang.split("-")[0]
    if isinstance(tb_json.get("languages"), dict):
        m = tb_json["languages"].get(lang_key) or tb_json["languages"].get(short)
        return m if isinstance(m, dict) else {}
    m = tb_json.get(lang_key) or tb_json.get(short)
    return m if isinstance(m, dict) else {}


def _calculate_termbase_coverage(termbase: Dict[str, list]) -> str:
    """
    Calculate termbase coverage across all languages.

    Args:
        termbase: Dictionary mapping language codes to lists of term entries

    Returns:
        Coverage level: "full", "partial", or "none"
    """
    if not termbase:
        return "none"

    languages_with_terms = [lang for lang, entries in termbase.items() if entries]
    total_languages = len(termbase)

    if len(languages_with_terms) == 0:
        return "none"
    elif len(languages_with_terms) == total_languages:
        return "full"
    else:
        return "partial"


def _load_batch_config(batch_root: Path, logger) -> Dict[str, Any]:
    """
    Load and normalize configuration from ai_config.json.

    Args:
        batch_root: Path to the batch directory
        logger: Logger instance for error reporting

    Returns:
        Normalized configuration with DNT terms and termbases

    Raises:
        FileNotFoundError: If ai_config.json is missing
        ValueError: If ai_config.json is invalid
    """
    config_path = batch_root / "ai_config.json"
    if not config_path.exists():
        logger.error("Required ai_config.json not found - stopping evaluation")
        raise FileNotFoundError(f"ai_config.json required for evaluation: {config_path}")

    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.error(f"Failed to parse ai_config.json: {e}")
        raise ValueError(f"Invalid ai_config.json: {e}") from e

    # Normalize the data structure
    normalized = {
        "version": config.get("version", "unknown"),
        "timestamp": config.get("timestamp", "unknown"),
        "target_languages": config.get("target_languages", []),
        "dnt_terms": config.get("dnt_terms", []),
        "termbase": {},
    }

    # Normalize termbase from per-language maps to lists of {source, target} pairs
    raw_termbase = config.get("termbase", {})
    for lang, term_map in raw_termbase.items():
        if isinstance(term_map, dict):
            normalized["termbase"][lang] = [
                {"source": src, "target": tgt} for src, tgt in term_map.items()
            ]
        else:
            logger.warning(f"Invalid termbase format for {lang}, skipping")
            normalized["termbase"][lang] = []

    logger.info(
        f"Loaded config from ai_config.json: version={normalized['version']}, "
        f"target_languages={len(normalized['target_languages'])}, "
        f"dnt_terms={len(normalized['dnt_terms'])}, "
        f"termbase_languages={len(normalized['termbase'])}"
    )

    return normalized


def _validate_batch_structure(batch_root: Path, logger, config: Dict[str, Any]) -> bool:
    """
    Validate that the batch has the required structure.

    Args:
        batch_root: Path to the batch directory
        logger: Logger instance for error reporting
        config: Normalized configuration from _load_batch_config

    Returns:
        True if structure is valid, False otherwise
    """
    # Check required directories
    originals_dir = batch_root / "originals"
    if not originals_dir.exists():
        logger.error("Required originals/ directory not found")
        return False

    # Check that we have at least one target language directory
    target_langs = config.get("target_languages", [])
    if not target_langs:
        logger.error("No target languages specified in ai_config.json")
        return False

    # Check that target language directories exist and contain SRT files
    missing_langs = []
    for lang in target_langs:
        lang_dir = batch_root / lang
        if not lang_dir.exists():
            missing_langs.append(lang)
            continue

        # Check if directory contains SRT files
        srt_files = list(lang_dir.glob("*.srt"))
        if not srt_files:
            missing_langs.append(f"{lang} (no SRT files)")

    if missing_langs:
        logger.error(f"Missing or empty target language directories: {missing_langs}")
        return False

    logger.info("Batch structure validation passed")
    return True


def _ensure_manifest_fields(batch_root: Path, log) -> None:
    """Ensure manifest.json has all required fields, merging/patching if needed."""
    man = batch_root / "manifest.json"
    manifest = {}
    if man.exists():
        try:
            manifest = json.loads(man.read_text(encoding="utf-8"))
        except Exception:
            log.warning("manifest.json unreadable; replacing with a fresh one.")
            manifest = {}

    # versions
    try:
        app_version = _pkg_version("srt_translator")
    except Exception:
        app_version = manifest.get("app_version") or "unknown"
    evaluator_version = manifest.get("evaluator_version") or "1.0.0"
    manifest["app_version"] = app_version
    manifest["evaluator_version"] = evaluator_version

    # source language (patch from ai_config.json if needed)
    ol = manifest.get("original_language") or {}
    if not ol.get("code") or not ol.get("name"):
        ai_cfg = batch_root / "ai_config.json"
        if ai_cfg.exists():
            try:
                ai = json.loads(ai_cfg.read_text(encoding="utf-8"))
                info = ai.get("source_language") or {}
                code = (info.get("normalized_code") or info.get("detected_code") or "").strip()
                name = (info.get("normalized_name") or "").strip()
                if code and not name:
                    # Use LanguageConfig to get friendly name
                    try:
                        project_root = _project_root()
                        languages_file = project_root / "config" / "languages.json"
                        if languages_file.exists():
                            data = json.loads(languages_file.read_text(encoding="utf-8"))
                            config = LanguageConfig(data)
                            name = config.get_language_name(code)
                    except Exception as e:
                        # Fallback to code if language lookup fails
                        print(f"Warning: Failed to load language name for {code}: {e}")  # noqa: T201
                if code or name:
                    manifest["original_language"] = {"code": code, "name": name}
            except Exception as ex:
                log.warning("Could not patch original_language from ai_config.json: %s", ex)

    man.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    log.debug("Ensured manifest.json has all required fields", extra={"path": str(man)})


def _write_manifest_if_missing(
    batch_root: Path,
    languages: List[str],
    files_per_lang: Dict[str, List[str]],
    rubric: dict,
    src_lang_info: Dict[str, str],
    logger,
):
    mf = batch_root / "manifest.json"
    if mf.exists():
        return
    try:
        data = {
            "batch_label": _discover_batch_label(batch_root),
            "created_at": datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
            "app_version": "unversioned",
            "evaluator_version": "unversioned",
            "original_language": (src_lang_info if src_lang_info else {"code": "", "name": ""}),
            "languages": languages,
            "files": files_per_lang,
            "rubric_snapshot": {
                "caps": rubric.get("caps", {}),
                "fragments": rubric.get("fragments", {}),
            },
        }
        mf.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("Wrote manifest.json", extra={"path": str(mf)})
    except Exception as e:
        logger.warning("Failed to write manifest.json (continuing)", extra={"error": str(e)})


def _ensure_batch_log_handler(batch_root: Path, logger) -> None:
    """
    Ensure the evaluation logger has access to the batch log file handler.
    This ensures evaluation logs appear in both console and batch log file.

    Args:
        batch_root: Path to the batch directory
        logger: Logger instance to configure
    """
    # Find the batch log file
    log_files = list(batch_root.glob("translation_issues_*.log"))
    if not log_files:
        logger.warning("No batch log file found - evaluation logs will only go to console")
        return

    # Use the first (and should be only) log file
    log_file = log_files[0]

    # Check if this logger already has a file handler for this log file
    for handler in logger.handlers:
        if (
            isinstance(handler, logging.FileHandler)
            and hasattr(handler, "baseFilename")
            and handler.baseFilename == str(log_file.absolute())
        ):
            logger.debug("Logger already has batch log file handler")
            return

    # Add file handler to ensure evaluation logs go to batch log file
    try:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.debug(f"Added batch log file handler: {log_file.name}")
    except Exception as e:
        logger.warning(f"Failed to add batch log file handler: {e}")


def run_batch_evaluation(
    batch_root: Path, logger, language_config: Optional[Any] = None
) -> Optional[Dict[str, Any]]:
    """
    Run batch evaluation on translated files.

    Args:
        batch_root: Path to the translation batch directory
        logger: Logger instance for evaluation output
        language_config: Optional TranslationConfig object containing source_language info
    """
    log = logger.getChild("runner")
    batch_root = Path(batch_root)

    # Ensure evaluation logger has access to batch log file handler
    _ensure_batch_log_handler(batch_root, logger)

    # Rubric gating
    rubric_file = _rubric_path()
    if not rubric_file.exists():
        log.info(
            "Evaluation skipped: rubric not found",
            extra={"expected_path": str(rubric_file)},
        )
        return None
    try:
        rubric = yaml.safe_load(rubric_file.read_text(encoding="utf-8")) or {}
    except Exception as e:
        log.error(
            "Invalid rubric; evaluation skipped",
            extra={"path": str(rubric_file), "error": str(e)},
        )
        return None

    batch_label = _discover_batch_label(batch_root)
    originals_dir = _find_originals_dir(batch_root)
    if not originals_dir:
        log.error(
            "Originals directory missing or ambiguous",
            extra={"batch_root": str(batch_root)},
        )
        return None

    artifacts_root = batch_root / "artifacts"
    artifacts_root.mkdir(exist_ok=True)

    language_dirs = _collect_language_dirs(batch_root)

    # Friendly source language from TranslationConfig (if available)
    src_lang_info = {}
    if log.isEnabledFor(logging.DEBUG):
        log.debug("language_config type: %s", type(language_config))
    if language_config:
        if log.isEnabledFor(logging.DEBUG):
            try:
                log.debug("language_config attributes: %s", dir(language_config))
            except Exception:
                log.debug("language_config attributes: <unavailable>")
        if hasattr(language_config, "source_language"):
            src_lang = language_config.source_language
            if log.isEnabledFor(logging.DEBUG):
                log.debug("source_language type: %s, value: %s", type(src_lang), src_lang)
            if src_lang and isinstance(src_lang, dict):
                if log.isEnabledFor(logging.DEBUG):
                    try:
                        log.debug("source_language keys: %s", list(src_lang.keys()))
                    except Exception:
                        log.debug("source_language keys: <unavailable>")
                # Check for normalized_code first, then detected_code
                code = src_lang.get("normalized_code") or src_lang.get("detected_code")
                if code:
                    name = src_lang.get("normalized_name") or src_lang.get("name") or str(code)
                    src_lang_info = {"code": str(code), "name": str(name)}
                    if log.isEnabledFor(logging.DEBUG):
                        log.debug("Using code: %s, name: %s", code, name)
                else:
                    if log.isEnabledFor(logging.DEBUG):
                        log.debug("No valid code found in source_language")
            else:
                if log.isEnabledFor(logging.DEBUG):
                    log.debug("source_language is not a dict or is empty")
        else:
            if log.isEnabledFor(logging.DEBUG):
                log.debug("language_config has no source_language attribute")
    else:
        if log.isEnabledFor(logging.DEBUG):
            log.debug("No language_config provided")

    if src_lang_info:
        log.info(
            "Source language: %s (%s)",
            src_lang_info.get("name"),
            src_lang_info.get("code"),
        )

    # ensure manifest is complete (source name, versions)
    _ensure_manifest_fields(batch_root, log)

    # Load and validate batch configuration from ai_config.json
    try:
        batch_config = _load_batch_config(batch_root, log)
    except (FileNotFoundError, ValueError) as e:
        log.error(f"Failed to load batch configuration: {e}")
        return None

    # Validate batch structure
    if not _validate_batch_structure(batch_root, log, batch_config):
        log.error("Batch structure validation failed - stopping evaluation")
        return None

    # Log coverage information for optional inputs
    dnt_terms = batch_config.get("dnt_terms", [])
    if not dnt_terms:
        log.info("No DNT terms provided; continuing without DNT coverage")
    else:
        log.debug(f"DNT terms loaded: {len(dnt_terms)} terms")

    termbase = batch_config.get("termbase", {})
    if not termbase:
        log.info("No termbase provided; continuing without termbase coverage")
    else:
        covered_langs = [lang for lang, entries in termbase.items() if entries]
        log.debug(f"Termbase coverage: {len(covered_langs)} languages with custom terms")

    rollup: Dict[str, Any] = {
        "batch_label": batch_label,
        "languages": {},
        "original_language": src_lang_info,  # report can use .name if non-empty
        # Required coverage fields for v1.0 evaluation policy
        "config_source": "ai_config.json",
        "dnt_coverage": "present" if dnt_terms else "none",
        "termbase_coverage": _calculate_termbase_coverage(termbase),
        "termbase_entry_counts": {lang: len(entries) for lang, entries in termbase.items()},
    }

    for lang_dir in language_dirs:
        lang = lang_dir.name
        out_dir = artifacts_root / lang
        out_dir.mkdir(parents=True, exist_ok=True)

        # Read once from ai_config.json earlier in runner
        batch_dnt_terms = batch_config.get("dnt_terms", []) or []
        tb_per_lang = batch_config.get("termbase", {}) or {}

        # Write normalized DNT/TB to artifacts for audit purposes
        if batch_dnt_terms:
            # NOTE: audit mirror only — not used by evaluation in v1.0
            (out_dir / "dnt_summary.json").write_text(
                json.dumps({"terms": batch_dnt_terms}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        if tb_per_lang:
            # NOTE: audit mirror only — not used by evaluation in v1.0
            (out_dir / "termbase_summary.json").write_text(
                json.dumps({"languages": tb_per_lang}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        cps_soft_cap, cps_hard_cap = _caps_for(lang, rubric)
        pairs = _pair_by_contract(originals_dir, lang_dir, lang)

        per_files: List[Dict[str, Any]] = []
        for source_file, target_file in pairs:
            # Run evaluator (writes CSVs/MD)
            try:
                # Build termbase map for this language
                tb_map = {}
                raw_map = tb_per_lang.get(lang) or tb_per_lang.get(lang.split("-")[0]) or {}
                # raw_map is expected to be {source: target}
                if isinstance(raw_map, dict):
                    tb_map = {str(k): str(v) for k, v in raw_map.items() if k}

                res = generate_eval(
                    source_path=str(source_file),
                    target_path=str(target_file),
                    lang=lang,
                    batch_label=batch_label,
                    out_dir=str(out_dir),
                    dnt_terms=batch_dnt_terms,
                    tb_map=tb_map,
                    cps_soft=cps_soft_cap,
                    cps_hard=cps_hard_cap,
                    rubric=rubric,
                )
            except Exception as e:
                log.error(
                    "Evaluation failed for pair",
                    extra={
                        "lang": lang,
                        "source": str(source_file),
                        "target": str(target_file),
                        "error": str(e),
                    },
                )
                continue

            # Build punch-list items by reading CSVs and SRTs
            source_cues = parse_srt(source_file)
            target_cues = parse_srt(target_file)

            # Untranslated after DNT
            un_csv = out_dir / f"untranslated_{lang}_{batch_label}.csv"
            un_issues = []
            if un_csv.exists():
                for row in csv.DictReader(un_csv.read_text(encoding="utf-8").splitlines()):
                    un_issues.append(
                        {
                            "cue": int(row["cue"]),
                            "original": row["original_text"],
                            "target": row["target_text"],
                        }
                    )

            # Missing translation with roll-up classification:
            # treat punctuation-only / placeholders as empty; exclude benign/suspect roll-ups.
            dnt_terms = _extract_dnt_terms({"terms": batch_dnt_terms})
            tb_map = _extract_tb_map({"languages": {lang: tb_per_lang.get(lang, {})}}, lang)
            missing_issues: List[Dict[str, Any]] = []
            for cue_idx, target_cue in enumerate(target_cues):
                tgt_norm = normalize_for_empty_check(target_cue.text or "")
                if tgt_norm:
                    continue  # definitely not empty
                # Target is effectively empty: decide if it was rolled into a neighbor
                rollup_class, _reason = classify_empty_target_rollup(
                    lang=lang,
                    cue_index=cue_idx,
                    source_cues=source_cues,
                    target_cues=target_cues,
                    do_not_translate_terms=dnt_terms,
                    termbase_map_for_lang=tb_map,
                )
                if rollup_class == "MISSING":
                    src_text = source_cues[cue_idx].text if cue_idx < len(source_cues) else ""
                    missing_issues.append({"idx": target_cue.index, "src": src_text, "tgt": ""})

                    # Timing stats (quick re-summarize)
            cue_count = min(len(source_cues), len(target_cues))
            timing_delta_start_ms = []
            timing_delta_end_ms = []
            for cue_idx in range(cue_count):
                try:
                    # Cue objects have start_ms and end_ms fields
                    src_start = source_cues[cue_idx].start_ms
                    src_end = source_cues[cue_idx].end_ms
                    tgt_start = target_cues[cue_idx].start_ms
                    tgt_end = target_cues[cue_idx].end_ms

                    delta_start_ms = abs(tgt_start - src_start)
                    delta_end_ms = abs(tgt_end - src_end)
                    timing_delta_start_ms.append(delta_start_ms)
                    timing_delta_end_ms.append(delta_end_ms)
                except Exception as e:
                    # Log any errors and skip this cue in drift stats
                    log.warning(
                        f"Error calculating timing drift for cue {cue_idx + 1}, skipping: {e}"
                    )
                    continue

            # Convert to float lists for percentile function
            start_floats = (
                [float(x) for x in timing_delta_start_ms] if timing_delta_start_ms else []
            )
            end_floats = [float(x) for x in timing_delta_end_ms] if timing_delta_end_ms else []
            med_ds = percentile(start_floats, 0.5) if start_floats else 0.0
            p95_ds = percentile(start_floats, 0.95) if start_floats else 0.0
            med_de = percentile(end_floats, 0.5) if end_floats else 0.0
            p95_de = percentile(end_floats, 0.95) if end_floats else 0.0
            timing_fail = med_ds > 200 or med_de > 200 or p95_ds > 500 or p95_de > 500

            verdict = res.get("verdict", "FAIL")

            # Attach ±2 context to issues (stored directly in the rollup JSON).
            _attach_context_to_issues(missing_issues, source_cues, target_cues)
            _attach_context_to_issues(un_issues, source_cues, target_cues)

            per_files.append(
                {
                    # human-friendly names (what MD shows)
                    "source_file": source_file.name,
                    "target_file": target_file.name,
                    # machine-resolvable paths (what report uses)
                    "source_rel": str(source_file.relative_to(batch_root)),
                    "target_rel": str(target_file.relative_to(batch_root)),
                    "status": verdict,
                    "metrics": {
                        "parity_ok": len(source_cues) == len(target_cues),
                        "med_ds_ms": round(med_ds, 1),
                        "p95_ds_ms": round(p95_ds, 1),
                        "med_de_ms": round(med_de, 1),
                        "p95_de_ms": round(p95_de, 1),
                        "cps_soft": cps_soft_cap,
                        "cps_hard": cps_hard_cap,
                    },
                    "issues": {
                        "untranslated_after_dnt": un_issues,
                        "missing_translation": missing_issues,  # computed in memory
                        "timing_fail": timing_fail,
                    },
                    "artifacts_dir": f"artifacts/{lang}",
                }
            )

        rollup["languages"][lang] = {
            "cps_soft": cps_soft_cap,
            "cps_hard": cps_hard_cap,
            "files": per_files,
        }

    # Note: eval_report.json is now written by the report module with strict EvalReportV1 format

    return rollup
