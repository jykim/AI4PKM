"""Unit tests for orchestrator data models."""
import pytest
from datetime import datetime
from pathlib import Path
from ai4pkm_cli.orchestrator.models import AgentDefinition, ExecutionContext, TriggerEvent


def test_agent_definition_minimal():
    """Test AgentDefinition with minimal required fields."""
    agent = AgentDefinition(
        name="Test Agent",
        abbreviation="TST",
        category="ingestion",
        trigger_pattern="test/*.md",
        trigger_event="created"
    )
    
    assert agent.name == "Test Agent"
    assert agent.max_parallel == 1
    assert agent.executor == "claude_code"


def test_execution_context_duration():
    """Test ExecutionContext duration calculation."""
    context = ExecutionContext()
    context.start_time = datetime(2025, 10, 25, 10, 0, 0)
    context.end_time = datetime(2025, 10, 25, 10, 5, 30)
    
    assert context.duration == 330.0


def test_execution_context_success():
    """Test ExecutionContext success property."""
    context = ExecutionContext()
    assert context.success is False

    # Success requires status == 'completed' and no error
    context.status = 'completed'
    assert context.success is True

    # With error, it's not successful
    context.error_message = "Some error"
    assert context.success is False


def test_trigger_event_creation():
    """Test TriggerEvent creation."""
    event = TriggerEvent(
        path="test.md",
        event_type="created",
        is_directory=False,
        timestamp=datetime.now()
    )
    
    assert event.path == "test.md"
    assert event.frontmatter == {}
