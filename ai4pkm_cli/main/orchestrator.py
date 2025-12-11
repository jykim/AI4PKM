"""Orchestrator daemon and status functions."""

import sys
import signal
from pathlib import Path
from rich.console import Console
from rich.panel import Panel

from ..orchestrator.core import Orchestrator
from ..logger import Logger

logger = Logger(console_output=True)


def run_orchestrator_daemon(vault_path: Path = None, debug: bool = False, working_dir: str = None):
    """
    Run orchestrator in daemon mode.

    Args:
        vault_path: Path to vault root (defaults to CWD)
        debug: Enable debug logging to console
        working_dir: Working directory for agent subprocess execution (defaults to vault_path)
    """
    from ..config import Config
    
    config = Config()
    
    # Use CWD as vault (requires config file in CWD)
    vault_path = vault_path or Path.cwd()
    max_concurrent = config.get_orchestrator_max_concurrent()

    debug_mode = "[yellow](DEBUG)[/yellow]" if debug else ""
    logger.info(Panel.fit(
        f"[bold cyan]AI4PKM Orchestrator[/bold cyan] {debug_mode}\n"
        f"Vault: {vault_path}\n"
        f"Max concurrent: {max_concurrent}",
        title="Starting"
    ))

    # Create orchestrator (it will load paths from config)
    orch = Orchestrator(
        vault_path=vault_path,
        max_concurrent=max_concurrent,
        config=config,
        working_dir=Path(working_dir) if working_dir else None
    )

    # Setup signal handlers
    def signal_handler(sig, frame):
        logger.info("\n[yellow]Received interrupt signal, shutting down...[/yellow]")
        if orch:
            orch.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Show loaded agents
    status = orch.get_status()
    logger.info(f"\n[green]✓[/green] Loaded {status['agents_loaded']} agent(s):")
    for agent_info in status['agent_list']:
        logger.info(
            f"  • [{agent_info['abbreviation']}] {agent_info['name']} "
            f"({agent_info['category']})"
        )

    # Show loaded pollers
    pollers_list = list(orch.poller_manager.pollers.items())
    if pollers_list:
        logger.info(f"\n[green]✓[/green] Loaded {len(pollers_list)} poller(s):")
        for poller_name, poller in sorted(pollers_list, key=lambda p: p[0]):
            # Use relative path from config instead of absolute path
            target_dir_rel = poller.poller_config.get('target_dir', str(poller.target_dir))
            logger.info(
                f"  • {poller_name} → {target_dir_rel} "
                f"(interval: {poller.poll_interval}s)"
            )

    # Start orchestrator
    logger.info("\n[cyan]Starting orchestrator...[/cyan]")
    orch.run_forever()


def show_orchestrator_status(vault_path: Path = None, working_dir: str = None):
    """
    Show orchestrator status and loaded agents.

    Args:
        vault_path: Path to vault root (defaults to CWD)
        working_dir: Working directory for agent subprocess execution (defaults to vault_path)
    """
    from ..config import Config
    
    config = Config()
    
    # Use CWD as vault (requires config file in CWD)
    vault_path = vault_path or Path.cwd()

    # Create orchestrator just to load agents (don't start)
    orch = Orchestrator(
        vault_path=vault_path,
        config=config,
        working_dir=Path(working_dir) if working_dir else None
    )

    status = orch.get_status()

    logger.info(Panel.fit(
        f"[bold]Vault:[/bold] {status['vault_path']}\n"
        f"[bold]Agents loaded:[/bold] {status['agents_loaded']}\n"
        f"[bold]Pollers loaded:[/bold] {status['pollers_loaded']}\n"
        f"[bold]Max concurrent:[/bold] {status['max_concurrent']}",
        title="Orchestrator Status"
    ))

    if status['agent_list']:
        logger.info("\n[bold]Available Agents:[/bold]")
        for agent_info in status['agent_list']:
            logger.info(
                f"  • [{agent_info['abbreviation']}] {agent_info['name']}\n"
                f"    Category: {agent_info['category']}"
            )

    # Show pollers
    pollers_list = list(orch.poller_manager.pollers.items())
    if pollers_list:
        logger.info("\n[bold]Available Pollers:[/bold]")
        for poller_name, poller in sorted(pollers_list, key=lambda p: p[0]):
            # Use relative path from config instead of absolute path
            target_dir_rel = poller.poller_config.get('target_dir', str(poller.target_dir))
            logger.info(
                f"  • {poller_name}\n"
                f"    Target: {target_dir_rel}\n"
                f"    Interval: {poller.poll_interval}s"
            )


def execute_prompt_with_session(
    prompt: str,
    session_id: str = None,
    vault_path: Path = None,
    working_dir: str = None
):
    """
    Execute a one-time prompt with Claude agent and optional session ID.
    Automatically resumes session if it exists, creates new if it doesn't.

    Args:
        prompt: The prompt text to execute
        session_id: Optional session ID for tracking related executions (auto resume/create)
        vault_path: Path to vault root (defaults to CWD)
        working_dir: Working directory for agent subprocess execution (defaults to vault_path)
    """
    from ..config import Config
    import time
    
    config = Config()
    vault_path = vault_path or Path.cwd()
    
    logger.info(Panel.fit(
        f"[bold cyan]Executing One-Time Prompt[/bold cyan]\n"
        f"Session ID: {session_id or '(none)'}\n"
        f"Mode: auto (resume if exists, create if not)",
        title="Prompt Execution"
    ))
    
    # Create orchestrator
    orch = Orchestrator(
        vault_path=vault_path,
        config=config,
        working_dir=Path(working_dir) if working_dir else None
    )
    
    # Execute prompt
    start_time = time.time()
    ctx = orch.execute_prompt_with_session(
        prompt=prompt,
        session_id=session_id
    )
    end_time = time.time()
    execution_time = end_time - start_time
    
    if ctx and ctx.success:
        logger.info(f"\n[green]✓ Prompt executed successfully ({execution_time:.1f}s)[/green]")
        if ctx.session_id:
            logger.info(f"[dim]Session ID: {ctx.session_id}[/dim]")
        # Display the response (cleaned for one-time prompts)
        if ctx.response:
            logger.info(f"\n[bold cyan]Response:[/bold cyan]")
            # Clean response: remove [Agent Name] prefixes for cleaner output
            import re
            cleaned_lines = []
            for line in ctx.response.split("\n"):
                cleaned_line = re.sub(r'^\[.*?\]\s*', '', line)
                cleaned_lines.append(cleaned_line)
            cleaned_response = "\n".join(cleaned_lines)
            logger.info(cleaned_response)
    else:
        error_msg = ctx.error_message if ctx else "Unknown error"
        logger.error(f"\n[red]✗ Prompt execution failed: {error_msg}[/red]")
    
    return ctx

