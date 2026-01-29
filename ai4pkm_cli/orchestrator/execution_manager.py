"""
Execution manager for orchestrator.

Manages concurrent execution of agent tasks without global semaphores.
Uses simple instance-level counter with threading lock.
"""
import threading
import subprocess
import time
import os
import shutil
import platform
from pathlib import Path
from typing import Dict, List, Optional, TYPE_CHECKING
from datetime import datetime

from .models import AgentDefinition, ExecutionContext
from .web_executors import WebExecutor
from ..logger import Logger

if TYPE_CHECKING:
    from ..config import Config

logger = Logger()

class ExecutionManager:
    """
    Manages concurrent execution of agent tasks.

    Uses simple instance-level counter instead of global semaphores.
    Each agent can specify max_parallel limit.
    """

    def __init__(self, vault_path: Path, max_concurrent: int = 3, config: Optional['Config'] = None, orchestrator_settings: Optional[dict] = None, working_dir: Optional[Path] = None):
        """
        Initialize execution manager.

        Args:
            vault_path: Path to vault root
            max_concurrent: Maximum concurrent executions across all agents
            config: Config instance (will create default if None)
            orchestrator_settings: Orchestrator settings from YAML (optional)
            working_dir: Working directory for agent subprocess execution (defaults to vault_path)
        """
        from ..config import Config

        self.vault_path = Path(vault_path)
        self.working_dir = Path(working_dir) if working_dir else self.vault_path
        self.max_concurrent = max_concurrent
        self.config = config or Config()
        self.orchestrator_settings = orchestrator_settings or {}

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
        
        # Load system prompt if it exists
        self.system_prompt = self._load_system_prompt()

        # Web executor helper (initialized lazily to avoid circular import issues)
        self._web_executor = None

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

    def execute(self, agent: AgentDefinition, trigger_data: Dict, slot_reserved: bool = False, session_id: Optional[str] = None, resume_session: bool = False) -> ExecutionContext:
        """
        Execute an agent task.

        Args:
            agent: Agent definition to execute
            trigger_data: Data about the triggering event
            slot_reserved: If True, slot was already reserved by reserve_slot()
            session_id: Optional session ID for tracking related executions
            resume_session: If True, resume existing session; if False, create new session

        Returns:
            ExecutionContext with execution results
        """
        ctx = ExecutionContext(
            agent=agent,
            trigger_data=trigger_data,
            start_time=datetime.now(),
            session_id=session_id,
            resume_session=resume_session,
            system_prompt=agent.system_prompt,
            system_prompt_file=agent.system_prompt_file,
            append_system_prompt=agent.append_system_prompt,
            append_system_prompt_file=agent.append_system_prompt_file
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

        existing_task_path = trigger_data.get('_existing_task_file')
        if existing_task_path:
            task_file = Path(existing_task_path)
            ctx.task_file = task_file

            self.task_manager.update_task_status(task_file, "IN_PROGRESS")
            logger.info(f"Using existing task file: {task_file.name}", console=True)
        else:
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
            elif agent.executor == 'cursor_agent':
                self._execute_cursor_agent(agent, ctx, trigger_data)
            elif agent.executor == 'continue_cli':
                self._execute_continue_cli(agent, ctx, trigger_data)
            elif agent.executor == 'grok_cli':
                self._execute_grok_cli(agent, ctx, trigger_data)
            elif agent.executor == 'gemini_web':
                self._get_web_executor().execute_gemini_web(agent, ctx, trigger_data)
            elif agent.executor == 'chatgpt_web':
                self._get_web_executor().execute_chatgpt_web(agent, ctx, trigger_data)
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
                # Check if agent updated task file
                agent_status = None
                agent_output = None
                if ctx.task_file.exists():
                    from ..markdown_utils import read_frontmatter
                    task_fm = read_frontmatter(ctx.task_file)
                    agent_status = task_fm.get('status', '').upper()
                    agent_output = task_fm.get('output', '').strip()
                
                # Validate output and determine final status
                final_status = ctx.status
                output_link = None
                validation_error = None

                if ctx.status == 'completed' and 'path' in trigger_data:
                    # Use agent-reported output if present and valid
                    if agent_status in ['COMPLETED', 'PROCESSED'] and agent_output:
                        # Validate agent-reported output file exists
                        output_valid, validated_link, validation_error = self._validate_agent_output(
                            agent_output, agent, trigger_data, ctx
                        )
                        if output_valid:
                            output_link = validated_link
                        else:
                            # Agent reported invalid output, fall back to heuristic discovery
                            output_valid, output_link, validation_error = self._validate_output(
                                agent, trigger_data, ctx
                            )
                    else:
                        # Agent didn't update, use heuristic discovery
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
                
                # Attach execution summary to Process Log
                if ctx.log_file and ctx.log_file.exists():
                    try:
                        summary = f"Execution completed at {ctx.end_time.isoformat()}. See generation_log for details."
                        content = ctx.task_file.read_text(encoding='utf-8')
                        updated = self.task_manager._append_to_process_log(content, summary)
                        ctx.task_file.write_text(updated, encoding='utf-8')
                    except Exception as e:
                        logger.warning(f"Failed to attach execution summary to task file: {e}")

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

    def _get_web_executor(self) -> WebExecutor:
        """Get or create the WebExecutor instance."""
        if self._web_executor is None:
            self._web_executor = WebExecutor(self.vault_path, self._build_prompt)
        return self._web_executor

    def _execute_claude_code(self, agent: AgentDefinition, ctx: ExecutionContext, trigger_data: Dict):
        """
        Execute agent using Claude Code CLI.

        Args:
            agent: Agent definition
            ctx: Execution context
            trigger_data: Trigger event data
        """
        # For one-time prompts, use just the prompt body without any context
        if trigger_data.get('event_type') == 'onetime_prompt':
            ctx.prompt = agent.prompt_body
        else:
            # Build prompt from agent definition with full context
            ctx.prompt = self._build_prompt(agent, trigger_data, ctx)
        
        # Build command with optional session ID (prompt will be passed via stdin)
        cmd = ['claude', '--permission-mode', 'bypassPermissions', '--print']

        # Add model if specified in agent_params
        if agent.agent_params and 'model' in agent.agent_params:
            cmd.extend(['--model', agent.agent_params['model']])

        if ctx.system_prompt_file:
            cmd.extend(['--system-prompt-file', str(ctx.system_prompt_file)])
        
        # Add system prompt if provided
        if ctx.system_prompt:
            cmd.extend(['--system-prompt', ctx.system_prompt])
        
        # Add append system prompt file if provided
        if ctx.append_system_prompt_file:
            cmd.extend(['--append-system-prompt-file', str(ctx.append_system_prompt_file)])
        
        # Add append system prompt if provided
        if ctx.append_system_prompt:
            cmd.extend(['--append-system-prompt', ctx.append_system_prompt])
        
        # Add session ID handling: try to create new first, resume if already exists
        if ctx.session_id:
            # First try to create new session with --session-id
            # If it fails because session exists, we'll catch and retry with --resume
            cmd.extend(['--session-id', ctx.session_id])
        
        try:
            self._execute_subprocess(ctx, 'Claude CLI', cmd, agent.timeout_minutes * 60, stdin_input=ctx.prompt)
        except RuntimeError as e:
            # Check if error is about session already existing
            error_msg = str(e)
            # Check both the error message and ctx.error_message (set by _execute_subprocess)
            full_error = f"{error_msg} {ctx.error_message or ''}"
            if ctx.session_id and ("already in use" in full_error.lower() or "already exists" in full_error.lower()):
                # Session exists, retry with --resume
                logger.info(f"Session {ctx.session_id} already exists, resuming...")
                # Clear previous error
                ctx.error_message = None
                cmd_resume = ['claude', '--permission-mode', 'bypassPermissions', '--print', '--resume', ctx.session_id]
                # Add model to resume command as well
                if agent.agent_params and 'model' in agent.agent_params:
                    cmd_resume.extend(['--model', agent.agent_params['model']])
                if ctx.system_prompt_file:
                    cmd_resume.extend(['--system-prompt-file', str(ctx.system_prompt_file)])
                # Add system prompt to resume command
                if ctx.system_prompt:
                    cmd_resume.extend(['--system-prompt', ctx.system_prompt])
                # Add append system prompt file to resume command
                if ctx.append_system_prompt_file:
                    cmd_resume.extend(['--append-system-prompt-file', str(ctx.append_system_prompt_file)])
                # Add append system prompt to resume command
                if ctx.append_system_prompt:
                    cmd_resume.extend(['--append-system-prompt', ctx.append_system_prompt])
                self._execute_subprocess(ctx, 'Claude CLI', cmd_resume, agent.timeout_minutes * 60, stdin_input=ctx.prompt)
            else:
                # Re-raise if it's a different error
                raise

    def _execute_gemini_cli(self, agent: AgentDefinition, ctx: ExecutionContext, trigger_data: Dict):
        """
        Execute agent using Gemini CLI.

        Args:
            agent: Agent definition
            ctx: Execution context
            trigger_data: Trigger event data
        """
        # Build prompt
        ctx.prompt = self._build_prompt(agent, trigger_data, ctx)

        cmd = ['gemini', '--yolo']

        # Add model if specified in agent_params
        if agent.agent_params and 'model' in agent.agent_params:
            cmd.extend(['--model', agent.agent_params['model']])

        self._execute_subprocess(ctx, 'Gemini CLI', cmd, agent.timeout_minutes * 60, stdin_input=ctx.prompt)

    def _execute_codex_cli(self, agent: AgentDefinition, ctx: ExecutionContext, trigger_data: Dict):
        """
        Execute agent using Codex CLI.

        Args:
            agent: Agent definition
            ctx: Execution context
            trigger_data: Trigger event data
        """
        # Build prompt
        ctx.prompt = self._build_prompt(agent, trigger_data, ctx)
        self._execute_subprocess(ctx, 'Codex CLI', ['codex', '--search', '--enable', 'web_search_request', 'exec', '--skip-git-repo-check', '--full-auto'], agent.timeout_minutes * 60, stdin_input=ctx.prompt)

    def _execute_cursor_agent(self, agent: AgentDefinition, ctx: ExecutionContext, trigger_data: Dict):
        """
        Execute agent using Cursor Agent CLI.

        Args:
            agent: Agent definition
            ctx: Execution context
            trigger_data: Trigger event data
        """
        # Build prompt
        ctx.prompt = self._build_prompt(agent, trigger_data, ctx)
        
        # Build command: cursor-agent --print --output-format text [prompt]
        cmd = ['cursor-agent', '--print', '--output-format', 'text']
        
        # Add model if specified in agent_params
        if agent.agent_params and 'model' in agent.agent_params:
            cmd.extend(['--model', agent.agent_params['model']])
        
        # Add MCP approval if specified in agent_params
        if agent.agent_params and agent.agent_params.get('approve_mcps', False):
            cmd.append('--approve-mcps')
        
        # Add browser support if specified in agent_params
        if agent.agent_params and agent.agent_params.get('browser', False):
            cmd.append('--browser')
        
        self._execute_subprocess(ctx, 'Cursor Agent', cmd, agent.timeout_minutes * 60, stdin_input=ctx.prompt)

    def _execute_continue_cli(self, agent: AgentDefinition, ctx: ExecutionContext, trigger_data: Dict):
        """
        Execute agent using Continue CLI (cn).

        Args:
            agent: Agent definition
            ctx: Execution context
            trigger_data: Trigger event data
        """
        # Build prompt
        ctx.prompt = self._build_prompt(agent, trigger_data, ctx)
        
        # Build command: cn --print [options] [prompt]
        cmd = ['cn', '--print']
        
        # Add format if specified in agent_params (default: json for structured output)
        if agent.agent_params and 'format' in agent.agent_params:
            output_format = agent.agent_params['format']
            cmd.extend(['--format', output_format])
        else:
            # Default to json for structured output if not specified
            cmd.extend(['--format', 'json'])
        
        # Add silent flag if specified in agent_params
        if agent.agent_params and agent.agent_params.get('silent', False):
            cmd.append('--silent')
        
        # Add model if specified in agent_params
        if agent.agent_params and 'model' in agent.agent_params:
            cmd.extend(['--model', agent.agent_params['model']])
        
        # Add MCP servers if specified in agent_params
        if agent.agent_params and 'mcp' in agent.agent_params:
            mcp_servers = agent.agent_params['mcp']
            if isinstance(mcp_servers, list):
                for mcp in mcp_servers:
                    cmd.extend(['--mcp', mcp])
            elif isinstance(mcp_servers, str):
                cmd.extend(['--mcp', mcp_servers])
        
        # Add rules if specified in agent_params
        if agent.agent_params and 'rule' in agent.agent_params:
            rules = agent.agent_params['rule']
            if isinstance(rules, list):
                for rule in rules:
                    cmd.extend(['--rule', rule])
            elif isinstance(rules, str):
                cmd.extend(['--rule', rules])
        
        # Add config if specified in agent_params
        if agent.agent_params and 'config' in agent.agent_params:
            cmd.extend(['--config', agent.agent_params['config']])
        
        # Add auto mode if specified in agent_params
        if agent.agent_params and agent.agent_params.get('auto', False):
            cmd.append('--auto')
        
        # Add readonly mode if specified in agent_params
        if agent.agent_params and agent.agent_params.get('readonly', False):
            cmd.append('--readonly')
        
        self._execute_subprocess(ctx, 'Continue CLI', cmd, agent.timeout_minutes * 60, stdin_input=ctx.prompt)

    def _execute_grok_cli(self, agent: AgentDefinition, ctx: ExecutionContext, trigger_data: Dict):
        """
        Execute agent using Grok CLI.

        Args:
            agent: Agent definition
            ctx: Execution context
            trigger_data: Trigger event data
        """
        # Build prompt
        ctx.prompt = self._build_prompt(agent, trigger_data, ctx)
        self._execute_subprocess(ctx, 'Grok CLI', ['grok'], agent.timeout_minutes * 60, stdin_input=ctx.prompt)

    def _execute_subprocess(self, ctx: ExecutionContext, agent_name: str, cmd: List[str], timeout_seconds: int, stdin_input: Optional[str] = None, env: Optional[Dict] = None):
        # On Windows, resolve .cmd/.bat files to their full paths
        if platform.system() == 'Windows' and cmd:
            executable = cmd[0]
            # Try to find the executable (handles .cmd, .bat, .exe)
            resolved = shutil.which(executable)
            if resolved:
                # Use the resolved full path
                cmd = [resolved] + cmd[1:]
            elif not os.path.splitext(executable)[1]:  # No extension
                # Try .cmd extension explicitly
                cmd_cmd = executable + '.cmd'
                resolved_cmd = shutil.which(cmd_cmd)
                if resolved_cmd:
                    cmd = [resolved_cmd] + cmd[1:]

        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            cwd=str(self.working_dir),
            env=env
        )

        if ctx.task_file:
            task_identifier = ctx.task_file.name
        elif ctx.agent and ctx.agent.abbreviation:
            task_identifier = f"task for {ctx.agent.abbreviation}"

        logs = []
        def stream_stderr(proc):
            for line in proc.stdout:
                logs.append(f"[{agent_name}] {line.strip()}")
                logger.info(logs[-1])

        status_stop_event = threading.Event()
        def print_status():
            while not status_stop_event.is_set():
                if process.poll() is None:
                    logger.info(f"⏳ {agent_name} is running for {task_identifier}", console=True)
                else:
                    break
                if status_stop_event.wait(5.0):
                    break

        stderr_thread = threading.Thread(target=stream_stderr, args=(process,), daemon=True)
        status_thread = threading.Thread(target=print_status, daemon=True)
        
        stderr_thread.start()
        status_thread.start()
        
        # Write stdin input if provided (after starting output reading threads)
        if stdin_input is not None:
            try:
                # Small delay to ensure process has started
                time.sleep(0.05)
                process.stdin.write(stdin_input)
                process.stdin.flush()
                process.stdin.close()
            except (BrokenPipeError, OSError, ValueError) as e:
                # Process may have already exited or stdin was closed
                logger.warning(f"Failed to write to stdin: {e}")
                # Check if process already failed
                if process.poll() is not None:
                    # Process already exited, we'll catch the error below
                    pass

        try:
            process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            process.kill()
            raise RuntimeError(f"{agent_name} timed out after {timeout_seconds} seconds")
        finally:
            status_stop_event.set()
            status_thread.join()
            stderr_thread.join()

        
        if process.returncode != 0:
            ctx.error_message = "\n".join(logs)
            raise RuntimeError(f"{agent_name} execution failed")
        else:
            ctx.response = "\n".join(logs)


    def _load_system_prompt(self) -> str:
        """
        Load system prompt from prompts_dir/System Prompt.md if it exists.
        
        Uses prompts_dir from orchestrator_settings or falls back to config.

        Returns:
            System prompt content or empty string if not found
        """
        # Get prompts_dir from orchestrator_settings or fallback to config
        if self.orchestrator_settings and 'prompts_dir' in self.orchestrator_settings:
            prompts_dir = self.orchestrator_settings['prompts_dir']
        else:
            prompts_dir = self.config.get_orchestrator_prompts_dir()
        
        system_prompt_path = self.vault_path / prompts_dir / "System Prompt.md"
        if system_prompt_path.exists():
            try:
                from ..markdown_utils import extract_body
                content = system_prompt_path.read_text(encoding='utf-8')
                return extract_body(content)
            except Exception as e:
                logger.warning(f"Failed to load system prompt: {e}")
                return ""
        return ""

    def _build_prompt(self, agent: AgentDefinition, trigger_data: Dict, ctx: Optional[ExecutionContext] = None) -> str:
        """
        Build execution prompt from agent definition and trigger data.

        Args:
            agent: Agent definition
            trigger_data: Trigger event data
            ctx: Execution context (optional, needed for task file path)

        Returns:
            Formatted prompt string
        """
        # Start with system prompt if available
        prompt = ""
        if self.system_prompt:
            prompt = self.system_prompt + "\n\n"
        
        # Add agent prompt body
        prompt += agent.prompt_body

        # Add trigger context
        prompt += "\n\n# Trigger Context\n"
        prompt += f"- Event: {trigger_data.get('event_type', 'unknown')}\n"
        prompt += f"- Input Path: {trigger_data.get('path', 'unknown')}\n"

        # Add worker context for multi-worker agents
        if '-' in agent.abbreviation:
            parts = agent.abbreviation.split('-', 1)
            worker_label = parts[1]
            prompt += f"- Worker: {worker_label} (multi-worker evaluation mode)\n"
        
        # Add task file path if available
        if ctx and ctx.task_file:
            try:
                rel_task = ctx.task_file.relative_to(self.vault_path)
                task_link = f"[[{rel_task.parent}/{rel_task.stem}]]"
                prompt += f"- Task File: {task_link}\n"
                prompt += f"- **Update upon completion**: Set `status:` and `output:` fields\n"
            except ValueError:
                # If relative path fails, use absolute path as fallback
                prompt += f"- Task File: {ctx.task_file}\n"
                prompt += f"- **Update upon completion**: Set `status:` and `output:` fields\n"

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

    def _validate_agent_output(self, agent_output: str, agent: AgentDefinition, trigger_data: Dict, ctx: ExecutionContext) -> tuple:
        """
        Validate that agent-reported output file exists.

        Args:
            agent_output: Output file link reported by agent (wiki link format)
            agent: Agent definition
            trigger_data: Trigger event data
            ctx: Execution context

        Returns:
            Tuple of (is_valid, output_link, error_message)
        """
        # Extract file path from wiki link format [[path/to/file]]
        import re
        match = re.search(r'\[\[([^\]]+)\]\]', agent_output)
        if not match:
            return False, None, f"Invalid output format: {agent_output}. Expected wiki link format [[path/to/file]]"
        
        file_path_str = match.group(1)
        # Handle paths with or without .md extension
        if not file_path_str.endswith('.md'):
            file_path_str += '.md'
        
        # Try to resolve the file path
        output_path = self.vault_path / file_path_str
        if output_path.exists():
            try:
                rel_path = output_path.relative_to(self.vault_path)
                output_link = f"[[{rel_path.parent}/{rel_path.stem}]]"
                return True, output_link, None
            except ValueError:
                return True, f"[[{file_path_str}]]", None
        else:
            return False, None, f"Output file not found: {file_path_str}"

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

        # Try to reuse existing log path from frontmatter
        log_link = ctx.trigger_data.get('_generation_log', '')
        if log_link and log_link.startswith('[[') and log_link.endswith(']]'):
            try:
                log_rel_path = log_link[2:-2]
                log_path = self.vault_path / log_rel_path
                logger.info(f"Reusing log file: {log_path.name}", console=True)
            except Exception as e:
                logger.warning(f"Failed to parse existing log path: {e}")
        
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Create empty log file if it doesn't exist to ensure wiki links work
        if not log_path.exists():
            log_path.touch()

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

    def update_settings(self, max_concurrent: int) -> None:
        """
        Update execution manager settings.
        
        Updates max_concurrent without affecting running executions.
        
        Args:
            max_concurrent: New maximum concurrent executions
        """
        with self._count_lock:
            old_max = self.max_concurrent
            self.max_concurrent = max_concurrent
            logger.info(f"Updated max_concurrent: {old_max} -> {max_concurrent}")

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
