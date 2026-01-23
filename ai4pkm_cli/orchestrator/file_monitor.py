"""
File system monitor for orchestrator.

Monitors vault for file changes and queues events for processing.
Uses debouncing to group rapid file changes and process them after a delay.
"""
import threading
from pathlib import Path
from queue import Queue
from datetime import datetime
from typing import Dict, Optional, Tuple
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from ..markdown_utils import read_frontmatter
from ..logger import Logger

logger = Logger()


class FileSystemMonitor:
    """
    Monitor file system for events and queue them for processing.
    
    Uses debouncing to group rapid file changes and process them after a delay.
    This prevents multiple triggers for the same file modification.
    """

    def __init__(self, vault_path: Path, agent_registry=None, debounce_interval: float = 0.5,
                 file_extensions: list = None):
        """
        Initialize file system monitor.

        Args:
            vault_path: Path to vault root
            agent_registry: AgentRegistry instance (optional, for future use)
            debounce_interval: Seconds to wait after last event before processing (default: 0.5)
            file_extensions: List of file extensions to monitor (default: ['.md'])
        """
        self.vault_path = Path(vault_path)
        self.agent_registry = agent_registry
        self.observer = Observer()
        self.event_queue = Queue()
        self._running = False
        self.debounce_interval = debounce_interval
        self.file_extensions = file_extensions or ['.md']
        
        # Debouncing state: (path, event_type) -> (event_data, timer)
        self._pending_events: Dict[Tuple[str, str], Tuple[dict, Optional[threading.Timer]]] = {}
        self._pending_events_lock = threading.Lock()

    def start(self):
        """Start monitoring file system."""
        event_handler = _FileEventHandler(self, self.vault_path, self.debounce_interval, self.file_extensions)
        self.observer.schedule(event_handler, str(self.vault_path), recursive=True)
        self.observer.start()
        self._running = True
        logger.info(f"File system monitoring started on {self.vault_path} (debounce: {self.debounce_interval}s, extensions: {self.file_extensions})")

    def stop(self):
        """Stop monitoring file system."""
        self._running = False
        
        # Cancel all pending debounce timers
        with self._pending_events_lock:
            for event_key, (_, timer) in self._pending_events.items():
                if timer:
                    timer.cancel()
            self._pending_events.clear()
        
        self.observer.stop()
        self.observer.join()
        logger.info("File system monitoring stopped")
    
    def _process_debounced_event(self, event_key: Tuple[str, str], event_data: dict):
        """
        Process a debounced event after delay.
        
        Args:
            event_key: (path, event_type) tuple
            event_data: Event data dictionary
        """
        with self._pending_events_lock:
            # Check if this event is still the latest (might have been replaced)
            if event_key in self._pending_events:
                stored_data, _ = self._pending_events[event_key]
                if stored_data is event_data:  # Still the latest event
                    del self._pending_events[event_key]
                    
                    # Read frontmatter now (file should be stable after debounce delay)
                    frontmatter = {}
                    if event_data['event_type'] != 'deleted' and 'file_path' in event_data:
                        file_path = event_data['file_path']
                        if file_path.exists():
                            try:
                                frontmatter = read_frontmatter(file_path)
                            except Exception as e:
                                logger.debug(f"Failed to read frontmatter for {event_data['path']}: {e}")
                    
                    # Create TriggerEvent and queue it
                    from .models import TriggerEvent
                    trigger_event = TriggerEvent(
                        path=event_data['path'],
                        event_type=event_data['event_type'],
                        is_directory=event_data['is_directory'],
                        timestamp=event_data['timestamp'],
                        frontmatter=frontmatter
                    )
                    
                    self.event_queue.put(trigger_event)
                    logger.debug(f"Processed debounced {event_data['event_type']} event: {event_data['path']}")
    
    def _debounce_event(self, relative_path: str, event_type: str, event_data: dict):
        """
        Debounce an event - group rapid events and process after delay.
        
        Args:
            relative_path: Relative file path
            event_type: Event type (created, modified, deleted, config_reload)
            event_data: Event data dictionary
        """
        event_key = (relative_path, event_type)
        
        with self._pending_events_lock:
            # Cancel existing timer for this event if any
            if event_key in self._pending_events:
                _, old_timer = self._pending_events[event_key]
                if old_timer:
                    old_timer.cancel()
            
            # Create new timer to process event after debounce interval
            timer = threading.Timer(
                self.debounce_interval,
                self._process_debounced_event,
                args=(event_key, event_data)
            )
            timer.daemon = True
            timer.start()
            
            # Store event data and timer
            self._pending_events[event_key] = (event_data, timer)
            
            logger.debug(f"Debouncing {event_type} event for {relative_path} "
                        f"(will process after {self.debounce_interval}s)")

    @property
    def is_running(self) -> bool:
        """Check if monitor is running."""
        return self._running and self.observer.is_alive()


