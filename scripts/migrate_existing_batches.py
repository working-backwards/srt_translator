#!/usr/bin/env python3
"""
Migration script for existing translation batches to work with the new evaluation system.

This script helps migrate existing batches that don't have ai_config.json files
to work with the new v1.0 evaluation policy.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Any

# Add the project root to the path so we can import modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from srt_translator.core.config.models import TranslationConfig
from srt_translator.core.config.language_config import LanguageConfig


def setup_logging():
    """Set up logging for the migration script."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('migration.log', encoding='utf-8')
        ]
    )
    return logging.getLogger(__name__)


def detect_batch_structure(batch_dir: Path) -> Dict[str, Any]:
    """Detect the structure of an existing batch directory."""
    logger = logging.getLogger(__name__)
    
    structure = {
        "batch_root": batch_dir,
        "has_originals": False,
        "has_targets": False,
        "target_languages": [],
        "has_ai_config": False,
        "has_legacy_files": False
    }
    
    # Check for ai_config.json
    ai_config_path = batch_dir / "ai_config.json"
    if ai_config_path.exists():
        structure["has_ai_config"] = True
        try:
            with open(ai_config_path, 'r', encoding='utf-8') as f:
                ai_config = json.load(f)
                structure["target_languages"] = ai_config.get("target_languages", [])
        except Exception as e:
            logger.warning(f"Could not read ai_config.json: {e}")
    
    # Check for originals directory
    originals_dir = batch_dir / "originals"
    if originals_dir.exists() and originals_dir.is_dir():
        structure["has_originals"] = True
    
    # Check for target language directories
    target_dirs = []
    for item in batch_dir.iterdir():
        if item.is_dir() and item.name not in ["originals", "artifacts"]:
            # Check if it contains SRT files (likely a language directory)
            srt_files = list(item.glob("*.srt"))
            if srt_files:
                target_dirs.append(item.name)
                structure["has_targets"] = True
    
    if not structure["target_languages"] and target_dirs:
        structure["target_languages"] = target_dirs
    
    # Check for legacy files (dnt_summary.json, termbase_summary.json)
    legacy_files = []
    for lang_dir in target_dirs:
        lang_path = batch_dir / lang_dir
        if (lang_path / "dnt_summary.json").exists():
            legacy_files.append(f"{lang_dir}/dnt_summary.json")
        if (lang_path / "termbase_summary.json").exists():
            legacy_files.append(f"{lang_dir}/termbase_summary.json")
    
    if legacy_files:
        structure["has_legacy_files"] = True
        structure["legacy_files"] = legacy_files
    
    return structure


def create_ai_config_from_legacy(batch_dir: Path, structure: Dict[str, Any]) -> Dict[str, Any]:
    """Create ai_config.json from legacy files and batch structure."""
    logger = logging.getLogger(__name__)
    
    ai_config = {
        "version": "1.0.0",
        "timestamp": "2025-01-01T00:00:00Z",  # Placeholder timestamp
        "target_languages": structure["target_languages"],
        "dnt_terms": [],
        "termbase": {}
    }
    
    # Try to extract DNT terms from legacy files
    dnt_terms = set()
    for lang in structure["target_languages"]:
        dnt_path = batch_dir / lang / "dnt_summary.json"
        if dnt_path.exists():
            try:
                with open(dnt_path, 'r', encoding='utf-8') as f:
                    dnt_data = json.load(f)
                    if "terms" in dnt_data:
                        dnt_terms.update(dnt_data["terms"])
            except Exception as e:
                logger.warning(f"Could not read DNT file for {lang}: {e}")
    
    ai_config["dnt_terms"] = list(dnt_terms)
    
    # Try to extract termbase from legacy files
    for lang in structure["target_languages"]:
        tb_path = batch_dir / lang / "termbase_summary.json"
        if tb_path.exists():
            try:
                with open(tb_path, 'r', encoding='utf-8') as f:
                    tb_data = json.load(f)
                    if "entries" in tb_data:
                        # Convert to the new format
                        termbase_entries = {}
                        for entry in tb_data["entries"]:
                            if isinstance(entry, dict) and "source" in entry and "target" in entry:
                                termbase_entries[entry["source"]] = entry["target"]
                        ai_config["termbase"][lang] = termbase_entries
            except Exception as e:
                logger.warning(f"Could not read termbase file for {lang}: {e}")
    
    return ai_config


def migrate_batch(batch_dir: Path, logger: logging.Logger) -> bool:
    """Migrate a single batch directory."""
    logger.info(f"Migrating batch: {batch_dir.name}")
    
    # Detect batch structure
    structure = detect_batch_structure(batch_dir)
    logger.info(f"Batch structure: {structure}")
    
    # If already has ai_config.json, skip
    if structure["has_ai_config"]:
        logger.info("Batch already has ai_config.json, skipping")
        return True
    
    # Create ai_config.json
    ai_config = create_ai_config_from_legacy(batch_dir, structure)
    
    # Write ai_config.json
    ai_config_path = batch_dir / "ai_config.json"
    try:
        with open(ai_config_path, 'w', encoding='utf-8') as f:
            json.dump(ai_config, f, indent=2, ensure_ascii=False)
        logger.info(f"Created ai_config.json: {ai_config_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to create ai_config.json: {e}")
        return False


def main():
    """Main migration function."""
    logger = setup_logging()
    logger.info("Starting batch migration")
    
    # Find all batch directories
    translated_dir = Path("translated_srt_files")
    if not translated_dir.exists():
        logger.error("translated_srt_files directory not found")
        return 1
    
    batch_dirs = [d for d in translated_dir.iterdir() 
                  if d.is_dir() and d.name.startswith("translation-batch-")]
    
    if not batch_dirs:
        logger.info("No batch directories found")
        return 0
    
    logger.info(f"Found {len(batch_dirs)} batch directories")
    
    # Migrate each batch
    success_count = 0
    for batch_dir in batch_dirs:
        try:
            if migrate_batch(batch_dir, logger):
                success_count += 1
        except Exception as e:
            logger.error(f"Failed to migrate {batch_dir.name}: {e}")
    
    logger.info(f"Migration complete: {success_count}/{len(batch_dirs)} batches migrated successfully")
    return 0 if success_count == len(batch_dirs) else 1


if __name__ == "__main__":
    sys.exit(main())
