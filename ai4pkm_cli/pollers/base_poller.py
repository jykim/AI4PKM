"""Base poller class with common functionality for all pollers."""

import json
import signal
import sys
import threading
import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from ..logger import Logger

logger = Logger()

class BasePoller(ABC):
    """Base class for all pollers with common state management and polling logic."""

    def __init__(
        self,
        poller_config: Dict[str, Any],
        vault_path: Optional[Path] = None,
    ):
        """
        Initialize base poller.

        Args:
            poller_config: Poller-specific configuration dictionary (must contain 'target_dir' and optionally 'poll_interval')
            vault_path: Vault root path (defaults to CWD)
        """
        # Get logger from the subclass's module
        import sys
        module = sys.modules[self.__class__.__module__]
        self.poller_config = poller_config or {}
        self.vault_path = Path(vault_path) if vault_path else Path.cwd()
        
        target_dir = self.poller_config.get('target_dir')
        if not target_dir:
            raise ValueError("poller_config must contain 'target_dir'")
        
        target_path = Path(target_dir)
        if target_path.is_absolute():
            self.target_dir = target_path
        else:
            self.target_dir = self.vault_path / target_dir
        
        self.target_dir.mkdir(parents=True, exist_ok=True)
        
        self.poll_interval = self.poller_config.get('poll_interval', 3600)
        self.state_file = self.target_dir / "state.json"
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
        self.state = self.load_state()

    def load_state(self) -> Dict[str, Any]:
        """
        Load state from state.json file.

        Returns:
            State dictionary for next polling
        """
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Failed to load state from {self.state_file}: {e}")
                return {}
        
        return {}

    def save_state(self) -> bool:
        """
        Save current state to state.json file.
        Only saves if state contains data for next polling.

        Returns:
            True if successful, False otherwise
        """
        if not self.state:
            if self.state_file.exists():
                try:
                    self.state_file.unlink()
                except OSError:
                    pass
            return True
        
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, indent=2, default=str)
            return True
        except OSError as e:
            logger.error(f"Failed to save state to {self.state_file}: {e}")
            return False

    def update_state(self, **kwargs) -> None:
        """
        Update state for next polling.

        Args:
            **kwargs: Key-value pairs to update in state
        """
        if kwargs:
            self.state.update(kwargs)
            self.save_state()

    @abstractmethod
    def poll(self) -> bool:
        """
        Perform one polling operation.

        Returns:
            True if successful, False otherwise
        """
        pass

    def run_once(self) -> bool:
        """
        Run a single poll operation (for standalone execution).

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Running {self.__class__.__name__}", console=True)

            success = self.poll()
            
            if success:
                logger.info(f"{self.__class__.__name__} completed successfully", console=True)
            else:
                logger.warning(f"{self.__class__.__name__} completed with errors", console=True)
            
            self.save_state()
            return success
            
        except Exception as e:
            logger.error(f"{self.__class__.__name__} failed: {e}", console=True, exc_info=True)
            self.save_state()
            return False

    def start(self) -> None:
        """Start the polling loop in a background thread."""
        if self._running:
            logger.warning(f"{self.__class__.__name__} is already running")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._polling_loop, daemon=True)
        self._thread.start()
        logger.info(f"{self.__class__.__name__} started (interval: {self.poll_interval}s)")

    def stop(self, timeout: float = 5.0) -> None:
        """
        Stop the polling loop.

        Args:
            timeout: Maximum time to wait for thread to stop
        """
        if not self._running:
            return
        
        logger.info(f"Stopping {self.__class__.__name__}...")
        self._running = False
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
            if self._thread.is_alive():
                logger.warning(f"{self.__class__.__name__} thread did not stop within timeout")
            else:
                logger.info(f"{self.__class__.__name__} stopped")

    def _polling_loop(self) -> None:
        """Main polling loop that runs in background thread."""
        logger.info(f"{self.__class__.__name__} polling loop started")
        
        first_run = True
        
        while self._running:
            try:
                if first_run:
                    logger.info(f"{self.__class__.__name__} running initial poll immediately", console=True)
                    first_run = False
                self.run_once()
                
                if not self._running:
                    logger.error(f"{self.__class__.__name__} polling loop stopped", console=True)
                    break
                time.sleep(self.poll_interval)
                    
            except Exception as e:
                logger.error(f"Error in {self.__class__.__name__} polling loop: {e}", console=True, exc_info=True)
                if not self._running:
                    break
                time.sleep(60)
        
        logger.info(f"{self.__class__.__name__} polling loop stopped")

    def is_running(self) -> bool:
        """Check if poller is currently running."""
        return self._running

    def get_state(self) -> Dict[str, Any]:
        """Get current state dictionary."""
        return self.state.copy()

