#!/usr/bin/env python3
"""Trigger command for orchestrator agents."""

import click

from .trigger_agent import trigger_orchestrator_agent


@click.command("trigger")
@click.argument("agent", required=False, default=None)
@click.pass_context
def trigger_cli(ctx, agent):
    """Trigger an orchestrator agent.
    
    If AGENT abbreviation is provided, triggers that agent directly.
    Otherwise, shows an interactive selector.
    
    Examples:
        ai4pkm trigger        # interactive selector
        ai4pkm trigger EIC    # trigger EIC agent directly
    """
    working_dir = ctx.obj.get("working_dir") if ctx.obj else None
    trigger_orchestrator_agent(abbreviation=agent, working_dir=working_dir)

