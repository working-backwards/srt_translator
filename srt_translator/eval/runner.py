# srt_translator/eval/runner.py
"""
Batch evaluation orchestrator for translated SRT files.

This module discovers source/target pairs and runs evaluation on each pair,
writing artifacts to the batch artifacts directory.

Evaluation is config-gated by config/translation_rubric.yaml.

File pairing follows a simple contract:
- Source: originals/<base>.srt
- Target: <lang>/<base> - <LANG_TOKEN>.srt
- Where LANG_TOKEN = lang.replace("_", "-").upper()
"""

from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import re
import yaml
import logging

from srt_translator.eval.tools import generate_eval

BATCH_NAME_RE = re.compile(r"translation-batch-([^/\\]+)$")


def _project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).resolve().parents[2]


def _rubric_path() -> Path:
    """Get the path to the translation rubric configuration."""
    return _project_root() / "config" / "translation_rubric.yaml"


def _discover_batch_label(batch_root: Path) -> str:
    """Extract batch label from directory name."""
    m = BATCH_NAME_RE.search(batch_root.as_posix())
    return m.group(1) if m else batch_root.name


def _find_originals_dir(batch_root: Path) -> Optional[Path]:
    """
    Find the originals directory containing source SRT files.

    Expected layouts:
    - batch_root/originals/<src_code>/*.srt
    - batch_root/originals/*.srt
    """
    base = batch_root / "originals"

    # Debug logging to see what we're checking
    log = logging.getLogger(__name__)
    log.info(f"🔍 Looking for originals directory at: {base}")
    log.info(f"📁 Batch root contents: {[p.name for p in batch_root.iterdir()]}")
    log.info(f"📁 Batch root absolute path: {batch_root.absolute()}")

    if not base.exists():
        log.info(f"❌ Originals directory does not exist at: {base}")
        return None

    # Expect exactly one <src_code> subdir OR SRTs directly under originals/
    subdirs = [d for d in base.iterdir() if d.is_dir()]
    log.info(f"📂 Found subdirectories in originals: {[d.name for d in subdirs]}")

    if subdirs and len(subdirs) == 1:
        log.info(f"✅ Using single subdirectory: {subdirs[0]}")
        return subdirs[0]

    # Check if SRTs are directly under originals/
    srt_files = list(base.glob("*.srt"))
    log.info(
        f"📄 Found SRT files directly under originals: {[f.name for f in srt_files]}"
    )

    if srt_files:
        log.info(
            f"✅ Using originals directory directly (contains {len(srt_files)} SRT files)"
        )
        return base

    log.info("❌ No valid originals structure found")
    return None


def _collect_language_dirs(batch_root: Path) -> List[Path]:
    """Collect language directories that contain SRT files."""
    log = logging.getLogger(__name__)
    log.info(f"🔍 Collecting language directories from: {batch_root}")

    out = []
    for p in batch_root.iterdir():
        if p.is_dir() and p.name not in ("originals", "artifacts", "config"):
            log.info(f"📁 Checking directory: {p.name}")
            srt_count = len(list(p.rglob("*.srt")))
            log.info(f"📄 Found {srt_count} SRT files in {p.name}")
            if srt_count > 0:
                out.append(p)
                log.info(f"✅ Added {p.name} as language directory")

    log.info(f"🎯 Total language directories found: {[d.name for d in out]}")
    return sorted(out)


