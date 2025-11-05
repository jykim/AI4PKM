"""
Orchestrator core - main event loop and coordination.

Ties together file monitoring, agent matching, and execution management.
"""
import logging
import threading
import time
from pathlib import Path
from typing import Optional
from queue import Empty

from .file_monitor import FileSystemMonitor
from .agent_registry import AgentRegistry
from .execution_manager import ExecutionManager
from .models import TriggerEvent, ExecutionContext

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Main orchestrator for multi-agent AI4PKM system.

    Coordinates file monitoring, agent matching, and task execution.
    """

    def __init__(
        self,
        vault_path: Path,
        agents_dir: Optional[Path] = None,
        max_concurrent: Optional[int] = None,
        poll_interval: Optional[float] = None,
        config: Optional['Config'] = None,
        debug: bool = False
    ):
        """
        Initialize orchestrator.

        Args:
            vault_path: Path to vault root
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
        self.debug = debug

        # Use config values if not explicitly provided
        if agents_dir is None:
            prompts_dir = self.config.get_orchestrator_prompts_dir()
            self.agents_dir = self.vault_path / prompts_dir
        else:
            self.agents_dir = agents_dir

        self.max_concurrent = max_concurrent or self.config.get_orchestrator_max_concurrent()
        self.poll_interval = poll_interval or self.config.get_orchestrator_poll_interval()

        # Setup logging before creating directories
        self._setup_logging()

        # Ensure required directories exist
        self._ensure_directories()

        # Initialize components
        self.agent_registry = AgentRegistry(self.agents_dir, self.vault_path, self.config)
        self.execution_manager = ExecutionManager(
            self.vault_path,
            self.max_concurrent,
            self.config,
            orchestrator_settings=self.agent_registry.orchestrator_settings
        )
        self.file_monitor = FileSystemMonitor(self.vault_path, self.agent_registry)

        # Initialize cron scheduler
        from .cron_scheduler import CronScheduler
        self.cron_scheduler = CronScheduler(
            self.agent_registry,
            self.file_monitor.event_queue
        )

        # Control state
        self._running = False
        self._event_thread: Optional[threading.Thread] = None

        logger.info(f"Orchestrator initialized for vault: {self.vault_path}")
        logger.info(f"Loaded {len(self.agent_registry.agents)} agents")

    def _setup_logging(self):
        """
        Configure logging for orchestrator.

        - Console: INFO+ (or DEBUG+ if debug=True)
        - File: DEBUG+ (all logs)
        """
        from datetime import datetime

        # Get logs directory from config
        logs_dir = self.vault_path / self.config.get_orchestrator_logs_dir()
        logs_dir.mkdir(parents=True, exist_ok=True)

        # Create log file with date stamp
        log_filename = f"orchestrator_{datetime.now().strftime('%Y-%m-%d')}.log"
        log_file = logs_dir / log_filename

        # Configure file handler (DEBUG level - captures everything)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)

        # Configure console handler (INFO or DEBUG based on flag)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG if self.debug else logging.INFO)
        console_formatter = logging.Formatter('%(message)s')
        console_handler.setFormatter(console_formatter)

        # Get root logger for orchestrator modules
        orchestrator_logger = logging.getLogger('ai4pkm_cli.orchestrator')
        orchestrator_logger.setLevel(logging.DEBUG)  # Capture all levels

        # Remove existing handlers to avoid duplicates
        orchestrator_logger.handlers.clear()

        # Add both handlers
        orchestrator_logger.addHandler(file_handler)
        orchestrator_logger.addHandler(console_handler)

        # Prevent propagation to root logger (avoid duplicate console output)
        orchestrator_logger.propagate = False

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

        # Start event processing thread
        self._running = True
        self._event_thread = threading.Thread(target=self._event_loop, daemon=True)
        self._event_thread.start()

        logger.info("Orchestrator started successfully")

    def stop(self):
        """Stop the orchestrator event loop."""
        if not self._running:
            logger.warning("Orchestrator not running")
            return

        logger.info("Stopping orchestrator...")

        # Stop event processing
        self._running = False

        # Stop cron scheduler
        self.cron_scheduler.stop()

        # Stop file monitor
        self.file_monitor.stop()

        # Wait for event thread to finish
        if self._event_thread and self._event_thread.is_alive():
            self._event_thread.join(timeout=5.0)

        logger.info("Orchestrator stopped")

    def _event_loop(self):
        """
        Main event processing loop.

        Polls file monitor queue and processes events.
        """
        logger.info("Event loop started")

        while self._running:
            try:
                # Poll event queue with timeout
                try:
                    trigger_event = self.file_monitor.event_queue.get(timeout=self.poll_interval)
                except Empty:
                    # No events, continue polling
                    continue

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
            # Try to reserve a slot atomically (prevents race conditions)
            if not self.execution_manager.reserve_slot(agent):
                # Create QUEUED task instead of dropping
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
                trigger_data_json = json.dumps(event_data_serializable).replace('"', '\\"')

                # Create minimal context for task file creation
                ctx = ExecutionContext(
                    agent=agent,
                    trigger_data=event_data,
                    start_time=datetime.now()
                )

                # Prepare log path
                log_path = self.execution_manager._prepare_log_path(agent, ctx)
                ctx.log_file = log_path

                # Create QUEUED task
                self.execution_manager.task_manager.create_task_file(
                    ctx, agent,
                    initial_status="QUEUED",
                    trigger_data_json=trigger_data_json
                )

                logger.info(f"Queued {agent.abbreviation}: concurrency limit reached")
                continue

            # Log agent trigger at INFO level for visibility
            input_filename = Path(trigger_event.path).name if trigger_event.path else "scheduled"
            logger.info(f"Triggering {trigger_event.event_type} agent: {agent.abbreviation} ({input_filename})")
            logger.debug(f"Starting {agent.abbreviation}: {trigger_event.path}")

            # Execute in background thread (slot already reserved)
            execution_thread = threading.Thread(
                target=self._execute_agent,
                args=(agent, event_data, True),  # slot_reserved=True
                daemon=True
            )
            execution_thread.start()

    def _execute_agent(self, agent, event_data, slot_reserved=False):
        """
        Execute an agent task.

        Args:
            agent: AgentDefinition to execute
            event_data: Event data dictionary
            slot_reserved: Whether slot was already reserved
        """
        try:
            ctx = self.execution_manager.execute(agent, event_data, slot_reserved=slot_reserved)

            if ctx.success:
                logger.info(f"{agent.abbreviation} completed ({ctx.duration:.1f}s)")
            else:
                duration_str = f"{ctx.duration:.1f}s" if ctx.duration else "unknown"
                error_msg = f"{agent.abbreviation} failed: {ctx.status} ({duration_str})"
                if ctx.error_message:
                    error_msg += f" - {ctx.error_message}"
                logger.error(error_msg)

        except Exception as e:
            logger.error(f"{agent.abbreviation} error: {e}", exc_info=True)

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

                # Extract agent abbreviation and trigger data
                agent_abbr = fm.get('task_type')
                trigger_data_json = fm.get('trigger_data_json')

                if not agent_abbr or not trigger_data_json:
                    logger.warning(f"Malformed QUEUED task: {task_path.name}")
                    continue

                # Look up agent definition
                agent = self.agent_registry.agents.get(agent_abbr)
                if not agent:
                    logger.warning(f"Agent not found for QUEUED task: {agent_abbr}")
                    continue

                # Try to reserve a slot atomically
                if not self.execution_manager.reserve_slot(agent):
                    break  # Still no capacity, wait for next iteration

                # Reconstruct trigger data (unescape quotes)
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

                # Update task status from QUEUED to IN_PROGRESS
                self.execution_manager.task_manager.update_task_status(task_path, "IN_PROGRESS")

                # Execute agent (slot already reserved)
                event_path = event_data.get('path', '')
                logger.debug(f"Starting queued {agent.abbreviation}: {event_path}")

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
