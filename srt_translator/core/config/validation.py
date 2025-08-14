"""
Custom validation error for configuration validation.
"""

from typing import List


class ConfigValidationError(ValueError):
    """Raised when configuration validation fails with multiple errors."""

    def __init__(self, errors: List[str], warnings: List[str] = None):
        self.errors = errors
        self.warnings = warnings or []

        # Build error message
        error_lines = ["Configuration validation failed:"]
        for error in self.errors:
            error_lines.append(f"  ❌ {error}")

        if self.warnings:
            error_lines.append("")
            error_lines.append("Warnings:")
            for warning in self.warnings:
                error_lines.append(f"  ⚠️  {warning}")

        super().__init__("\n".join(error_lines))

    def __str__(self) -> str:
        return self.args[0]
