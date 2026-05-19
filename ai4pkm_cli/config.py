"""Configuration management for AI4PKM CLI (orchestrator.yaml)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, TYPE_CHECKING

import yaml
from .logger import Logger

if TYPE_CHECKING:
    from .config_validator import ValidationResult

logger = Logger()


class Config:
    """Read orchestrator configuration sourced from orchestrator.yaml."""

    def __init__(
        self,
        config_file: Optional[str] = None,
        vault_path: Optional[Path] = None,
    ):
        """
        Initialize configuration loader.

        Args:
            config_file: Explicit path to orchestrator.yaml (overrides vault_path)
            vault_path: Vault directory containing orchestrator.yaml
        """
        if config_file:
            self.config_path = Path(config_file)
        else:
            base_path = Path(vault_path) if vault_path else Path.cwd()
            self.config_path = base_path / "orchestrator.yaml"

        self.config: Dict[str, Any] = self._load_config()

    # --------------------------------------------------------------------- #
    # Internal helpers
    # --------------------------------------------------------------------- #
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge override dict into base dict."""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def _load_config(self) -> Dict[str, Any]:
        """Load orchestrator.yaml and merge with secrets.yaml if present."""
        config_data: Dict[str, Any] = {}

        if self.config_path.exists():
            try:
                with self.config_path.open("r", encoding="utf-8") as fh:
                    loaded = yaml.safe_load(fh) or {}
                    if not isinstance(loaded, dict):
                        logger.warning(
                            "orchestrator.yaml did not contain a mapping; falling back to defaults"
                        )
                    else:
                        config_data = loaded
            except yaml.YAMLError as exc:
                logger.error(f"Failed to parse orchestrator.yaml: {exc}")
            except OSError as exc:
                logger.error(f"Failed to read orchestrator.yaml: {exc}")
        else:
            logger.warning(f"orchestrator.yaml not found at {self.config_path}")

        secrets_path = self.config_path.parent / "secrets.yaml"
        if secrets_path.exists():
            try:
                with secrets_path.open("r", encoding="utf-8") as fh:
                    secrets = yaml.safe_load(fh) or {}
                    if isinstance(secrets, dict):
                        config_data = self._deep_merge(config_data, secrets)
                        logger.debug(f"Loaded secrets from {secrets_path}")
                    else:
                        logger.warning(f"secrets.yaml did not contain a mapping")
            except yaml.YAMLError as exc:
                logger.error(f"Failed to parse secrets.yaml: {exc}")
            except OSError as exc:
                logger.error(f"Failed to read secrets.yaml: {exc}")

        return config_data

    def reload(self, validate: bool = True) -> bool:
        """
        Reload orchestrator.yaml and secrets.yaml from disk.

        Args:
            validate: If True, run validation after reload and log issues

        Returns:
            True if reload succeeded, False otherwise
        """
        try:
            new_config = self._load_config()
            if new_config:
                self.config = new_config
                logger.info(f"Configuration reloaded from {self.config_path}")

                # Run validation if requested
                if validate:
                    result = self.validate()
                    if not result.valid:
                        logger.warning(f"Configuration has validation errors:\n{result.summary()}")
                    elif result.warnings:
                        logger.info(f"Configuration warnings:\n{result.summary()}")

                return True
            else:
                logger.warning("Reload resulted in empty config, keeping existing config")
                return False
        except Exception as e:
            logger.error(f"Failed to reload configuration: {e}", exc_info=True)
            return False

    def validate(self) -> "ValidationResult":
        """
        Validate the current configuration.

        Checks for:
        - Missing required fields
        - Unknown/unused fields (typos, deprecated)
        - Type validation
        - Enum value validation

        Returns:
            ValidationResult with all issues found
        """
        from .config_validator import validate_config
        return validate_config(self.config)

    # --------------------------------------------------------------------- #
    # Public accessors
    # --------------------------------------------------------------------- #
    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a dotted-path value from configuration."""
        if not key:
            return self.config

        value: Any = self.config
        for part in key.split("."):
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default
        return value

    def get_orchestrator_config(self) -> Dict[str, Any]:
        """Get entire orchestrator runtime configuration section."""
        section = self.get("orchestrator", {})
        return section.copy() if isinstance(section, dict) else {}

    def get_orchestrator_prompts_dir(self) -> str:
        """Directory containing agent prompt definitions."""
        return self.get(
            "orchestrator.prompts_dir",
            "_Settings_/Prompts",
        )

    def get_orchestrator_tasks_dir(self) -> str:
        """Directory containing task tracking files."""
        return self.get(
            "orchestrator.tasks_dir",
            "_Settings_/Tasks",
        )

    def get_orchestrator_logs_dir(self) -> str:
        """Directory where orchestrator writes execution logs."""
        return self.get(
            "orchestrator.logs_dir",
            "_Settings_/Logs",
        )

    def get_orchestrator_skills_dir(self) -> str:
        """Directory for orchestrator skills library."""
        return self.get(
            "orchestrator.skills_dir",
            "_Settings_/Skills",
        )

    def get_orchestrator_bases_dir(self) -> str:
        """Directory for orchestrator knowledge bases."""
        return self.get(
            "orchestrator.bases_dir",
            "_Settings_/Bases",
        )

    def get_orchestrator_max_concurrent(self) -> int:
        """Maximum global concurrent executions."""
        return self.get(
            "orchestrator.max_concurrent",
            3,
        )

    def get_orchestrator_poll_interval(self) -> float:
        """Event queue poll interval in seconds."""
        return self.get(
            "orchestrator.poll_interval",
            1.0,
        )

    def get_defaults(self) -> Dict[str, Any]:
        """Global defaults applied to agents."""
        section = self.get("defaults", {})
        return section.copy() if isinstance(section, dict) else {}

    def get_nodes(self) -> Any:
        """Return configured nodes list."""
        nodes = self.get("nodes", [])
        return nodes if isinstance(nodes, list) else []

    def get_pollers_config(self) -> Dict[str, Any]:
        """Get pollers configuration section."""
        section = self.get("pollers", {})
        return section.copy() if isinstance(section, dict) else {}