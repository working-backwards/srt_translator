import os
import shutil
import sys
import tempfile

import pytest

from gui.validation import ConfigurationValidator, ValidationResult

#!/usr/bin/env python3
"""
Test validation functionality
"""


# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestConfigurationValidator:
    """Test cases for ConfigurationValidator class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = ConfigurationValidator()

        # Create temporary source files for testing
        self.temp_dir = tempfile.mkdtemp()
        self.source_files = []

        # Create test files with sample content
        test_content = """
        Welcome to our business course. The CEO will discuss the company's API integration.
        The CFO has prepared the quarterly report. We'll explore modern development practices.
        """

        for i in range(3):
            file_path = os.path.join(self.temp_dir, f"test_file_{i}.srt")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(test_content)
            self.source_files.append(file_path)

    def teardown_method(self):
        """Clean up test fixtures."""
        # Remove temporary files
        for file_path in self.source_files:
            if os.path.exists(file_path):
                os.remove(file_path)
        if os.path.exists(self.temp_dir):
            os.rmdir(self.temp_dir)

    def test_validate_dnt_terms_valid(self):
        """Test validation of DNT terms with valid entries."""
        dnt_terms = ["CEO", "CFO", "API"]
        result = self.validator.validate_dnt_terms(dnt_terms, self.source_files)

        assert result.is_valid == True
        assert result.score == 1.0  # All terms found
        assert len(result.issues) == 0

    def test_validate_dnt_terms_invalid(self):
        """Test validation of DNT terms with invalid entries."""
        dnt_terms = ["CEO", "NONEXISTENT", "MISSING"]
        result = self.validator.validate_dnt_terms(dnt_terms, self.source_files)

        assert result.is_valid == False  # Less than 60% valid
        assert result.score == 1 / 3  # 1 out of 3 entries valid
        assert len(result.issues) >= 2

    def test_validate_dnt_terms_empty(self):
        """Test validation with empty DNT terms."""
        dnt_terms = []
        result = self.validator.validate_dnt_terms(dnt_terms, self.source_files)

        assert result.is_valid == True
        assert result.score == 1.0
        assert result.confidence == 0.5
        assert "No DNT terms to validate" in result.issues[0]

    def test_validate_termbase_valid(self):
        """Test validation of termbase with valid entries."""
        termbase = {
            "Spanish": {"CEO": "CEO", "CFO": "CFO"},
            "French": {"API": "API"},
        }
        result = self.validator.validate_termbase(termbase, self.source_files)

        assert result.is_valid == True
        assert result.score == 1.0  # All terms found
        # Note: Issues will be flagged for identical translations, but score is still 1.0
        assert (
            "CEO" in result.issues[0]
            or "CFO" in result.issues[0]
            or "API" in result.issues[0]
        )

    def test_validate_termbase_invalid(self):
        """Test validation of termbase with invalid entries."""
        termbase = {
            "Spanish": {
                "CEO": "CEO",
                "NONEXISTENT": "",  # Empty translation
                "MISSING": "MISSING",  # Term not in files
            }
        }
        result = self.validator.validate_termbase(termbase, self.source_files)

        assert result.is_valid == False  # Less than 60% valid
        assert result.score == 1 / 3  # 1 out of 3 entries valid
        # Multiple issues: identical translations, missing terms, empty translations
        assert len(result.issues) >= 2

    def test_validate_termbase_empty(self):
        """Test validation with empty termbase."""
        termbase = {}
        result = self.validator.validate_termbase(termbase, self.source_files)

        assert result.is_valid == True
        assert result.score == 1.0
        assert result.confidence == 0.5
        assert "No termbase to validate" in result.issues[0]

    def test_validate_configuration_quality_good(self):
        """Test quality validation with good configuration."""
        dnt_terms = ["CEO", "CFO", "API"]
        termbase = {"Spanish": {"CEO": "CEO"}, "French": {"CFO": "CFO"}}
        result = self.validator.validate_configuration_quality(dnt_terms, termbase)

        assert result.is_valid == True
        assert result.score >= 0.7
        assert len(result.issues) == 0

    def test_validate_configuration_quality_too_many_terms(self):
        """Test quality validation with too many DNT terms."""
        dnt_terms = [f"TERM_{i}" for i in range(60)]  # 60 terms
        termbase = {}
        result = self.validator.validate_configuration_quality(dnt_terms, termbase)

        # Score should be reduced but still valid (0.7 threshold)
        assert result.score == 0.7  # 1.0 - 0.3 penalty
        assert "Too many DNT terms" in result.issues[0]

    def test_validate_configuration_quality_too_few_terms(self):
        """Test quality validation with too few DNT terms."""
        dnt_terms = ["CEO"]  # Only 1 term
        termbase = {}
        result = self.validator.validate_configuration_quality(dnt_terms, termbase)

        # Score should be reduced but still valid (0.8 threshold)
        assert result.score == 0.8  # 1.0 - 0.2 penalty
        assert "Very few DNT terms" in result.issues[0]

    def test_calculate_confidence_score(self):
        """Test confidence score calculation."""
        dnt_result = ValidationResult(
            is_valid=True, score=0.9, issues=[], suggestions=[], confidence=0.9
        )
        termbase_result = ValidationResult(
            is_valid=True, score=0.8, issues=[], suggestions=[], confidence=0.8
        )

        confidence = self.validator.calculate_confidence_score(
            dnt_result, termbase_result
        )

        # Should be weighted average: 0.9 * 0.6 + 0.8 * 0.4 = 0.86
        expected_confidence = 0.9 * 0.6 + 0.8 * 0.4
        assert abs(confidence - expected_confidence) < 0.01

    def test_get_validation_summary(self):
        """Test comprehensive validation summary."""
        dnt_terms = ["CEO", "CFO", "API"]
        termbase = {"Spanish": {"CEO": "CEO"}, "French": {"CFO": "CFO"}}

        summary = self.validator.get_validation_summary(
            dnt_terms, termbase, self.source_files
        )

        # Check overall structure
        assert "overall" in summary
        assert "dnt_terms" in summary
        assert "termbase" in summary
        assert "quality" in summary
        assert "statistics" in summary

        # Check statistics
        stats = summary["statistics"]
        assert stats["dnt_terms_count"] == 3
        assert stats["termbase_languages"] == 2
        assert stats["total_termbase_terms"] == 2
        assert stats["source_files_count"] == 3

        # Check overall status
        overall = summary["overall"]
        assert "is_valid" in overall
        assert "confidence" in overall
        assert "issues" in overall
        assert "suggestions" in overall

    def test_get_validation_summary_empty_config(self):
        """Test validation summary with empty configuration."""
        dnt_terms = []
        termbase = {}

        summary = self.validator.get_validation_summary(
            dnt_terms, termbase, self.source_files
        )

        # Should still return valid structure
        assert "overall" in summary
        assert "dnt_terms" in summary
        assert "termbase" in summary
        assert "quality" in summary
        assert "statistics" in summary

        # Statistics should reflect empty config
        stats = summary["statistics"]
        assert stats["dnt_terms_count"] == 0
        assert stats["termbase_languages"] == 0
        assert stats["total_termbase_terms"] == 0

    def test_get_validation_summary_no_files(self):
        """Test validation summary with no source files."""
        dnt_terms = ["CEO", "CFO"]
        termbase = {}

        summary = self.validator.get_validation_summary(dnt_terms, termbase, [])

        # Should handle empty file list gracefully
        assert "overall" in summary
        assert "statistics" in summary
        assert summary["statistics"]["source_files_count"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
