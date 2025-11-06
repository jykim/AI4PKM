"""
Agent registry for orchestrator.

Loads and manages agent definitions from _Settings_/Agents/.
"""
import logging
import json
import re
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import fnmatch
from croniter import croniter

from .models import AgentDefinition
from ..markdown_utils import read_frontmatter, extract_body

logger = logging.getLogger(__name__)


# JSON Schema for agent definition validation
AGENT_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["title", "abbreviation", "category", "trigger_pattern", "trigger_event"],
    "properties": {
        "title": {"type": "string"},
        "abbreviation": {"type": "string", "pattern": "^[A-Z]{3}$"},
        "category": {"enum": ["ingestion", "publish", "research"]},
        "trigger_pattern": {"type": "string"},
        "trigger_event": {"enum": ["created", "modified", "deleted", "scheduled", "manual"]},
        "executor": {"enum": ["claude_code", "gemini_cli", "custom_script"]},
        "max_parallel": {"type": "integer", "minimum": 1},
        "timeout_minutes": {"type": "integer", "minimum": 1}
    }
}


class AgentRegistry:
    """
    Registry of all available agents.
    
    Loads agent definitions from _Settings_/Agents/ directory.
    """

    def __init__(self, agents_dir: Path, vault_path: Path, config: Optional['Config'] = None):
        """
        Initialize agent registry.

        Args:
            agents_dir: Directory containing agent definition files
            vault_path: Path to vault root
            config: Config instance (will create default if None)
        """
        from ..config import Config

        self.agents_dir = Path(agents_dir)
        self.vault_path = Path(vault_path)
        self.config = config or Config()
        self.agents: Dict[str, AgentDefinition] = {}

        # Load centralized orchestrator configuration
        orchestrator_yaml_path = vault_path / "orchestrator.yaml"
        self.orchestrator_config = self._load_orchestrator_yaml(orchestrator_yaml_path)

        # Extract orchestrator runtime settings from YAML
        self.orchestrator_settings = self.orchestrator_config.get('orchestrator', {})

        self.load_all_agents()

    def load_all_agents(self):
        """
        Load agents from orchestrator.yaml nodes list.

        Agents are loaded based on the 'nodes' list in orchestrator.yaml.
        orchestrator.yaml is the single source of truth for all configuration.
        """
        nodes = self.orchestrator_config.get('nodes', [])

        if not nodes:
            logger.warning("No nodes defined in orchestrator.yaml")
            return

        # Filter for agent nodes
        agent_nodes = [n for n in nodes if n.get('type') == 'agent']
        logger.info(f"Loading {len(agent_nodes)} agents from orchestrator.yaml")

        for node in agent_nodes:
            try:
                # Extract abbreviation from name field: "Name (ABBR)"
                abbr = self._extract_abbreviation(node.get('name', ''))
                if not abbr:
                    logger.warning(f"Cannot extract abbreviation from: {node.get('name')}")
                    continue

                # Find prompt file by abbreviation
                agent_file = self._find_agent_prompt_file(abbr)

                if agent_file:
                    agent = self._load_agent(agent_file, node)
                    if agent:
                        self.agents[agent.abbreviation] = agent
                        logger.info(f"Loaded agent: {agent.abbreviation} ({agent.name})")
                else:
                    logger.warning(f"No prompt file found for agent: {abbr}")
            except Exception as e:
                logger.error(f"Error loading agent from node: {e}")

        logger.info(f"Total agents loaded: {len(self.agents)}")

    def _find_agent_prompt_file(self, abbreviation: str) -> Optional[Path]:
        """
        Find the prompt file for an agent by abbreviation.

        Searches for files matching the pattern "*({ABBR}).md" in the agents directory.

        Args:
            abbreviation: Agent abbreviation (e.g., "EIC", "HTC")

        Returns:
            Path to prompt file, or None if not found
        """
        if not self.agents_dir.exists():
            return None

        # Pattern: "*({ABBR}).md"
        pattern = f"*({abbreviation}).md"

        matching_files = list(self.agents_dir.glob(pattern))

        if not matching_files:
            logger.debug(f"No prompt file found matching pattern: {pattern}")
            return None

        if len(matching_files) > 1:
            logger.warning(f"Multiple prompt files found for {abbreviation}: {matching_files}")
            logger.warning(f"Using first match: {matching_files[0]}")

        return matching_files[0]

    def _extract_abbreviation(self, name: str) -> Optional[str]:
        """
        Extract abbreviation from agent name.

        Expects format: "Full Name (ABBR)"

        Args:
            name: Agent name string

        Returns:
            Abbreviation string, or None if not found
        """
        match = re.search(r'\(([A-Z]{3,4})\)$', name)
        return match.group(1) if match else None

    def _load_orchestrator_yaml(self, yaml_path: Path) -> dict:
        """
        Load centralized orchestrator configuration from YAML file.

        Args:
            yaml_path: Path to orchestrator.yaml file

        Returns:
            Dictionary with 'agents' and 'defaults' keys
        """
        if not yaml_path.exists():
            logger.warning(f"orchestrator.yaml not found at {yaml_path}")
            logger.warning("Agent input/output configuration will not be available")
            return {'agents': {}, 'defaults': {}}

        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            if not config:
                logger.warning(f"Empty orchestrator.yaml at {yaml_path}")
                return {'agents': {}, 'defaults': {}}

            logger.info(f"Loaded orchestrator configuration from {yaml_path}")
            logger.info(f"  Agents configured: {len(config.get('agents', {}))}")

            return config
        except Exception as e:
            logger.error(f"Failed to load orchestrator.yaml: {e}")
            return {'agents': {}, 'defaults': {}}

    def _load_agent(self, file_path: Path, node: dict) -> Optional[AgentDefinition]:
        """
        Load a single agent definition from file and node config.

        Args:
            file_path: Path to agent prompt file
            node: Node configuration from orchestrator.yaml

        Returns:
            AgentDefinition instance or None if invalid
        """
        frontmatter = read_frontmatter(file_path)
        if not frontmatter:
            logger.warning(f"No frontmatter found in {file_path}")
            return None

        # Only validate basic metadata from frontmatter
        # All configuration comes from orchestrator.yaml node
        required = ['title', 'abbreviation', 'category']
        for field in required:
            if field not in frontmatter:
                logger.error(f"Missing required field '{field}' in {file_path}")
                return None

        # Extract prompt body
        prompt_body = extract_body(file_path.read_text(encoding='utf-8'))

        # Get defaults from orchestrator config
        defaults = self.orchestrator_config.get('defaults', {})

        # Extract input_path from node config (orchestrator.yaml only source)
        input_path = node.get('input_path', [])

        # Handle null input_path (for manual agents)
        if input_path is None or input_path == 'null':
            input_path = []
        elif isinstance(input_path, str):
            input_path = [input_path] if input_path else []

        # Get input/output types from node config with defaults
        # Infer input_type if not specified
        input_type = node.get('input_type')
        if not input_type:
            # Infer from input_path: empty = manual, otherwise = new_file
            input_type = 'manual' if not input_path else 'new_file'

        output_path = node.get('output_path', '')
        output_type = node.get('output_type', 'new_file')

        # Validate output_type
        valid_output_types = ['new_file', 'update_file', '']
        if output_type and output_type not in valid_output_types:
            logger.error(
                f"Invalid output_type '{output_type}' for agent {frontmatter.get('abbreviation', 'unknown')} "
                f"in {file_path}. Valid types: {valid_output_types}"
            )
            logger.warning(f"Defaulting to 'new_file' for agent {frontmatter.get('abbreviation', 'unknown')}")
            output_type = 'new_file'

        input_pattern = node.get('input_pattern')

        # Derive trigger_pattern and trigger_event
        trigger_pattern, trigger_event = self._derive_trigger_from_input(
            input_path,
            input_type,
            input_pattern
        )

        # Get skills and mcp_servers from node (if specified)
        skills = node.get('skills', [])
        if isinstance(skills, str):
            skills = [skills]

        mcp_servers = node.get('mcp_servers', [])
        if isinstance(mcp_servers, str):
            mcp_servers = [mcp_servers]

        trigger_wait_for = node.get('trigger_wait_for', [])
        if isinstance(trigger_wait_for, str):
            trigger_wait_for = [trigger_wait_for]

        # Extract cron expression from node config
        cron = node.get('cron')

        # Apply node config with defaults (orchestrator.yaml is only source)
        executor = node.get('executor', defaults.get('executor', 'claude_code'))
        max_parallel = int(node.get('max_parallel', defaults.get('max_parallel', 1)))
        timeout_minutes = int(node.get('timeout_minutes', defaults.get('timeout_minutes', 30)))
        task_create = node.get('task_create', defaults.get('task_create', True))
        task_priority = node.get('task_priority', defaults.get('task_priority', 'medium'))
        task_archived = node.get('task_archived', defaults.get('task_archived', False))

        # Infer output_optional: if no input_path, output is optional
        # This means scheduled/manual agents can complete without producing output
        output_optional = not bool(input_path)  # True when input_path is empty

        # Get agent_params from node (explicit YAML property)
        agent_params = node.get('agent_params', {})

        agent = AgentDefinition(
            name=frontmatter['title'],
            abbreviation=frontmatter['abbreviation'],
            category=frontmatter['category'],
            trigger_pattern=trigger_pattern,
            trigger_event=trigger_event,
            trigger_exclude_pattern=node.get('trigger_exclude_pattern'),
            trigger_content_pattern=node.get('trigger_content_pattern'),
            trigger_schedule=node.get('trigger_schedule'),
            trigger_wait_for=trigger_wait_for,
            cron=cron,
            input_path=input_path,
            input_type=input_type,
            output_path=output_path,
            output_type=output_type,
            output_optional=output_optional,
            output_naming=node.get('output_naming', '{title} - {agent}.md'),
            prompt_body=prompt_body,
            skills=skills,
            mcp_servers=mcp_servers,
            executor=executor,
            max_parallel=max_parallel,
            timeout_minutes=timeout_minutes,
            log_prefix=node.get('log_prefix', frontmatter['abbreviation']),
            log_pattern=node.get('log_pattern', '{timestamp}-{agent}.log'),
            post_process_action=node.get('post_process_action'),
            task_create=task_create,
            task_priority=task_priority,
            task_archived=task_archived,
            file_path=file_path,
            version=node.get('version', '1.0'),
            agent_params=agent_params
        )

        return agent

    def _derive_trigger_from_input(self, input_paths: List[str], input_type: str, input_pattern: Optional[str] = None) -> tuple:
        """
        Derive trigger_pattern and trigger_event from input_path and input_type.

        Args:
            input_paths: List of input paths (relative to vault root)
            input_type: Type of input (new_file, updated_file, daily_file, manual)
            input_pattern: Optional custom file pattern (e.g., "*.{jpg,png}")

        Returns:
            Tuple of (trigger_pattern, trigger_event)
        """
        # Map input_type to trigger_event
        event_mapping = {
            'new_file': 'created',
            'updated_file': 'modified',
            'daily_file': 'scheduled',
            'manual': 'manual'
        }
        trigger_event = event_mapping.get(input_type, 'created')

        # Handle manual agents - they should never match file events
        if input_type == 'manual':
            trigger_pattern = None  # No file pattern for manual agents
            logger.debug(f"Manual agent: no file trigger (input_type={input_type})")
            return trigger_pattern, trigger_event

        # Build trigger_pattern
        if not input_paths or (len(input_paths) == 1 and input_paths[0] == ""):
            # Empty input_path means watch entire vault (e.g., HTC)
            trigger_pattern = "**/*.md"
            logger.debug(f"Vault-wide trigger pattern: {trigger_pattern}")
        else:
            # Directory-specific trigger
            first_path = input_paths[0].rstrip('/')  # Remove trailing slash

            # Use custom input_pattern if specified
            if input_pattern:
                # Extract file extensions if provided
                trigger_pattern = f"{first_path}/{input_pattern}"
            else:
                # Default to *.md for text files
                trigger_pattern = f"{first_path}/*.md"

        logger.debug(f"Derived trigger: pattern='{trigger_pattern}', event='{trigger_event}' from input_paths={input_paths}, input_type={input_type}")

        return trigger_pattern, trigger_event

    def find_matching_agents(self, event_data: Dict) -> List[AgentDefinition]:
        """
        Find agents whose triggers match the event.

        Args:
            event_data: Event dictionary with path, event_type, etc.

        Returns:
            List of matching AgentDefinition instances
        """
        matching = []
        event_path = event_data.get('path', '')
        event_type = event_data.get('event_type', '')
        
        for agent in self.agents.values():
            if self._matches_trigger(agent, event_path, event_type):
                matching.append(agent)

        return matching

    def _matches_trigger(self, agent: AgentDefinition, event_path: str, event_type: str) -> bool:
        """
        Check if event matches agent's trigger conditions.

        Args:
            agent: AgentDefinition to check
            event_path: File path from event (may be empty for scheduled events)
            event_type: Event type (created, modified, deleted, scheduled)

        Returns:
            True if event matches agent's trigger
        """
        # Handle scheduled events (cron-based)
        if event_type == 'scheduled':
            # Only match if agent has cron and current time matches the schedule
            if agent.cron is None:
                return False

            try:
                now = datetime.now()
                cron = croniter(agent.cron, now)
                prev_run = cron.get_prev(datetime)

                # If the previous run time is within the last minute, this agent should trigger
                time_diff = (now - prev_run).total_seconds()
                return 0 <= time_diff < 60
            except Exception as e:
                logger.error(f"Error validating cron schedule for {agent.abbreviation}: {e}")
                return False

        # Manual agents never match file events
        if agent.trigger_pattern is None or agent.trigger_event == 'manual':
            return False

        # Check event type matches
        if agent.trigger_event != event_type:
            return False

        # Check pattern matches
        if not fnmatch.fnmatch(event_path, agent.trigger_pattern):
            return False

        # Check exclusion pattern if specified
        if agent.trigger_exclude_pattern:
            # Support multiple patterns separated by |
            exclude_patterns = agent.trigger_exclude_pattern.split('|')
            for pattern in exclude_patterns:
                if fnmatch.fnmatch(event_path, pattern.strip()):
                    return False

        # Check content pattern if specified
        if agent.trigger_content_pattern:
            if not self._check_content_pattern(event_path, agent.trigger_content_pattern):
                return False

            # Check for existing task to avoid duplication
            if self._has_existing_task(event_path):
                logger.debug(f"Skipping {event_path} - task already exists")
                return False

        return True

    def _check_content_pattern(self, event_path: str, pattern: str) -> bool:
        """
        Check if file content matches the pattern.

        Args:
            event_path: Relative file path from event
            pattern: Regex pattern to match in file content

        Returns:
            True if pattern found in file content
        """
        try:
            # Convert to absolute path
            file_path = self.vault_path / event_path
            if not file_path.exists():
                return False

            content = file_path.read_text(encoding='utf-8')

            # Apply pattern (case-insensitive)
            return bool(re.search(pattern, content, re.IGNORECASE | re.MULTILINE))

        except Exception as e:
            logger.error(f"Error reading file {event_path}: {e}")
            return False

    def _has_existing_task(self, event_path: str) -> bool:
        """
        Check if a task already exists for this file in tasks directory.

        Args:
            event_path: Relative file path from event

        Returns:
            True if task file already exists
        """
        try:
            # Get tasks directory from config
            tasks_dir_path = self.config.get_orchestrator_tasks_dir()
            tasks_dir = self.vault_path / tasks_dir_path
            if not tasks_dir.exists():
                return False

            # Extract filename without extension
            source_filename = Path(event_path).stem

            # Search for task files containing the source filename
            # Format: YYYY-MM-DD {agent} - {source_filename}.md
            for task_file in tasks_dir.glob("*.md"):
                if source_filename in task_file.stem:
                    logger.debug(f"Found existing task: {task_file.name}")
                    return True

            return False

        except Exception as e:
            logger.error(f"Error checking for existing task: {e}")
            return False

    def export_config_snapshot(self, output_path: Path):
        """
        Export current agent configurations to JSON for debugging.

        Args:
            output_path: Path to output JSON file
        """
        config = {}
        
        for abbr, agent in self.agents.items():
            config[abbr] = {
                'name': agent.name,
                'category': agent.category,
                'trigger_pattern': agent.trigger_pattern,
                'trigger_event': agent.trigger_event,
                'executor': agent.executor,
                'skills': agent.skills,
                'mcp_servers': agent.mcp_servers,
                'file_path': str(agent.file_path) if agent.file_path else None
            }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(config, indent=2), encoding='utf-8')
        logger.info(f"Agent configuration snapshot saved to {output_path}")

    def get_orchestrator_setting(self, key: str, default=None):
        """
        Get orchestrator runtime setting from YAML config.

        Args:
            key: Setting key (e.g., 'tasks_dir', 'max_concurrent')
            default: Default value if not found

        Returns:
            Setting value or default
        """
        return self.orchestrator_settings.get(key, default)
