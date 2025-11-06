"""Main PKM CLI application class."""

import os
import time
import glob
from datetime import datetime
from typing import Dict, Any, Tuple
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from .cron_manager import CronManager
from .logger import Logger
from .config import Config
from .agent_factory import AgentFactory
from .commands.command_runner import CommandRunner
from .server import Server
from watchdog.observers import Observer
from .watchdog.file_watchdog import FileWatchdogHandler


class PKMApp:
    """Main PKM CLI application."""

    def __init__(self, suppress_agent_logging=False):
        """Initialize the PKM application."""
        self.console = Console()
        self.logger = Logger(
            console_output=True
        )  # Enable console output for main logger
        self.config = Config()
        # Temporarily suppress agent logging if requested
        if suppress_agent_logging:
            original_info = self.logger.info
            self.logger.info = (
                lambda msg: None if "🤖 Using agent:" in msg else original_info(msg)
            )
            self.agent = AgentFactory.create_agent(self.logger, self.config)
            self.logger.info = original_info  # Restore logging
        else:
            self.agent = AgentFactory.create_agent(self.logger, self.config)
        self.command_runner = CommandRunner(self.logger, self.config)
        self.running = False
        self.server = None

    def find_matching_prompt(self, prompt_query):
        """Find matching prompt in the Prompts folder."""
        prompts_dir = "_Settings_/Prompts"

        # Get all .md files in prompts directory (excluding subdirectories for now)
        prompt_files = glob.glob(os.path.join(prompts_dir, "*.md"))

        # Extract base names without extension and path
        available_prompts = []
        for file_path in prompt_files:
            base_name = os.path.basename(file_path)
            if base_name.endswith(".md"):
                prompt_name = base_name[:-3]  # Remove .md extension
                available_prompts.append((prompt_name, file_path))

        # Try exact match first (case insensitive)
        query_lower = prompt_query.lower()
        for prompt_name, file_path in available_prompts:
            if prompt_name.lower() == query_lower:
                return prompt_name

        # Try matching shortcut codes in parentheses (e.g., CTP, GDR, etc.)
        for prompt_name, file_path in available_prompts:
            # Look for content in parentheses at the end of the filename
            if "(" in prompt_name and prompt_name.endswith(")"):
                # Extract shortcut code from parentheses
                paren_start = prompt_name.rfind("(")
                shortcut = prompt_name[paren_start + 1 : -1].strip()
                if shortcut.lower() == query_lower:
                    return prompt_name

        # Try partial name matching
        matches = []
        for prompt_name, file_path in available_prompts:
            if query_lower in prompt_name.lower():
                matches.append(prompt_name)

        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            self.logger.warning(
                f"Multiple prompts match '{prompt_query}': {', '.join(matches)}"
            )
            self.logger.info(f"Using first match: {matches[0]}")
            return matches[0]

        # List available prompts if no match found
        self.logger.error(f"No prompt found matching '{prompt_query}'")
        self.logger.info("Available prompts:")
        for prompt_name, file_path in available_prompts:
            # Show shortcut code if available
            shortcut = ""
            if "(" in prompt_name and prompt_name.endswith(")"):
                paren_start = prompt_name.rfind("(")
                shortcut = f" [{prompt_name[paren_start + 1 : -1]}]"
            self.logger.info(f"  • {prompt_name}{shortcut}")

        return None

    def _get_execution_agent(self, agent_override=None):
        """Determine which agent to use for execution."""
        if agent_override:
            # Map shorthand names to full agent types
            agent_shortcuts = {
                "c": "claude_code",
                "g": "gemini_cli",
                "o": "codex_cli",
                "claude": "claude_code",
                "gemini": "gemini_cli",
                "codex": "codex_cli",
            }

            # Use shorthand mapping if provided
            if agent_override in agent_shortcuts:
                agent_override = agent_shortcuts[agent_override]

            # Validate agent type
            if agent_override not in ["claude_code", "gemini_cli", "codex_cli"]:
                self.console.print(
                    f"[red]Error:[/red] Invalid agent type '{agent_override}'"
                )
                self.console.print(
                    "[yellow]Available agents:[/yellow] claude_code, gemini_cli, codex_cli"
                )
                self.console.print(
                    "[yellow]Shortcuts:[/yellow] c/claude, g/gemini, o/codex"
                )
                return

            # Create temporary agent for this execution
            try:
                # Create a temporary config without saving to disk
                temp_config = Config()
                temp_config.config["default-agent"] = agent_override  # Modify in memory only
                execution_agent = AgentFactory.create_agent(self.logger, temp_config)
                self.logger.info(
                    f"🤖 Using {execution_agent.get_agent_name()} for this prompt execution"
                )
            except Exception as e:
                self.logger.error(f"Failed to create agent {agent_override}: {e}")
                execution_agent = self.agent
        else:
            execution_agent = self.agent
        return execution_agent

    def execute_prompt(self, prompt, agent_override=None):
        """Execute a one-time prompt with optional agent override."""
        execution_agent = self._get_execution_agent(agent_override)

        self.logger.info(f"Executing prompt: {prompt}")

        # Execute the prompt directly as arbitrary text
        result = execution_agent.run_prompt(inline_prompt=prompt)
        if result and result[0]:  # Check if result is not None and has content
            self.logger.info(result[0])
        else:
            self.logger.error("No response received from agent")

    def execute_command(self, command, arguments, agent_override=None):
        """Execute a one-time command."""
        execution_agent = self._get_execution_agent(agent_override)

        self.logger.info(f"Executing command: {command}")

        # Execute the command
        result = self.command_runner.run_command(command, arguments, execution_agent)

        if result:
            self.logger.info("Command completed successfully")
        else:
            self.logger.error("Command failed")

    def test_cron_job(self):
        """Test a specific cron job interactively."""
        # Load cron jobs from config
        jobs = self.config.get_cron_jobs()

        if not jobs:
            self.logger.error(
                "No cron jobs found in config. Edit ai4pkm_cli.json to add cron jobs."
            )
            return

        # Display available cron jobs
        self.console.print("\n[bold blue]Available Cron Jobs:[/bold blue]")
        for i, job in enumerate(jobs, 1):
            inline_prompt = job.get("inline_prompt")
            command = job.get("command")
            description = job.get("description", "No description")
            cron_expr = job.get("cron", "N/A")
            enabled = job.get("enabled", True)

            status_color = "green" if enabled else "dim red"
            status_text = "ENABLED" if enabled else "DISABLED"

            title = f'"{inline_prompt}"' if inline_prompt else f"\\[{command}]"
            self.console.print(
                f"[cyan]{i}.[/cyan] [bold]{title}[/bold] [{status_color}]({status_text})[/{status_color}]"
            )
            self.console.print(f"   Schedule: {cron_expr}")
            self.console.print(f"   Description: {description}\n")

        # Get user selection
        try:
            choice = input(f"Enter job number (1-{len(jobs)}) or 'q' to quit: ").strip()

            if choice.lower() == "q":
                self.logger.info("Test cancelled by user")
                return

            job_index = int(choice) - 1
            if job_index < 0 or job_index >= len(jobs):
                self.logger.error(
                    f"Invalid choice: {choice}. Please enter a number between 1 and {len(jobs)}"
                )
                return

        except ValueError:
            self.logger.error(f"Invalid input: {choice}. Please enter a number or 'q'")
            return
        except KeyboardInterrupt:
            self.logger.info("\nTest cancelled by user")
            return

        # Run the selected job
        selected_job = jobs[job_index]
        inline_prompt = selected_job.get("inline_prompt")
        command = selected_job.get("command")
        arguments = selected_job.get("arguments")
        title = f'"{inline_prompt}"' if inline_prompt else f"\\[{command}]"

        if not inline_prompt and not command:
            self.logger.error("Selected job has no inline_prompt or command")
            return

        self.logger.info(f"Testing cron job: {title}")
        self.console.print(f"\n[green]Running test for:[/green] {title}")

        start_time = time.time()

        try:
            if inline_prompt:
                result = self.agent.run_prompt(inline_prompt=inline_prompt)
            else:
                result = self.command_runner.run_command(command, arguments, self.agent)
            end_time = time.time()
            execution_time = end_time - start_time

            if inline_prompt:
                if result and result[0]:
                    self.logger.info(
                        f"✓ Test completed successfully ({execution_time:.1f}s)"
                    )
                    self.console.print(
                        f"\n[green]✓ Test completed successfully[/green]"
                    )
                    self.console.print(
                        f"[dim]Execution time: {execution_time:.2f}s | Response: {len(result[0])} chars[/dim]"
                    )
                else:
                    self.logger.error("✗ Test failed - no response received")
                    self.console.print(
                        f"\n[red]✗ Test failed - no response received[/red]"
                    )
            else:
                if result:
                    self.logger.info(
                        f"✓ Test completed successfully ({execution_time:.1f}s)"
                    )
                    self.console.print(
                        f"\n[green]✓ Test completed successfully[/green]"
                    )
                    self.console.print(
                        f"[dim]Execution time: {execution_time:.2f}s[/dim]"
                    )
                else:
                    self.logger.error("✗ Test failed - no response received")
                    self.console.print(
                        f"\n[red]✗ Test failed - no response received[/red]"
                    )
        except Exception as e:
            end_time = time.time()
            execution_time = end_time - start_time
            self.logger.error(f"✗ Test error ({execution_time:.1f}s): {e}")
            self.console.print(
                f"\n[red]✗ Test error after {execution_time:.2f}s: {e}[/red]"
            )

    def trigger_orchestrator_agent(self):
        """Trigger an orchestrator agent interactively."""
        from .orchestrator_cli import OrchestratorCLI
        from pathlib import Path

        # Initialize orchestrator CLI
        orch_cli = OrchestratorCLI()

        try:
            # Load orchestrator to get agents
            from .config import Config
            config_path = Path.cwd() / "ai4pkm_cli.json"
            if not config_path.exists():
                self.console.print(
                    f"[red]✗ Error:[/red] ai4pkm_cli.json not found in current directory"
                )
                self.console.print(f"[yellow]Current directory:[/yellow] {Path.cwd()}")
                self.console.print(
                    f"\n[cyan]Must run from vault directory containing ai4pkm_cli.json[/cyan]"
                )
                return

            config = Config(config_file=str(config_path))

            # Create orchestrator (but don't start daemon)
            from .orchestrator.core import Orchestrator
            orch = Orchestrator(vault_path=Path.cwd(), config=config)

            # Get agents that can be triggered manually
            # Include: agents with cron schedules (can run on-demand)
            # Exclude: pure file-based agents (no cron, need specific file events)
            agents_list = []
            for abbr, agent in orch.agent_registry.agents.items():
                # Show agents that have a cron schedule (scheduled agents)
                # These can be triggered manually and will work without specific file input
                if agent.cron:
                    agents_list.append(agent)
                # Also show agents with no input_path and no cron (manual agents)
                elif not agent.input_path or (isinstance(agent.input_path, list) and not any(agent.input_path)):
                    agents_list.append(agent)

            if not agents_list:
                self.logger.error("No triggerable agents found")
                self.console.print(
                    "[yellow]No agents available for manual trigger.[/yellow]"
                )
                self.console.print(
                    "[dim]File-based agents (EIC, CTP) require file events to trigger.[/dim]"
                )
                return

            # Sort by abbreviation for consistent display
            agents_list.sort(key=lambda a: a.abbreviation)

            # Display available agents
            self.console.print("\n[bold blue]Available Orchestrator Agents:[/bold blue]")
            for i, agent in enumerate(agents_list, 1):
                cron_info = f" [dim]cron: {agent.cron}[/dim]" if agent.cron else ""
                input_info = (
                    f" [dim]→ {agent.output_path}[/dim]" if agent.output_path else ""
                )

                self.console.print(
                    f"[cyan]{i}.[/cyan] [bold]{agent.name} ({agent.abbreviation})[/bold]"
                )
                self.console.print(f"   Category: {agent.category}{cron_info}{input_info}\n")

            # Get user selection
            try:
                choice = input(
                    f"Enter agent number (1-{len(agents_list)}) or 'q' to quit: "
                ).strip()

                if choice.lower() == "q":
                    self.logger.info("Trigger cancelled by user")
                    return

                agent_index = int(choice) - 1
                if agent_index < 0 or agent_index >= len(agents_list):
                    self.logger.error(
                        f"Invalid choice: {choice}. Please enter a number between 1 and {len(agents_list)}"
                    )
                    return

            except ValueError:
                self.logger.error(f"Invalid input: {choice}. Please enter a number or 'q'")
                return
            except KeyboardInterrupt:
                self.logger.info("\nTrigger cancelled by user")
                return

            # Trigger the selected agent
            selected_agent = agents_list[agent_index]
            self.logger.info(f"Triggering agent: {selected_agent.abbreviation}")
            self.console.print(
                f"\n[green]Triggering:[/green] {selected_agent.name} ({selected_agent.abbreviation})"
            )

            start_time = time.time()

            try:
                # Trigger agent once (synchronously)
                ctx = orch.trigger_agent_once(selected_agent.abbreviation)

                end_time = time.time()
                execution_time = end_time - start_time

                if ctx and ctx.success:
                    self.logger.info(
                        f"✓ Agent completed successfully ({execution_time:.1f}s)"
                    )
                    self.console.print(f"\n[green]✓ Agent completed successfully[/green]")
                    self.console.print(
                        f"[dim]Execution time: {execution_time:.2f}s[/dim]"
                    )
                    if ctx.task_file:
                        self.console.print(f"[dim]Task file: {ctx.task_file.name}[/dim]")
                else:
                    error_msg = ctx.error_message if ctx else "Unknown error"
                    self.logger.error(f"✗ Agent failed: {error_msg}")
                    self.console.print(f"\n[red]✗ Agent failed: {error_msg}[/red]")

            except Exception as e:
                end_time = time.time()
                execution_time = end_time - start_time
                self.logger.error(f"✗ Trigger error ({execution_time:.1f}s): {e}")
                self.console.print(
                    f"\n[red]✗ Trigger error after {execution_time:.2f}s: {e}[/red]"
                )

        except Exception as e:
            self.logger.error(f"Error initializing orchestrator: {e}")
            self.console.print(f"[red]✗ Error: {e}[/red]")

    def run_continuous(self):
        """Run continuously with cron job scheduler and web API server."""
        self.running = True
        self.cron_manager = CronManager(self.logger, self.agent)

        # Start web API server for custom chat endpoint
        self.server = Server(self.logger, self.config)
        self.server.start_server()
        
        # Display welcome message
        self._display_welcome()

        # Start cron manager and keep running
        self.cron_manager.start()

    def run_task_management(self):
        """Run continuous task management (full KTG+KTP pipeline)."""
        self.running = True

        # Show deprecation warning
        self.console.print("\n" + "=" * 80, style="yellow")
        self.console.print("⚠️  DEPRECATION WARNING: Task Management mode (KTG+KTP) is deprecated", style="bold yellow")
        self.console.print("   This system will be removed in a future version.", style="yellow")
        self.console.print("   Please migrate to the new orchestrator system:", style="yellow")
        self.console.print("   → Use: ai4pkm -o (or ai4pkm --orchestrator)", style="cyan")
        self.console.print("   → Migration guide: docs/_specs/2025-10-24 KTM to Multi-Agent Migration Plan - Claude Code.md", style="cyan")
        self.console.print("=" * 80 + "\n", style="yellow")

        # Display welcome message for task management mode
        welcome_text = Text()
        welcome_text.append(
            "PKM CLI - Task Management Mode\n", style="bold blue"
        )
        welcome_text.append(
            f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n", style="dim"
        )
        welcome_text.append("Press Ctrl+C to stop\n", style="dim")
        
        panel = Panel(welcome_text, title="Task Management (KTG+KTP)", border_style="blue")
        self.console.print(panel)
        
        # Process all existing tasks that need work at startup
        self.console.print("\n[cyan]🔍 Scanning for tasks that need processing...[/cyan]")

        # 1. Process PROCESSED tasks (evaluation pending)
        try:
            self.console.print("[dim]  • Checking PROCESSED tasks for evaluation...[/dim]")
            self.execute_command("ktp", {"status": "PROCESSED"})
        except Exception as e:
            self.logger.error(f"Error processing PROCESSED tasks: {e}")
            self.console.print(f"[yellow]⚠️  PROCESSED task processing failed: {e}[/yellow]")

        # 2. Check UNDER_REVIEW tasks (may be interrupted evaluations)
        try:
            self.console.print("[dim]  • Checking UNDER_REVIEW tasks (interrupted evaluations)...[/dim]")
            self._check_under_review_tasks()
        except Exception as e:
            self.logger.error(f"Error checking UNDER_REVIEW tasks: {e}")

        # 3. Check IN_PROGRESS tasks (may need retry or cleanup)
        try:
            self.console.print("[dim]  • Checking IN_PROGRESS tasks (potential interruptions)...[/dim]")
            # Note: IN_PROGRESS tasks will be logged but not auto-processed to avoid conflicts
            # They should be manually reviewed or will be picked up if status changes
            self._check_in_progress_tasks()
        except Exception as e:
            self.logger.error(f"Error checking IN_PROGRESS tasks: {e}")

        # 4. Process TBD tasks (ready to start)
        try:
            self.console.print("[dim]  • Processing TBD tasks...[/dim]")
            self.execute_command("ktp", {})
            self.console.print("[green]✅ Initial task processing complete[/green]\n")
        except Exception as e:
            self.logger.error(f"Error processing TBD tasks: {e}")
            self.console.print(f"[yellow]⚠️  TBD task processing failed: {e}[/yellow]\n")
        
        # Set up file watchdog with all task-related handlers
        from .watchdog.handlers.task_request_file_handler import TaskRequestFileHandler
        from .watchdog.handlers.task_processor import TaskProcessor
        from .watchdog.handlers.task_evaluator import TaskEvaluator
        from .watchdog.handlers.gobi_file_handler import GobiFileHandler
        from .watchdog.handlers.limitless_file_handler import LimitlessFileHandler
        from .watchdog.handlers.clipping_file_handler import ClippingFileHandler
        from .watchdog.handlers.hashtag_file_handler import HashtagFileHandler
        
        event_handler = FileWatchdogHandler(
            pattern_handlers=[
                ('AI/Tasks/Requests/*/*.json', TaskRequestFileHandler),
                ('AI/Tasks/*.md', TaskProcessor),
                ('AI/Tasks/*.md', TaskEvaluator),
                ('Ingest/Gobi/*.md', GobiFileHandler),
                ('Ingest/Limitless/*.md', LimitlessFileHandler),
                ('Ingest/Clippings/*.md', ClippingFileHandler),
                ('*.md', HashtagFileHandler),
            ],
            excluded_patterns=[
                '.git',
                'ai4pkm_cli',
            ],
            logger=self.logger,
            workspace_path=os.getcwd()
        )
        
        # Create and start observer
        observer = Observer()
        observer.schedule(event_handler, '.', recursive=True)
        observer.start()

        # Add periodic polling for TBD tasks (fallback for FSEvents issues)
        # macOS FSEvents doesn't reliably detect files created by subprocesses
        from .watchdog.tbd_poller import TBDTaskPoller

        # Get TaskProcessor handler instance to trigger manually
        task_processor_handler = None
        for pattern, handler_class in [
            ('AI/Tasks/*.md', TaskProcessor),
        ]:
            if handler_class == TaskProcessor:
                task_processor_handler = TaskProcessor(self.logger)
                break

        tbd_poller = None
        if task_processor_handler:
            # Get polling interval from config (default: 30 seconds)
            polling_interval = self.config.get('task_management.polling_interval', 30)

            if polling_interval > 0:
                tbd_poller = TBDTaskPoller(
                    workspace_path=os.getcwd(),
                    task_handler=task_processor_handler,
                    interval=polling_interval,
                    logger=self.logger
                )
                tbd_poller.start()

        self.console.print(f"\n[green]🐶 Task Management File Monitoring started[/green]")
        self.console.print(f"[dim]Watching: Gobi, Limitless, Clippings, Hashtags, Task Requests, TBD Tasks[/dim]")
        if tbd_poller:
            self.console.print(f"[dim]Polling: TBD tasks ({polling_interval}s interval as FSEvents fallback)[/dim]")
        self.console.print("\n" + "=" * 60)
        self.console.print("[bold]Live Logs:[/bold]")
        self.console.print("=" * 60)

        try:
            # Keep running until interrupted
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("Task management stopped by user")
        finally:
            observer.stop()
            if tbd_poller:
                tbd_poller.stop()
            observer.join()

    def _validate_task_output(self, task_data: Dict[str, Any], tasks_dir: str) -> Tuple[bool, str]:
        """Validate if task output files exist and look complete.

        Args:
            task_data: Task frontmatter data
            tasks_dir: Path to tasks directory

        Returns:
            (is_valid, reason) tuple where:
            - is_valid: True if output exists and looks complete
            - reason: Human-readable explanation
        """
        import re

        output = task_data.get('output', '')
        if not output:
            return (False, "No output property")

        # Parse wiki links [[path/to/file]]
        wiki_links = re.findall(r'\[\[([^\]]+)\]\]', output)

        if not wiki_links:
            return (False, "No wiki links in output")

        # Check each output file
        for link in wiki_links:
            # Convert wiki link to file path
            # Wiki links are relative to workspace root (e.g., AI/Articles/...)
            file_path = link

            # Construct full path from workspace root
            full_path = os.path.join(os.getcwd(), file_path)
            if not full_path.endswith('.md'):
                full_path += '.md'

            if not os.path.exists(full_path):
                return (False, f"Output file missing: {link}")

            # Check file has substance (>50 lines, has frontmatter)
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')

                    if len(lines) < 50:
                        return (False, f"Output too short: {len(lines)} lines")

                    if not content.startswith('---'):
                        return (False, "No frontmatter in output")

                # Output looks good
                return (True, f"Output validated: {len(lines)} lines")
            except Exception as e:
                return (False, f"Error reading output: {e}")

        # All outputs valid
        return (True, "All outputs valid")

    def _check_under_review_tasks(self):
        """Check and recover UNDER_REVIEW tasks stuck from old code bugs.

        Smart cleanup that validates task output:
        - If output valid → mark COMPLETED
        - If output invalid/missing → reset to PROCESSED for retry

        Note: Ignores old 'evaluated' flag - uses status as single source of truth.
        """
        from .commands.ktp_runner import KTPRunner

        runner = KTPRunner(self.logger, self.config)
        tasks = runner._get_task_queue(status='UNDER_REVIEW')

        if not tasks:
            return

        self.console.print(f"[yellow]⚠️  Found {len(tasks)} UNDER_REVIEW task(s)[/yellow]")

        completed = 0
        reset = 0

        for task in tasks:
            task_path = os.path.join(runner.tasks_dir, task['file'])
            task_data = runner._read_task_file(task_path)

            # Check if output exists and is valid
            is_valid, reason = self._validate_task_output(task_data, runner.tasks_dir)

            if is_valid:
                # Output complete → mark as COMPLETED
                runner._update_task_status(task['file'], 'COMPLETED',
                                          worker=task_data.get('worker', ''))
                self.console.print(f"[green]    ✅ Completed: {task['file']} ({reason})[/green]")
                completed += 1
            else:
                # Output invalid → reset to PROCESSED for retry
                runner._update_task_status(task['file'], 'PROCESSED',
                                          worker=task_data.get('worker', ''))
                self.console.print(f"[yellow]    ♻️  Reset: {task['file']} ({reason})[/yellow]")
                reset += 1

        # Summary
        if completed > 0:
            self.console.print(f"[cyan]✅ Marked {completed} task(s) as COMPLETED[/cyan]")
        if reset > 0:
            self.console.print(f"[cyan]♻️  Reset {reset} task(s) to PROCESSED for retry[/cyan]")

    def _check_in_progress_tasks(self):
        """Check for IN_PROGRESS tasks that may be stuck."""
        from .commands.ktp_runner import KTPRunner

        runner = KTPRunner(self.logger, self.config)
        tasks = runner._get_task_queue(status='IN_PROGRESS')

        if tasks:
            self.console.print(f"[yellow]⚠️  Found {len(tasks)} IN_PROGRESS task(s)[/yellow]")
            for task in tasks:
                self.console.print(f"[dim]    - {task['file']} (may need manual review)[/dim]")
            self.console.print("[dim]    These tasks will auto-retry if files are modified or on timeout[/dim]")

    def _display_welcome(self):
        """Display welcome message and status."""
        welcome_text = Text()
        welcome_text.append(
            "PKM CLI - Personal Knowledge Management\n", style="bold blue"
        )
        welcome_text.append(
            f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n", style="dim"
        )
        welcome_text.append("Press Ctrl+C to stop\n", style="dim")

        panel = Panel(welcome_text, title="PKM CLI", border_style="blue")
        self.console.print(panel)

        # Display web API server status
        if self.server and self.server.is_server_running():
            api_port = self.config.get_web_api_port()
            self.console.print(f"\n[green]🌐 Web Server: Running on port {api_port}[/green]")
        
        # Display cron job status
        jobs = self.cron_manager.get_jobs()
        if jobs:
            self.console.print(f"\n[green]Loaded {len(jobs)} cron jobs:[/green]")
            for job in jobs:
                inline_prompt = job.get("inline_prompt")
                command = job.get("command")
                title = f'"{inline_prompt}"' if inline_prompt else f"\\[{command}]"
                self.console.print(f"  • {title} - {job['cron']}")
        else:
            self.console.print(
                "\n[yellow]No cron jobs configured. Edit ai4pkm_cli.json to add cron jobs.[/yellow]"
            )

        self.console.print("\n" + "=" * 60)
        self.console.print("[bold]Live Logs:[/bold]")
        self.console.print("=" * 60)

    def list_agents(self):
        """List available AI agents and their status."""
        self.console.print("\n[bold blue]Available AI Agents:[/bold blue]")

        agents = AgentFactory.list_available_agents(self.logger)
        current_agent = self.config.get_agent()

        for agent in agents:
            current_marker = "🔥" if agent["type"] == current_agent else "  "
            self.console.print(
                f"{current_marker} [cyan]{agent['type']}[/cyan]: {agent['name']} - {agent['status']}"
            )

        self.console.print(f"\n[green]Current agent:[/green] {current_agent}")
        self.console.print(
            f"[dim]Edit ai4pkm_cli.json to change the default-agent[/dim]"
        )

    def show_config(self):
        """Show current configuration."""
        self.console.print("\n[bold blue]Current Configuration:[/bold blue]")

        # Show agent configuration
        current_agent = self.config.get_agent()
        agent_config = self.config.get_agent_config()

        self.console.print(f"[green]Agent:[/green] {current_agent}")
        self.console.print(f"[green]Agent Name:[/green] {self.agent.get_agent_name()}")
        self.console.print(
            f"[green]Agent Available:[/green] {'✅ Yes' if self.agent.is_available() else '❌ No'}"
        )

        if agent_config:
            self.console.print(f"\n[cyan]Agent Configuration:[/cyan]")
            for key, value in agent_config.items():
                self.console.print(f"  {key}: {value}")

        # Show config file location
        self.console.print(f"\n[dim]Config file: {self.config.config_file}[/dim]")

    def set_agent(self, agent_type: str):
        """Set the current AI agent."""
        try:
            # Map shorthand names to full agent types
            agent_shortcuts = {
                "c": "claude_code",
                "g": "gemini_cli",
                "o": "codex_cli",
                "claude": "claude_code",
                "gemini": "gemini_cli",
                "codex": "codex_cli",
            }

            # Use shorthand mapping if provided
            if agent_type in agent_shortcuts:
                agent_type = agent_shortcuts[agent_type]

            # Validate agent type
            if agent_type not in ["claude_code", "gemini_cli", "codex_cli"]:
                self.console.print(
                    f"[red]Error:[/red] Invalid agent type '{agent_type}'"
                )
                self.console.print(
                    "[yellow]Available agents:[/yellow] claude_code, gemini_cli, codex_cli"
                )
                self.console.print(
                    "[yellow]Shortcuts:[/yellow] c/claude, g/gemini, o/codex"
                )
                return

            # Set the agent in config
            self.config.set_agent(agent_type)

            # Create new agent instance
            self.agent = AgentFactory.create_agent(self.logger, self.config)

            # Show success message
            self.console.print(f"[green]✓ Agent set to:[/green] {agent_type}")
            self.console.print(
                f"[green]Agent Name:[/green] {self.agent.get_agent_name()}"
            )
            self.console.print(
                f"[green]Agent Available:[/green] {'✅ Yes' if self.agent.is_available() else '❌ No'}"
            )

            if not self.agent.is_available():
                self.console.print(
                    f"[yellow]⚠️  Warning:[/yellow] Selected agent is not available. The system may fall back to other agents."
                )

        except Exception as e:
            self.console.print(f"[red]Error setting agent:[/red] {e}")
            self.logger.error(f"Failed to set agent {agent_type}: {e}")

    def show_default_info(self):
        """Show default information with current config and usage instructions."""
        # Show header
        welcome_text = Text()
        welcome_text.append("AI4PKM CLI", style="bold blue")
        welcome_text.append(" - Personal Knowledge Management Framework", style="blue")

        panel = Panel(welcome_text, border_style="blue")
        self.console.print(panel)

        # Show current configuration
        self.console.print(f"\n[bold green]Current Configuration:[/bold green]")
        self.console.print(f"🤖 Agent: {self.agent.get_agent_name()}")
        self.console.print(f"📝 Log file: {self.logger.log_file}")

        # Show cron jobs
        jobs = self.cron_manager.get_jobs() if hasattr(self, "cron_manager") else []
        if not jobs:
            # Load jobs to show them
            from .cron_manager import CronManager

            temp_cron_manager = CronManager(self.logger, self.agent)
            jobs = temp_cron_manager.get_jobs()

        if jobs:
            self.console.print(
                f"\n[bold cyan]Scheduled Jobs ({len(jobs)}):[/bold cyan]"
            )
            for i, job in enumerate(jobs, 1):
                agent_name = job.get("agent")
                if agent_name:
                    agent_shortcuts = {
                        "claude_code": "claude",
                        "gemini_cli": "gemini",
                        "codex_cli": "codex",
                    }
                    agent_display = f" [green]\\[{agent_shortcuts.get(agent_name, agent_name)}][/green]"
                else:
                    agent_display = f" [dim]\\[default][/dim]"
                # Get job name with proper formatting convention
                inline_prompt = job.get("inline_prompt")
                command = job.get("command")
                job_name = (
                    f'"{inline_prompt}"'
                    if inline_prompt
                    else f"[{command}]"
                    if command
                    else "Unknown"
                )
                self.console.print(
                    f"  {i}. {job_name} - {job.get('cron', 'No schedule')}{agent_display}"
                )
        else:
            self.console.print(f"\n[dim]No cron jobs configured.[/dim]")

        # Show usage instructions
        self.console.print(f"\n[bold yellow]Quick Commands:[/bold yellow]")
        self.console.print(f'  [cyan]ai4pkm -p "GDR"[/cyan]              Run a prompt')
        self.console.print(
            f'  [cyan]ai4pkm -a g -p "TKI"[/cyan]          Run prompt with specific agent'
        )
        self.console.print(
            f"  [cyan]ai4pkm -o[/cyan]                     Start orchestrator (multi-agent system)"
        )
        self.console.print(
            f"  [cyan]ai4pkm -c[/cyan]                     Start cron scheduler + web server"
        )
        self.console.print(
            f"  [cyan]ai4pkm -r[/cyan]                     Run a cron job once"
        )
        self.console.print(
            f"  [cyan]ai4pkm -t[/cyan]                     Trigger orchestrator agent"
        )
        self.console.print(
            f"  [cyan]ai4pkm --list-agents[/cyan]          List available agents"
        )
        self.console.print(
            f"  [cyan]ai4pkm --show-config[/cyan]          Show config (edit ai4pkm_cli.json for settings)"
        )

        self.console.print(f"\n[bold yellow]Agent Shortcuts:[/bold yellow]")
        self.console.print(
            f"  [green]c/claude[/green], [green]g/gemini[/green], [green]o/codex[/green]"
        )

        self.console.print(f"\n[dim]Use 'ai4pkm --help' for all options[/dim]")
