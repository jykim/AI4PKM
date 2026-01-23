"""
Orchestrator core - main event loop and coordination.

Ties together file monitoring, agent matching, and execution management.
"""
import threading
import time
from pathlib import Path
from typing import Optional
from queue import Empty

from .file_monitor import FileSystemMonitor
from .agent_registry import AgentRegistry
from .execution_manager import ExecutionManager
from .models import TriggerEvent, ExecutionContext, AgentDefinition, WorkerConfig
from ..logger import Logger

logger = Logger()


class Orchestrator:
    """
    Main orchestrator for multi-agent AI4PKM system.

    Coordinates file monitoring, agent matching, and task execution.
    """

    def __init__(
        self,
        vault_path: Path,
        working_dir: Optional[Path] = None,
        agents_dir: Optional[Path] = None,
        max_concurrent: Optional[int] = None,
        poll_interval: Optional[float] = None,
        config: Optional['Config'] = None,
    ):
        """
        Initialize orchestrator.

        Args:
            vault_path: Path to vault root
            working_dir: Working directory for agent subprocess execution (defaults to vault_path)
            agents_dir: Directory containing agent definitions (defaults to config orchestrator.prompts_dir)
            max_concurrent: Maximum concurrent task executions (defaults to config)
            poll_interval: Seconds between event queue polls (defaults to config)
            config: Config instance (will create default if None)
            debug: Enable debug logging to console
        """
        from ..config import Config
        from datetime import datetime

        self.vault_path = Path(vault_path)
        self.config = config or Config()

        # Use config values if not explicitly provided
        if agents_dir is None:
            prompts_dir = self.config.get_orchestrator_prompts_dir()
            self.agents_dir = self.vault_path / prompts_dir
        else:
            self.agents_dir = agents_dir

        self.max_concurrent = max_concurrent or self.config.get_orchestrator_max_concurrent()
        self.poll_interval = poll_interval or self.config.get_orchestrator_poll_interval()

        # Ensure required directories exist
        self._ensure_directories()

        # Initialize components
        self.agent_registry = AgentRegistry(self.agents_dir, self.vault_path, self.config)
        self.execution_manager = ExecutionManager(
            self.vault_path,
            self.max_concurrent,
            self.config,
            orchestrator_settings=self.agent_registry.orchestrator_settings,
            working_dir=working_dir
        )
        # Get file_extensions from orchestrator_settings (default to ['.md'] if not specified)
        file_extensions = self.agent_registry.orchestrator_settings.get('file_extensions', ['.md'])
        self.file_monitor = FileSystemMonitor(self.vault_path, self.agent_registry, file_extensions=file_extensions)

        # Initialize cron scheduler
        from .cron_scheduler import CronScheduler
        self.cron_scheduler = CronScheduler(
            self.agent_registry,
            self.file_monitor.event_queue
        )

        # Initialize poller manager
        from .poller_manager import PollerManager
        self.poller_manager = PollerManager(
            vault_path=self.vault_path,
            config=self.config
        )

        # Control state
        self._running = False
        self._event_thread: Optional[threading.Thread] = None

        # Hot-reload state management
        self._reload_lock = threading.Lock()
        self._reload_thread: Optional[threading.Thread] = None
        self._pending_reload_during_reload = False  # Flag to track if reload needed after current reload completes
        self._swap_lock = threading.Lock()
        self._swap_in_progress = False
        self._reload_in_progress = False  # Flag to prevent concurrent reload starts
        self._reload_start_lock = threading.Lock()  # Lock for atomic reload start check

        logger.info(f"Orchestrator initialized for vault: {self.vault_path}")
        logger.info(f"Loaded {len(self.agent_registry.agents)} agents")
        logger.info(f"Loaded {len(self.poller_manager.pollers)} poller(s)")

    def _ensure_directories(self):
        """Create orchestrator directories if they don't exist."""
        # Get all configured directories from orchestrator_settings if available
        # This method is called before agent_registry is initialized, so use config as fallback
        directories = [
            self.config.get_orchestrator_prompts_dir(),
            self.config.get_orchestrator_tasks_dir(),
            self.config.get_orchestrator_logs_dir(),
            self.config.get('orchestrator.skills_dir', '_Settings_/Skills'),
            self.config.get('orchestrator.bases_dir', '_Settings_/Bases'),
        ]

        created = []
        # Create each directory
        for dir_path in directories:
            full_path = self.vault_path / dir_path
            if not full_path.exists():
                full_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created directory: {dir_path}")
                created.append(dir_path)

        if created:
            dir_word = "directory" if len(created) == 1 else "directories"
            logger.info(f"Created {len(created)} missing {dir_word}: {', '.join(created)}")

    def start(self):
        """Start the orchestrator event loop."""
        if self._running:
            logger.warning("Orchestrator already running")
            return

        logger.info("Starting orchestrator...")

        # Start file monitor
        self.file_monitor.start()

        # Start cron scheduler
        self.cron_scheduler.start()

        # Start pollers
        self.poller_manager.start_all()

        # Start event processing thread
        self._running = True
        self._event_thread = threading.Thread(target=self._event_loop, daemon=True)
        self._event_thread.start()

        logger.info("Orchestrator started successfully")

        # Process any existing QUEUED tasks from previous run
        self._load_queued_tasks_on_startup()

    def _load_queued_tasks_on_startup(self):
        """
        Load and process existing QUEUED tasks on startup.

        Scans the tasks directory for tasks with status=QUEUED and
        processes them (up to max_concurrent limit).
        """
        from ..markdown_utils import read_frontmatter

        try:
            task_files = sorted(self.execution_manager.task_manager.tasks_dir.glob("*.md"))
            queued_count = 0

            for task_path in task_files:
                fm = read_frontmatter(task_path)
                if fm.get('status') == 'QUEUED':
                    queued_count += 1

            if queued_count > 0:
                logger.info(f"Found {queued_count} QUEUED task(s) from previous run")
                # Process queued tasks (will respect max_concurrent limit)
                for _ in range(queued_count):
                    self._process_queued_tasks()
        except Exception as e:
            logger.error(f"Error loading queued tasks on startup: {e}", exc_info=True)

    def stop(self):
        """Stop the orchestrator event loop."""
        if not self._running:
            logger.warning("Orchestrator not running")
            return

        logger.info("Stopping orchestrator...")

        # Stop event processing
        self._running = False

        # Stop pollers
        self.poller_manager.stop_all()

        # Stop cron scheduler
        self.cron_scheduler.stop()

        # Stop file monitor
        self.file_monitor.stop()

        # Wait for reload thread to finish (if in progress)
        if self._reload_thread and self._reload_thread.is_alive():
            logger.info("Waiting for configuration reload to complete...")
            self._reload_thread.join(timeout=10.0)

        # Wait for event thread to finish
        if self._event_thread and self._event_thread.is_alive():
            self._event_thread.join(timeout=5.0)

        logger.info("Orchestrator stopped")

    def _trigger_reload(self):
        """Trigger configuration reload immediately."""
        # Use lock to atomically check and set reload start flag
        with self._reload_start_lock:
            # Double-check after acquiring lock (prevent race condition)
            if self._reload_in_progress:
                return
            
            # Check if reload thread is already running
            if self._reload_thread is not None and self._reload_thread.is_alive():
                return
            
            # Set flag and start reload in background thread (atomic)
            self._reload_in_progress = True
            self._reload_thread = threading.Thread(
                target=self._reload_configuration,
                daemon=True
            )
            self._reload_thread.start()
            logger.info("Starting configuration reload...")

    def _reload_configuration(self):
        """
        Two-phase reload: build new config in parallel, then atomically swap.
        
        Phase 1: Build new config (non-blocking)
        Phase 2: Wait for old executions, then atomically swap
        """
        # Acquire reload lock to prevent concurrent reloads
        if not self._reload_lock.acquire(blocking=False):
            logger.warning("Reload already in progress, skipping")
            self._reload_in_progress = False  # Reset flag if we couldn't acquire lock
            return

        try:
            logger.info("=" * 60)
            logger.info("🔄 Starting configuration hot-reload", console=True)
            logger.info("=" * 60)

            # Phase 1: Build New Config (Non-blocking)
            logger.info("Phase 1: Building new configuration...")
            
            # Reload config from disk
            if not self.config.reload():
                logger.error("Failed to reload config, aborting reload")
                return
            
            # Create new AgentRegistry instance (doesn't affect running system)
            new_agent_registry = AgentRegistry(
                self.agents_dir,
                self.vault_path,
                self.config
            )
            
            # Get new orchestrator settings
            new_orchestrator_settings = new_agent_registry.orchestrator_settings
            new_max_concurrent = new_orchestrator_settings.get(
                'max_concurrent',
                self.config.get_orchestrator_max_concurrent()
            )
            
            logger.info("Phase 1 complete: New configuration built")
            logger.info(f"  - Agents loaded: {len(new_agent_registry.agents)}")
            logger.info(f"  - Max concurrent: {new_max_concurrent}")

            # Phase 2: Atomic Swap (Blocking)
            logger.info("Phase 2: Waiting for running executions to complete...")
            
            # Pause event processing during entire Phase 2 (prevents new executions from starting)
            self._swap_in_progress = True
            logger.info("Event processing paused - new events will be queued until reload completes")
            
            # Wait for all running executions to complete
            timeout_seconds = 300  # 5 minutes
            start_wait_time = time.time()
            last_log_time = start_wait_time
            
            while True:
                running_executions = self.execution_manager.get_running_executions()
                
                if not running_executions:
                    logger.info("All running executions completed")
                    break
                
                # Check timeout
                elapsed = time.time() - start_wait_time
                if elapsed > timeout_seconds:
                    logger.warning(
                        f"Timeout waiting for {len(running_executions)} execution(s) to complete. "
                        "Proceeding with reload anyway."
                    )
                    break
                
                # Log progress every 10 seconds
                if time.time() - last_log_time >= 10:
                    logger.info(f"Waiting for {len(running_executions)} execution(s) to complete...")
                    last_log_time = time.time()
                
                time.sleep(0.5)
            
            # Atomic swap
            logger.info("Performing atomic configuration swap...")
            
            try:
                with self._swap_lock:
                    # Swap agent registry
                    old_agent_registry = self.agent_registry
                    self.agent_registry = new_agent_registry
                    
                    # Update execution manager settings
                    self.execution_manager.update_settings(new_max_concurrent)
                    
                    # Update max_concurrent for orchestrator
                    self.max_concurrent = new_max_concurrent
                    
                    # Reload pollers
                    self.poller_manager.reload()
                    
                    # Update cron scheduler with new agent registry
                    self.cron_scheduler.update_agent_registry(new_agent_registry)
                    
                    logger.info("Atomic swap complete")
            
            finally:
                self._swap_in_progress = False
            
            logger.info("=" * 60)
            logger.info("🎉 Configuration hot-reload completed successfully", console=True)
            logger.info("=" * 60)
            
            # Process any pending QUEUED tasks with new registry
            logger.info("Processing pending QUEUED tasks with new configuration...")
            self._process_queued_tasks()

        except Exception as e:
            logger.error(f"Error during configuration reload: {e}", exc_info=True)
            logger.error("Keeping existing configuration active")
        finally:
            self._reload_lock.release()
            self._reload_in_progress = False  # Reset flag when reload completes
            
            # Check if another reload was requested during this reload
            if self._pending_reload_during_reload:
                logger.info("Another orchestrator.yaml change detected during reload, triggering follow-up reload...")
                self._pending_reload_during_reload = False
                self._trigger_reload()

    def _event_loop(self):
        """
        Main event processing loop.

        Polls file monitor queue and processes events.
        """
        logger.info("Event loop started")

        while self._running:
            try:
                # Check if reload is in progress (pause event processing during reload wait phase)
                if self._swap_in_progress:
                    time.sleep(0.1)
                    continue  # Skip event processing - events will queue up and process after reload

                # Poll event queue with timeout
                try:
                    trigger_event = self.file_monitor.event_queue.get(timeout=self.poll_interval)
                except Empty:
                    # No events, continue polling
                    continue

                # Handle config reload events specially
                if trigger_event.event_type == 'config_reload':
                    logger.info("Detected orchestrator.yaml change")
                    # If reload is already in progress, mark that we need another reload after this one completes
                    if self._reload_in_progress:
                        logger.debug("Reload already in progress, will trigger another reload after current one completes")
                        self._pending_reload_during_reload = True
                    else:
                        # Trigger reload immediately (no debounce)
                        self._trigger_reload()
                    continue  # Don't process as regular event

                # Process event
                self._process_event(trigger_event)

                # Check for queued tasks after processing event
                self._process_queued_tasks()

            except Exception as e:
                logger.error(f"Error in event loop: {e}", exc_info=True)
                time.sleep(self.poll_interval)

        logger.info("Event loop stopped")

    def _process_event(self, trigger_event: TriggerEvent):
        """
        Process a single trigger event.

        Args:
            trigger_event: Trigger event to process (file or scheduled)
        """
        logger.debug(f"Processing event: {trigger_event.event_type} {trigger_event.path}")

        # 1. Handle Task Files
        # Task files are special: they control execution flow and shouldn't trigger other agents
        if self._is_task_file(trigger_event.path):
            try:
                # Always read from file to get the latest status
                from ..markdown_utils import read_frontmatter
                frontmatter = read_frontmatter(self.vault_path / trigger_event.path)
                status = frontmatter.get('status', '').upper()
                
                if status == 'QUEUED':
                    logger.debug(f"Detected QUEUED task file: {trigger_event.path}")
                    self._enrich_queued_task(trigger_event)
                else:
                    logger.debug(f"Ignoring task file update (status={status}): {trigger_event.path}")
            except Exception as e:
                logger.error(f"Error processing task file {trigger_event.path}: {e}")
            
            return  # Stop processing for task files (don't trigger agents)

        # 2. Regular File Processing
        # Convert TriggerEvent to event_data dict
        event_data = {
            'path': trigger_event.path,
            'event_type': trigger_event.event_type,
            'is_directory': trigger_event.is_directory,
            'timestamp': trigger_event.timestamp,
            'frontmatter': trigger_event.frontmatter
        }

        # Find matching agents
        matching_agents = self.agent_registry.find_matching_agents(event_data)

        if not matching_agents:
            logger.debug(f"No agents match event: {trigger_event.path}")
            return

        logger.debug(f"Found {len(matching_agents)} matching agent(s) for {trigger_event.path}")

        # Execute each matching agent
        for agent in matching_agents:
            # Check if this is a multi-worker agent
            if agent.workers:
                # Dispatch to ALL workers in parallel
                self._dispatch_multi_worker(agent, event_data, trigger_event)
            else:
                # Single-worker execution (existing logic)
                self._dispatch_single_worker(agent, event_data, trigger_event)

    def _dispatch_single_worker(self, agent: AgentDefinition, event_data: dict, trigger_event: TriggerEvent):
        """
        Dispatch a single-worker agent execution.

        Args:
            agent: Agent definition to execute
            event_data: Event data dictionary
            trigger_event: Original trigger event
        """
        # Try to reserve a slot atomically (prevents race conditions)
        if not self.execution_manager.reserve_slot(agent):
            # Create QUEUED task instead of dropping
            self._create_queued_task(agent, event_data)
            logger.info(f"Queued {agent.abbreviation}: concurrency limit reached")
            return

        # Log agent trigger at INFO level for visibility
        input_filename = Path(trigger_event.path).name if trigger_event.path else "scheduled"
        logger.info(f"🚀 Triggering {trigger_event.event_type} agent: {agent.abbreviation} ({input_filename})", console=True)
        logger.debug(f"Starting {agent.abbreviation}: {trigger_event.path}")

        # Execute in background thread (slot already reserved)
        execution_thread = threading.Thread(
            target=self._execute_agent,
            args=(agent, event_data, True),  # slot_reserved=True
            daemon=True
        )
        execution_thread.start()

    def _dispatch_multi_worker(self, agent: AgentDefinition, event_data: dict, trigger_event: TriggerEvent):
        """
        Dispatch a multi-worker agent to all configured workers in parallel.

        Args:
            agent: Base agent definition with workers list
            event_data: Event data dictionary
            trigger_event: Original trigger event
        """
        input_filename = Path(trigger_event.path).name if trigger_event.path else "scheduled"
        logger.info(f"🚀 Triggering multi-worker agent: {agent.abbreviation} ({input_filename}) with {len(agent.workers)} workers", console=True)

        for worker in agent.workers:
            # Create worker-specific agent variant
            worker_agent = self._create_worker_agent_variant(agent, worker)

            # Try to reserve a slot for this worker
            if not self.execution_manager.reserve_slot(worker_agent):
                # Create QUEUED task for this worker
                self._create_queued_task(worker_agent, event_data)
                logger.info(f"Queued {worker_agent.abbreviation}: concurrency limit reached")
                continue

            logger.debug(f"Starting worker {worker_agent.abbreviation}: {trigger_event.path}")

            # Execute in background thread (slot already reserved)
            execution_thread = threading.Thread(
                target=self._execute_agent,
                args=(worker_agent, event_data, True),  # slot_reserved=True
                daemon=True
            )
            execution_thread.start()

    def _create_queued_task(self, agent: AgentDefinition, event_data: dict):
        """
        Create a QUEUED task file for an agent that couldn't get a slot.

        Args:
            agent: Agent definition (may be a worker variant)
            event_data: Event data dictionary
        """
        import json
        from datetime import datetime, date

        # Convert all date/datetime objects to strings for JSON serialization
        def make_json_serializable(obj):
            """Recursively convert date/datetime objects to ISO strings."""
            if isinstance(obj, (datetime, date)):
                return obj.isoformat()
            elif isinstance(obj, dict):
                return {k: make_json_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [make_json_serializable(item) for item in obj]
            else:
                return obj

        event_data_serializable = make_json_serializable(event_data)

        # Serialize trigger data (escape quotes for YAML)
        trigger_data_json = json.dumps(event_data_serializable, ensure_ascii=False).replace('"', '\\"')

        # Create minimal context for task file creation
        ctx = ExecutionContext(
            agent=agent,
            trigger_data=event_data,
            start_time=datetime.now()
        )

        # Create QUEUED task
        self.execution_manager.task_manager.create_task_file(
            ctx, agent,
            initial_status="QUEUED",
            trigger_data_json=trigger_data_json
        )

    def _execute_agent(self, agent, event_data, slot_reserved=False):
        """
        Execute an agent task.

        Args:
            agent: AgentDefinition to execute
            event_data: Event data dictionary (may contain 'session_id' key or in 'frontmatter')
            slot_reserved: Whether slot was already reserved

        Returns:
            ExecutionContext if execution completed, None on error
        """
        try:
            # Extract session_id from event_data
            session_id = event_data.get('session_id')
            if not session_id and 'frontmatter' in event_data:
                session_id = event_data['frontmatter'].get('session_id')
            
            ctx = self.execution_manager.execute(
                agent, event_data, 
                slot_reserved=slot_reserved, 
                session_id=session_id,
                resume_session=False  # Auto-detect in _execute_claude_code
            )

            if ctx.success:
                logger.info(f"{agent.abbreviation} completed ({ctx.duration:.1f}s)")
            else:
                duration_str = f"{ctx.duration:.1f}s" if ctx.duration else "unknown"
                error_msg = f"{agent.abbreviation} failed: {ctx.status} ({duration_str})"
                if ctx.error_message:
                    error_msg += f" - {ctx.error_message}"
                logger.error(error_msg)

            return ctx

        except Exception as e:
            logger.error(f"{agent.abbreviation} error: {e}", exc_info=True)
            return None

    def _process_queued_tasks(self):
        """
        Process any QUEUED tasks if capacity is available.

        Checks task files for QUEUED status and executes them when slots free up.
        Only processes one task per iteration to avoid thundering herd.
        """
        import json
        from ..markdown_utils import read_frontmatter

        try:
            # Find all task files (sorted for FIFO ordering)
            task_files = sorted(self.execution_manager.task_manager.tasks_dir.glob("*.md"))

            for task_path in task_files:
                # Parse frontmatter using existing utils
                fm = read_frontmatter(task_path)

                # Skip non-queued tasks
                if fm.get('status') != 'QUEUED':
                    continue

                # Extract agent abbreviation, worker label, executor, and trigger data
                agent_abbr = fm.get('task_type')
                worker_label = fm.get('worker_label', '')
                worker_executor = fm.get('worker')  # Executor stored in task file
                trigger_data_json = fm.get('trigger_data_json')

                if not agent_abbr:
                    logger.warning(f"Malformed QUEUED task: missing task_type: {task_path.name}")
                    continue

                # If trigger_data_json is missing, enrich the task with trigger data
                if not trigger_data_json:
                    logger.debug(f"QUEUED task missing trigger_data_json, enriching: {task_path.name}")
                    trigger_data_json = self._enrich_queued_task_with_trigger_data(task_path, fm)
                    if not trigger_data_json:
                        logger.warning(f"Failed to enrich QUEUED task: {task_path.name}")
                        continue

                # Look up base agent definition
                base_agent = self.agent_registry.agents.get(agent_abbr)
                if not base_agent:
                    logger.warning(
                        f"Agent '{agent_abbr}' not found for QUEUED task: {task_path.name}. "
                        "Agent may have been removed in configuration reload."
                    )
                    self.execution_manager.task_manager.update_task_status(
                        task_path,
                        "FAILED",
                        error_message=f"Agent '{agent_abbr}' not found after configuration reload"
                    )
                    logger.info(f"Marked QUEUED task as FAILED: {task_path.name}")
                    continue

                # Reconstruct worker agent variant if this was a multi-worker task
                if worker_label and base_agent.workers:
                    # Find the matching worker config
                    worker_config = None
                    for w in base_agent.workers:
                        if w.label == worker_label:
                            worker_config = w
                            break

                    if worker_config:
                        agent = self._create_worker_agent_variant(base_agent, worker_config)
                    elif worker_executor:
                        # Worker config changed but task has stored executor - use it
                        from dataclasses import replace
                        logger.info(f"Worker '{worker_label}' not in current config, using stored executor '{worker_executor}'")
                        agent = replace(
                            base_agent,
                            abbreviation=f"{agent_abbr}-{worker_label}",
                            executor=worker_executor
                        )
                    else:
                        logger.warning(f"Worker '{worker_label}' not found in agent '{agent_abbr}', using base agent")
                        agent = base_agent
                else:
                    agent = base_agent

                # Try to reserve a slot atomically
                if not self.execution_manager.reserve_slot(agent):
                    break  # Still no capacity, wait for next iteration

                # Reconstruct trigger data
                # Handle both formats:
                # 1. Old format: escaped quotes in quoted string "{\\"path\\": ...}"
                # 2. New format: literal block scalar (already unescaped by YAML parser)
                try:
                    # Try parsing directly first (works for literal block scalar format)
                    event_data = json.loads(trigger_data_json)
                except json.JSONDecodeError:
                    # Fall back to unescaping (for old quoted string format)
                    try:
                        event_data = json.loads(trigger_data_json.replace('\\"', '"'))
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse trigger_data_json: {e}")
                        # Release the reserved slot since we can't process this task
                        with self.execution_manager._count_lock:
                            self.execution_manager._running_count -= 1
                        with self.execution_manager._agent_lock:
                            self.execution_manager._agent_counts[agent.abbreviation] -= 1
                        continue

                # Execute agent (slot already reserved)
                event_path = event_data.get('path', '')
                logger.debug(f"Starting queued {agent.abbreviation}: {event_path}")

                # Inject existing task file path into event_data
                event_data['_existing_task_file'] = str(task_path)
                # Also inject generation_log to avoid re-reading frontmatter
                event_data['_generation_log'] = fm.get('generation_log', '')

                execution_thread = threading.Thread(
                    target=self._execute_agent,
                    args=(agent, event_data, True),  # slot_reserved=True
                    daemon=True
                )
                execution_thread.start()

                # Only start one task per iteration
                break

        except Exception as e:
            logger.error(f"Error processing queued tasks: {e}", exc_info=True)

    def _is_task_file(self, file_path: str) -> bool:
        """
        Check if the file is in the tasks directory.
        
        Args:
            file_path: Relative path to check
            
        Returns:
            True if file is in tasks directory and is a markdown file
        """
        try:
            tasks_dir = self.execution_manager.task_manager.tasks_dir
            file_full_path = self.vault_path / file_path
            
            try:
                file_full_path.relative_to(tasks_dir)
                return file_path.endswith('.md')
            except ValueError:
                return False
        except Exception:
            return False

    def _extract_input_path_from_task_body(self, task_body: str) -> Optional[str]:
        """
        Extract input file path from task body content.

        Looks for wiki links in the "## Input" section.

        Args:
            task_body: Task file body content (after frontmatter)

        Returns:
            Extracted input path or None if not found
        """
        import re
        
        # Look for "## Input" section
        input_section_match = re.search(r'##\s+Input\s*\n(.*?)(?=\n##|\Z)', task_body, re.DOTALL | re.IGNORECASE)
        if not input_section_match:
            return None
        
        input_section = input_section_match.group(1)
        
        # Look for wiki links [[path/to/file]] or `[[path/to/file]]`
        wiki_link_pattern = r'(?:`)?\[\[([^\]]+)\]\](?:`)?'
        matches = re.findall(wiki_link_pattern, input_section)
        
        if matches:
            # Return first wiki link found
            return matches[0]
        
        # Look for file paths in backticks
        backtick_pattern = r'`([^`]+\.md)`'
        matches = re.findall(backtick_pattern, input_section)
        
        if matches:
            return matches[0]
        
        return None

    def _enrich_queued_task(self, trigger_event: TriggerEvent):
        """
        Enrich a QUEUED task file by adding trigger_data_json if missing.

        Reads the task file, extracts agent type and input path,
        creates synthetic trigger event data, and adds trigger_data_json.

        Args:
            trigger_event: Trigger event for the QUEUED task file
        """
        from ..markdown_utils import read_frontmatter, extract_body

        try:
            # Get full path to task file
            task_file_path = self.vault_path / trigger_event.path
            
            if not task_file_path.exists():
                logger.warning(f"QUEUED task file not found: {trigger_event.path}")
                return

            # Read task file
            frontmatter = read_frontmatter(task_file_path)
            
            # Check if status is actually QUEUED and missing trigger_data_json
            current_status = frontmatter.get('status', '').upper()
            if current_status != 'QUEUED':
                logger.debug(f"Task file {trigger_event.path} is not QUEUED (status: {current_status}), skipping")
                return

            # Skip if trigger_data_json already exists
            if frontmatter.get('trigger_data_json'):
                logger.debug(f"QUEUED task already has trigger_data_json: {trigger_event.path}")
                return

            # Enrich with trigger data
            trigger_data_json = self._enrich_queued_task_with_trigger_data(task_file_path, frontmatter)
            if trigger_data_json:
                logger.info(f"🔄 Enriched QUEUED task with trigger data: {task_file_path.name}", console=True)

        except Exception as e:
            logger.error(f"Error enriching QUEUED task {trigger_event.path}: {e}", exc_info=True)

    def _enrich_queued_task_with_trigger_data(self, task_file_path: Path, frontmatter: dict) -> Optional[str]:
        """
        Enrich a QUEUED task with trigger_data_json by extracting input path and creating synthetic event.

        Args:
            task_file_path: Path to task file
            frontmatter: Task file frontmatter

        Returns:
            JSON string of trigger data, or None if enrichment failed
        """
        from ..markdown_utils import extract_body
        import json
        from datetime import datetime, date

        try:
            # Extract agent abbreviation
            agent_abbr = frontmatter.get('task_type')
            if not agent_abbr:
                logger.warning(f"QUEUED task file missing task_type: {task_file_path}")
                self.execution_manager.task_manager.update_task_status(
                    task_file_path,
                    "FAILED",
                    error_message="Missing task_type in frontmatter"
                )
                return None

            # Look up agent definition
            agent = self.agent_registry.agents.get(agent_abbr)
            if not agent:
                logger.warning(
                    f"Agent '{agent_abbr}' not found for QUEUED task: {task_file_path}. "
                    "Agent may have been removed in configuration reload."
                )
                self.execution_manager.task_manager.update_task_status(
                    task_file_path,
                    "FAILED",
                    error_message=f"Agent '{agent_abbr}' not found"
                )
                return None

            # Read task body to extract input path
            task_content = task_file_path.read_text(encoding='utf-8')
            task_body = extract_body(task_content)

            # Extract input file path from task body
            input_path = self._extract_input_path_from_task_body(task_body)
            
            # If no input path found, try to infer from task filename
            if not input_path:
                # Task filename format: YYYY-MM-DD {ABBR} - {input_filename}.md
                # Extract input filename from task filename
                task_filename = task_file_path.stem
                parts = task_filename.split(' - ', 1)
                if len(parts) > 1:
                    # Try to find a file matching the input filename
                    input_filename = parts[1]
                    # Search in common input directories
                    for input_dir in agent.input_path:
                        search_path = self.vault_path / input_dir
                        if search_path.exists():
                            # Look for matching file
                            for ext in ['.md', '.txt']:
                                candidate = search_path / f"{input_filename}{ext}"
                                if candidate.exists():
                                    input_path = str(candidate.relative_to(self.vault_path))
                                    break
                            if input_path:
                                break

            # Use task file path as fallback if no input found
            if not input_path:
                input_path = str(task_file_path.relative_to(self.vault_path))

            # Create synthetic trigger event data
            def make_json_serializable(obj):
                """Recursively convert date/datetime objects to ISO strings."""
                if isinstance(obj, (datetime, date)):
                    return obj.isoformat()
                elif isinstance(obj, dict):
                    return {k: make_json_serializable(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [make_json_serializable(item) for item in obj]
                else:
                    return obj

            event_data = {
                'path': input_path,
                'event_type': 'manual_reprocess',
                'is_directory': False,
                'timestamp': datetime.now(),
                'frontmatter': {}
            }

            event_data_serializable = make_json_serializable(event_data)

            # Serialize trigger data (keep as JSON string, will be properly escaped in task_manager)
            trigger_data_json = json.dumps(event_data_serializable, ensure_ascii=False)

            # Add trigger_data_json to task file
            self.execution_manager.task_manager.update_task_status_with_trigger_data(
                task_file_path,
                "QUEUED",  # Keep status as QUEUED
                trigger_data_json
            )

            return trigger_data_json

        except Exception as e:
            logger.error(f"Error enriching QUEUED task with trigger data: {e}", exc_info=True)
            return None

    def _create_worker_agent_variant(self, base_agent: AgentDefinition, worker: WorkerConfig) -> AgentDefinition:
        """
        Create an agent variant with worker-specific settings.

        Args:
            base_agent: Base agent definition to copy
            worker: Worker configuration with executor and label

        Returns:
            New AgentDefinition with worker-specific settings
        """
        from dataclasses import replace

        # Create a copy with worker-specific overrides
        worker_abbr = f"{base_agent.abbreviation}-{worker.label}"

        # Merge agent_params: base agent params + worker-specific params
        merged_params = {**base_agent.agent_params, **worker.agent_params}

        # Modify output_naming to include worker label
        output_naming = base_agent.output_naming
        if '{agent}' in output_naming:
            # Replace {agent} pattern to include worker label
            output_naming = output_naming.replace('{agent}', f'{{agent}}-{worker.label}')
        else:
            # Append worker label to filename
            if output_naming.endswith('.md'):
                output_naming = output_naming[:-3] + f' - {worker.label}.md'
            else:
                output_naming = output_naming + f' - {worker.label}'

        return replace(
            base_agent,
            abbreviation=worker_abbr,
            executor=worker.executor,
            agent_params=merged_params,
            output_path=worker.output_path or base_agent.output_path,
            output_naming=output_naming,
            log_pattern='{timestamp}-{agent}.log',  # Agent abbr includes worker label
            workers=[]  # Clear workers list to prevent recursion
        )

    def get_status(self) -> dict:
        """
        Get current orchestrator status.

        Returns:
            Dictionary with status information
        """
        return {
            'running': self._running,
            'vault_path': str(self.vault_path),
            'agents_loaded': len(self.agent_registry.agents),
            'pollers_loaded': len(self.poller_manager.pollers),
            'running_executions': self.execution_manager.get_running_count(),
            'max_concurrent': self.max_concurrent,
            'agent_list': [
                {
                    'abbreviation': agent.abbreviation,
                    'name': agent.name,
                    'category': agent.category,
                    'running': self.execution_manager.get_agent_running_count(agent.abbreviation)
                }
                for agent in self.agent_registry.agents.values()
            ]
        }

    def trigger_agent_once(self, agent_abbreviation: str, session_id: Optional[str] = None) -> Optional[ExecutionContext]:
        """
        Manually trigger an agent once (synchronously).

        Args:
            agent_abbreviation: Agent abbreviation (e.g., "GDR", "EIC")
            session_id: Optional session ID for tracking related executions

        Returns:
            ExecutionContext if agent was found and executed, None otherwise
        """
        from datetime import datetime

        # Look up agent
        agent = self.agent_registry.agents.get(agent_abbreviation)
        if not agent:
            logger.error(f"Agent '{agent_abbreviation}' not found")
            return None

        logger.info(f"Manually triggering agent: {agent.abbreviation} ({agent.name})")

        # Create synthetic TriggerEvent for manual execution
        trigger_event = TriggerEvent(
            path="",  # No file path for manual triggers
            event_type="manual",
            is_directory=False,
            timestamp=datetime.now(),
            frontmatter={}
        )

        # Convert to event data dict
        event_data = {
            'path': trigger_event.path,
            'event_type': trigger_event.event_type,
            'is_directory': trigger_event.is_directory,
            'timestamp': trigger_event.timestamp,
            'frontmatter': trigger_event.frontmatter,
            'session_id': session_id  # Add session_id to event_data
        }

        # Execute synchronously via _execute_agent
        try:
            ctx = self._execute_agent(agent, event_data, slot_reserved=False)
            return ctx
        except Exception as e:
            logger.error(f"Error executing agent {agent_abbreviation}: {e}", exc_info=True)
            return None

    def execute_prompt_with_session(self, prompt: str, system_prompt: str = None, system_prompt_file: Optional[Path] = None, append_system_prompt: str = None, append_system_prompt_file: Optional[Path] = None, session_id: Optional[str] = None) -> Optional[ExecutionContext]:
        """
        Execute a one-time prompt with Claude agent and optional session ID.
        Automatically resumes session if it exists, creates new if it doesn't.

        Args:
            prompt: The prompt text to execute
            system_prompt: The system prompt to use for the agent
            system_prompt_file: Path to file containing system prompt
            append_system_prompt: Additional system prompt to append
            append_system_prompt_file: Path to file containing additional system prompt to append
            session_id: Optional session ID for tracking related executions (auto resume/create)

        Returns:
            ExecutionContext if execution succeeded, None otherwise
        """
        from datetime import datetime
        from .models import AgentDefinition

        # Create a temporary agent definition with claude_code executor
        agent = AgentDefinition(
            name="One-time prompt",
            system_prompt=system_prompt,
            system_prompt_file=system_prompt_file,
            append_system_prompt=append_system_prompt,
            append_system_prompt_file=append_system_prompt_file,
            abbreviation="ONETIME",
            category="adhoc",
            trigger_pattern="",
            trigger_event="manual",
            prompt_body=prompt,
            executor="claude_code",  # Always use claude
            max_parallel=1,
            timeout_minutes=30,
            output_path="",
            output_type="new_file",
            task_create=False  # Don't create task files for one-time prompts
        )

        logger.info(f"Executing one-time prompt with Claude (session_id: {session_id or 'none'}, auto resume/create)")

        # Create event data with session_id
        event_data = {
            'path': "",
            'event_type': 'onetime_prompt',
            'is_directory': False,
            'timestamp': datetime.now(),
            'frontmatter': {},
            'session_id': session_id  # Add session_id to event_data
        }

        # Execute via _execute_agent (which will extract session_id and pass to execute)
        try:
            # Reserve slot first
            if not self.execution_manager.reserve_slot(agent):
                logger.error("Cannot execute: concurrency limit reached")
                return None

            # Execute via _execute_agent (which returns ctx)
            ctx = self._execute_agent(agent, event_data, slot_reserved=True)
            return ctx
        except Exception as e:
            logger.error(f"Error executing one-time prompt: {e}", exc_info=True)
            return None

    def run_forever(self):
        """
        Start orchestrator and run forever (until interrupted).

        Blocks until KeyboardInterrupt or stop() is called.
        """
        self.start()

        try:
            logger.info("Orchestrator running. Press Ctrl+C to stop.")
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        finally:
            self.stop()
