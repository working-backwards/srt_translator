#!/usr/bin/env python3
"""
Test script for the new v1.0 evaluation system with external batches.

This script allows you to test the evaluation system against batches located
outside the repository without adding external paths to the repo.

Usage:
    python test_external_batch.py "C:\\Users\\cbrya\\Projects\\Op Cadence\\translation-batch-20250828_152100_"
    
    Or use forward slashes:
    python test_external_batch.py "C:/Users/cbrya/Projects/Op Cadence/translation-batch-20250828_152100_"
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict

# Add the project root to the path so we can import modules
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from srt_translator.eval.runner import run_batch_evaluation


def setup_logging():
    """Set up logging for the test."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
        ],
    )
    return logging.getLogger("test_external_batch")


def analyze_batch_structure(batch_dir: Path) -> Dict[str, Any]:
    """Analyze the structure of the batch directory."""
    logger = logging.getLogger("analyzer")

    structure = {
        "batch_root": str(batch_dir),
        "exists": batch_dir.exists(),
        "is_dir": batch_dir.is_dir() if batch_dir.exists() else False,
        "contents": [],
        "has_ai_config": False,
        "has_originals": False,
        "target_languages": [],
        "has_log_file": False,
        "log_files": [],
        "srt_files": [],
    }

    if not batch_dir.exists():
        logger.error(f"Batch directory does not exist: {batch_dir}")
        return structure

    if not batch_dir.is_dir():
        logger.error(f"Path is not a directory: {batch_dir}")
        return structure

    # List contents
    try:
        structure["contents"] = [item.name for item in batch_dir.iterdir()]
    except Exception as e:
        logger.error(f"Could not read directory contents: {e}")
        return structure

    # Check for ai_config.json
    ai_config_path = batch_dir / "ai_config.json"
    if ai_config_path.exists():
        structure["has_ai_config"] = True
        try:
            with open(ai_config_path, "r", encoding="utf-8") as f:
                ai_config = json.load(f)
                structure["target_languages"] = ai_config.get("target_languages", [])
                logger.info(
                    f"Found ai_config.json with target languages: {structure['target_languages']}"
                )
        except Exception as e:
            logger.warning(f"Could not read ai_config.json: {e}")

    # Check for originals directory
    originals_dir = batch_dir / "originals"
    if originals_dir.exists() and originals_dir.is_dir():
        structure["has_originals"] = True
        logger.info("Found originals directory")

    # Check for log files
    log_files = list(batch_dir.glob("translation_issues_*.log"))
    if log_files:
        structure["has_log_file"] = True
        structure["log_files"] = [f.name for f in log_files]
        logger.info(f"Found log files: {structure['log_files']}")

    # Check for SRT files and potential language directories
    srt_files = list(batch_dir.rglob("*.srt"))
    structure["srt_files"] = [str(f.relative_to(batch_dir)) for f in srt_files]

    # Try to identify target language directories
    if not structure["target_languages"]:
        potential_langs = []
        for item in batch_dir.iterdir():
            if item.is_dir() and item.name not in ["originals", "artifacts", "config"]:
                # Check if it contains SRT files (likely a language directory)
                lang_srt_files = list(item.glob("*.srt"))
                if lang_srt_files:
                    potential_langs.append(item.name)
                    logger.info(
                        f"Potential language directory: {item.name} with {len(lang_srt_files)} SRT files"
                    )

        if potential_langs:
            structure["target_languages"] = potential_langs
            logger.info(f"Detected potential target languages: {potential_langs}")

    return structure


def test_evaluation_system(batch_dir: Path, logger: logging.Logger):
    """Test the new v1.0 evaluation system against the batch."""
    logger.info(f"Testing evaluation system against: {batch_dir}")

    # Analyze batch structure first
    structure = analyze_batch_structure(batch_dir)
    logger.info("Batch structure analysis:")
    for key, value in structure.items():
        logger.info(f"  {key}: {value}")

    # Check if this batch can be evaluated
    if not structure["exists"]:
        logger.error("Cannot evaluate: batch directory does not exist")
        return False

    if not structure["is_dir"]:
        logger.error("Cannot evaluate: path is not a directory")
        return False

    # Check if batch has required structure
    if not structure["has_originals"]:
        logger.warning("Batch missing originals directory - evaluation may fail")

    if not structure["target_languages"]:
        logger.warning("No target languages detected - evaluation may fail")

    # Try to run evaluation
    try:
        logger.info("Attempting to run batch evaluation...")

        # Run evaluation without any runtime configuration objects
        # The new v1.0 system reads only from batch files on disk
        result = run_batch_evaluation(batch_dir, logger, None)

        if result is None:
            logger.info("Evaluation completed with no result (likely skipped)")
            return True
        else:
            logger.info("Evaluation completed successfully!")
            logger.info(f"Evaluation result keys: {list(result.keys())}")

            # Check for new v1.0 coverage fields
            if "config_source" in result:
                logger.info(f"✓ Config source: {result['config_source']}")
            if "dnt_coverage" in result:
                logger.info(f"✓ DNT coverage: {result['dnt_coverage']}")
            if "termbase_coverage" in result:
                logger.info(f"✓ Termbase coverage: {result['termbase_coverage']}")
            if "termbase_entry_counts" in result:
                logger.info(
                    f"✓ Termbase entry counts: {result['termbase_entry_counts']}"
                )

            return True

    except Exception as e:
        logger.error(f"Evaluation failed with error: {e}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")
        return False


def main():
    """Main test function."""
    if len(sys.argv) != 2:
        print("Usage: python test_external_batch.py <batch_directory_path>")
        print("")
        print("Examples:")
        print(
            '  python test_external_batch.py "C:\\Users\\cbrya\\Projects\\Op Cadence\\translation-batch-20250828_152100_"'
        )
        print(
            '  python test_external_batch.py "C:/Users/cbrya/Projects/Op Cadence/translation-batch-20250828_152100_"'
        )
        print("")
        print("Note: Use double backslashes \\\\ or forward slashes / in Windows paths")
        return 1

    batch_path = Path(sys.argv[1])
    logger = setup_logging()

    logger.info("=" * 60)
    logger.info("Testing New v1.0 Evaluation System")
    logger.info("=" * 60)

    # Test the evaluation system
    success = test_evaluation_system(batch_path, logger)

    logger.info("=" * 60)
    if success:
        logger.info("✓ Test completed successfully!")
    else:
        logger.error("✗ Test failed!")
    logger.info("=" * 60)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
