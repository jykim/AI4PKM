"""
Data models for orchestrator components.
"""
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any
import uuid


@dataclass
class AgentDefinition:
    """Represents a loaded agent definition."""
    # Basic identity
    name: str
    abbreviation: str
    category: str  # ingestion, publish, research

    # Trigger specification
    trigger_pattern: str
    trigger_event: str
    trigger_exclude_pattern: Optional[str] = None
    trigger_content_pattern: Optional[str] = None  # Regex pattern to match in file content
    trigger_schedule: Optional[str] = None
    trigger_wait_for: List[str] = field(default_factory=list)

    # Input/output
    input_path: List[str] = field(default_factory=list)
    cron: Optional[str] = None  # Cron expression for scheduled triggers
    input_type: str = "new_file"
    output_path: str = ""
    output_type: str = "new_file"
    output_naming: str = "{title} - {agent}.md"

    # Execution
    prompt_body: str = ""
    skills: List[str] = field(default_factory=list)
    mcp_servers: List[str] = field(default_factory=list)
    executor: str = "claude_code"
    max_parallel: int = 1
    timeout_minutes: int = 30

    # Post-processing
    post_process_action: Optional[str] = None  # e.g., "remove_trigger_content"

    # Logging
    log_prefix: str = ""
    log_pattern: str = "{timestamp}-{agent}.log"

    # Task file configuration
    task_create: bool = True  # Whether to create task tracking files
    task_priority: str = "medium"  # low, medium, high
    task_archived: bool = False  # Default archived status

    # Metadata
    file_path: Optional[Path] = None
    version: str = "1.0"
    last_updated: Optional[datetime] = None


@dataclass
class ExecutionContext:
    """Context for a single agent execution."""
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent: Optional[AgentDefinition] = None
    trigger_data: Dict[str, Any] = field(default_factory=dict)

    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    # Execution results
    status: str = "pending"  # pending, completed, failed, timeout
    prompt: Optional[str] = None
    error_message: Optional[str] = None
    response: Optional[str] = None

    # File paths
    log_file: Optional[Path] = None
    task_file: Optional[Path] = None  # Path to task tracking file in AI/Tasks/

    @property
    def duration(self) -> Optional[float]:
        """Execution duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    @property
    def success(self) -> bool:
        """Whether execution succeeded."""
        return self.status == "completed" and self.error_message is None


@dataclass
class TriggerEvent:
    """Represents a trigger event (file system or scheduled)."""
    path: str
    event_type: str  # created, modified, deleted, scheduled
    is_directory: bool
    timestamp: datetime
    frontmatter: Dict[str, Any] = field(default_factory=dict)
