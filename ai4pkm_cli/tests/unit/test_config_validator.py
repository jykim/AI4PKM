"""Unit tests for config validator."""
import pytest
from ai4pkm_cli.config_validator import ConfigValidator, validate_config, ValidationSeverity


class TestConfigValidator:
    """Test ConfigValidator class."""

    def test_empty_config(self):
        """Empty config should produce a warning."""
        result = validate_config({})
        assert result.valid is True
        assert len(result.warnings) == 1
        assert "empty" in result.warnings[0].message.lower()

    def test_valid_minimal_config(self):
        """Minimal valid config should pass."""
        config = {
            "version": "1.0",
            "orchestrator": {},
            "defaults": {},
            "nodes": [],
            "pollers": {},
        }
        result = validate_config(config)
        assert result.valid is True
        assert len(result.errors) == 0

    def test_unknown_top_level_field(self):
        """Unknown top-level field should warn."""
        config = {
            "version": "1.0",
            "unknwon_field": "value",  # typo
        }
        result = validate_config(config)
        assert result.valid is True
        assert len(result.warnings) == 1
        assert "unknwon_field" in result.warnings[0].path

    def test_unknown_orchestrator_field(self):
        """Unknown field in orchestrator section should warn."""
        config = {
            "orchestrator": {
                "max_concurrent": 3,
                "poll_intervl": 1.0,  # typo
            }
        }
        result = validate_config(config)
        assert result.valid is True
        assert any("poll_intervl" in w.path for w in result.warnings)

    def test_invalid_executor_enum(self):
        """Invalid executor value should error."""
        config = {
            "defaults": {
                "executor": "invalid_executor",
            }
        }
        result = validate_config(config)
        assert result.valid is False
        assert any("invalid_executor" in e.message for e in result.errors)

    def test_valid_executor_enum(self):
        """Valid executor should pass."""
        config = {
            "defaults": {
                "executor": "gemini_cli",
            }
        }
        result = validate_config(config)
        assert result.valid is True

    def test_node_missing_required_fields(self):
        """Node without required fields should error."""
        config = {
            "nodes": [
                {"output_path": "AI/Output"}  # missing type and name
            ]
        }
        result = validate_config(config)
        assert result.valid is False
        assert any("type" in e.field for e in result.errors)
        assert any("name" in e.field for e in result.errors)

    def test_node_with_required_fields(self):
        """Node with required fields should pass."""
        config = {
            "nodes": [
                {
                    "type": "agent",
                    "name": "Test Agent (TST)",
                    "output_path": "AI/Output",
                }
            ]
        }
        result = validate_config(config)
        assert result.valid is True

    def test_node_unknown_field(self):
        """Unknown field in node should warn."""
        config = {
            "nodes": [
                {
                    "type": "agent",
                    "name": "Test Agent (TST)",
                    "ouput_path": "AI/Output",  # typo
                }
            ]
        }
        result = validate_config(config)
        assert any("ouput_path" in w.path for w in result.warnings)

    def test_node_invalid_output_type(self):
        """Invalid output_type should error."""
        config = {
            "nodes": [
                {
                    "type": "agent",
                    "name": "Test Agent (TST)",
                    "output_type": "invalid_type",
                }
            ]
        }
        result = validate_config(config)
        assert result.valid is False
        assert any("output_type" in e.path for e in result.errors)

    def test_worker_missing_required(self):
        """Worker without executor/label should error."""
        config = {
            "nodes": [
                {
                    "type": "agent",
                    "name": "Test Agent (TST)",
                    "workers": [
                        {"output_path": "path"}  # missing executor and label
                    ]
                }
            ]
        }
        result = validate_config(config)
        assert result.valid is False
        assert any("executor" in e.path for e in result.errors)
        assert any("label" in e.path for e in result.errors)

    def test_worker_valid(self):
        """Valid worker config should pass."""
        config = {
            "nodes": [
                {
                    "type": "agent",
                    "name": "Test Agent (TST)",
                    "workers": [
                        {"executor": "claude_code", "label": "Claude"}
                    ]
                }
            ]
        }
        result = validate_config(config)
        assert result.valid is True

    def test_unknown_poller(self):
        """Unknown poller name should warn."""
        config = {
            "pollers": {
                "unknwon_poller": {
                    "enabled": False,
                }
            }
        }
        result = validate_config(config)
        assert any("unknwon_poller" in w.path for w in result.warnings)

    def test_poller_missing_target_dir_when_enabled(self):
        """Enabled poller without target_dir should error."""
        config = {
            "pollers": {
                "limitless": {
                    "enabled": True,
                    # missing target_dir
                }
            }
        }
        result = validate_config(config)
        assert result.valid is False
        assert any("target_dir" in e.path for e in result.errors)

    def test_poller_valid(self):
        """Valid poller config should pass."""
        config = {
            "pollers": {
                "limitless": {
                    "enabled": True,
                    "target_dir": "Ingest/Limitless",
                    "poll_interval": 3600,
                }
            }
        }
        result = validate_config(config)
        assert result.valid is True

    def test_poller_specific_field_unknown(self):
        """Unknown field specific to a poller should warn."""
        config = {
            "pollers": {
                "limitless": {
                    "enabled": False,
                    "unknwon_field": "value",
                }
            }
        }
        result = validate_config(config)
        assert any("unknwon_field" in w.path for w in result.warnings)

    def test_node_without_abbreviation_warns(self):
        """Node name without (ABBR) and no prompt field should warn."""
        config = {
            "nodes": [
                {
                    "type": "agent",
                    "name": "Test Agent",  # no (TST) suffix
                    # no prompt field
                }
            ]
        }
        result = validate_config(config)
        assert any("ABBR" in w.message for w in result.warnings)

    def test_summary_format(self):
        """Summary should be well-formatted."""
        config = {
            "defaults": {
                "executor": "invalid",
            },
            "unknown_top": "value",
        }
        result = validate_config(config)
        summary = result.summary()
        assert "error" in summary.lower()
        assert "warn" in summary.lower()


class TestValidationResult:
    """Test ValidationResult dataclass."""

    def test_errors_property(self):
        """errors property should filter correctly."""
        from ai4pkm_cli.config_validator import ValidationResult, ValidationIssue

        result = ValidationResult(valid=False)
        result.issues = [
            ValidationIssue(ValidationSeverity.ERROR, "a", "error"),
            ValidationIssue(ValidationSeverity.WARNING, "b", "warning"),
            ValidationIssue(ValidationSeverity.ERROR, "c", "error2"),
        ]
        assert len(result.errors) == 2
        assert len(result.warnings) == 1

    def test_add_error_sets_invalid(self):
        """add_error should set valid to False."""
        from ai4pkm_cli.config_validator import ValidationResult

        result = ValidationResult(valid=True)
        result.add_error("path", "message")
        assert result.valid is False
