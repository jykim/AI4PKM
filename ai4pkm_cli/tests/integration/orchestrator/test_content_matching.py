"""Integration tests for content-based trigger matching and post-processing."""

import pytest
import tempfile
import time
from pathlib import Path

from ai4pkm_cli.orchestrator.agent_registry import AgentRegistry
from ai4pkm_cli.orchestrator.execution_manager import ExecutionManager
from ai4pkm_cli.orchestrator.models import AgentDefinition


class TestContentMatching:
    """Test content-based triggering and post-processing."""

    @pytest.fixture
    def temp_vault(self):
        """Create temporary vault structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vault_path = Path(tmpdir)

            # Create required directories
            (vault_path / "_Settings_" / "Agents").mkdir(parents=True)
            (vault_path / "_Tasks_").mkdir(parents=True)
            (vault_path / "AI" / "Tasks" / "Logs").mkdir(parents=True)
            (vault_path / "Test").mkdir(parents=True)

            yield vault_path

    @pytest.fixture
    def htc_agent_file(self, temp_vault):
        """Create HTC agent definition file."""
        agents_dir = temp_vault / "_Settings_" / "Agents"

        # Use proper YAML format (no extra quotes, proper indentation)
        agent_content = """---
title: Hashtag Task Creator
abbreviation: HTC
category: ingestion
trigger_pattern: "**/*.md"
trigger_event: modified
trigger_exclude_pattern: "_Tasks_/*.md"
trigger_content_pattern: "%%\\\\s*#ai\\\\s*%%"
output_path: _Tasks_
executor: claude_code
max_parallel: 1
timeout_minutes: 5
post_process_action: remove_trigger_content
task_create: true
task_priority: high
---

# HTC Test Prompt

Analyze the file and create a task.
"""

        agent_file = agents_dir / "HTC.md"
        agent_file.write_text(agent_content, encoding='utf-8')

        return temp_vault

    def test_content_pattern_matching(self, htc_agent_file):
        """Test that content pattern is matched correctly."""
        vault_path = htc_agent_file
        agents_dir = vault_path / "_Settings_" / "Agents"

        # Create test file WITH hashtag comment
        test_file = vault_path / "Test" / "with_hashtag.md"
        test_file.write_text("""---
title: Test File
---

# Test Content

This is a test file. %% #ai %%

Some more content.
""", encoding='utf-8')

        # Load agent registry
        registry = AgentRegistry(agents_dir, vault_path)

        # Check matching
        event_data = {
            'path': 'Test/with_hashtag.md',
            'event_type': 'modified'
        }

        matches = registry.find_matching_agents(event_data)

        # Should match HTC agent
        assert len(matches) == 1
        assert matches[0].abbreviation == "HTC"

    def test_content_pattern_not_matching(self, htc_agent_file):
        """Test that files without pattern don't match."""
        vault_path = htc_agent_file
        agents_dir = vault_path / "_Settings_" / "Agents"

        # Create test file WITHOUT hashtag comment
        test_file = vault_path / "Test" / "without_hashtag.md"
        test_file.write_text("""---
title: Test File
---

# Test Content

This is a test file with no special marker.
""", encoding='utf-8')

        # Load agent registry
        registry = AgentRegistry(agents_dir, vault_path)

        # Check matching
        event_data = {
            'path': 'Test/without_hashtag.md',
            'event_type': 'modified'
        }

        matches = registry.find_matching_agents(event_data)

        # Should NOT match
        assert len(matches) == 0

    def test_excluded_directory(self, htc_agent_file):
        """Test that excluded directories are not matched."""
        vault_path = htc_agent_file
        agents_dir = vault_path / "_Settings_" / "Agents"

        # Create test file in _Tasks_ (excluded)
        test_file = vault_path / "_Tasks_" / "task.md"
        test_file.write_text("""---
title: Task File
---

# Task

This has %% #ai %% but should be excluded.
""", encoding='utf-8')

        # Load agent registry
        registry = AgentRegistry(agents_dir, vault_path)

        # Check matching
        event_data = {
            'path': '_Tasks_/task.md',
            'event_type': 'modified'
        }

        matches = registry.find_matching_agents(event_data)

        # Should NOT match (excluded by trigger_exclude_pattern)
        assert len(matches) == 0

    def test_duplicate_task_check(self, htc_agent_file):
        """Test that existing tasks prevent duplicate matching."""
        vault_path = htc_agent_file
        agents_dir = vault_path / "_Settings_" / "Agents"

        # Create test source file
        source_file = vault_path / "Test" / "source.md"
        source_file.write_text("""---
title: Source
---

Content %% #ai %%
""", encoding='utf-8')

        # Create existing task file for this source
        tasks_dir = vault_path / "_Tasks_"
        existing_task = tasks_dir / "2025-10-25 HTC - source.md"
        existing_task.write_text("""---
title: Task for source
---

Existing task.
""", encoding='utf-8')

        # Load agent registry
        registry = AgentRegistry(agents_dir, vault_path)

        # Check matching
        event_data = {
            'path': 'Test/source.md',
            'event_type': 'modified'
        }

        matches = registry.find_matching_agents(event_data)

        # Should NOT match (task already exists)
        assert len(matches) == 0

    def test_pattern_removal_from_markdown_utils(self):
        """Test the pattern removal utility function."""
        from ai4pkm_cli.markdown_utils import remove_pattern_from_content

        content = """---
title: Test
---

# Content

This is before. %% #ai %%

This is after.
"""

        pattern = r"%%\s*#ai\s*%%"
        result = remove_pattern_from_content(content, pattern)

        # Should remove the pattern
        assert "%% #ai %%" not in result
        assert "This is before." in result
        assert "This is after." in result

    def test_case_insensitive_matching(self, htc_agent_file):
        """Test that pattern matching is case-insensitive."""
        vault_path = htc_agent_file
        agents_dir = vault_path / "_Settings_" / "Agents"

        # Create test file with uppercase AI
        test_file = vault_path / "Test" / "uppercase.md"
        test_file.write_text("""---
title: Test
---

Content %% #AI %%
""", encoding='utf-8')

        # Load agent registry
        registry = AgentRegistry(agents_dir, vault_path)

        # Check matching
        event_data = {
            'path': 'Test/uppercase.md',
            'event_type': 'modified'
        }

        matches = registry.find_matching_agents(event_data)

        # Should match (case-insensitive)
        assert len(matches) == 1

    def test_pattern_with_varying_whitespace(self, htc_agent_file):
        """Test that pattern matches with different whitespace."""
        vault_path = htc_agent_file
        agents_dir = vault_path / "_Settings_" / "Agents"

        # Create test files with different whitespace
        test_cases = [
            "%%#ai%%",      # No spaces
            "%% #ai%%",     # Space before
            "%%#ai %%",     # Space after
            "%%  #ai  %%",  # Multiple spaces
        ]

        registry = AgentRegistry(agents_dir, vault_path)

        for i, marker in enumerate(test_cases):
            test_file = vault_path / "Test" / f"whitespace_{i}.md"
            test_file.write_text(f"Content {marker}", encoding='utf-8')

            event_data = {
                'path': f'Test/whitespace_{i}.md',
                'event_type': 'modified'
            }

            matches = registry.find_matching_agents(event_data)
            assert len(matches) == 1, f"Failed to match: {marker}"
