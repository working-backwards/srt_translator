import os
import sys
import tempfile
import shutil
import pytest
from gui.validation import ConfigurationValidator, ValidationResult

#!/usr/bin/env python3
"""
Test validation functionality
"""


# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))



class TestConfigurationValidator:
    """Test the ConfigurationValidator class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = ConfigurationValidator()

        # Create temporary test files
        self.temp_dir = tempfile.mkdtemp()
        self.test_file1 = os.path.join(self.temp_dir, "test1.srt")
        self.test_file2 = os.path.join(self.temp_dir, "test2.srt")

        # Write test content
        with open(self.test_file1, "w", encoding="utf-8") as f:
            f.write(
                "Welcome to our business course. The CEO will discuss the company's API integration."
            )

        with open(self.test_file2, "w", encoding="utf-8") as f:
            f.write(
                "The CFO has prepared the quarterly report with Amazon Web Services."
            )

        self.source_files = [self.test_file1, self.test_file2]

    def teardown_method(self):
        """Clean up test fixtures."""

        shutil.rmtree(self.temp_dir)

    def test_validate_dnt_terms_valid(self):
        """Test validation of DNT terms that exist in files."""
        dnt_terms = ["CEO", "CFO", "API"]
        result = self.validator.validate_dnt_terms(
            dnt_terms, self.source_files
        )
        assert result.is_valid == True
        assert result.score == 1.0
        assert len(result.issues) == 0

    def test_validate_dnt_terms_invalid(self):
        """Test validation of DNT terms that don't exist in files."""
        dnt_terms = ["CEO", "CFO", "NONEXISTENT", "MISSING"]
        result = self.validator.validate_dnt_terms(
            dnt_terms, self.source_files
        )
        assert result.is_valid == False
        assert result.score < 1.0
        assert len(result.issues) > 0

    def test_validate_dnt_terms_empty(self):
        """Test validation with no DNT terms."""
        dnt_terms = []
        result = self.validator.validate_dnt_terms(
            dnt_terms, self.source_files
        )
        assert result.is_valid == True
        assert result.score == 1.0
        assert "No DNT terms to validate" in result.issues[0]

    def test_validate_business_glossary_valid(self):
        """Test validation of business glossary with valid entries."""
        business_glossary = {
            "Spanish": {"CEO": "CEO", "CFO": "CFO"},
            "French": {"API": "API"},
        }
        result = self.validator.validate_business_glossary(
            business_glossary, self.source_files
        )

        assert result.is_valid == True
        assert result.score == 1.0  # All terms found
        # Note: Issues will be flagged for identical translations, but score is still 1.0
        assert (
            "CEO" in result.issues[0]
            or "CFO" in result.issues[0]
            or "API" in result.issues[0]
        )

    def test_validate_business_glossary_invalid(self):
        """Test validation of business glossary with invalid entries."""
        business_glossary = {
            "Spanish": {
                "CEO": "CEO",
                "NONEXISTENT": "",  # Empty translation
                "MISSING": "MISSING",  # Term not in files
            }
        }
        result = self.validator.validate_business_glossary(
            business_glossary, self.source_files
        )

        assert result.is_valid == False  # Less than 60% valid
        assert result.score == 1 / 3  # 1 out of 3 entries valid
        # Multiple issues: identical translations, missing terms, empty translations
        assert len(result.issues) >= 2

    def test_validate_business_glossary_empty(self):
        """Test validation with empty business glossary."""
        business_glossary = {}
        result = self.validator.validate_business_glossary(
            business_glossary, self.source_files
        )

        assert result.is_valid == True
        assert result.score == 1.0
        assert result.confidence == 0.5
        assert "No business glossary to validate" in result.issues[0]

    def test_validate_configuration_quality_good(self):
        """Test quality validation with good configuration."""
        dnt_terms = ["CEO", "CFO", "API"]
        business_glossary = {"Spanish": {"CEO": "CEO"}, "French": {"CFO": "CFO"}}
        result = self.validator.validate_configuration_quality(
            dnt_terms, business_glossary
        )

        assert result.is_valid == True
        assert result.score >= 0.7
        assert len(result.issues) == 0

    def test_validate_configuration_quality_too_many_terms(self):
        """Test quality validation with too many DNT terms."""
        dnt_terms = [f"TERM_{i}" for i in range(60)]  # 60 terms
        business_glossary = {}
        result = self.validator.validate_configuration_quality(
            dnt_terms, business_glossary
        )

        # Score should be reduced but still valid (0.7 threshold)
        assert result.score == 0.7  # 1.0 - 0.3 penalty
        assert "Too many DNT terms" in result.issues[0]

    def test_validate_configuration_quality_too_few_terms(self):
        """Test quality validation with too few DNT terms."""
        dnt_terms = ["CEO"]  # Only 1 term
        business_glossary = {}
        result = self.validator.validate_configuration_quality(
            dnt_terms, business_glossary
        )

        # Score should be reduced but still valid (0.8 threshold)
        assert result.score == 0.8  # 1.0 - 0.2 penalty
        assert "Very few DNT terms" in result.issues[0]

    def test_calculate_confidence_score(self):
        """Test confidence score calculation."""
        dnt_result = ValidationResult(
            is_valid=True, score=0.9, issues=[], suggestions=[], confidence=0.9
        )
        glossary_result = ValidationResult(
            is_valid=True, score=0.8, issues=[], suggestions=[], confidence=0.8
        )

        confidence = self.validator.calculate_confidence_score(
            dnt_result, glossary_result
        )

        # Should be weighted average: 0.9 * 0.6 + 0.8 * 0.4 = 0.86
        expected_confidence = 0.9 * 0.6 + 0.8 * 0.4
        assert abs(confidence - expected_confidence) < 0.01

    def test_get_validation_summary(self):
        """Test comprehensive validation summary."""
        dnt_terms = ["CEO", "CFO", "API"]
        business_glossary = {"Spanish": {"CEO": "CEO"}, "French": {"CFO": "CFO"}}

        summary = self.validator.get_validation_summary(
            dnt_terms, business_glossary, self.source_files
        )

        assert "overall_valid" in summary
        assert "overall_confidence" in summary
        assert "dnt_terms" in summary
        assert "business_glossary" in summary
        assert "quality" in summary
        assert "statistics" in summary

        # Check statistics
        stats = summary["statistics"]
        assert stats["dnt_terms_count"] == 3
        assert stats["glossary_languages"] == 2
        assert stats["total_glossary_terms"] == 2
        assert stats["source_files_count"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
