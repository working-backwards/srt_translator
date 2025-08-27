# srt_translator/eval/runner.py
from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import re, json, datetime, yaml, shutil, csv

from srt_translator.eval.tools import (
    generate_eval,
    parse_srt,
    percentile,
    should_emit_fragments,
)
from srt_translator.core.config.language_config import LanguageConfig
from importlib.metadata import version as _pkg_version

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


def _pair_by_contract(
    originals_dir: Path, lang_dir: Path, lang: str
) -> List[Tuple[Path, Path]]:
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
    except Exception:
        pass
    return {"name": code, "code": code}


def _ensure_manifest_fields(batch_root: Path, logger) -> None:
    """Ensure manifest.json has all required fields, merging/patching if needed."""
    man = batch_root / "manifest.json"
    manifest = {}
    if man.exists():
        try:
            manifest = json.loads(man.read_text(encoding="utf-8"))
        except Exception:
            logger.warning("manifest.json unreadable; replacing with a fresh one.")
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
                code = (
                    info.get("normalized_code") or info.get("detected_code") or ""
                ).strip()
                name = (info.get("normalized_name") or "").strip()
                if code and not name:
                    # Use LanguageConfig to get friendly name
                    try:
                        project_root = _project_root()
                        languages_file = project_root / "config" / "languages.json"
                        if languages_file.exists():
                            data = json.loads(
                                languages_file.read_text(encoding="utf-8")
                            )
                            config = LanguageConfig(data)
                            name = config.get_language_name(code)
                    except Exception:
                        pass
                if code or name:
                    manifest["original_language"] = {"code": code, "name": name}
            except Exception as ex:
                logger.warning(
                    "Could not patch original_language from ai_config.json: %s", ex
                )

    man.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(
        "Ensured manifest.json has all required fields", extra={"path": str(man)}
    )


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
            "created_at": datetime.datetime.utcnow().replace(microsecond=0).isoformat()
            + "Z",
            "app_version": "unversioned",
            "evaluator_version": "unversioned",
            "original_language": (
                src_lang_info if src_lang_info else {"code": "", "name": ""}
            ),
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
        logger.warning(
            "Failed to write manifest.json (continuing)", extra={"error": str(e)}
        )


