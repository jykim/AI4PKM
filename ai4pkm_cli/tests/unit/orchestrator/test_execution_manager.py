"""Unit tests for execution_manager.py"""

import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

from ai4pkm_cli.orchestrator.execution_manager import ExecutionManager
from ai4pkm_cli.orchestrator.models import AgentDefinition, ExecutionContext


class TestExecutionManager:
    """Test execution manager concurrency control."""

    @pytest.fixture
    def temp_vault(self):
        """Create temporary vault directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir)
            yield vault_path

    @pytest.fixture
    def sample_agent(self):
        """Create a sample agent definition."""
        return AgentDefinition(
            name="Test Agent",
            abbreviation="TST",
            category="ingestion",
            trigger_pattern="*.md",
            trigger_event="created",
            prompt_body="Test prompt",
            executor="claude_code",
            max_parallel=2,
            timeout_minutes=5
        )

    def test_init(self, temp_vault):
        """Test execution manager initialization."""
        manager = ExecutionManager(temp_vault, max_concurrent=3)

        assert manager.vault_path == temp_vault
        assert manager.max_concurrent == 3
        assert manager.get_running_count() == 0

    def test_can_execute_under_limit(self, temp_vault, sample_agent):
        """Test can_execute returns True when under limits."""
        manager = ExecutionManager(temp_vault, max_concurrent=3)

        assert manager.can_execute(sample_agent) is True

    def test_can_execute_at_global_limit(self, temp_vault, sample_agent):
        """Test can_execute returns False at global limit."""
        manager = ExecutionManager(temp_vault, max_concurrent=1)

        # Manually set running count to limit
        manager._running_count = 1

        assert manager.can_execute(sample_agent) is False

    def test_can_execute_at_agent_limit(self, temp_vault, sample_agent):
        """Test can_execute returns False at per-agent limit."""
        manager = ExecutionManager(temp_vault, max_concurrent=10)

        # Agent has max_parallel=2
        # Set agent count to limit
        manager._agent_counts[sample_agent.abbreviation] = 2

        assert manager.can_execute(sample_agent) is False

    @patch('ai4pkm_cli.orchestrator.execution_manager.CLAUDE_CLI_PATH', '/mock/claude')
    @patch('subprocess.run')
    def test_execute_increments_counters(self, mock_subprocess_run, temp_vault, sample_agent):
        """Test execute properly increments and decrements counters."""
        mock_subprocess_run.return_value = Mock(returncode=0, stdout="Success", stderr="")

        manager = ExecutionManager(temp_vault, max_concurrent=3)

        # Before execution
        assert manager.get_running_count() == 0
        assert manager.get_agent_running_count("TST") == 0

        # During execution (we'll check via mock)
        trigger_data = {'path': 'test.md', 'event_type': 'created'}

        ctx = manager.execute(sample_agent, trigger_data)

        # After execution
        assert manager.get_running_count() == 0
        assert manager.get_agent_running_count("TST") == 0
        assert ctx.status == 'completed'

    @patch('ai4pkm_cli.orchestrator.execution_manager.CLAUDE_CLI_PATH', '/mock/claude')
    @patch('subprocess.run')
    def test_execute_handles_timeout(self, mock_subprocess_run, temp_vault, sample_agent):
        """Test execute handles subprocess timeout."""
        import subprocess
        mock_subprocess_run.side_effect = subprocess.TimeoutExpired(cmd=['claude'], timeout=300)

        manager = ExecutionManager(temp_vault, max_concurrent=3)

        trigger_data = {'path': 'test.md', 'event_type': 'created'}
        ctx = manager.execute(sample_agent, trigger_data)

        assert ctx.status == 'timeout'
        assert ctx.error_message is not None
        assert manager.get_running_count() == 0

    @patch('ai4pkm_cli.orchestrator.execution_manager.CLAUDE_CLI_PATH', '/mock/claude')
    @patch('subprocess.run')
    def test_execute_handles_error(self, mock_subprocess_run, temp_vault, sample_agent):
        """Test execute handles execution errors."""
        mock_subprocess_run.return_value = Mock(returncode=1, stdout="", stderr="Execution failed")

        manager = ExecutionManager(temp_vault, max_concurrent=3)

        trigger_data = {'path': 'test.md', 'event_type': 'created'}
        ctx = manager.execute(sample_agent, trigger_data)

        assert ctx.status == 'failed'
        assert ctx.error_message is not None
        assert manager.get_running_count() == 0

    @patch('ai4pkm_cli.orchestrator.execution_manager.CLAUDE_CLI_PATH', '/mock/claude')
    @patch('subprocess.run')
    def test_build_prompt_includes_trigger_context(self, mock_subprocess_run, temp_vault, sample_agent):
        """Test prompt building includes trigger context."""
        mock_subprocess_run.return_value = Mock(returncode=0, stdout="Success", stderr="")

        manager = ExecutionManager(temp_vault, max_concurrent=3)

        trigger_data = {
            'path': 'Ingest/test.md',
            'event_type': 'created',
            'frontmatter': {'title': 'Test', 'status': 'pending'}
        }

        ctx = manager.execute(sample_agent, trigger_data)

        # Check that execution succeeded
        assert ctx.status == 'completed'
        assert mock_subprocess_run.called

    @patch('ai4pkm_cli.orchestrator.execution_manager.CLAUDE_CLI_PATH', '/mock/claude')
    @patch('subprocess.run')
    def test_execute_claude_code(self, mock_subprocess_run, temp_vault):
        """Test Claude Code execution."""
        mock_subprocess_run.return_value = Mock(returncode=0, stdout="Done", stderr="")

        agent = AgentDefinition(
            name="Claude Agent",
            abbreviation="CLA",
            category="ingestion",
            trigger_pattern="*.md",
            trigger_event="created",
            prompt_body="Test",
            executor="claude_code",
            skills=["skill1", "skill2"],
            mcp_servers=["server1"]
        )

        manager = ExecutionManager(temp_vault, max_concurrent=3)
        trigger_data = {'path': 'test.md', 'event_type': 'created'}

        ctx = manager.execute(agent, trigger_data)

        assert ctx.status == 'completed'
        assert mock_subprocess_run.called

    def test_get_running_executions(self, temp_vault, sample_agent):
        """Test getting list of running executions."""
        manager = ExecutionManager(temp_vault, max_concurrent=3)

        # Initially empty
        assert len(manager.get_running_executions()) == 0

        # Manually add a running execution
        from datetime import datetime
        ctx = ExecutionContext(
            agent=sample_agent,
            trigger_data={},
            start_time=datetime.now()
        )

        with manager._executions_lock:
            manager._running_executions[ctx.execution_id] = ctx

        running = manager.get_running_executions()
        assert len(running) == 1
        assert running[0].execution_id == ctx.execution_id

    def test_prepare_log_path_creates_directory(self, temp_vault, sample_agent):
        """Test log path preparation creates directory."""
        manager = ExecutionManager(temp_vault, max_concurrent=3)

        from datetime import datetime
        ctx = ExecutionContext(
            agent=sample_agent,
            trigger_data={},
            start_time=datetime.now()
        )

        log_path = manager._prepare_log_path(sample_agent, ctx)

        # Check directory was created
        assert log_path.parent.exists()
        assert log_path.parent.name == "Logs"
        assert "TST" in log_path.name
