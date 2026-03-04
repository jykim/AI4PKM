"""Handler for --trigger-agent command."""

import time
from pathlib import Path
from rich.console import Console

from ..logger import Logger
from ..config import Config
from ..orchestrator.core import Orchestrator

logger = Logger(console_output=True)

def trigger_orchestrator_agent(abbreviation=None, config_file=None, working_dir=None, mcp_config=None, claude_settings=None, input_file=None):
    """Trigger an orchestrator agent or poller interactively.

    Args:
        abbreviation: Optional agent abbreviation or poller name to skip selection UX
        config_file: Optional path to orchestrator config file
        working_dir: Optional working directory for agent subprocess execution (defaults to vault_path)
        mcp_config: Optional tuple of MCP config JSON files or strings
        claude_settings: Optional path or JSON string for Claude --settings flag
        input_file: Optional input file path to pass to the agent
    """
    try:
        config = Config(config_file=config_file)

        # Create orchestrator (but don't start daemon)
        orch = Orchestrator(
            vault_path=Path.cwd(),
            config=config,
            working_dir=Path(working_dir) if working_dir else None,
            mcp_config=mcp_config,
            claude_settings=claude_settings
        )

        agents_list = [agent for agent in orch.agent_registry.agents.values()]
        pollers_list = list(orch.poller_manager.pollers.items())
        
        if not agents_list and not pollers_list:
            logger.error("No agents or pollers found", console=True)
            return

        # If abbreviation/name provided, skip selection
        if abbreviation:
            abbreviation_upper = abbreviation.upper()
            selected_agent = orch.agent_registry.agents.get(abbreviation_upper)
            selected_poller_name = None
            selected_poller = None
            
            if selected_agent:
                # Found as agent
                pass
            else:
                # Try as poller name (case-insensitive)
                for poller_name, poller in pollers_list:
                    if poller_name.lower() == abbreviation.lower():
                        selected_poller_name = poller_name
                        selected_poller = poller
                        break
                
                if not selected_poller:
                    logger.error(f"Agent or poller '{abbreviation}' not found", console=True)
                    available_items = []
                    if agents_list:
                        available_items.extend([f"Agent: {abbr}" for abbr in sorted(orch.agent_registry.agents.keys())])
                    if pollers_list:
                        available_items.extend([f"Poller: {name}" for name in sorted([p[0] for p in pollers_list])])
                    logger.info(f"[dim]Available: {', '.join(available_items)}[/dim]")
                    return
        else:
            # Build unified list for selection
            items = []
            item_types = []  # 'agent' or 'poller'
            
            # Add agents
            agents_list.sort(key=lambda a: a.abbreviation)
            for agent in agents_list:
                items.append(agent)
                item_types.append('agent')
            
            # Add pollers
            pollers_list.sort(key=lambda p: p[0])  # Sort by name
            for poller_name, poller in pollers_list:
                items.append((poller_name, poller))
                item_types.append('poller')
            
            if not items:
                logger.error("No agents or pollers available", console=True)
                return

            # Display available agents
            if agents_list:
                logger.info("\n[bold blue]Available Orchestrator Agents:[/bold blue]")
                agent_num = 1
                for agent in agents_list:
                    cron_info = f" [dim]cron: {agent.cron}[/dim]" if agent.cron else ""
                    output_info = (
                        f" [dim]→ {agent.output_path}[/dim]" if agent.output_path else ""
                    )

                    logger.info(
                        f"[cyan]{agent_num}.[/cyan] [bold]{agent.name} ({agent.abbreviation})[/bold]"
                    )
                    logger.info(f"   Category: {agent.category}{cron_info}{output_info}\n")
                    agent_num += 1

            # Display available pollers
            if pollers_list:
                logger.info("\n[bold blue]Available Pollers:[/bold blue]")
                poller_start_num = len(agents_list) + 1
                for poller_name, poller in pollers_list:
                    # Use relative path from config instead of absolute path
                    target_dir_rel = poller.poller_config.get('target_dir', str(poller.target_dir))
                    target_info = f" [dim]→ {target_dir_rel}[/dim]"
                    interval_info = f" [dim]interval: {poller.poll_interval}s[/dim]"
                    
                    logger.info(
                        f"[cyan]{poller_start_num}.[/cyan] [bold]{poller_name}[/bold]"
                    )
                    logger.info(f"   Poller{target_info}{interval_info}\n")
                    poller_start_num += 1

            # Get user selection
            try:
                choice = input(
                    f"Enter number (1-{len(items)}) or 'q' to quit: "
                ).strip()

                if choice.lower() == "q":
                    logger.info("Trigger cancelled by user")
                    return

                item_index = int(choice) - 1
                if item_index < 0 or item_index >= len(items):
                    logger.error(
                        f"Invalid choice: {choice}. Please enter a number between 1 and {len(items)}"
                    )
                    return

            except ValueError:
                logger.error(f"Invalid input: {choice}. Please enter a number or 'q'")
                return
            except KeyboardInterrupt:
                logger.info("\nTrigger cancelled by user")
                return

            # Determine if selected item is agent or poller
            selected_item = items[item_index]
            item_type = item_types[item_index]
            
            if item_type == 'agent':
                selected_agent = selected_item
                selected_poller = None
                selected_poller_name = None
            else:
                selected_poller_name, selected_poller = selected_item
                selected_agent = None
        
        # Execute selected item
        start_time = time.time()

        try:
            if selected_agent:
                # Trigger agent
                logger.info(f"Triggering agent: {selected_agent.abbreviation}")
                ctx = orch.trigger_agent_once(selected_agent.abbreviation, input_file=input_file)

                end_time = time.time()
                execution_time = end_time - start_time

                if ctx and ctx.success:
                    logger.info(
                        f"✓ Agent completed successfully ({execution_time:.1f}s)"
                    )
                    logger.info(f"\n[green]✓ Agent completed successfully[/green]")
                    logger.info(
                        f"[dim]Execution time: {execution_time:.2f}s[/dim]"
                    )
                    if ctx.task_file:
                        logger.info(f"[dim]Task file: {ctx.task_file.name}[/dim]")
                else:
                    error_msg = ctx.error_message if ctx else "Unknown error"
                    logger.error(f"✗ Agent failed: {error_msg}")
                    logger.info(f"\n[red]✗ Agent failed: {error_msg}[/red]")
            
            elif selected_poller:
                # Run poller once
                logger.info(f"Running poller: {selected_poller_name}")
                success = selected_poller.run_once()

                end_time = time.time()
                execution_time = end_time - start_time

                if success:
                    logger.info(
                        f"✓ Poller completed successfully ({execution_time:.1f}s)"
                    )
                    logger.info(f"\n[green]✓ Poller completed successfully[/green]")
                    logger.info(
                        f"[dim]Execution time: {execution_time:.2f}s[/dim]"
                    )
                else:
                    logger.error(f"✗ Poller failed")
                    logger.info(f"\n[red]✗ Poller failed after {execution_time:.2f}s[/red]")

        except Exception as e:
            end_time = time.time()
            execution_time = end_time - start_time
            item_type_str = "agent" if selected_agent else "poller"
            logger.error(f"✗ {item_type_str.capitalize()} error ({execution_time:.1f}s): {e}")
            logger.info(
                f"\n[red]✗ {item_type_str.capitalize()} error after {execution_time:.2f}s: {e}[/red]"
            )

    except Exception as e:
        logger.error(f"Error initializing orchestrator: {e}")
        logger.info(f"[red]✗ Error: {e}[/red]")

