import os
import sys
import time
import re
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Type
from datetime import datetime
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import fnmatch


class BaseFileHandler(ABC):
    """Abstract base class for file pattern handlers."""
    
    REQUESTS_BASE_DIR = "AI/Tasks/Requests"
    
    def __init__(self, logger=None, workspace_path=None):
        """
        Initialize the handler with optional logger and workspace path.
        
        Args:
            logger: Logger instance
            workspace_path: Path to the workspace root
        """
        self.logger = logger or logging.getLogger(__name__)
        self.workspace_path = workspace_path or os.getcwd()
    
    def _get_source_name(self) -> str:
        """
        Get the source name for this handler (e.g., 'Limitless', 'Gobi').
        
        Returns:
            Source name derived from handler class name
        """
        return self.__class__.__name__.replace('FileHandler', '')
    
    def _get_requests_dir(self) -> str:
        """
        Get the requests directory for this handler's source.
        
        Returns:
            Full path to requests directory for this source
        """
        source_name = self._get_source_name()
        return os.path.join(self.workspace_path, self.REQUESTS_BASE_DIR, source_name)
    
    def get_last_sync_timestamp(self) -> Optional[datetime]:
        """
        Get the last sync timestamp by finding the most recent request file.
        
        Returns:
            datetime object of last sync, or None if no files exist
        """
        try:
            requests_dir = self._get_requests_dir()
            
            if not os.path.exists(requests_dir):
                return None
            
            # Find all json files in the requests directory
            files = [f for f in os.listdir(requests_dir) if f.endswith('.json')]
            
            if not files:
                return None
            
            # Parse timestamps from filenames (format: YYYY-MM-DD-{milliseconds}.json)
            latest_timestamp = None
            
            for filename in files:
                # Extract date and milliseconds from filename
                # Pattern: YYYY-MM-DD-{milliseconds}.json
                match = re.match(r'(\d{4}-\d{2}-\d{2})-(\d+)\.json', filename)
                if match:
                    date_str = match.group(1)
                    milliseconds_str = match.group(2)
                    
                    try:
                        # Convert milliseconds since epoch to datetime
                        milliseconds = int(milliseconds_str)
                        file_timestamp = datetime.fromtimestamp(milliseconds / 1000.0)
                        
                        if latest_timestamp is None or file_timestamp > latest_timestamp:
                            latest_timestamp = file_timestamp
                    except (ValueError, OSError) as e:
                        self.logger.debug(f"Could not parse timestamp from filename: {filename} - {e}")
                        continue
            
            return latest_timestamp
            
        except Exception as e:
            self.logger.error(f"Error getting last sync timestamp: {e}")
            return None
    
    @abstractmethod
    def process(self, file_path: str, event_type: str) -> None:
        """
        Process a file that matches the handler's pattern.
        
        Args:
            file_path: Path to the file that triggered the event
            event_type: Type of event ('created' or 'modified')
        """
        pass


class FileWatchdogHandler(FileSystemEventHandler):
    """
    A custom event handler that responds to file modification and creation events,
    mapping file patterns to specific handler classes.
    """
    def __init__(self, pattern_handlers: Optional[List[Tuple[str, Type[BaseFileHandler]]]] = None,
                 excluded_patterns=None, logger=None, workspace_path=None):
        """
        Initialize the file watchdog handler.
        
        Args:
            pattern_handlers: Ordered list of (pattern, handler_class) tuples.
                Patterns are checked in order, and the first match is used.
                Example: [
                    ('Ingest/Gobi/*.md', GobiFileHandler),
                    ('Journal/*.md', JournalFileHandler),
                    ('*.md', MarkdownFileHandler)
                ]
            excluded_patterns: Patterns to exclude
            logger: Logger instance
            workspace_path: Path to the workspace root
        """
        super().__init__()
        self.logger = logger or logging.getLogger(__name__)
        self.workspace_path = workspace_path or os.getcwd()
        
        # Initialize pattern handlers as ordered list
        self.pattern_handlers = []
        if pattern_handlers:
            for pattern, handler_class in pattern_handlers:
                try:
                    handler = handler_class(logger=self.logger, workspace_path=self.workspace_path)
                    self.pattern_handlers.append((pattern, handler))
                except Exception as e:
                    self.logger.error(f"Failed to initialize handler for pattern {pattern}: {e}")
        
        self.excluded_patterns = excluded_patterns if excluded_patterns else []

    def _is_excluded(self, path):
        """
        Checks if a given path should be excluded.
        
        Supports both directory names and glob patterns:
        - Directory names (e.g., '.git', 'node_modules') will exclude any file under that directory
        - Glob patterns (e.g., '*.tmp', 'test/*') use fnmatch for pattern matching
        """
        # Split path into components to check directory names
        path_parts = path.split(os.sep)
        
        for pattern in self.excluded_patterns:
            # Check if pattern is a simple directory name (no wildcards)
            if '*' not in pattern and '?' not in pattern and '[' not in pattern:
                # Check if this directory name appears anywhere in the path
                if pattern in path_parts:
                    return True
            else:
                # Use fnmatch for glob patterns
                if fnmatch.fnmatch(path, pattern):
                    return True
        return False

    def _find_matching_handler(self, path: str) -> Optional[BaseFileHandler]:
        """
        Find the first handler that matches the given file path.
        Patterns are checked in order, and the first match is used.
        
        Args:
            path: File path to match against patterns
            
        Returns:
            Handler instance if a pattern matches, None otherwise
        """
        # Convert absolute path to relative path for pattern matching
        if os.path.isabs(path):
            try:
                rel_path = os.path.relpath(path, self.workspace_path)
            except ValueError:
                # Can't make relative path (different drives on Windows, etc.)
                rel_path = path
        else:
            rel_path = path
        
        for pattern, handler in self.pattern_handlers:
            # Try matching both with and without wildcard expansion
            if fnmatch.fnmatch(rel_path, pattern):
                return handler
            # Also try matching the full path for absolute patterns
            if fnmatch.fnmatch(path, pattern):
                return handler
        return None
    
    def _process_with_handler(self, file_path: str, event_type: str):
        """
        Process an event using pattern-based handlers.
        
        Args:
            event: FileSystemEvent object
            event_type: Type of event ('created' or 'modified')
        """
        # Check if file is excluded
        if self._is_excluded(file_path):
            return
        
        # Find matching handler
        handler = self._find_matching_handler(file_path)
        if handler:
            try:
                handler.process(file_path, event_type)
            except Exception as e:
                self.logger.error(f"Error processing {file_path} with handler: {e}")

    def on_modified(self, event):
        """
        Called when a file or directory is modified.

        Args:
            event (FileSystemEvent): Event representing file/directory modification.
        """
        
        if event.is_directory:
            return
            
        self._process_with_handler(event.src_path, 'modified')

    def on_created(self, event):
        """
        Called when a file or directory is created.

        Args:
            event (FileSystemEvent): Event representing file/directory creation.
        """
        if event.is_directory:
            return
            
        self._process_with_handler(event.src_path, 'created')

    def on_moved(self, event):
        """
        Called when a file or directory is moved.

        Args:
            event (FileSystemEvent): Event representing file/directory movement.
        """
        if event.is_directory:
            return
            
        self._process_with_handler(event.dest_path, 'created')