#!/usr/bin/env python3
"""Main entry point for PKM CLI."""

import signal
import sys
import click
from .cli import PKMApp
import logging

from dotenv import load_dotenv
import json

load_dotenv()


def signal_handler(sig, frame):
    """Handle SIGINT (Ctrl+C) gracefully."""
    print("\n\nShutting down PKM CLI...")
    sys.exit(0)


@click.command()
@click.option("-p", "--prompt", help="Execute a one-time prompt")
@click.option("-cmd", "--command", help="Execute a one-time command")
@click.option("-args", "--arguments", help="Arguments for the command", default="{}")
@click.option(
    "--ktp",
    is_flag=True,
    help="Run Knowledge Task Processor (process tasks from AI/Tasks/)",
)
@click.option(
    "--ktp-task",
    help="Process specific task file with KTP (e.g., 2025-10-16-task.md)",
)
@click.option(
    "--ktp-priority",
    type=click.Choice(["P0", "P1", "P2", "P3"], case_sensitive=False),
    help="Filter KTP tasks by priority",
)
@click.option(
    "--ktp-status",
    type=click.Choice(["TBD", "IN_PROGRESS", "PROCESSED", "UNDER_REVIEW"], case_sensitive=False),
    help="Filter KTP tasks by status (default: TBD)",
)
@click.option(
    "-r",
    "--run-job-once",
    "run_job_once",
    is_flag=True,
    help="Test/run a specific cron job interactively once",
)
@click.option(
    "-t",
    "--trigger-agent",
    "trigger_agent",
    is_flag=True,
    help="Trigger an orchestrator agent interactively once",
)
@click.option(
    "--task-management",
    "task_management",
    is_flag=True,
    help="[DEPRECATED] Run continuous task management (KTG+KTP pipeline with file monitoring)",
)
@click.option(
    "-c", "--cron", "run_cron", is_flag=True, help="Run continuous cron job scheduler and web server"
)
@click.option(
    "-a",
    "--agent",
    help="Override agent for prompt execution (c/claude, g/gemini, o/codex) - only usable with -p",
)
@click.option("-d", "--debug", is_flag=True, help="Enable debug logging")
@click.option(
    "--list-agents", is_flag=True, help="List available AI agents and their status"
)
@click.option("--show-config", is_flag=True, help="Show current configuration")
@click.option(
    "-o",
    "--orchestrator",
    "orchestrator",
    is_flag=True,
    help="Run orchestrator daemon (new multi-agent system)",
)
@click.option(
    "--orchestrator-status",
    is_flag=True,
    help="Show orchestrator status and loaded agents",
)
@click.option(
    "--max-concurrent",
    type=int,
    default=3,
    help="Maximum concurrent executions for orchestrator (default: 3)",
)
def main(
    prompt,
    command,
    arguments,
    ktp,
    ktp_task,
    ktp_priority,
    ktp_status,
    run_job_once,
    trigger_agent,
    task_management,
    run_cron,
    agent,
    debug,
    list_agents,
    show_config,
    orchestrator,
    orchestrator_status,
    max_concurrent,
):
    """PKM CLI - Personal Knowledge Management framework."""
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)

    if debug:
        logging.basicConfig(level=logging.DEBUG)
        # Suppress noisy debug logs from watchdog/fsevents
        logging.getLogger('fsevents').setLevel(logging.WARNING)
        logging.getLogger('watchdog').setLevel(logging.WARNING)
    else:
        logging.basicConfig(level=logging.INFO)

    # Initialize the PKM application
    # Suppress default agent logging when using agent override for prompts
    suppress_logging = bool(agent and prompt)
    app = PKMApp(suppress_agent_logging=suppress_logging)

    if orchestrator or orchestrator_status:
        # Use new orchestrator system
        from .orchestrator_cli import OrchestratorCLI
        orch_cli = OrchestratorCLI()

        if orchestrator_status:
            orch_cli.show_status()
        else:
            orch_cli.run_daemon(max_concurrent=max_concurrent, debug=debug)
    elif list_agents:
        # List available agents
        app.list_agents()
    elif show_config:
        # Show current configuration
        app.show_config()
    elif ktp or ktp_task:
        # Run Knowledge Task Processor
        click.echo("=" * 80)
        click.echo("⚠️  DEPRECATION WARNING: --ktp flag is deprecated")
        click.echo("   This system will be removed in a future version.")
        click.echo("   Please migrate to the new orchestrator system:")
        click.echo("   → Use: ai4pkm -o (or ai4pkm --orchestrator)")
        click.echo("   → Migration guide: docs/_specs/2025-10-24 KTM to Multi-Agent Migration Plan - Claude Code.md")
        click.echo("=" * 80)
        click.echo()

        ktp_args = {}
        if ktp_task:
            ktp_args["task"] = ktp_task
        if ktp_priority:
            ktp_args["priority"] = ktp_priority.upper()
        if ktp_status:
            ktp_args["status"] = ktp_status.upper()

        app.execute_command("ktp", ktp_args)
    elif agent and not prompt:
        # Error: agent option can only be used with prompts
        click.echo(
            "❌ Error: The --agent (-a) option can only be used with --prompt (-p)"
        )
        click.echo(
            "   Use 'ai4pkm --show-config' to view/change the default agent in ai4pkm_cli.json"
        )
        sys.exit(1)
    elif prompt:
        # Execute the prompt (with optional agent for this execution only)
        app.execute_prompt(prompt, agent)
    elif command:
        # Execute the command
        app.execute_command(command, json.loads(arguments))
    elif run_job_once:
        # Test/run a specific cron job once
        app.test_cron_job()
    elif trigger_agent:
        # Trigger an orchestrator agent interactively once
        app.trigger_orchestrator_agent()
    elif task_management:
        # Run continuous task management (KTG+KTP pipeline)
        click.echo("=" * 80)
        click.echo("⚠️  DEPRECATION WARNING: --task-management (-t) flag is deprecated")
        click.echo("   This system will be removed in a future version.")
        click.echo("   Please migrate to the new orchestrator system:")
        click.echo("   → Use: ai4pkm -o (or ai4pkm --orchestrator)")
        click.echo("   → Migration guide: docs/_specs/2025-10-24 KTM to Multi-Agent Migration Plan - Claude Code.md")
        click.echo("=" * 80)
        click.echo()

        app.run_task_management()
    elif run_cron:
        # Run continuously with cron jobs and web server
        app.run_continuous()
    else:
        # Show default information (config and instructions)
        app.show_default_info()


if __name__ == "__main__":
    main()