def run_batch_evaluation(
    batch_root: Path, logger, language_config: Optional[Any] = None
) -> Optional[Dict[str, Any]]:
    """
    Run batch evaluation on translated files.

    Args:
        batch_root: Path to the translation batch directory
        logger: Logger instance for evaluation output
        language_config: Optional TranslationConfiguration object containing source_language info
    """
    log = logger.getChild("runner")
    batch_root = Path(batch_root)

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
    languages = [p.name for p in language_dirs]

    # Friendly source language from TranslationConfiguration (if available)
    src_lang_info = {}
    log.info("DEBUG: language_config type: %s", type(language_config))
    if language_config:
        log.info("DEBUG: language_config attributes: %s", dir(language_config))
        if hasattr(language_config, "source_language"):
            src_lang = language_config.source_language
            log.info(
                "DEBUG: source_language type: %s, value: %s", type(src_lang), src_lang
            )
            if src_lang and isinstance(src_lang, dict):
                log.info("DEBUG: source_language keys: %s", list(src_lang.keys()))
                # Check for normalized_code first, then detected_code
                code = src_lang.get("normalized_code") or src_lang.get("detected_code")
                if code:
                    name = (
                        src_lang.get("normalized_name")
                        or src_lang.get("detected_name")
                        or str(code)
                    )
                    src_lang_info = {"code": str(code), "name": str(name)}
                    log.info("DEBUG: Using code: %s, name: %s", code, name)
                else:
                    log.info("DEBUG: No valid code found in source_language")
            else:
                log.info("DEBUG: source_language is not a dict or is empty")
        else:
            log.info("DEBUG: language_config has no source_language attribute")
    else:
        log.info("DEBUG: No language_config provided")

    log.info("Source language info from TranslationConfiguration: %s", src_lang_info)

    # ensure manifest is complete (source name, versions)
    _ensure_manifest_fields(batch_root, log)

    rollup: Dict[str, Any] = {
        "batch_label": batch_label,
        "languages": {},
        "original_language": src_lang_info,  # report can use .name if non-empty
    }

    for lang_dir in language_dirs:
        lang = lang_dir.name
        out_dir = artifacts_root / lang
        out_dir.mkdir(parents=True, exist_ok=True)

        # Discover DNT/TB in batch root (no fallback to ai_config by design).
        dnt_path = batch_root / "dnt_summary.json"
        tb_path = batch_root / "termbase_summary.json"
        if not dnt_path.exists() or not tb_path.exists():
            log.info(
                "DNT/TB summaries not found in batch root; DNT coverage will be skipped."
            )
            dnt_data, tb_data = {}, {}
        else:
            dnt_data = json.loads(dnt_path.read_text(encoding="utf-8"))
            tb_data = json.loads(tb_path.read_text(encoding="utf-8"))

        # Copy batch-level DNT/TB into per-lang artifacts for self-contained audits
        if dnt_data:
            (out_dir / "dnt_summary.json").write_text(
                json.dumps(dnt_data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        if tb_data:
            (out_dir / "termbase_summary.json").write_text(
                json.dumps(tb_data, ensure_ascii=False, indent=2), encoding="utf-8"
            )

        cps_soft_cap, cps_hard_cap = _caps_for(lang, rubric)
        pairs = _pair_by_contract(originals_dir, lang_dir, lang)

        per_files: List[Dict[str, Any]] = []
        for source_file, target_file in pairs:
            # Run evaluator (writes CSVs/MD)
            try:
                res = generate_eval(
                    source_path=str(source_file),
                    target_path=str(target_file),
                    lang=lang,
                    batch_label=batch_label,
                    out_dir=str(out_dir),
                    dnt_path=str(dnt_path) if dnt_path else None,
                    tb_path=str(tb_path) if tb_path else None,
                    cps_soft=cps_soft_cap,
                    cps_hard=cps_hard_cap,
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

            # Numbers mismatches (read from CSV we always wrote)
            num_csv = out_dir / f"number_mismatch_{lang}_{batch_label}.csv"
            num_issues = []
            if num_csv.exists():
                for row in csv.DictReader(
                    num_csv.read_text(encoding="utf-8").splitlines()
                ):
                    cue = int(row["cue"])
                    en_text = (
                        source_cues[cue - 1].text
                        if 1 <= cue <= len(source_cues)
                        else ""
                    )
                    num_issues.append(
                        {"cue": cue, "original": en_text, "target": row["target_text"]}
                    )

            # Untranslated after DNT
            un_csv = out_dir / f"untranslated_{lang}_{batch_label}.csv"
            un_issues = []
            if un_csv.exists():
                for row in csv.DictReader(
                    un_csv.read_text(encoding="utf-8").splitlines()
                ):
                    un_issues.append(
                        {
                            "cue": int(row["cue"]),
                            "original": row["original_text"],
                            "target": row["target_text"],
                        }
                    )

            # Missing translation (empty cue text) - computed in memory
            missing_issues = []
            for cue_idx, target_cue in enumerate(target_cues):
                if not target_cue.text or not target_cue.text.strip():
                    src_text = (
                        source_cues[cue_idx].text if cue_idx < len(source_cues) else ""
                    )
                    missing_issues.append(
                        {
                            "idx": target_cue.index,  # Cue class uses 'index' field
                            "src": src_text,
                            "tgt": "",  # empty target text
                        }
                    )

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
                        f"Error calculating timing drift for cue {cue_idx+1}, skipping: {e}"
                    )
                    continue

            med_ds = (
                percentile(timing_delta_start_ms, 0.5) if timing_delta_start_ms else 0.0
            )
            p95_ds = (
                percentile(timing_delta_start_ms, 0.95)
                if timing_delta_start_ms
                else 0.0
            )
            med_de = (
                percentile(timing_delta_end_ms, 0.5) if timing_delta_end_ms else 0.0
            )
            p95_de = (
                percentile(timing_delta_end_ms, 0.95) if timing_delta_end_ms else 0.0
            )
            timing_fail = med_ds > 200 or med_de > 200 or p95_ds > 500 or p95_de > 500

            verdict = res.get("verdict", "FAIL")
            per_files.append(
                {
                    "source_file": source_file.name,
                    "target_file": target_file.name,
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
                        "numbers": num_issues,  # keep MD manageable
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

    return rollup
