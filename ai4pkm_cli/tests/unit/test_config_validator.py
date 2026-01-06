"""Tests for config_validator module."""

import pytest

from ai4pkm_cli.config_validator import (
    ConfigValidator,
    ValidationResult,
    ValidationSeverity,
    validate_config,
)


class TestValidationResult:
    """Tests for ValidationResult class."""

    def test_empty_result_is_valid(self):
        result = ValidationResult(valid=True)
        assert result.valid
        assert len(result.issues) == 0

    def test_add_error_makes_invalid(self):
        result = ValidationResult(valid=True)
        result.add_error("test.path", "test error")
        assert not result.valid
        assert len(result.errors) == 1

    def test_add_warning_keeps_valid(self):
        result = ValidationResult(valid=True)
        result.add_warning("test.path", "test warning")
        assert result.valid
        assert len(result.warnings) == 1

    def test_summary_empty(self):
        result = ValidationResult(valid=True)
        assert result.summary() == "Configuration valid"

    def test_summary_with_errors(self):
        result = ValidationResult(valid=True)
        result.add_error("test", "error message")
        summary = result.summary()
        assert "1 error(s)" in summary
        assert "[ERROR]" in summary


class TestConfigValidator:
    """Tests for ConfigValidator class."""

    def test_empty_config(self):
        result = validate_config({})
        assert result.valid
        assert len(result.warnings) == 1
        assert "empty" in result.warnings[0].message.lower()

    def test_valid_minimal_config(self):
        config = {
            "version": "1.0",
            "name": "Test Vault"
        }
        result = validate_config(config)
        assert result.valid
        assert len(result.issues) == 0

    def test_valid_full_config(self):
        config = {
            "version": "1.0",
            "name": "Test Vault",
            "id": "TV",
            "description": "A test vault",
            "orchestrator": {
                "prompts_dir": "_Settings_/Prompts",
                "tasks_dir": "_Settings_/Tasks",
                "max_concurrent": 3,
                "poll_interval": 1.0,
            },
            "defaults": {
                "executor": "claude_code",
                "timeout_minutes": 30,
            },
            "nodes": [
                {
                    "type": "agent",
                    "name": "Test Agent (TA)",
                    "input_path": "Ingest/Test",
                    "output_path": "AI/Test",
                }
            ],
            "pollers": {
                "limitless": {
                    "enabled": True,
                    "target_dir": "Ingest/Limitless",
                    "poll_interval": 3600,
                }
            }
        }
        result = validate_config(config)
        assert result.valid
        assert len(result.errors) == 0


class TestUnknownFields:
    """Tests for unknown field detection."""

    def test_unknown_top_level_field(self):
        config = {"unknown_field": "value"}
        result = validate_config(config)
        assert len(result.warnings) == 1
        assert "unknown_field" in result.warnings[0].message.lower()

    def test_unknown_orchestrator_field(self):
        config = {
            "orchestrator": {"invalid_setting": "value"}
        }
        result = validate_config(config)
        assert len(result.warnings) == 1

    def test_unknown_node_field(self):
        config = {
            "nodes": [
                {"type": "agent", "name": "Test", "invalid_node_field": "value"}
            ]
        }
        result = validate_config(config)
        assert len(result.warnings) == 1


class TestRequiredFields:
    """Tests for required field validation."""

    def test_missing_node_type(self):
        config = {
            "nodes": [{"name": "Missing Type"}]
        }
        result = validate_config(config)
        assert not result.valid
        assert len(result.errors) == 1
        assert "type" in result.errors[0].message.lower()

    def test_missing_node_name(self):
        config = {
            "nodes": [{"type": "agent"}]
        }
        result = validate_config(config)
        assert not result.valid
        assert len(result.errors) == 1
        assert "name" in result.errors[0].message.lower()

    def test_missing_worker_required_fields(self):
        config = {
            "nodes": [
                {
                    "type": "agent",
                    "name": "Test",
                    "workers": [{"output_path": "test"}]  # Missing executor and label
                }
            ]
        }
        result = validate_config(config)
        assert not result.valid
        assert len(result.errors) >= 1


class TestEnumValidation:
    """Tests for enum value validation."""

    def test_invalid_executor(self):
        config = {
            "defaults": {"executor": "invalid_executor"}
        }
        result = validate_config(config)
        assert not result.valid
        assert len(result.errors) == 1
        assert "invalid_executor" in result.errors[0].message

    def test_valid_executor(self):
        config = {
            "defaults": {"executor": "claude_code"}
        }
        result = validate_config(config)
        assert result.valid

    def test_invalid_task_priority(self):
        config = {
            "defaults": {"task_priority": "critical"}  # Not in enum
        }
        result = validate_config(config)
        assert not result.valid

    def test_valid_task_priority(self):
        config = {
            "defaults": {"task_priority": "high"}
        }
        result = validate_config(config)
        assert result.valid

    def test_invalid_input_type(self):
        config = {
            "nodes": [
                {"type": "agent", "name": "Test", "input_type": "invalid_type"}
            ]
        }
        result = validate_config(config)
        assert not result.valid


class TestTypeValidation:
    """Tests for type validation."""

    def test_string_instead_of_int(self):
        config = {
            "orchestrator": {"max_concurrent": "three"}  # Should be int
        }
        result = validate_config(config)
        # Type mismatch is a warning
        assert len(result.warnings) == 1

    def test_string_instead_of_bool(self):
        config = {
            "orchestrator": {"ambient_mode": "yes"}  # Should be bool
        }
        result = validate_config(config)
        assert len(result.warnings) == 1


class TestPollerValidation:
    """Tests for poller configuration validation."""

    def test_valid_limitless_poller(self):
        config = {
            "pollers": {
                "limitless": {
                    "enabled": True,
                    "target_dir": "Ingest/Limitless",
                    "poll_interval": 3600,
                    "start_days_ago": 7,
                }
            }
        }
        result = validate_config(config)
        assert result.valid

    def test_valid_apple_photos_poller(self):
        config = {
            "pollers": {
                "apple_photos": {
                    "enabled": True,
                    "target_dir": "Ingest/Photos",
                    "days": 7,
                    "albums": ["Favorites", "Screenshots"],
                }
            }
        }
        result = validate_config(config)
        assert result.valid

    def test_unknown_poller(self):
        config = {
            "pollers": {
                "unknown_poller": {"enabled": True}
            }
        }
        result = validate_config(config)
        # Unknown poller should be flagged
        assert len(result.warnings) >= 1


class TestArrayFields:
    """Tests for array field validation."""

    def test_input_path_as_string(self):
        config = {
            "nodes": [
                {"type": "agent", "name": "Test", "input_path": "single/path"}
            ]
        }
        result = validate_config(config)
        assert result.valid

    def test_input_path_as_array(self):
        config = {
            "nodes": [
                {"type": "agent", "name": "Test", "input_path": ["path1", "path2"]}
            ]
        }
        result = validate_config(config)
        assert result.valid
