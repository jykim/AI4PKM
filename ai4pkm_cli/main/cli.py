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
from .interactive import run_interactive_mode
from .update import update_cli
from .template import template_group


def signal_handler(sig, frame):
    """Handle SIGINT (Ctrl+C) gracefully."""
    print("\n\nShutting down PKM CLI...")
    sys.exit(0)


@click.group(invoke_without_command=True)
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
    is_flag=False,
    flag_value="",
    default=None,
    help="Trigger an orchestrator agent (optionally specify abbreviation, e.g., -t EIC)",
)
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
    "-sp",
    "--system-prompt",
    "system_prompt",
    type=str,
    help="System prompt to use for the agent",
)
@click.option(
    "-spf",
    "--system-prompt-file",
    "system_prompt_file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path),
    help="Path to file containing system prompt to use for the agent",
)
@click.option(
    "-asp",
    "--append-system-prompt",
    "append_system_prompt",
    type=str,
    help="Additional system prompt to append to the base system prompt",
)
@click.option(
    "-aspf",
    "--append-system-prompt-file",
    "append_system_prompt_file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path),
    help="Path to file containing additional system prompt to append",
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
@click.option(
    "-i",
    "--interactive",
    "interactive",
    is_flag=True,
    help="Launch interactive mode with Claude Code (streaming JSON I/O)",
)
@click.pass_context
def main(
    ctx,
    orchestrator,
    orchestrator_status,
    trigger_agent,
    debug,
    list_agents,
    show_config,
    working_dir,
    system_prompt,
    system_prompt_file,
    append_system_prompt,
    append_system_prompt_file,
    prompt_text,
    session_id,
    interactive,
):
    """PKM CLI - Personal Knowledge Management framework."""
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)

    if debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    # If a subcommand was invoked, let it handle execution
    if ctx.invoked_subcommand is not None:
        return

    # Handle legacy flag-based commands
    if interactive:
        run_interactive_mode(working_dir=working_dir, system_prompt=system_prompt, system_prompt_file=system_prompt_file, append_system_prompt=append_system_prompt, append_system_prompt_file=append_system_prompt_file, session_id=session_id)
    elif orchestrator_status:
        show_orchestrator_status(working_dir=working_dir)
    elif orchestrator:
        run_orchestrator_daemon(debug=debug, working_dir=working_dir)
    elif trigger_agent is not None:
        # trigger_agent can be "" (flag used without value) or an abbreviation string
        trigger_orchestrator_agent(abbreviation=trigger_agent or None, working_dir=working_dir)
    elif prompt_text:
        execute_prompt_with_session(
            prompt=prompt_text,
            session_id=session_id,
            working_dir=working_dir,
            system_prompt=system_prompt,
            system_prompt_file=system_prompt_file,
            append_system_prompt=append_system_prompt,
            append_system_prompt_file=append_system_prompt_file
        )
    elif list_agents:
        list_agents_handler()
    elif show_config:
        show_config_handler()
    else:
        click.echo(ctx.get_help())


# Register subcommands
main.add_command(update_cli, name="update")
main.add_command(template_group, name="template")


if __name__ == "__main__":
    main()
