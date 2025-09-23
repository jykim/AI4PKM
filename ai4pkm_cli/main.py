#!/usr/bin/env python3
"""Main entry point for PKM CLI."""

import signal
import sys
import click
from .cli import PKMApp
import logging

def signal_handler(sig, frame):
    """Handle SIGINT (Ctrl+C) gracefully."""
    print("\n\nShutting down PKM CLI...")
    sys.exit(0)


@click.command()
@click.option('-p', '--prompt', help='Execute a one-time prompt')
@click.option('-cmd', '--command', help='Execute a one-time command')
@click.option('-t', '--test', 'test_cron', is_flag=True, help='Test a specific cron job interactively')
@click.option('-c', '--cron', 'run_cron', is_flag=True, help='Run continuous cron job scheduler')
@click.option('-a', '--agent', help='Override agent for prompt execution (c/claude, g/gemini, o/codex) - only usable with -p')
@click.option('-d', '--debug', is_flag=True, help='Enable debug logging (shows shell commands for CLI agents)')
@click.option('--list-agents', is_flag=True, help='List available AI agents and their status')
@click.option('--show-config', is_flag=True, help='Show current configuration')
def main(prompt, command, test_cron, run_cron, agent, debug, list_agents, show_config):
    """PKM CLI - Personal Knowledge Management framework."""
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    if debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    
    # Initialize the PKM application
    # Suppress default agent logging when using agent override for prompts
    suppress_logging = bool(agent and prompt)
    app = PKMApp(suppress_agent_logging=suppress_logging)
    
    if list_agents:
        # List available agents
        app.list_agents()
    elif show_config:
        # Show current configuration
        app.show_config()
    elif agent and not prompt:
        # Error: agent option can only be used with prompts
        click.echo("❌ Error: The --agent (-a) option can only be used with --prompt (-p)")
        click.echo("   Use 'ai4pkm --show-config' to view/change the default agent in ai4pkm_cli.json")
        sys.exit(1)
    elif prompt:
        # Execute the prompt (with optional agent for this execution only)
        app.execute_prompt(prompt, agent)
    elif command:
        # Execute the command
        app.execute_command(command)
    elif test_cron:
        # Test a specific cron job
        app.test_cron_job()
    elif run_cron:
        # Run continuously with cron jobs and log display
        app.run_continuous()
    else:
        # Show default information (config and instructions)
        app.show_default_info()


if __name__ == '__main__':
    main()