class _FileEventHandler(FileSystemEventHandler):
    """Internal handler for watchdog file events."""

    def __init__(self, file_monitor: 'FileSystemMonitor', vault_path: Path, debounce_interval: float, file_extensions: list):
        self.file_monitor = file_monitor
        self.vault_path = vault_path
        self.debounce_interval = debounce_interval
        self.file_extensions = file_extensions

    def _matches_extension(self, path: str) -> bool:
        """Check if path matches any configured file extension."""
        return any(path.lower().endswith(ext.lower()) for ext in self.file_extensions)

    def on_created(self, event: FileSystemEvent):
        """Handle file creation events."""
        file_path = Path(event.src_path)
        
        # Make path relative to vault
        try:
            relative_path = file_path.relative_to(self.vault_path)
        except ValueError:
            relative_path = file_path
        
        # Check if this is orchestrator.yaml (special handling for hot-reload)
        if str(relative_path) == "orchestrator.yaml":
            self._debounce_reload_event(event)
        elif not event.is_directory and self._matches_extension(event.src_path):
            self._debounce_file_event(event, 'created')

    def on_modified(self, event: FileSystemEvent):
        """Handle file modification events."""
        file_path = Path(event.src_path)
        
        # Make path relative to vault
        try:
            relative_path = file_path.relative_to(self.vault_path)
        except ValueError:
            relative_path = file_path
        
        # Check if this is orchestrator.yaml (special handling for hot-reload)
        if str(relative_path) == "orchestrator.yaml":
            self._debounce_reload_event(event)
        elif not event.is_directory and self._matches_extension(event.src_path):
            self._debounce_file_event(event, 'modified')

    def on_deleted(self, event: FileSystemEvent):
        """Handle file deletion events."""
        if not event.is_directory and self._matches_extension(event.src_path):
            self._debounce_file_event(event, 'deleted')

    def on_moved(self, event: FileSystemEvent):
        """Handle file move/rename events (e.g., atomic writes)."""
        if not event.is_directory and self._matches_extension(event.dest_path):
            # Treat destination of move as a creation event
            # This handles atomic writes (temp file -> final file)
            self._debounce_file_event_for_moved(event, 'created')

    def _debounce_file_event(self, event: FileSystemEvent, event_type: str):
        """Debounce a file event - will process after delay."""
        file_path = Path(event.src_path)

        # Make path relative to vault
        try:
            relative_path = file_path.relative_to(self.vault_path)
        except ValueError:
            relative_path = file_path

        # Prepare event data (frontmatter will be read when event is processed)
        event_data = {
            'path': str(relative_path),
            'event_type': event_type,
            'is_directory': event.is_directory,
            'timestamp': datetime.now(),
            'file_path': file_path,  # Store for later reading
            'frontmatter': {}  # Will be populated when processed
        }

        # Debounce the event
        self.file_monitor._debounce_event(str(relative_path), event_type, event_data)

    def _debounce_file_event_for_moved(self, event: FileSystemEvent, event_type: str):
        """Debounce a move event using the destination path."""
        file_path = Path(event.dest_path)  # Use destination path

        # Make path relative to vault
        try:
            relative_path = file_path.relative_to(self.vault_path)
        except ValueError:
            relative_path = file_path

        # Prepare event data
        event_data = {
            'path': str(relative_path),
            'event_type': event_type,
            'is_directory': event.is_directory,
            'timestamp': datetime.now(),
            'file_path': file_path,  # Store for later reading
            'frontmatter': {}  # Will be populated when processed
        }

        # Debounce the event
        self.file_monitor._debounce_event(str(relative_path), event_type, event_data)

    def _debounce_reload_event(self, event: FileSystemEvent):
        """Debounce a config reload event for orchestrator.yaml changes."""
        event_data = {
            'path': "orchestrator.yaml",
            'event_type': "config_reload",
            'is_directory': False,
            'timestamp': datetime.now(),
            'frontmatter': {}
        }

        # Debounce the event (orchestrator.yaml uses same debouncing)
        self.file_monitor._debounce_event("orchestrator.yaml", "config_reload", event_data)
        logger.debug("Debouncing config reload event: orchestrator.yaml changed")
