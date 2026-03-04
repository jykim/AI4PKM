#!/usr/bin/env python3
"""Trigger command for orchestrator agents."""

import click

from .trigger_agent import trigger_orchestrator_agent


@click.command("trigger")
@click.argument("agent", required=False, default=None)
@click.option(
    "-c",
    "--config-file",
    "config_file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    help="Path to orchestrator config file (default: orchestrator.yaml in working directory)",
)
@click.option(
    "--mcp-config",
    "mcp_config",
    multiple=True,
    help="Load MCP servers from JSON files or strings (can be specified multiple times)",
)
@click.option(
    "--claude-settings",
    "claude_settings",
    type=str,
    help="Path to a settings JSON file or a JSON string for Claude Code (passed as --settings to claude CLI)",
)
@click.option("--file", "input_file", default=None, help="Input file path to pass to the agent (relative to vault root).")
@click.pass_context
def trigger_cli(ctx, agent, config_file, mcp_config, claude_settings, input_file):
    """Trigger an orchestrator agent.

    If AGENT abbreviation is provided, triggers that agent directly.
    Otherwise, shows an interactive selector.

    Examples:
        ai4pkm trigger        # interactive selector
        ai4pkm trigger EIC    # trigger EIC agent directly
        ai4pkm trigger EIC --file Eval/Pilot_SRPCompare/Queries/query_01.md
    """
    working_dir = ctx.obj.get("working_dir") if ctx.obj else None
    # Use local --config-file if provided, otherwise fall back to parent context
    effective_config_file = config_file or (ctx.obj.get("config_file") if ctx.obj else None)
    # Merge mcp_config from parent context and local option
    parent_mcp_config = ctx.obj.get("mcp_config") if ctx.obj else ()
    combined_mcp_config = parent_mcp_config + mcp_config if mcp_config else parent_mcp_config
    # Use local --claude-settings if provided, otherwise fall back to parent context
    effective_claude_settings = claude_settings or (ctx.obj.get("claude_settings") if ctx.obj else None)
    trigger_orchestrator_agent(abbreviation=agent, config_file=effective_config_file, working_dir=working_dir, mcp_config=combined_mcp_config, claude_settings=effective_claude_settings, input_file=input_file)

