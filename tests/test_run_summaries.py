#!/usr/bin/env python3
"""
Tests for run summaries utilities.
"""

import json
import logging
import tempfile
import unittest
from pathlib import Path

from srt_translator.core.utils.run_summaries import (
    create_dnt_summary,
    create_termbase_summary,
    create_manifest_summary,
    write_run_artifacts,
    normalize_language_code,
    hash_content,
    get_filtering_rules,
)

# Set up logging for tests
logging.basicConfig(level=logging.INFO)


class TestRunSummaries(unittest.TestCase):
    """Test cases for run summaries utilities."""

    def test_normalize_language_code(self):
        """Test language code normalization."""
        # Test common normalizations
        self.assertEqual(normalize_language_code("zh"), "zh-Hans")
        self.assertEqual(normalize_language_code("pt"), "pt-BR")
        self.assertEqual(normalize_language_code("en"), "en-US")
        
        # Test already normalized codes
        self.assertEqual(normalize_language_code("es"), "es")
        self.assertEqual(normalize_language_code("zh-Hans"), "zh-Hans")
        self.assertEqual(normalize_language_code("pt-BR"), "pt-BR")
        
        # Test case insensitivity
        self.assertEqual(normalize_language_code("ZH"), "zh-Hans")
        self.assertEqual(normalize_language_code("Pt"), "pt-BR")

    def test_hash_content(self):
        """Test content hashing functionality."""
        # Test list hashing
        test_list = ["term1", "term2", "term3"]
        hash1 = hash_content(test_list)
        self.assertIsInstance(hash1, str)
        self.assertEqual(len(hash1), 64)  # SHA256 hex length
        
        # Test dict hashing (should be consistent regardless of key order)
        test_dict1 = {"a": 1, "b": 2, "c": 3}
        test_dict2 = {"c": 3, "a": 1, "b": 2}
        hash1 = hash_content(test_dict1)
        hash2 = hash_content(test_dict2)
        self.assertEqual(hash1, hash2)  # Should be same hash for same content
        
        # Test string hashing
        test_string = "test content"
        hash_string = hash_content(test_string)
        self.assertIsInstance(hash_string, str)
        self.assertEqual(len(hash_string), 64)

    def test_get_filtering_rules(self):
        """Test filtering rules configuration."""
        rules = get_filtering_rules()
        expected_keys = ["numeric_filter", "dnt_precedence", "relevant_only_tb", "tb_cap", "tolerant_match"]
        
        for key in expected_keys:
            self.assertIn(key, rules)
        
        self.assertTrue(rules["numeric_filter"])
        self.assertTrue(rules["dnt_precedence"])
        self.assertTrue(rules["relevant_only_tb"])
        self.assertEqual(rules["tb_cap"], 30)

    def test_create_dnt_summary(self):
        """Test DNT summary creation."""
        user_terms = ["term1", "300 milliseconds", "term2", "500"]
        filtered_terms = ["term1", "term2"]
        filtered_out = ["300 milliseconds (filtered: numeric/number-like)", "500 (filtered: numeric/number-like)"]
        lang_code = "zh"
        filtering_rules = get_filtering_rules()
        
        summary = create_dnt_summary(user_terms, filtered_terms, filtered_out, lang_code, filtering_rules)
        
        # Check structure
        self.assertIn("description", summary)
        self.assertIn("lang", summary)
        self.assertIn("timestamp", summary)
        self.assertIn("user_provided", summary)
        self.assertIn("filtered_for_translation", summary)
        
        # Check language normalization
        self.assertEqual(summary["lang"], "zh-Hans")
        
        # Check user provided data
        self.assertEqual(summary["user_provided"]["count"], 4)
        self.assertEqual(summary["user_provided"]["terms"], user_terms)
        self.assertIn("sha256", summary["user_provided"])
        
        # Check filtered data
        self.assertEqual(summary["filtered_for_translation"]["count"], 2)
        self.assertEqual(summary["filtered_for_translation"]["terms"], filtered_terms)
        self.assertEqual(summary["filtered_for_translation"]["filtered_out"], filtered_out)
        self.assertEqual(summary["filtered_for_translation"]["filters"], filtering_rules)

    def test_create_termbase_summary(self):
        """Test termbase summary creation."""
        user_termbase = {
            "es": {"hello": "hola", "world": "mundo"},
            "zh": {"hello": "你好", "world": "世界"}
        }
        filtered_termbase = {
            "es": {"hello": "hola"},
            "zh": {"hello": "你好"}
        }
        collisions_removed = {
            "es": {"filtered_out": ["world"], "reason": "DNT collision"},
            "zh": {"filtered_out": ["world"], "reason": "DNT collision"}
        }
        lang_code = "zh"
        filtering_rules = get_filtering_rules()
        
        summary = create_termbase_summary(user_termbase, filtered_termbase, collisions_removed, lang_code, filtering_rules)
        
        # Check structure
        self.assertIn("description", summary)
        self.assertIn("lang", summary)
        self.assertIn("timestamp", summary)
        self.assertIn("user_provided", summary)
        self.assertIn("filtered_for_translation", summary)
        
        # Check language normalization
        self.assertEqual(summary["lang"], "zh-Hans")
        
        # Check user provided data
        self.assertEqual(summary["user_provided"]["total_entries"], 4)
        self.assertEqual(summary["user_provided"]["entry_counts"]["es"], 2)
        self.assertEqual(summary["user_provided"]["entry_counts"]["zh"], 2)
        self.assertIn("sha256", summary["user_provided"])
        
        # Check filtered data
        self.assertEqual(summary["filtered_for_translation"]["total_entries"], 2)
        self.assertEqual(summary["filtered_for_translation"]["entry_counts"]["es"], 1)
        self.assertEqual(summary["filtered_for_translation"]["entry_counts"]["zh"], 1)
        self.assertEqual(summary["filtered_for_translation"]["collisions_removed"], collisions_removed)
        self.assertEqual(summary["filtered_for_translation"]["filters"], filtering_rules)

    def test_create_manifest_summary(self):
        """Test manifest summary creation."""
        version = "1.0.0"
        timestamp = "20250116_120000-0800"
        mode = "GUI"
        source_files = ["test.srt"]
        target_languages = ["zh", "es"]
        summary = {"total_files": 1, "successes": 1}
        processing_summary = {"dnt_terms": {"provided": 2, "used": 1}}
        
        # Create sample metadata
        dnt_meta = create_dnt_summary(
            ["term1", "300"], ["term1"], ["300 (filtered: numeric/number-like)"], "zh", get_filtering_rules()
        )
        tb_meta = create_termbase_summary(
            {"zh": {"hello": "你好"}}, {"zh": {"hello": "你好"}}, {}, "zh", get_filtering_rules()
        )
        
        manifest = create_manifest_summary(
            version, timestamp, mode, source_files, target_languages, summary, processing_summary, dnt_meta, tb_meta
        )
        
        # Check structure
        self.assertEqual(manifest["version"], version)
        self.assertEqual(manifest["timestamp"], timestamp)
        self.assertEqual(manifest["mode"], mode)
        self.assertEqual(manifest["source_files"], source_files)
        
        # Check language normalization
        self.assertEqual(manifest["target_languages"], ["zh-Hans", "es"])
        
        # Check artifacts section
        self.assertIn("artifacts", manifest)
        self.assertIn("dnt_terms", manifest["artifacts"])
        self.assertIn("termbase", manifest["artifacts"])
        self.assertIn("quality_improvements", manifest["artifacts"])
        self.assertIn("filters", manifest["artifacts"])

    def test_write_run_artifacts(self):
        """Test writing run artifacts to filesystem."""
        with tempfile.TemporaryDirectory() as temp_dir:
            artifacts_dir = Path(temp_dir) / "artifacts"
            
            # Create sample metadata
            dnt_meta = create_dnt_summary(
                ["term1", "300"], ["term1"], ["300 (filtered: numeric/number-like)"], "zh", get_filtering_rules()
            )
            tb_meta = create_termbase_summary(
                {"zh": {"hello": "你好"}}, {"zh": {"hello": "你好"}}, {}, "zh", get_filtering_rules()
            )
            manifest_data = create_manifest_summary(
                "1.0.0", "20250116_120000-0800", "GUI", ["test.srt"], ["zh"], 
                {"total_files": 1}, {"dnt_terms": {"provided": 2, "used": 1}}, 
                dnt_meta, tb_meta
            )
            
            # Write artifacts
            dnt_path, tb_path, manifest_path = write_run_artifacts(
                str(artifacts_dir), "zh", dnt_meta, tb_meta, manifest_data
            )
            
            # Check files were created
            self.assertTrue(Path(dnt_path).exists())
            self.assertTrue(Path(tb_path).exists())
            self.assertTrue(Path(manifest_path).exists())
            
            # Check directory structure
            lang_dir = artifacts_dir / "zh-Hans"
            self.assertTrue(lang_dir.exists())
            
            # Check file contents
            with open(dnt_path, 'r', encoding='utf-8') as f:
                dnt_content = json.load(f)
                self.assertEqual(dnt_content["lang"], "zh-Hans")
            
            with open(tb_path, 'r', encoding='utf-8') as f:
                tb_content = json.load(f)
                self.assertEqual(tb_content["lang"], "zh-Hans")
            
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest_content = json.load(f)
                self.assertEqual(manifest_content["target_languages"], ["zh-Hans"])


if __name__ == "__main__":
    unittest.main()