def _pair_by_contract(
    originals_dir: Path, lang_dir: Path, lang: str
) -> List[Tuple[Path, Path]]:
    """
    Pair files using the naming contract:

    Contract:
    - Source: originals/<base>.srt
    - Target: <lang>/<base> - <LANG_TOKEN>.srt
    - Where LANG_TOKEN = lang.replace("_", "-").upper()

    Examples:
    - es → ES: "File.srt" ↔ "File - ES.srt"
    - zh-Hans → ZH-HANS: "File.srt" ↔ "File - ZH-HANS.srt"
    """
    log = logging.getLogger(__name__)
    log.info(f"🔍 Pairing files using contract for language: {lang}")

    # Calculate the expected language token
    lang_token = lang.replace("_", "-").upper()
    suffix = f" - {lang_token}"
    log.info(f"🔧 Expected suffix: '{suffix}'")

    # Build source map: base_name -> path
    src_files = list(originals_dir.rglob("*.srt"))
    src_map: Dict[str, Path] = {p.stem: p for p in src_files}
    log.info(f"📄 Source files: {[f.name for f in src_files]}")
    log.info(f"🗺️ Source map keys: {list(src_map.keys())}")

    # Find target files and match by contract
    pairs: List[Tuple[Path, Path]] = []
    for tgt in lang_dir.rglob("*.srt"):
        log.info(f"🎯 Processing target: {tgt.name}")

        stem = tgt.stem
        if stem.endswith(suffix):
            base = stem[: -len(suffix)]
            log.info(f"🔍 Target '{stem}' → base '{base}'")

            src = src_map.get(base)
            if src:
                pairs.append((src, tgt))
                log.info(f"✅ Paired: {src.name} ↔ {tgt.name}")
            else:
                log.warning(f"❌ No source found for base '{base}'")
        else:
            log.warning(
                f"❌ Target '{stem}' doesn't end with expected suffix '{suffix}'"
            )

    log.info(f"🎯 Total pairs found: {len(pairs)}")
    return pairs


def _caps_for(lang: str, rubric: dict) -> Tuple[int, int]:
    """
    Get CPS thresholds for a specific language from the rubric.

    Falls back to defaults if language-specific caps are not defined.
    Sanitizes invalid caps (soft >= hard) by using language defaults.
    """
    caps = rubric.get("caps", {})
    per = caps.get("per_language") or {}

    if lang in per:
        soft = int(per[lang]["cps_soft"])
        hard = int(per[lang]["cps_hard"])
        # Validate caps
        if soft >= hard:
            # Use language defaults for invalid caps
            return (12, 15) if lang.lower().startswith("zh") else (15, 20)
        return soft, hard

    # Use global defaults
    d = caps.get("defaults") or {}
    soft = int(d.get("cps_soft", 15))
    hard = int(d.get("cps_hard", 20))

    # Validate defaults
    if soft >= hard:
        return (12, 15) if lang.lower().startswith("zh") else (15, 20)

    return soft, hard


