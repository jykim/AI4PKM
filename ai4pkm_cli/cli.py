"""Main PKM CLI application class."""

import os
import time
import glob
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from .cron_manager import CronManager
from .logger import Logger
from .config import Config
from .agent_factory import AgentFactory
from .commands.command_runner import CommandRunner

class PKMApp:
    """Main PKM CLI application."""
    
    def __init__(self, suppress_agent_logging=False):
        """Initialize the PKM application."""
        self.console = Console()
        self.logger = Logger(console_output=True)  # Enable console output for main logger
        self.config = Config()
        # Temporarily suppress agent logging if requested
        if suppress_agent_logging:
            original_info = self.logger.info
            self.logger.info = lambda msg: None if "🤖 Using agent:" in msg else original_info(msg)
            self.agent = AgentFactory.create_agent(self.logger, self.config)
            self.logger.info = original_info  # Restore logging
        else:
            self.agent = AgentFactory.create_agent(self.logger, self.config)
        self.command_runner = CommandRunner(self.logger, self.config)
        self.running = False

    def find_matching_prompt(self, prompt_query):
        """Find matching prompt in the Prompts folder."""
        prompts_dir = "_Settings_/Prompts"
        
        # Get all .md files in prompts directory (excluding subdirectories for now)
        prompt_files = glob.glob(os.path.join(prompts_dir, "*.md"))
        
        # Extract base names without extension and path
        available_prompts = []
        for file_path in prompt_files:
            base_name = os.path.basename(file_path)
            if base_name.endswith('.md'):
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
            if '(' in prompt_name and prompt_name.endswith(')'):
                # Extract shortcut code from parentheses
                paren_start = prompt_name.rfind('(')
                shortcut = prompt_name[paren_start + 1:-1].strip()
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
            self.logger.warning(f"Multiple prompts match '{prompt_query}': {', '.join(matches)}")
            self.logger.info(f"Using first match: {matches[0]}")
            return matches[0]
        
        # List available prompts if no match found
        self.logger.error(f"No prompt found matching '{prompt_query}'")
        self.logger.info("Available prompts:")
        for prompt_name, file_path in available_prompts:
            # Show shortcut code if available
            shortcut = ""
            if '(' in prompt_name and prompt_name.endswith(')'):
                paren_start = prompt_name.rfind('(')
                shortcut = f" [{prompt_name[paren_start + 1:-1]}]"
            self.logger.info(f"  • {prompt_name}{shortcut}")
        
        return None

    def _get_execution_agent(self, agent_override=None):
        """Determine which agent to use for execution."""
        if agent_override:
            # Map shorthand names to full agent types
            agent_shortcuts = {
                'c': 'claude_code',
                'g': 'gemini_cli', 
                'o': 'codex_cli',
                'claude': 'claude_code',
                'gemini': 'gemini_cli',
                'codex': 'codex_cli'
            }
            
            # Use shorthand mapping if provided
            if agent_override in agent_shortcuts:
                agent_override = agent_shortcuts[agent_override]
            
            # Validate agent type
            if agent_override not in ['claude_code', 'gemini_cli', 'codex_cli']:
                self.console.print(f"[red]Error:[/red] Invalid agent type '{agent_override}'")
                self.console.print("[yellow]Available agents:[/yellow] claude_code, gemini_cli, codex_cli")
                self.console.print("[yellow]Shortcuts:[/yellow] c/claude, g/gemini, o/codex")
                return
                
            # Create temporary agent for this execution
            try:
                # Create a temporary config without saving to disk
                temp_config = Config()
                temp_config.config['default-agent'] = agent_override  # Modify in memory only
                execution_agent = AgentFactory.create_agent(self.logger, temp_config)
                self.logger.info(f"🤖 Using {execution_agent.get_agent_name()} for this prompt execution")
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

    def execute_command(self, command, agent_override=None):
        """Execute a one-time command."""
        execution_agent = self._get_execution_agent(agent_override)
       
        self.logger.info(f"Executing command: {command}")

        # Execute the command
        result = self.command_runner.run_command(command, execution_agent)

        if result:
            self.logger.info("Command completed successfully")
        else:
            self.logger.error("Command failed")

    
    def test_cron_job(self):
        """Test a specific cron job interactively."""
        # Load cron jobs from config
        jobs = self.config.get_cron_jobs()
        
        if not jobs:
            self.logger.error("No cron jobs found in config. Edit ai4pkm_cli.json to add cron jobs.")
            return
        
        # Display available cron jobs
        self.console.print("\n[bold blue]Available Cron Jobs:[/bold blue]")
        for i, job in enumerate(jobs, 1):
            inline_prompt = job.get('inline_prompt')
            command = job.get('command')
            description = job.get('description', 'No description')
            cron_expr = job.get('cron', 'N/A')
            enabled = job.get('enabled', True)
            
            status_color = "green" if enabled else "dim red"
            status_text = "ENABLED" if enabled else "DISABLED"
            
            title = f'"{inline_prompt}"' if inline_prompt else f"\\[{command}]"
            self.console.print(f"[cyan]{i}.[/cyan] [bold]{title}[/bold] [{status_color}]({status_text})[/{status_color}]")
            self.console.print(f"   Schedule: {cron_expr}")
            self.console.print(f"   Description: {description}\n")
        
        # Get user selection
        try:
            choice = input(f"Enter job number (1-{len(jobs)}) or 'q' to quit: ").strip()
            
            if choice.lower() == 'q':
                self.logger.info("Test cancelled by user")
                return
            
            job_index = int(choice) - 1
            if job_index < 0 or job_index >= len(jobs):
                self.logger.error(f"Invalid choice: {choice}. Please enter a number between 1 and {len(jobs)}")
                return
                
        except ValueError:
            self.logger.error(f"Invalid input: {choice}. Please enter a number or 'q'")
            return
        except KeyboardInterrupt:
            self.logger.info("\nTest cancelled by user")
            return
        
        # Run the selected job
        selected_job = jobs[job_index]
        inline_prompt = selected_job.get('inline_prompt')
        command = selected_job.get('command')
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
                result = self.command_runner.run_command(command, self.agent)
            end_time = time.time()
            execution_time = end_time - start_time
            
            if inline_prompt:
                if result and result[0]:
                    self.logger.info(f"✓ Test completed successfully ({execution_time:.1f}s)")
                    self.console.print(f"\n[green]✓ Test completed successfully[/green]")
                    self.console.print(f"[dim]Execution time: {execution_time:.2f}s | Response: {len(result[0])} chars[/dim]")
                else:
                    self.logger.error("✗ Test failed - no response received")
                    self.console.print(f"\n[red]✗ Test failed - no response received[/red]")
            else:
                if result:
                    self.logger.info(f"✓ Test completed successfully ({execution_time:.1f}s)")
                    self.console.print(f"\n[green]✓ Test completed successfully[/green]")
                    self.console.print(f"[dim]Execution time: {execution_time:.2f}s[/dim]")
                else:
                    self.logger.error("✗ Test failed - no response received")
                    self.console.print(f"\n[red]✗ Test failed - no response received[/red]")
        except Exception as e:
            end_time = time.time()
            execution_time = end_time - start_time
            self.logger.error(f"✗ Test error ({execution_time:.1f}s): {e}")
            self.console.print(f"\n[red]✗ Test error after {execution_time:.2f}s: {e}[/red]")
            
    def run_continuous(self):
        """Run continuously with cron jobs and log display."""
        self.running = True
        self.cron_manager = CronManager(self.logger, self.agent)
        
        # Display welcome message
        self._display_welcome()
        
        self.cron_manager.start()
        
    def _display_welcome(self):
        """Display welcome message and status."""
        welcome_text = Text()
        welcome_text.append("PKM CLI - Personal Knowledge Management\n", style="bold blue")
        welcome_text.append(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n", style="dim")
        welcome_text.append("Press Ctrl+C to stop\n", style="dim")
        
        panel = Panel(welcome_text, title="PKM CLI", border_style="blue")
        self.console.print(panel)
        
        # Display cron job status
        jobs = self.cron_manager.get_jobs()
        if jobs:
            self.console.print(f"\n[green]Loaded {len(jobs)} cron jobs:[/green]")
            for job in jobs:
                inline_prompt = job.get('inline_prompt')
                command = job.get('command')
                title = f'"{inline_prompt}"' if inline_prompt else f"\\[{command}]"
                self.console.print(f"  • {title} - {job['cron']}")
        else:
            self.console.print("\n[yellow]No cron jobs configured. Edit ai4pkm_cli.json to add cron jobs.[/yellow]")
        
        self.console.print("\n" + "="*60)
        self.console.print("[bold]Live Logs:[/bold]")
        self.console.print("="*60)
        
    def list_agents(self):
        """List available AI agents and their status."""
        self.console.print("\n[bold blue]Available AI Agents:[/bold blue]")
        
        agents = AgentFactory.list_available_agents(self.logger)
        current_agent = self.config.get_agent()
        
        for agent in agents:
            current_marker = "🔥" if agent['type'] == current_agent else "  "
            self.console.print(f"{current_marker} [cyan]{agent['type']}[/cyan]: {agent['name']} - {agent['status']}")
            
        self.console.print(f"\n[green]Current agent:[/green] {current_agent}")
        self.console.print(f"[dim]Edit ai4pkm_cli.json to change the default-agent[/dim]")
        
    def show_config(self):
        """Show current configuration."""
        self.console.print("\n[bold blue]Current Configuration:[/bold blue]")
        
        # Show agent configuration
        current_agent = self.config.get_agent()
        agent_config = self.config.get_agent_config()
        
        self.console.print(f"[green]Agent:[/green] {current_agent}")
        self.console.print(f"[green]Agent Name:[/green] {self.agent.get_agent_name()}")
        self.console.print(f"[green]Agent Available:[/green] {'✅ Yes' if self.agent.is_available() else '❌ No'}")
        
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
                'c': 'claude_code',
                'g': 'gemini_cli', 
                'o': 'codex_cli',
                'claude': 'claude_code',
                'gemini': 'gemini_cli',
                'codex': 'codex_cli'
            }
            
            # Use shorthand mapping if provided
            if agent_type in agent_shortcuts:
                agent_type = agent_shortcuts[agent_type]
            
            # Validate agent type
            if agent_type not in ['claude_code', 'gemini_cli', 'codex_cli']:
                self.console.print(f"[red]Error:[/red] Invalid agent type '{agent_type}'")
                self.console.print("[yellow]Available agents:[/yellow] claude_code, gemini_cli, codex_cli")
                self.console.print("[yellow]Shortcuts:[/yellow] c/claude, g/gemini, o/codex")
                return
                
            # Set the agent in config
            self.config.set_agent(agent_type)
            
            # Create new agent instance
            self.agent = AgentFactory.create_agent(self.logger, self.config)
            
            # Show success message
            self.console.print(f"[green]✓ Agent set to:[/green] {agent_type}")
            self.console.print(f"[green]Agent Name:[/green] {self.agent.get_agent_name()}")
            self.console.print(f"[green]Agent Available:[/green] {'✅ Yes' if self.agent.is_available() else '❌ No'}")
            
            if not self.agent.is_available():
                self.console.print(f"[yellow]⚠️  Warning:[/yellow] Selected agent is not available. The system may fall back to other agents.")
                
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
        jobs = self.cron_manager.get_jobs() if hasattr(self, 'cron_manager') else []
        if not jobs:
            # Load jobs to show them
            from .cron_manager import CronManager
            temp_cron_manager = CronManager(self.logger, self.agent)
            jobs = temp_cron_manager.get_jobs()
            
        if jobs:
            self.console.print(f"\n[bold cyan]Scheduled Jobs ({len(jobs)}):[/bold cyan]")
            for i, job in enumerate(jobs, 1):
                agent_name = job.get('agent')
                if agent_name:
                    agent_shortcuts = {'claude_code': 'claude', 'gemini_cli': 'gemini', 'codex_cli': 'codex'}
                    agent_display = f" [green]\\[{agent_shortcuts.get(agent_name, agent_name)}][/green]"
                else:
                    agent_display = f" [dim]\\[default][/dim]"
                # Get job name with proper formatting convention
                inline_prompt = job.get('inline_prompt')
                command = job.get('command')
                job_name = f'"{inline_prompt}"' if inline_prompt else f"[{command}]" if command else "Unknown"
                self.console.print(f"  {i}. {job_name} - {job.get('cron', 'No schedule')}{agent_display}")
        else:
            self.console.print(f"\n[dim]No cron jobs configured.[/dim]")
        
        # Show usage instructions
        self.console.print(f"\n[bold yellow]Quick Commands:[/bold yellow]")
        self.console.print(f"  [cyan]ai4pkm -p \"GDR\"[/cyan]              Run a prompt")
        self.console.print(f"  [cyan]ai4pkm -a g -p \"TKI\"[/cyan]          Run prompt with specific agent")  
        self.console.print(f"  [cyan]ai4pkm -c[/cyan]                     Start cron scheduler")
        self.console.print(f"  [cyan]ai4pkm -t[/cyan]                     Test cron jobs")
        self.console.print(f"  [cyan]ai4pkm --list-agents[/cyan]          List available agents")
        self.console.print(f"  [cyan]ai4pkm --show-config[/cyan]          Show config (edit ai4pkm_cli.json for settings)")
        
        self.console.print(f"\n[bold yellow]Agent Shortcuts:[/bold yellow]")
        self.console.print(f"  [green]c/claude[/green], [green]g/gemini[/green], [green]o/codex[/green]")
        
        self.console.print(f"\n[dim]Use 'ai4pkm --help' for all options[/dim]")