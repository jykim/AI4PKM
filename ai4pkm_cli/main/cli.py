#!/usr/bin/env python3
"""Main entry point for PKM CLI."""

import signal
import sys
import click
import logging
from pathlib import Path

from .trigger_agent import trigger_orchestrator_agent
from .list_agents import list_agents as list_agents_handler
from .show_config import show_config as show_config_handler
from .orchestrator import run_orchestrator_daemon, show_orchestrator_status, execute_prompt_with_session


def signal_handler(sig, frame):
    """Handle SIGINT (Ctrl+C) gracefully."""
    print("\n\nShutting down PKM CLI...")
    sys.exit(0)


@click.command()
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
    "-t",
    "--trigger-agent",
    "trigger_agent",
    is_flag=True,
    help="Trigger an orchestrator agent interactively once",
)
@click.argument("agent_abbreviation", required=False)
@click.option("-d", "--debug", is_flag=True, help="Enable debug logging")
@click.option(
    "--list-agents", is_flag=True, help="List available AI agents and their status"
)
@click.option("--show-config", is_flag=True, help="Show current configuration")
@click.option(
    "-w",
    "--working-dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=str),
    help="Working directory to launch the agent from",
)
@click.option(
    "-p",
    "--prompt",
    "prompt_text",
    type=str,
    help="Execute a one-time prompt with Claude agent",
)
@click.option(
    "-s",
    "--session-id",
    "session_id",
    type=str,
    help="Session ID - automatically resumes if exists, creates if not",
)
def main(
    orchestrator,
    orchestrator_status,
    trigger_agent,
    agent_abbreviation,
    debug,
    list_agents,
    show_config,
    working_dir,
    prompt_text,
    session_id,
):
    """PKM CLI - Personal Knowledge Management framework."""
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)

    if debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    if orchestrator_status:
        show_orchestrator_status(working_dir=working_dir)
    elif orchestrator:
        run_orchestrator_daemon(debug=debug, working_dir=working_dir)
    elif trigger_agent:
        trigger_orchestrator_agent(abbreviation=agent_abbreviation, working_dir=working_dir)
    elif prompt_text:
        execute_prompt_with_session(
            prompt=prompt_text,
            session_id=session_id,
            working_dir=working_dir
        )
    elif list_agents:
        list_agents_handler()
    elif show_config:
        show_config_handler()
    else:
        click.echo(main.get_help(click.get_current_context()))


if __name__ == "__main__":
    main()