def run_batch_evaluation(batch_root: Path, logger) -> Optional[Dict[str, Any]]:
    """
    Run evaluation on all source/target pairs in a batch.

    Args:
        batch_root: Path to the translation batch directory
        logger: Logger instance for evaluation logging

    Returns:
        Evaluation rollup data, or None if evaluation is skipped

    The batch directory should have this structure:
    - originals/<src_code>/*.srt (source files)
    - <lang>/*.srt (translated files, one folder per language)
    - artifacts/ (will be created)

    File pairing follows the naming contract:
    - Source: originals/<base>.srt
    - Target: <lang>/<base> - <LANG_TOKEN>.srt
    - Where LANG_TOKEN = lang.replace("_", "-").upper()
    """
    log = logger.getChild("runner")

    # Debug logging to see what we're working with
    log.info(f"Starting batch evaluation for: {batch_root}")
    log.info(f"Batch root exists: {batch_root.exists()}")
    log.info(f"Batch root is directory: {batch_root.is_dir()}")
    log.info(f"Batch root contents: {[p.name for p in batch_root.iterdir()]}")

    # Check if rubric exists (config-gated evaluation)
    rubric_file = _rubric_path()
    log.info(f"Looking for rubric at: {rubric_file}")
    log.info(f"Rubric exists: {rubric_file.exists()}")

    if not rubric_file.exists():
        log.info(
            "Evaluation skipped: rubric not found",
            extra={"expected_path": str(rubric_file)},
        )
        return None

    try:
        rubric = yaml.safe_load(rubric_file.read_text(encoding="utf-8"))
        log.info("Successfully loaded rubric")
    except Exception as e:
        log.error(
            "Invalid rubric; evaluation skipped",
            extra={"path": str(rubric_file), "error": str(e)},
        )
        return None

    batch_label = _discover_batch_label(batch_root)
    log.info(f"Discovered batch label: {batch_label}")

    originals_dir = _find_originals_dir(batch_root)
    log.info(f"Found originals directory: {originals_dir}")

    if not originals_dir or not originals_dir.exists():
        log.error(
            "Originals directory not found or ambiguous",
            extra={"batch_root": str(batch_root)},
        )
        return None

    # Create artifacts directory
    artifacts_root = batch_root / "artifacts"
    artifacts_root.mkdir(exist_ok=True)
    log.info(f"Created artifacts directory: {artifacts_root}")

    # Initialize rollup data
    rollup: Dict[str, Any] = {"batch_label": batch_label, "languages": {}}

    # Helper function for evaluating a single pair
    def eval_one(lang: str, src: Path, tgt: Path, out_dir: Path):
        """Evaluate one source/target pair."""
        soft, hard = _caps_for(lang, rubric)

        try:
            res = generate_eval(
                en_path=str(src),
                tgt_path=str(tgt),
                lang=lang,
                batch_label=batch_label,
                out_dir=str(out_dir),
                cps_soft=soft,
                cps_hard=hard,
            )
        except Exception as e:
            log.error(
                "Evaluation failed for pair",
                extra={
                    "lang": lang,
                    "source": str(src),
                    "target": str(tgt),
                    "error": str(e),
                },
            )
            return None, soft, hard

        return res, soft, hard

    # Discover by language directories and contract-based pairing
    for lang_dir in _collect_language_dirs(batch_root):
        lang = lang_dir.name
        log.info(f"🌍 Processing language directory: {lang}")
        log.info(f"📁 Language directory path: {lang_dir.absolute()}")

        out_dir = artifacts_root / lang
        out_dir.mkdir(parents=True, exist_ok=True)
        log.info(f"📁 Created output directory: {out_dir}")

        # Find source/target pairs using the naming contract
        pairs = _pair_by_contract(originals_dir, lang_dir, lang)
        log.info(f"🎯 Found {len(pairs)} pairs for language {lang}")

        if not pairs:
            lang_token = lang.replace("_", "-").upper()
            log.warning(
                f"❌ No pairs found by contract; ensure targets are named '<base> - {lang_token}.srt'",
                extra={
                    "lang": lang,
                    "expected_suffix": f" - {lang_token}",
                    "originals_dir": str(originals_dir),
                    "lang_dir": str(lang_dir),
                },
            )
            rollup["languages"][lang] = {
                "cps_soft": _caps_for(lang, rubric)[0],
                "cps_hard": _caps_for(lang, rubric)[1],
                "files": [],
            }
            continue

        log.info(f"✅ Proceeding with {len(pairs)} pairs for evaluation")

        # Evaluate each pair
        per_files = []
        for src, tgt in pairs:
            log.info(f"🔍 Evaluating pair: {src.name} ↔ {tgt.name}")
            res, soft, hard = eval_one(lang, src, tgt, out_dir)
            if res is None:
                log.warning(f"❌ Evaluation failed for pair: {src.name} ↔ {tgt.name}")
                continue

            log.info(f"✅ Evaluation successful for pair: {src.name} ↔ {tgt.name}")
            per_files.append(
                {
                    "source_file": src.name,
                    "target_file": tgt.name,
                    "status": res.get("verdict"),
                    "notes": ", ".join(res.get("fail_reasons", [])),
                    "artifacts_dir": str(out_dir),
                }
            )

        rollup["languages"][lang] = {
            "cps_soft": soft,
            "cps_hard": hard,
            "files": per_files,
        }
        log.info(
            f"✅ Completed evaluation for {lang}: {len(per_files)} files processed"
        )

    log.info(
        f"Evaluation completed. Languages processed: {list(rollup['languages'].keys())}"
    )
    return rollup
