"""
File system monitor for orchestrator.

Monitors vault for file changes and queues events for processing.
Simplified from KTM approach - no complex semaphores.
"""
import logging
from pathlib import Path
from queue import Queue
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from ..markdown_utils import read_frontmatter

logger = logging.getLogger(__name__)


class FileSystemMonitor:
    """
    Monitor file system for events and queue them for processing.
    """

    def __init__(self, vault_path: Path, agent_registry=None):
        """
        Initialize file system monitor.

        Args:
            vault_path: Path to vault root
            agent_registry: AgentRegistry instance (optional, for future use)
        """
        self.vault_path = Path(vault_path)
        self.agent_registry = agent_registry
        self.observer = Observer()
        self.event_queue = Queue()
        self._running = False

    def start(self):
        """Start monitoring file system."""
        event_handler = _FileEventHandler(self.event_queue, self.vault_path)
        self.observer.schedule(event_handler, str(self.vault_path), recursive=True)
        self.observer.start()
        self._running = True
        logger.info(f"File system monitoring started on {self.vault_path}")

    def stop(self):
        """Stop monitoring file system."""
        self._running = False
        self.observer.stop()
        self.observer.join()
        logger.info("File system monitoring stopped")

    @property
    def is_running(self) -> bool:
        """Check if monitor is running."""
        return self._running and self.observer.is_alive()


class _FileEventHandler(FileSystemEventHandler):
    """Internal handler for watchdog file events."""

    def __init__(self, event_queue: Queue, vault_path: Path):
        self.event_queue = event_queue
        self.vault_path = vault_path

    def on_created(self, event: FileSystemEvent):
        """Handle file creation events."""
        if not event.is_directory and event.src_path.endswith('.md'):
            self._queue_event(event, 'created')

    def on_modified(self, event: FileSystemEvent):
        """Handle file modification events."""
        if not event.is_directory and event.src_path.endswith('.md'):
            self._queue_event(event, 'modified')

    def on_deleted(self, event: FileSystemEvent):
        """Handle file deletion events."""
        if not event.is_directory and event.src_path.endswith('.md'):
            self._queue_event(event, 'deleted')

    def on_moved(self, event: FileSystemEvent):
        """Handle file move/rename events (e.g., atomic writes)."""
        if not event.is_directory and event.dest_path.endswith('.md'):
            # Treat destination of move as a creation event
            # This handles atomic writes (temp file -> final file)
            self._queue_event_for_moved(event, 'created')

    def _queue_event(self, event: FileSystemEvent, event_type: str):
        """Queue a file event for processing."""
        file_path = Path(event.src_path)

        # Make path relative to vault
        try:
            relative_path = file_path.relative_to(self.vault_path)
        except ValueError:
            relative_path = file_path

        # Parse frontmatter if file exists
        frontmatter = {}
        if file_path.exists() and event_type != 'deleted':
            frontmatter = read_frontmatter(file_path)

        # Create FileEvent object (not dict!)
        from .models import FileEvent
        file_event = FileEvent(
            path=str(relative_path),
            event_type=event_type,
            is_directory=event.is_directory,
            timestamp=datetime.now(),
            frontmatter=frontmatter
        )

        self.event_queue.put(file_event)
        logger.debug(f"Queued {event_type} event: {relative_path}")

    def _queue_event_for_moved(self, event: FileSystemEvent, event_type: str):
        """Queue a move event using the destination path."""
        file_path = Path(event.dest_path)  # Use destination path

        # Make path relative to vault
        try:
            relative_path = file_path.relative_to(self.vault_path)
        except ValueError:
            relative_path = file_path

        # Parse frontmatter if file exists
        frontmatter = {}
        if file_path.exists():
            frontmatter = read_frontmatter(file_path)

        # Create FileEvent object
        from .models import FileEvent
        file_event = FileEvent(
            path=str(relative_path),
            event_type=event_type,
            is_directory=event.is_directory,
            timestamp=datetime.now(),
            frontmatter=frontmatter
        )

        self.event_queue.put(file_event)
        logger.debug(f"Queued {event_type} event (from move): {relative_path}")
