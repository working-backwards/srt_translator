#!/usr/bin/env python3
"""
Demonstration of the new standardized output format for SRT Translator.
This script shows how the new artifacts structure works without requiring
a full translation run.
"""

import json
import os
import tempfile
from pathlib import Path

# Add the project root to the path so we can import our modules
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from srt_translator.core.utils.run_summaries import (
    create_dnt_summary,
    create_termbase_summary,
    create_manifest_summary,
    write_run_artifacts,
    get_filtering_rules,
)


def demo_standardized_output():
    """Demonstrate the new standardized output format."""
    print("🚀 SRT Translator - Standardized Output Format Demo")
    print("=" * 60)
    
    # Sample data (similar to what would be in a real translation run)
    sample_dnt_terms = [
        "S-Team",
        "300 milliseconds",  # This will be filtered out
        "API endpoint",
        "500",               # This will be filtered out
        "user authentication"
    ]
    
    sample_termbase = {
        "es": {
            "hello": "hola",
            "world": "mundo",
            "S-Team": "Equipo-S"  # This will conflict with DNT
        },
        "zh-Hans": {
            "hello": "你好",
            "world": "世界",
            "S-Team": "S团队"     # This will conflict with DNT
        }
    }
    
    # Simulate filtering results
    filtered_dnt_terms = ["S-Team", "API endpoint", "user authentication"]
    dnt_filtered_out = ["300 milliseconds (filtered: numeric/number-like)", "500 (filtered: numeric/number-like)"]
    
    filtered_termbase = {
        "es": {"hello": "hola", "world": "mundo"},
        "zh-Hans": {"hello": "你好", "world": "世界"}
    }
    
    collisions_removed = {
        "es": {"filtered_out": ["S-Team"], "reason": "DNT collision"},
        "zh-Hans": {"filtered_out": ["S-Team"], "reason": "DNT collision"}
    }
    
    # Get filtering rules
    filtering_rules = get_filtering_rules()
    
    print(f"\n📋 Sample Data:")
    print(f"  DNT Terms: {len(sample_dnt_terms)} (user provided)")
    print(f"  DNT Terms (filtered): {len(filtered_dnt_terms)} (used in translation)")
    print(f"  DNT Terms (removed): {len(dnt_filtered_out)} (numeric/number-like)")
    print(f"  Termbase: {sum(len(lang) for lang in sample_termbase.values())} total entries")
    print(f"  Termbase (filtered): {sum(len(lang) for lang in filtered_termbase.values())} entries used")
    print(f"  Collisions resolved: {sum(len(lang.get('filtered_out', [])) for lang in collisions_removed.values())}")
    
    # Create temporary directory for demo
    with tempfile.TemporaryDirectory() as temp_dir:
        artifacts_dir = Path(temp_dir) / "artifacts"
        
        print(f"\n📁 Creating artifacts in: {artifacts_dir}")
        
        # Process each language
        for lang_code in ["es", "zh-Hans"]:
            print(f"\n🌐 Processing language: {lang_code}")
            
            # Create DNT summary for this language
            dnt_meta = create_dnt_summary(
                user_terms=sample_dnt_terms,
                filtered_terms=filtered_dnt_terms,
                filtered_out=dnt_filtered_out,
                lang_code=lang_code,
                filtering_rules=filtering_rules
            )
            
            # Create termbase summary for this language
            tb_meta = create_termbase_summary(
                user_termbase=sample_termbase,
                filtered_termbase=filtered_termbase,
                collisions_removed=collisions_removed,
                lang_code=lang_code,
                filtering_rules=filtering_rules
            )
            
            # Create enriched manifest for this language
            lang_manifest = create_manifest_summary(
                version="1.0.0",
                timestamp="20250116_120000-0800",
                mode="GUI",
                source_files=["demo.srt"],
                target_languages=[lang_code],
                summary={"total_files": 1, "successes": 1, "errors": 0},
                processing_summary={
                    "dnt_terms": {"provided": len(sample_dnt_terms), "used": len(filtered_dnt_terms), "filtered": len(dnt_filtered_out)},
                    "termbase": {"provided_entries": sum(len(lang) for lang in sample_termbase.values()), "used_entries": sum(len(lang) for lang in filtered_termbase.values())}
                },
                dnt_meta=dnt_meta,
                tb_meta=tb_meta
            )
            
            # Write all artifacts for this language
            dnt_path, tb_path, manifest_path = write_run_artifacts(
                artifacts_dir=str(artifacts_dir),
                lang_code=lang_code,
                dnt_meta=dnt_meta,
                tb_meta=tb_meta,
                manifest_data=lang_manifest
            )
            
            print(f"  ✅ DNT summary: {os.path.basename(dnt_path)}")
            print(f"  ✅ Termbase summary: {os.path.basename(tb_path)}")
            print(f"  ✅ Manifest: {os.path.basename(manifest_path)}")
        
        # Show the directory structure
        print(f"\n📂 Final Artifacts Directory Structure:")
        print(f"  {artifacts_dir}/")
        for item in sorted(artifacts_dir.rglob("*")):
            if item.is_file():
                rel_path = item.relative_to(artifacts_dir)
                print(f"    📄 {rel_path}")
            elif item.is_dir():
                rel_path = item.relative_to(artifacts_dir)
                print(f"    📁 {rel_path}/")
        
        # Show sample content from one of the files
        print(f"\n📄 Sample Content (DNT Summary for es):")
        sample_file = artifacts_dir / "es" / "dnt_summary.json"
        if sample_file.exists():
            with open(sample_file, 'r', encoding='utf-8') as f:
                content = json.load(f)
                print(json.dumps(content, indent=2, ensure_ascii=False))
        
        print(f"\n🎉 Demo completed! Check the artifacts directory for the full output.")
        print(f"   This demonstrates the new standardized format with:")
        print(f"   - Per-language artifacts directories")
        print(f"   - Consistent JSON structure across all files")
        print(f"   - Language code normalization (zh → zh-Hans)")
        print(f"   - SHA256 hashes for reproducibility")
        print(f"   - Complete filtering metadata and reasons")


if __name__ == "__main__":
    demo_standardized_output()
