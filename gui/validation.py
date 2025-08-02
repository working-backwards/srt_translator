#!/usr/bin/env python3
"""
Validation and Quality Checks for AI Configuration

Provides validation for:
- Term existence in source files
- Configuration quality metrics
- Confidence scoring
- Data integrity checks
"""

import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class ValidationResult:
    """Result of a validation check."""

    is_valid: bool
    score: float  # 0.0 to 1.0
    issues: List[str]
    suggestions: List[str]
    confidence: float  # 0.0 to 1.0


@dataclass
class TermValidationResult:
    """Result of term validation."""

    term: str
    found_in_files: List[str]
    occurrence_count: int
    is_valid: bool
    confidence: float


class ConfigurationValidator:
    """Validates AI-generated configuration for quality and accuracy."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def validate_dnt_terms(
        self, dnt_terms: List[str], source_files: List[str]
    ) -> ValidationResult:
        """Validate that DNT terms actually exist in the source files."""
        issues = []
        suggestions = []
        valid_terms = 0
        total_terms = len(dnt_terms)

        if total_terms == 0:
            return ValidationResult(
                is_valid=True,
                score=1.0,
                issues=["No DNT terms to validate"],
                suggestions=[
                    "Consider adding some DNT terms for better translation control"
                ],
                confidence=0.5,
            )

        # Check each term
        for term in dnt_terms:
            term_found = False
            for file_path in source_files:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read().lower()
                        if term.lower() in content:
                            term_found = True
                            break
                except Exception as e:
                    self.logger.warning(f"Could not read file {file_path}: {e}")

            if term_found:
                valid_terms += 1
            else:
                issues.append(f"Term '{term}' not found in any source files")
                suggestions.append(f"Remove '{term}' or add it to your content")

        # Calculate scores
        validity_score = valid_terms / total_terms if total_terms > 0 else 0.0
        confidence = min(
            validity_score + 0.2, 1.0
        )  # Boost confidence if most terms are valid

        is_valid = validity_score >= 0.7  # At least 70% of terms should be found

        return ValidationResult(
            is_valid=is_valid,
            score=validity_score,
            issues=issues,
            suggestions=suggestions,
            confidence=confidence,
        )

    def validate_business_glossary(
        self, business_glossary: Dict[str, Dict[str, str]], source_files: List[str]
    ) -> ValidationResult:
        """Validate business glossary entries."""
        issues = []
        suggestions = []
        valid_entries = 0
        total_entries = 0

        if not business_glossary:
            return ValidationResult(
                is_valid=True,
                score=1.0,
                issues=["No business glossary to validate"],
                suggestions=[
                    "Consider adding a business glossary for better translation consistency"
                ],
                confidence=0.5,
            )

        # Check each language and term
        for language, terms in business_glossary.items():
            for english_term, translation in terms.items():
                total_entries += 1

                # Check if English term exists in source files
                term_found = False
                for file_path in source_files:
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read().lower()
                            if english_term.lower() in content:
                                term_found = True
                                break
                    except Exception as e:
                        self.logger.warning(f"Could not read file {file_path}: {e}")

                if term_found:
                    valid_entries += 1
                else:
                    issues.append(
                        f"Glossary term '{english_term}' not found in source files"
                    )
                    suggestions.append(
                        f"Remove '{english_term}' from {language} glossary or add it to your content"
                    )

                # Check translation quality
                if not translation or translation.strip() == "":
                    issues.append(
                        f"Empty translation for '{english_term}' in {language}"
                    )
                    suggestions.append(
                        f"Provide a translation for '{english_term}' in {language}"
                    )
                elif translation.lower() == english_term.lower():
                    issues.append(
                        f"Translation '{translation}' is identical to English term '{english_term}' in {language}"
                    )
                    suggestions.append(
                        f"Consider providing a proper translation for '{english_term}' in {language}"
                    )

        # Calculate scores
        validity_score = valid_entries / total_entries if total_entries > 0 else 0.0
        confidence = min(validity_score + 0.1, 1.0)

        is_valid = validity_score >= 0.6  # At least 60% of entries should be valid

        return ValidationResult(
            is_valid=is_valid,
            score=validity_score,
            issues=issues,
            suggestions=suggestions,
            confidence=confidence,
        )

    def validate_dnt_terms(
        self, dnt_terms: List[str], source_files: List[str]
    ) -> ValidationResult:
        """
        Validate that DNT terms exist in source files

        Args:
            dnt_terms: List of DNT terms to validate
            source_files: List of source file paths

        Returns:
            ValidationResult with validation status and issues
        """
        if not dnt_terms:
            return ValidationResult(
                is_valid=True,
                score=1.0,
                issues=["No DNT terms to validate"],
                suggestions=[
                    "Consider adding some DNT terms for better translation control"
                ],
                confidence=0.5,
            )

        total_terms = len(dnt_terms)
        found_terms = []
        missing_terms = []

        # Read all source files
        all_content = ""
        for file_path in source_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    all_content += f.read() + " "
            except Exception as e:
                self.logger.warning(f"Could not read file {file_path}: {e}")

        # Check each term
        for term in dnt_terms:
            if term in all_content:
                found_terms.append(term)
            else:
                missing_terms.append(term)

        # Calculate confidence based on found vs missing terms
        if total_terms == 0:
            confidence = 1.0
        else:
            confidence = len(found_terms) / total_terms

        # Generate issues
        issues = []
        if missing_terms:
            issues.append(
                f"Missing DNT terms in source files: {', '.join(missing_terms)}"
            )

        if not found_terms and total_terms > 0:
            issues.append("No DNT terms found in any source files")

        return ValidationResult(
            is_valid=len(missing_terms) == 0,
            score=confidence,
            issues=issues,
            suggestions=["Consider adding some DNT terms for better translation control"],
            confidence=confidence,
        )

    def calculate_confidence_score(
        self, dnt_terms_result: ValidationResult, glossary_result: ValidationResult
    ) -> float:
        """Calculate overall confidence score for the configuration."""
        # Weight the scores (DNT terms are more important)
        dnt_weight = 0.6
        glossary_weight = 0.4

        weighted_score = (
            dnt_terms_result.confidence * dnt_weight
            + glossary_result.confidence * glossary_weight
        )

        return min(weighted_score, 1.0)

    def validate_configuration_quality(
        self, dnt_terms: List[str], business_glossary: Dict[str, Dict[str, str]]
    ) -> ValidationResult:
        """Validate overall configuration quality."""
        issues = []
        suggestions = []

        # Check for reasonable number of terms
        if len(dnt_terms) > 50:
            issues.append(
                "Too many DNT terms (50+) may impact translation quality"
            )
            suggestions.append(
                "Consider reducing DNT terms to the most important ones"
            )

        if len(dnt_terms) < 3:
            issues.append("Very few DNT terms may not provide enough control")
            suggestions.append(
                "Consider adding more important terms to exclude from translation"
            )

        # Check glossary coverage
        total_glossary_terms = sum(len(terms) for terms in business_glossary.values())
        if total_glossary_terms > 100:
            issues.append("Large glossary (100+ terms) may be difficult to maintain")
            suggestions.append("Consider focusing on the most important business terms")

        # Check for common patterns
        for term in dnt_terms:
            if len(term) < 2:
                issues.append(f"Very short term '{term}' may cause over-exclusion")
                suggestions.append(
                    f"Consider removing '{term}' or making it more specific"
                )

        # Calculate quality score
        quality_score = 1.0
        if len(dnt_terms) > 50:
            quality_score -= 0.3
        if len(dnt_terms) < 3:
            quality_score -= 0.2
        if total_glossary_terms > 100:
            quality_score -= 0.2

        quality_score = max(0.0, quality_score)

        return ValidationResult(
            is_valid=quality_score >= 0.7,
            score=quality_score,
            issues=issues,
            suggestions=suggestions,
            confidence=quality_score,
        )

    def get_validation_summary(
        self,
        dnt_terms: List[str],
        business_glossary: Dict[str, Dict[str, str]],
        source_files: List[str],
    ) -> Dict[str, any]:
        """Get comprehensive validation summary."""

        # Run all validations
        dnt_validation = self.validate_dnt_terms(dnt_terms, source_files)
        glossary_validation = self.validate_business_glossary(
            business_glossary, source_files
        )
        quality_validation = self.validate_configuration_quality(
            dnt_terms, business_glossary
        )

        # Calculate overall confidence
        overall_confidence = self.calculate_confidence_score(
            dnt_validation, glossary_validation
        )

        # Determine overall status
        all_valid = (
            dnt_validation.is_valid
            and glossary_validation.is_valid
            and quality_validation.is_valid
        )

        return {
            "overall_valid": all_valid,
            "overall_confidence": overall_confidence,
            "dnt_terms": {
                "valid": dnt_validation.is_valid,
                "score": dnt_validation.score,
                "confidence": dnt_validation.confidence,
                "issues": dnt_validation.issues,
                "suggestions": dnt_validation.suggestions,
            },
            "business_glossary": {
                "valid": glossary_validation.is_valid,
                "score": glossary_validation.score,
                "confidence": glossary_validation.confidence,
                "issues": glossary_validation.issues,
                "suggestions": glossary_validation.suggestions,
            },
            "quality": {
                "valid": quality_validation.is_valid,
                "score": quality_validation.score,
                "confidence": quality_validation.confidence,
                "issues": quality_validation.issues,
                "suggestions": quality_validation.suggestions,
            },
            "statistics": {
                "dnt_terms_count": len(dnt_terms),
                "glossary_languages": len(business_glossary),
                "total_glossary_terms": sum(
                    len(terms) for terms in business_glossary.values()
                ),
                "source_files_count": len(source_files),
            },
        }
