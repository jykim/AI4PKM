"""
Execution manager for orchestrator.

Manages concurrent execution of agent tasks without global semaphores.
Uses simple instance-level counter with threading lock.
"""
import logging
import threading
import subprocess
import time
import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from .models import AgentDefinition, ExecutionContext

logger = logging.getLogger(__name__)

# Claude CLI discovery
def _find_claude_cli():
    """Find the Claude CLI executable."""
    # First try the user's local installation
    local_path = Path.home() / ".claude" / "local" / "claude"
    if local_path.exists():
        return str(local_path)

    # Try to find it in PATH
    try:
        result = subprocess.run(
            ["which", "claude"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception as e:
        logger.warning(f"Could not find claude in PATH: {e}")

    # Last resort: try common locations
    common_paths = [
        "/usr/local/bin/claude",
        str(Path.home() / "node_modules" / ".bin" / "claude"),
    ]
    for path in common_paths:
        if Path(path).exists():
            return path

    return None

CLAUDE_CLI_PATH = _find_claude_cli()


class ExecutionManager:
    """
    Manages concurrent execution of agent tasks.

    Uses simple instance-level counter instead of global semaphores.
    Each agent can specify max_parallel limit.
    """

    def __init__(self, vault_path: Path, max_concurrent: int = 3, config: Optional['Config'] = None, orchestrator_settings: Optional[dict] = None):
        """
        Initialize execution manager.

        Args:
            vault_path: Path to vault root
            max_concurrent: Maximum concurrent executions across all agents
            config: Config instance (will create default if None)
            orchestrator_settings: Orchestrator settings from YAML (optional)
        """
        from ..config import Config

        self.vault_path = Path(vault_path)
        self.max_concurrent = max_concurrent
        self.config = config or Config()

        # Instance-level state (no global state)
        self._running_count = 0
        self._count_lock = threading.Lock()

        # Track running executions
        self._running_executions: Dict[str, ExecutionContext] = {}
        self._executions_lock = threading.Lock()

        # Track per-agent running counts
        self._agent_counts: Dict[str, int] = {}
        self._agent_lock = threading.Lock()

        # Task file manager
        from .task_manager import TaskFileManager
        self.task_manager = TaskFileManager(vault_path, config=self.config, orchestrator_settings=orchestrator_settings)

    def can_execute(self, agent: AgentDefinition) -> bool:
        """
        Check if agent can execute given current load.

        Args:
            agent: Agent definition

        Returns:
            True if execution is allowed
        """
        with self._count_lock:
            # Check global limit
            if self._running_count >= self.max_concurrent:
                return False

        with self._agent_lock:
            # Check per-agent limit
            agent_count = self._agent_counts.get(agent.abbreviation, 0)
            if agent_count >= agent.max_parallel:
                return False

        return True

    def reserve_slot(self, agent: AgentDefinition) -> bool:
        """
        Atomically check if can execute and reserve a slot.

        This prevents race conditions where multiple threads check can_execute()
        before any of them increment the counters.

        Args:
            agent: Agent definition

        Returns:
            True if slot was reserved, False if at capacity
        """
        with self._count_lock:
            # Check global limit
            if self._running_count >= self.max_concurrent:
                return False

            # Reserve global slot immediately
            self._running_count += 1

        with self._agent_lock:
            # Check per-agent limit
            agent_count = self._agent_counts.get(agent.abbreviation, 0)
            if agent_count >= agent.max_parallel:
                # Release global slot since we can't reserve agent slot
                with self._count_lock:
                    self._running_count -= 1
                return False

            # Reserve agent slot immediately
            self._agent_counts[agent.abbreviation] = agent_count + 1

        return True

    def execute(self, agent: AgentDefinition, trigger_data: Dict, slot_reserved: bool = False) -> ExecutionContext:
        """
        Execute an agent task.

        Args:
            agent: Agent definition to execute
            trigger_data: Data about the triggering event
            slot_reserved: If True, slot was already reserved by reserve_slot()

        Returns:
            ExecutionContext with execution results
        """
        ctx = ExecutionContext(
            agent=agent,
            trigger_data=trigger_data,
            start_time=datetime.now()
        )

        # Increment counters only if not already reserved
        if not slot_reserved:
            with self._count_lock:
                self._running_count += 1

            with self._agent_lock:
                self._agent_counts[agent.abbreviation] = self._agent_counts.get(agent.abbreviation, 0) + 1

        with self._executions_lock:
            self._running_executions[ctx.execution_id] = ctx

        # Prepare log file path BEFORE execution (needed for task file)
        log_path = self._prepare_log_path(agent, ctx)
        ctx.log_file = log_path

        # Create task file BEFORE execution starts
        task_path = self.task_manager.create_task_file(ctx, agent)
        ctx.task_file = task_path

        try:
            logger.debug(f"Starting execution: {agent.abbreviation} (ID: {ctx.execution_id})")

            # Execute based on executor type
            if agent.executor == 'claude_code':
                self._execute_claude_code(agent, ctx, trigger_data)
            elif agent.executor == 'gemini_cli':
                self._execute_gemini_cli(agent, ctx, trigger_data)
            elif agent.executor == 'codex_cli':
                self._execute_codex_cli(agent, ctx, trigger_data)
            else:
                raise ValueError(f"Unknown executor: {agent.executor}")

            ctx.status = 'completed'
            logger.info(f"Completed execution: {agent.abbreviation} (ID: {ctx.execution_id})")

        except subprocess.TimeoutExpired:
            ctx.status = 'timeout'
            logger.error(f"Timeout: {agent.abbreviation} (ID: {ctx.execution_id})")

        except Exception as e:
            ctx.status = 'failed'
            logger.error(f"Failed execution: {agent.abbreviation} (ID: {ctx.execution_id}): {e}")

        finally:
            ctx.end_time = datetime.now()

            # Update task file with final status
            if ctx.task_file:
                # Validate output and determine final status
                final_status = ctx.status
                output_link = None
                validation_error = None

                if ctx.status == 'completed' and 'path' in trigger_data:
                    # Validate output based on output_type
                    output_valid, output_link, validation_error = self._validate_output(
                        agent, trigger_data, ctx
                    )

                    # If validation failed, mark as FAILED
                    if not output_valid:
                        final_status = 'failed'
                        ctx.error_message = validation_error
                    # If validation passed but no output (optional no-output scenario)
                    elif output_valid and output_link is None and agent.output_optional:
                        final_status = 'ignored'

                self.task_manager.update_task_status(
                    task_path=ctx.task_file,
                    status="IGNORE" if final_status == 'ignored' else
                           "PROCESSED" if final_status == 'completed' else "FAILED",
                    output=output_link,
                    error_message=ctx.error_message
                )

            # Post-processing actions (e.g., remove trigger content)
            if ctx.status == 'completed' and agent.post_process_action:
                self._apply_post_processing(agent, trigger_data)

            # Log result to file
            if ctx.log_file:
                with open(ctx.log_file, 'w', encoding='utf-8') as f:
                    f.write(f"# Execution Log: {agent.abbreviation}\n")
                    f.write(f"# Start: {ctx.start_time}\n")
                    f.write(f"# Execution ID: {ctx.execution_id}\n")
                    f.write(f"# Status: {ctx.status}\n")
                    f.write(f"# Prompt:\n{ctx.prompt}\n\n")
                    f.write(f"# Response:\n{ctx.response}\n\n")
                    if ctx.error_message:
                        f.write(f"# Error Message:\n{ctx.error_message}\n\n")

            # Decrement counters
            with self._count_lock:
                self._running_count -= 1

            with self._agent_lock:
                self._agent_counts[agent.abbreviation] -= 1

            with self._executions_lock:
                del self._running_executions[ctx.execution_id]

        return ctx

    def _execute_claude_code(self, agent: AgentDefinition, ctx: ExecutionContext, trigger_data: Dict):
        """
        Execute agent using Claude Code CLI.

        Args:
            agent: Agent definition
            ctx: Execution context
            trigger_data: Trigger event data
        """
        if CLAUDE_CLI_PATH is None:
            raise RuntimeError("Claude CLI not found. Install Claude Code from https://claude.com/claude-code")

        # Build prompt from agent definition
        ctx.prompt = self._build_prompt(agent, trigger_data)
        self._execute_subprocess(ctx, 'Claude CLI', [CLAUDE_CLI_PATH, '--permission-mode', 'bypassPermissions'], agent.timeout_minutes * 60, ctx.prompt)

    def _execute_gemini_cli(self, agent: AgentDefinition, ctx: ExecutionContext, trigger_data: Dict):
        """
        Execute agent using Gemini CLI.

        Args:
            agent: Agent definition
            ctx: Execution context
            trigger_data: Trigger event data
        """
        # Build prompt
        ctx.prompt = self._build_prompt(agent, trigger_data)
        self._execute_subprocess(ctx, 'Gemini CLI', ['gemini', '--yolo', '--debug', '--prompt', ctx.prompt], agent.timeout_minutes * 60)

    def _execute_codex_cli(self, agent: AgentDefinition, ctx: ExecutionContext, trigger_data: Dict):
        """
        Execute agent using Codex CLI.

        Args:
            agent: Agent definition
            ctx: Execution context
            trigger_data: Trigger event data
        """
        # Build prompt
        ctx.prompt = self._build_prompt(agent, trigger_data)
        self._execute_subprocess(ctx, 'Codex CLI', ['codex', '--search', 'exec', '--full-auto', ctx.prompt], agent.timeout_minutes * 60)

    def _execute_subprocess(self, ctx: ExecutionContext, agent_name: str, cmd: List[str], timeout_seconds: int, input: Optional[str] = None):
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE if input else subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=str(self.vault_path)
        )

        if input:
            process.stdin.write(input)
            process.stdin.close()
        
        logs = []
        def stream_stderr(proc):
            for line in proc.stdout:
                logs.append(f"[{agent_name}] {line.strip()}")
                logger.info(logs[-1])

        stderr_thread = threading.Thread(target=stream_stderr, args=(process,))
        stderr_thread.start()

        try:
            process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            process.kill()
            raise RuntimeError(f"{agent_name} timed out after {timeout_seconds} seconds")
        finally:
            stderr_thread.join()

        
        if process.returncode != 0:
            ctx.error_message = "\n".join(logs)
            raise RuntimeError(f"{agent_name} execution failed")
        else:
            ctx.response = "\n".join(logs)


    def _build_prompt(self, agent: AgentDefinition, trigger_data: Dict) -> str:
        """
        Build execution prompt from agent definition and trigger data.

        Args:
            agent: Agent definition
            trigger_data: Trigger event data

        Returns:
            Formatted prompt string
        """
        # Start with prompt body from agent definition
        prompt = agent.prompt_body

        # Add trigger context
        prompt += "\n\n# Trigger Context\n"
        prompt += f"- Event: {trigger_data.get('event_type', 'unknown')}\n"
        prompt += f"- Input Path: {trigger_data.get('path', 'unknown')}\n"

        # Add output configuration
        if agent.output_path:
            prompt += f"\n# Output Configuration\n"
            prompt += f"- Output Directory: {agent.output_path}\n"
            prompt += f"- Output Type: {agent.output_type}\n"

            # Add guidance based on output type
            if agent.output_type == "new_file":
                prompt += f"\n**IMPORTANT**: Create a NEW file in the `{agent.output_path}` directory.\n"
                prompt += f"Do NOT modify the input file inline. The output should be a separate file.\n"
                if agent.output_naming:
                    prompt += f"Use naming pattern: {agent.output_naming}\n"
            elif agent.output_type == "update_file":
                prompt += f"\n**IMPORTANT**: Update the input file IN PLACE.\n"
                prompt += f"Do NOT create a new file.\n"

        # Add frontmatter if available
        if 'frontmatter' in trigger_data:
            prompt += "\n# File Metadata\n"
            for key, value in trigger_data['frontmatter'].items():
                prompt += f"- {key}: {value}\n"

        # Add agent parameters if available
        if agent.agent_params:
            prompt += "\n# Agent Parameters\n"
            for key, value in agent.agent_params.items():
                prompt += f"- {key}: {value}\n"

        return prompt

    def _validate_output(self, agent: AgentDefinition, trigger_data: Dict, ctx: ExecutionContext) -> tuple:
        """
        Validate that the expected output was created.

        Args:
            agent: Agent definition
            trigger_data: Trigger event data
            ctx: Execution context

        Returns:
            Tuple of (is_valid, output_link, error_message)
        """
        input_path_str = trigger_data.get('path', '')
        input_path = self.vault_path / input_path_str if input_path_str else None

        # If no output_path configured, assume inline update
        if not agent.output_path:
            # Verify input file still exists
            if input_path and input_path.exists():
                return True, f"[[{input_path_str}]]", None
            else:
                return False, None, "Input file no longer exists"

        # For update_file: verify input file was modified
        if agent.output_type == "update_file":
            if not input_path or not input_path.exists():
                return False, None, f"Input file not found: {input_path_str}"

            # Check if file was modified during execution
            file_mtime = input_path.stat().st_mtime
            start_time = ctx.start_time.timestamp() - 5 if ctx.start_time else 0

            if file_mtime >= start_time:
                return True, f"[[{input_path_str}]]", None
            else:
                return False, f"[[{input_path_str}]]", "Input file was not modified (update_file mode)"

        # For new_file: verify output directory has new files
        if agent.output_type == "new_file":
            output_dir = self.vault_path / agent.output_path
            if not output_dir.exists():
                output_dir.mkdir(parents=True, exist_ok=True)

            # Look for markdown files created/modified after execution started
            start_time = ctx.start_time.timestamp() - 5 if ctx.start_time else 0
            input_filename = Path(input_path_str).stem if input_path_str else ''

            recent_files = []
            for md_file in output_dir.glob("*.md"):
                if md_file.stat().st_mtime >= start_time:
                    # Prioritize files with matching input filename
                    if input_filename and input_filename in md_file.stem:
                        recent_files.insert(0, md_file)
                    else:
                        recent_files.append(md_file)

            if recent_files:
                # Use the most relevant file (first in list)
                output_file = recent_files[0]
                try:
                    rel_path = output_file.relative_to(self.vault_path)
                    output_link = f"[[{rel_path.parent}/{rel_path.stem}]]"
                    logger.info(f"Found output file: {rel_path}")
                    return True, output_link, None
                except ValueError:
                    return True, f"[[{output_file}]]", None
            else:
                # No output files found
                if agent.output_optional:
                    # No output is acceptable for agents with optional output
                    logger.info(f"No output found for {agent.abbreviation}, but output is optional")
                    return True, None, None
                else:
                    return False, None, f"No new file found in {agent.output_path} (new_file mode)"

        # Default: no validation
        return True, f"[[{input_path_str}]]" if input_path_str else None, None

    def _prepare_log_path(self, agent: AgentDefinition, ctx: ExecutionContext) -> Path:
        """
        Prepare log file path for execution.

        Args:
            agent: Agent definition
            ctx: Execution context

        Returns:
            Path to log file
        """
        # Format log pattern
        log_name = agent.log_pattern.format(
            timestamp=ctx.start_time.strftime('%Y-%m-%d-%H%M%S'),
            agent=agent.abbreviation,
            execution_id=ctx.execution_id
        )

        # Get logs directory from config
        logs_dir = self.config.get_orchestrator_logs_dir()
        log_path = self.vault_path / logs_dir / log_name
        log_path.parent.mkdir(parents=True, exist_ok=True)

        return log_path

    def get_running_count(self) -> int:
        """
        Get current number of running executions.

        Returns:
            Number of running executions
        """
        with self._count_lock:
            return self._running_count

    def get_agent_running_count(self, agent_abbr: str) -> int:
        """
        Get current number of running executions for specific agent.

        Args:
            agent_abbr: Agent abbreviation

        Returns:
            Number of running executions for this agent
        """
        with self._agent_lock:
            return self._agent_counts.get(agent_abbr, 0)

    def get_running_executions(self) -> List[ExecutionContext]:
        """
        Get list of currently running executions.

        Returns:
            List of ExecutionContext instances
        """
        with self._executions_lock:
            return list(self._running_executions.values())

    def _apply_post_processing(self, agent: AgentDefinition, trigger_data: Dict):
        """
        Apply post-processing actions after successful execution.

        Args:
            agent: Agent definition
            trigger_data: Trigger event data
        """
        if agent.post_process_action == "remove_trigger_content":
            self._remove_trigger_content(agent, trigger_data)
        else:
            logger.warning(f"Unknown post-process action: {agent.post_process_action}")

    def _remove_trigger_content(self, agent: AgentDefinition, trigger_data: Dict):
        """
        Remove trigger content pattern from source file.

        Args:
            agent: Agent definition
            trigger_data: Trigger event data
        """
        if not agent.trigger_content_pattern:
            logger.warning("No trigger_content_pattern defined for remove_trigger_content action")
            return

        try:
            # Get source file path
            event_path = trigger_data.get('path')
            if not event_path:
                logger.warning("No path in trigger_data for post-processing")
                return

            file_path = self.vault_path / event_path

            if not file_path.exists():
                logger.warning(f"Source file not found for post-processing: {file_path}")
                return

            # Read file content
            content = file_path.read_text(encoding='utf-8')

            # Remove trigger pattern
            from ..markdown_utils import remove_pattern_from_content
            updated_content = remove_pattern_from_content(content, agent.trigger_content_pattern)

            # Write back if changed
            if updated_content != content:
                file_path.write_text(updated_content, encoding='utf-8')
                logger.info(f"Removed trigger content from: {event_path}")
            else:
                logger.debug(f"No trigger content found to remove in: {event_path}")

        except Exception as e:
            logger.error(f"Error during post-processing: {e}")
