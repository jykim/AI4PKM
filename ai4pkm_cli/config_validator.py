"""Configuration validator for orchestrator.yaml.

Validates configuration after reload, checking for:
- Missing required fields
- Unknown/unused fields (typos, deprecated fields)
- Type validation
- Enum value validation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union

from .logger import Logger

logger = Logger()


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


class ConfigValidator:
    """Validates orchestrator.yaml configuration."""

    # Top-level sections
    TOP_LEVEL_FIELDS = {
        "version": {"type": str, "required": False},
        "name": {"type": str, "required": False},          # Vault display name
        "id": {"type": str, "required": False},            # Vault identifier
        "description": {"type": str, "required": False},   # Vault description
        "icon": {"type": str, "required": False},          # Vault icon
        "color": {"type": str, "required": False},         # Vault color
        "orchestrator": {"type": dict, "required": False},
        "defaults": {"type": dict, "required": False},
        "nodes": {"type": list, "required": False},
        "pollers": {"type": dict, "required": False},
    }

    # Orchestrator section fields
    ORCHESTRATOR_FIELDS = {
        # Directory settings
        "prompts_dir": {"type": str, "required": False},
        "tasks_dir": {"type": str, "required": False},
        "logs_dir": {"type": str, "required": False},
        "skills_dir": {"type": str, "required": False},
        "bases_dir": {"type": str, "required": False},
        # Runtime settings
        "max_concurrent": {"type": int, "required": False},
        "poll_interval": {"type": (int, float), "required": False},
        # Voice/Ambient mode settings
        "mode": {"type": str, "required": False},
        "ambient_mode": {"type": bool, "required": False},
        "system_prompt": {"type": str, "required": False},
        "orchestrator_language": {"type": str, "required": False},
        # STT/TTS settings
        "stt_provider": {"type": str, "required": False},
        "stt_language": {"type": str, "required": False},
        "tts_provider": {"type": str, "required": False},
        "mic_gain": {"type": (int, float), "required": False},
        "manual_end_detection": {"type": bool, "required": False},
        # Wakeword settings
        "wakeword_enabled": {"type": bool, "required": False},
        "wakeword_mode": {"type": str, "required": False},
        # Periodic processing settings
        "periodic_processing": {"type": bool, "required": False},
        "periodic_seconds": {"type": int, "required": False},
        "periodic_prompt": {"type": str, "required": False},
    }

    # Defaults section fields
    DEFAULTS_FIELDS = {
        "executor": {"type": str, "required": False, "enum": [
            "claude_code", "gemini_cli", "codex_cli",
            "cursor_agent", "continue_cli", "grok_cli"
        ]},
        "timeout_minutes": {"type": int, "required": False},
        "max_parallel": {"type": int, "required": False},
        "task_create": {"type": bool, "required": False},
        "task_priority": {"type": str, "required": False, "enum": ["low", "medium", "high"]},
        "task_archived": {"type": bool, "required": False},
    }

    # Node (agent) fields
    NODE_FIELDS = {
        "type": {"type": str, "required": True},
        "name": {"type": str, "required": True},
        "enabled": {"type": bool, "required": False},  # Enable/disable agent
        "completion_status": {"type": str, "required": False},  # Agent completion state
        "prompt": {"type": str, "required": False},  # Can be derived from name
        "input_path": {"type": (str, list), "required": False},
        "input_type": {"type": str, "required": False, "enum": [
            "new_file", "updated_file", "daily_file", "manual"
        ]},
        "input_pattern": {"type": str, "required": False},
        "output_path": {"type": str, "required": False},
        "output_type": {"type": str, "required": False, "enum": ["new_file", "update_file", ""]},
        "output_naming": {"type": str, "required": False},
        "cron": {"type": str, "required": False},
        "trigger_exclude_pattern": {"type": str, "required": False},
        "trigger_content_pattern": {"type": str, "required": False},
        "trigger_schedule": {"type": str, "required": False},
        "trigger_wait_for": {"type": (str, list), "required": False},
        "skills": {"type": (str, list), "required": False},
        "mcp_servers": {"type": (str, list), "required": False},
        "executor": {"type": str, "required": False, "enum": [
            "claude_code", "gemini_cli", "codex_cli",
            "cursor_agent", "continue_cli", "grok_cli"
        ]},
        "max_parallel": {"type": int, "required": False},
        "timeout_minutes": {"type": int, "required": False},
        "task_create": {"type": bool, "required": False},
        "task_priority": {"type": str, "required": False, "enum": ["low", "medium", "high"]},
        "task_archived": {"type": bool, "required": False},
        "post_process_action": {"type": str, "required": False},
        "agent_params": {"type": dict, "required": False},
        "log_prefix": {"type": str, "required": False},
        "log_pattern": {"type": str, "required": False},
        "version": {"type": str, "required": False},
        "workers": {"type": list, "required": False},
    }

    # Worker fields (inside nodes.workers)
    WORKER_FIELDS = {
        "executor": {"type": str, "required": True, "enum": [
            "claude_code", "gemini_cli", "codex_cli",
            "cursor_agent", "continue_cli", "grok_cli"
        ]},
        "label": {"type": str, "required": True},
        "output_path": {"type": str, "required": False},
        "agent_params": {"type": dict, "required": False},
    }

    # Poller common fields
    POLLER_COMMON_FIELDS = {
        "enabled": {"type": bool, "required": False},
        "target_dir": {"type": str, "required": False},  # Required if enabled
        "poll_interval": {"type": int, "required": False},
    }

    # Poller-specific fields
    POLLER_SPECIFIC_FIELDS = {
        "apple_photos": {
            "days": {"type": int, "required": False},
            "albums": {"type": list, "required": False},
        },
        "apple_notes": {},
        "gobi": {
            "api_base_url": {"type": str, "required": False},
            "api_key": {"type": str, "required": False},
            "local_timezone": {"type": str, "required": False},
        },
        "gobi_by_tags": {
            "api_base_url": {"type": str, "required": False},
            "api_key": {"type": str, "required": False},
            "admin_api_key": {"type": str, "required": False},
            "local_timezone": {"type": str, "required": False},
            "tags": {"type": (list, str), "required": False},
        },
        "limitless": {
            "start_days_ago": {"type": int, "required": False},
            "local_timezone": {"type": str, "required": False},
            "api_key": {"type": str, "required": False},
        },
    }

    # Known poller names
    KNOWN_POLLERS = {"apple_photos", "apple_notes", "gobi", "gobi_by_tags", "limitless"}

    def __init__(self):
        """Initialize validator."""
        pass

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

        # Validate top-level fields
        self._validate_section(
            config,
            self.TOP_LEVEL_FIELDS,
            "",
            result
        )

        # Validate orchestrator section
        if "orchestrator" in config:
            self._validate_section(
                config["orchestrator"],
                self.ORCHESTRATOR_FIELDS,
                "orchestrator",
                result
            )

        # Validate defaults section
        if "defaults" in config:
            self._validate_section(
                config["defaults"],
                self.DEFAULTS_FIELDS,
                "defaults",
                result
            )

        # Validate nodes
        if "nodes" in config:
            self._validate_nodes(config["nodes"], result)

        # Validate pollers
        if "pollers" in config:
            self._validate_pollers(config["pollers"], result)

        return result

    def _validate_section(
        self,
        section: Dict[str, Any],
        schema: Dict[str, Dict],
        path: str,
        result: ValidationResult
    ) -> None:
        """
        Validate a configuration section against its schema.

        Checks for:
        - Missing required fields
        - Unknown fields
        - Type mismatches
        - Invalid enum values
        """
        if not isinstance(section, dict):
            result.add_error(path, f"Expected dict, got {type(section).__name__}")
            return

        known_fields = set(schema.keys())
        actual_fields = set(section.keys())

        # Check for unknown fields
        unknown = actual_fields - known_fields
        for field_name in unknown:
            field_path = f"{path}.{field_name}" if path else field_name
            result.add_warning(
                field_path,
                f"Unknown field '{field_name}' (possible typo or deprecated)",
                field=field_name
            )

        # Check required and validate types
        for field_name, field_schema in schema.items():
            field_path = f"{path}.{field_name}" if path else field_name

            if field_name not in section:
                if field_schema.get("required"):
                    result.add_error(
                        field_path,
                        f"Missing required field '{field_name}'",
                        field=field_name
                    )
                continue

            value = section[field_name]

            # Type validation
            expected_type = field_schema.get("type")
            if expected_type and value is not None:
                if not isinstance(value, expected_type):
                    result.add_warning(
                        field_path,
                        f"Type mismatch: expected {self._type_name(expected_type)}, got {type(value).__name__}",
                        field=field_name,
                        expected=self._type_name(expected_type),
                        actual=type(value).__name__
                    )

            # Enum validation
            allowed = field_schema.get("enum")
            if allowed and value is not None and value not in allowed:
                result.add_error(
                    field_path,
                    f"Invalid value '{value}'. Allowed: {allowed}",
                    field=field_name,
                    expected=str(allowed),
                    actual=str(value)
                )

    def _validate_nodes(self, nodes: List, result: ValidationResult) -> None:
        """Validate the nodes (agents) list."""
        if not isinstance(nodes, list):
            result.add_error("nodes", f"Expected list, got {type(nodes).__name__}")
            return

        for idx, node in enumerate(nodes):
            path = f"nodes[{idx}]"

            if not isinstance(node, dict):
                result.add_error(path, f"Expected dict, got {type(node).__name__}")
                continue

            # Validate node fields
            self._validate_section(node, self.NODE_FIELDS, path, result)

            # Validate workers if present
            if "workers" in node and node["workers"]:
                self._validate_workers(node["workers"], f"{path}.workers", result)

            # Additional semantic validation
            self._validate_node_semantics(node, path, result)

    def _validate_workers(self, workers: List, path: str, result: ValidationResult) -> None:
        """Validate worker configurations."""
        if not isinstance(workers, list):
            result.add_error(path, f"Expected list, got {type(workers).__name__}")
            return

        for idx, worker in enumerate(workers):
            worker_path = f"{path}[{idx}]"

            if not isinstance(worker, dict):
                result.add_error(worker_path, f"Expected dict, got {type(worker).__name__}")
                continue

            self._validate_section(worker, self.WORKER_FIELDS, worker_path, result)

    def _validate_pollers(self, pollers: Dict[str, Any], result: ValidationResult) -> None:
        """Validate poller configurations."""
        if not isinstance(pollers, dict):
            result.add_error("pollers", f"Expected dict, got {type(pollers).__name__}")
            return

        for name, config in pollers.items():
            path = f"pollers.{name}"

            # Check if poller name is known
            if name not in self.KNOWN_POLLERS:
                result.add_warning(
                    path,
                    f"Unknown poller '{name}' (will be ignored)",
                    field=name
                )
                continue

            if not isinstance(config, dict):
                result.add_error(path, f"Expected dict, got {type(config).__name__}")
                continue

            # Build complete schema for this poller
            poller_schema = {**self.POLLER_COMMON_FIELDS}
            if name in self.POLLER_SPECIFIC_FIELDS:
                poller_schema.update(self.POLLER_SPECIFIC_FIELDS[name])

            # Validate fields
            self._validate_section(config, poller_schema, path, result)

            # Check target_dir required if enabled
            if config.get("enabled") and not config.get("target_dir"):
                result.add_error(
                    f"{path}.target_dir",
                    "target_dir is required when poller is enabled"
                )

    def _validate_node_semantics(self, node: Dict, path: str, result: ValidationResult) -> None:
        """Perform semantic validation on a node."""
        name = node.get("name", "")

        # Check that name has abbreviation OR prompt is specified
        # Accepts: (ABC), (ABCD), (ABC-XYZ), (SPT-CUA) patterns
        import re
        has_abbr = bool(re.search(r'\([A-Z]{3,4}(?:-[A-Z]{2,4})?\)$', name))
        has_prompt = bool(node.get("prompt"))

        if not has_abbr and not has_prompt:
            result.add_warning(
                f"{path}.name",
                f"Node name '{name}' has no (ABBR) suffix and no 'prompt' field"
            )

        # Warn if cron is set but input_type is not daily/manual
        if node.get("cron") and node.get("input_type") not in (None, "daily_file", "manual"):
            result.add_info(
                f"{path}.cron",
                "cron schedule with non-scheduled input_type may cause unexpected behavior"
            )

    def _type_name(self, t: Union[type, tuple]) -> str:
        """Get human-readable type name."""
        if isinstance(t, tuple):
            return " or ".join(x.__name__ for x in t)
        return t.__name__


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
