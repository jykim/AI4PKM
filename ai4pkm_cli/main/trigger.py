#!/usr/bin/env python3
"""Trigger command for orchestrator agents."""

import click

from .trigger_agent import trigger_orchestrator_agent


@click.command("trigger")
@click.argument("agent", required=False, default=None)
@click.option(
    "--mcp-config",
    "mcp_config",
    multiple=True,
    help="Load MCP servers from JSON files or strings (can be specified multiple times)",
)
@click.pass_context
def trigger_cli(ctx, agent, mcp_config):
    """Trigger an orchestrator agent.
    
    If AGENT abbreviation is provided, triggers that agent directly.
    Otherwise, shows an interactive selector.
    
    Examples:
        ai4pkm trigger        # interactive selector
        ai4pkm trigger EIC    # trigger EIC agent directly
    """
    working_dir = ctx.obj.get("working_dir") if ctx.obj else None
    # Merge mcp_config from parent context and local option
    parent_mcp_config = ctx.obj.get("mcp_config") if ctx.obj else ()
    combined_mcp_config = parent_mcp_config + mcp_config if mcp_config else parent_mcp_config
    trigger_orchestrator_agent(abbreviation=agent, working_dir=working_dir, mcp_config=combined_mcp_config)

