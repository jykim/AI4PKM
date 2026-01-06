"""Configuration validator for orchestrator.yaml.

Uses JSON Schema for validation, checking for:
- Missing required fields
- Unknown/unused fields (typos, deprecated fields)
- Type validation
- Enum value validation
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import jsonschema
from jsonschema import Draft202012Validator

from .logger import Logger

logger = Logger()

# Path to the schema file
SCHEMA_PATH = Path(__file__).parent / "schemas" / "orchestrator.schema.json"


class ValidationSeverity(Enum):
    """Severity level for validation issues."""
    ERROR = "error"      # Prevents operation
    WARNING = "warning"  # May cause issues
    INFO = "info"        # Informational only


@dataclass
class ValidationIssue:
    """A single validation issue."""
    severity: ValidationSeverity
    path: str           # Dot-notation path to field (e.g., "nodes[0].executor")
    message: str
    field: Optional[str] = None
    expected: Optional[str] = None
    actual: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of configuration validation."""
    valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)

    def add_error(self, path: str, message: str, **kwargs):
        self.issues.append(ValidationIssue(ValidationSeverity.ERROR, path, message, **kwargs))
        self.valid = False

    def add_warning(self, path: str, message: str, **kwargs):
        self.issues.append(ValidationIssue(ValidationSeverity.WARNING, path, message, **kwargs))

    def add_info(self, path: str, message: str, **kwargs):
        self.issues.append(ValidationIssue(ValidationSeverity.INFO, path, message, **kwargs))

    @property
    def errors(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == ValidationSeverity.ERROR]

    @property
    def warnings(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]

    def summary(self) -> str:
        """Generate human-readable summary."""
        lines = []
        error_count = len(self.errors)
        warning_count = len(self.warnings)

        if self.valid and not self.warnings:
            return "Configuration valid"

        lines.append(f"Validation: {error_count} error(s), {warning_count} warning(s)")

        for issue in self.issues:
            prefix = "ERROR" if issue.severity == ValidationSeverity.ERROR else "WARN"
            lines.append(f"  [{prefix}] {issue.path}: {issue.message}")

        return "\n".join(lines)


def _load_schema() -> Dict[str, Any]:
    """Load the JSON schema from file."""
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _json_path_to_dotpath(path: list) -> str:
    """Convert JSON Schema path (deque) to dot-notation string."""
    if not path:
        return ""

    parts = []
    for item in path:
        if isinstance(item, int):
            # Array index
            if parts:
                parts[-1] = f"{parts[-1]}[{item}]"
            else:
                parts.append(f"[{item}]")
        else:
            parts.append(str(item))

    return ".".join(parts)


def _categorize_error(error: jsonschema.ValidationError) -> ValidationSeverity:
    """Determine severity based on error type."""
    # additionalProperties errors are warnings (unknown fields)
    if error.validator == "additionalProperties":
        return ValidationSeverity.WARNING

    # Type mismatches are warnings (may still work)
    if error.validator == "type":
        return ValidationSeverity.WARNING

    # Required fields and enum errors are errors
    if error.validator in ("required", "enum"):
        return ValidationSeverity.ERROR

    # Default to warning for other validation errors
    return ValidationSeverity.WARNING


def _format_error_message(error: jsonschema.ValidationError) -> str:
    """Format a validation error into a readable message."""
    if error.validator == "additionalProperties":
        # Extract the unknown field name from the error
        if error.message.startswith("Additional properties are not allowed"):
            return f"Unknown field (possible typo or deprecated): {error.message}"
        return error.message

    if error.validator == "required":
        # Extract missing field name
        missing = error.message.replace("'", "").split(" ")[0]
        return f"Missing required field '{missing}'"

    if error.validator == "enum":
        allowed = error.schema.get("enum", [])
        return f"Invalid value '{error.instance}'. Allowed: {allowed}"

    if error.validator == "type":
        expected = error.schema.get("type", "unknown")
        actual = type(error.instance).__name__
        return f"Type mismatch: expected {expected}, got {actual}"

    return error.message


class ConfigValidator:
    """Validates orchestrator.yaml configuration using JSON Schema."""

    def __init__(self):
        """Initialize validator with schema."""
        self._schema = _load_schema()
        self._validator = Draft202012Validator(self._schema)

    def validate(self, config: Dict[str, Any]) -> ValidationResult:
        """
        Validate the entire configuration.

        Args:
            config: Parsed configuration dictionary

        Returns:
            ValidationResult with all issues found
        """
        result = ValidationResult(valid=True)

        if not config:
            result.add_warning("", "Configuration is empty")
            return result

        # Collect all validation errors
        errors = list(self._validator.iter_errors(config))

        for error in errors:
            path = _json_path_to_dotpath(list(error.absolute_path))
            severity = _categorize_error(error)
            message = _format_error_message(error)

            if severity == ValidationSeverity.ERROR:
                result.add_error(path, message)
            elif severity == ValidationSeverity.WARNING:
                result.add_warning(path, message)
            else:
                result.add_info(path, message)

        return result


def validate_config(config: Dict[str, Any]) -> ValidationResult:
    """
    Convenience function to validate configuration.

    Args:
        config: Parsed configuration dictionary

    Returns:
        ValidationResult with all issues found
    """
    validator = ConfigValidator()
    return validator.validate(config)
