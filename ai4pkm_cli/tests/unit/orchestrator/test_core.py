"""Unit tests for orchestrator core.py"""

import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import pytest

from ai4pkm_cli.orchestrator.core import Orchestrator
from ai4pkm_cli.orchestrator.models import AgentDefinition, TriggerEvent


class TestOrchestrator:
    """Test orchestrator core functionality."""

    @pytest.fixture
    def temp_vault(self):
        """Create temporary vault with agents directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir)
            agents_dir = vault_path / "_Settings_" / "Agents"
            agents_dir.mkdir(parents=True)
            yield vault_path, agents_dir

    @pytest.fixture
    def sample_agent_file(self, temp_vault):
        """Create a sample agent definition file."""
        vault_path, agents_dir = temp_vault

        agent_content = """---
title: "Test Agent"
abbreviation: "TST"
category: "ingestion"
trigger_pattern: "Ingest/Clippings/*.md"
trigger_event: "created"
input_path: "Ingest/Clippings"
input_type: "new_file"
---

Test prompt body
"""
        agent_file = agents_dir / "Test Agent.md"
        agent_file.write_text(agent_content, encoding='utf-8')

        return vault_path, agents_dir

    def test_init(self, temp_vault):
        """Test orchestrator initialization."""
        vault_path, agents_dir = temp_vault

        orch = Orchestrator(vault_path, agents_dir, max_concurrent=5)

        assert orch.vault_path == vault_path
        assert orch.agents_dir == agents_dir
        assert orch.max_concurrent == 5
        assert orch._running is False
        assert orch.agent_registry is not None
        assert orch.execution_manager is not None
        assert orch.file_monitor is not None

    def test_init_with_agents_loaded(self, sample_agent_file):
        """Test orchestrator loads agents on init."""
        vault_path, agents_dir = sample_agent_file

        orch = Orchestrator(vault_path, agents_dir)

        assert len(orch.agent_registry.agents) == 1
        assert "TST" in orch.agent_registry.agents

    def test_start_stop(self, temp_vault):
        """Test orchestrator start and stop."""
        vault_path, agents_dir = temp_vault

        orch = Orchestrator(vault_path, agents_dir)

        # Initially not running
        assert orch._running is False

        # Start
        orch.start()
        assert orch._running is True
        assert orch._event_thread is not None

        # Stop
        orch.stop()
        assert orch._running is False

    def test_start_when_already_running(self, temp_vault):
        """Test starting orchestrator when already running."""
        vault_path, agents_dir = temp_vault

        orch = Orchestrator(vault_path, agents_dir)
        orch.start()

        # Try to start again (should log warning but not error)
        orch.start()

        assert orch._running is True
        orch.stop()

    def test_stop_when_not_running(self, temp_vault):
        """Test stopping orchestrator when not running."""
        vault_path, agents_dir = temp_vault

        orch = Orchestrator(vault_path, agents_dir)

        # Stop without starting (should log warning but not error)
        orch.stop()

        assert orch._running is False

    @patch('ai4pkm_cli.orchestrator.core.ExecutionManager.execute')
    @patch('ai4pkm_cli.orchestrator.core.ExecutionManager.can_execute')
    def test_process_event_with_matching_agent(self, mock_can_execute, mock_execute, sample_agent_file):
        """Test processing event with matching agent."""
        vault_path, agents_dir = sample_agent_file

        # Setup mocks
        mock_can_execute.return_value = True
        mock_ctx = Mock()
        mock_ctx.success = True
        mock_ctx.duration = 1.5
        mock_execute.return_value = mock_ctx

        orch = Orchestrator(vault_path, agents_dir)

        # Create event that matches agent pattern
        trigger_event = TriggerEvent(
            path="Ingest/Clippings/test.md",
            event_type="created",
            is_directory=False,
            timestamp=datetime.now(),
            frontmatter={}
        )

        # Process event
        orch._process_event(trigger_event)

        # Give thread time to execute
        time.sleep(0.1)

        # Verify execution was attempted
        assert mock_can_execute.called
        # Note: mock_execute might be called in a thread, so we can't reliably check it synchronously

    def test_process_event_no_matching_agent(self, temp_vault):
        """Test processing event with no matching agents."""
        vault_path, agents_dir = temp_vault

        orch = Orchestrator(vault_path, agents_dir)

        # Create event that doesn't match any pattern
        trigger_event = TriggerEvent(
            path="Random/path/file.md",
            event_type="created",
            is_directory=False,
            timestamp=datetime.now(),
            frontmatter={}
        )

        # Process event (should not raise error)
        orch._process_event(trigger_event)

    @patch('ai4pkm_cli.orchestrator.core.ExecutionManager.can_execute')
    def test_process_event_concurrency_limit_reached(self, mock_can_execute, sample_agent_file):
        """Test event processing when concurrency limit is reached."""
        vault_path, agents_dir = sample_agent_file

        # Mock concurrency limit reached
        mock_can_execute.return_value = False

        orch = Orchestrator(vault_path, agents_dir)

        trigger_event = TriggerEvent(
            path="Ingest/Clippings/test.md",
            event_type="created",
            is_directory=False,
            timestamp=datetime.now(),
            frontmatter={}
        )

        # Process event (should log warning but not error)
        orch._process_event(trigger_event)

        assert mock_can_execute.called

    def test_get_status(self, sample_agent_file):
        """Test getting orchestrator status."""
        vault_path, agents_dir = sample_agent_file

        orch = Orchestrator(vault_path, agents_dir, max_concurrent=5)

        status = orch.get_status()

        assert status['running'] is False
        assert status['vault_path'] == str(vault_path)
        assert status['agents_loaded'] == 1
        assert status['running_executions'] == 0
        assert status['max_concurrent'] == 5
        assert len(status['agent_list']) == 1
        assert status['agent_list'][0]['abbreviation'] == 'TST'

    def test_get_status_when_running(self, temp_vault):
        """Test status when orchestrator is running."""
        vault_path, agents_dir = temp_vault

        orch = Orchestrator(vault_path, agents_dir)
        orch.start()

        status = orch.get_status()

        assert status['running'] is True

        orch.stop()

    def test_event_loop_stops_when_running_false(self, temp_vault):
        """Test event loop stops when _running is set to False."""
        vault_path, agents_dir = temp_vault

        orch = Orchestrator(vault_path, agents_dir, poll_interval=0.1)
        orch.start()

        # Let it run briefly
        time.sleep(0.2)

        # Stop it
        orch.stop()

        # Give time for thread to finish
        time.sleep(0.2)

        # Event thread should have stopped
        assert not orch._event_thread.is_alive()

    @patch('ai4pkm_cli.orchestrator.core.ExecutionManager.execute')
    def test_execute_agent_success(self, mock_execute, temp_vault):
        """Test successful agent execution."""
        vault_path, agents_dir = temp_vault

        mock_ctx = Mock()
        mock_ctx.success = True
        mock_ctx.duration = 2.0
        mock_execute.return_value = mock_ctx

        orch = Orchestrator(vault_path, agents_dir)

        agent = AgentDefinition(
            name="Test",
            abbreviation="TST",
            category="ingestion",
            trigger_pattern="*.md",
            trigger_event="created",
            prompt_body="Test"
        )

        event_data = {'path': 'test.md', 'event_type': 'created'}

        # Execute (should not raise error)
        orch._execute_agent(agent, event_data)

        assert mock_execute.called

    @patch('ai4pkm_cli.orchestrator.core.ExecutionManager.execute')
    def test_execute_agent_failure(self, mock_execute, temp_vault):
        """Test failed agent execution."""
        vault_path, agents_dir = temp_vault

        mock_ctx = Mock()
        mock_ctx.success = False
        mock_ctx.status = 'failed'
        mock_ctx.duration = 1.0
        mock_ctx.error_message = "Test error"
        mock_execute.return_value = mock_ctx

        orch = Orchestrator(vault_path, agents_dir)

        agent = AgentDefinition(
            name="Test",
            abbreviation="TST",
            category="ingestion",
            trigger_pattern="*.md",
            trigger_event="created",
            prompt_body="Test"
        )

        event_data = {'path': 'test.md', 'event_type': 'created'}

        # Execute (should log error but not raise exception)
        orch._execute_agent(agent, event_data)

        assert mock_execute.called
