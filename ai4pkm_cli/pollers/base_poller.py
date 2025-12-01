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
        self.logger = getattr(module, 'logger', None)
        if self.logger is None:
            raise ValueError(f"Logger not found in module {self.__class__.__module__}. Each poller must define 'logger' at module level.")
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
        self._shutdown_event = threading.Event()
        
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
                self.logger.warning(f"Failed to load state from {self.state_file}: {e}")
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
            self.logger.error(f"Failed to save state to {self.state_file}: {e}")
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
        self.logger.info(f"Running {self.__class__.__name__} once...")
        
        try:
            success = self.poll()
            
            if success:
                self.logger.info(f"{self.__class__.__name__} completed successfully")
            else:
                self.logger.warning(f"{self.__class__.__name__} completed with errors")
            
            self.save_state()
            return success
            
        except Exception as e:
            self.logger.error(f"{self.__class__.__name__} failed: {e}", exc_info=True)
            self.save_state()
            return False

    def start(self) -> None:
        """Start the polling loop in a background thread."""
        if self._running:
            self.logger.warning(f"{self.__class__.__name__} is already running")
            return
        
        self._running = True
        self._shutdown_event.clear()
        self._thread = threading.Thread(target=self._polling_loop, daemon=True)
        self._thread.start()
        self.logger.info(f"{self.__class__.__name__} started (interval: {self.poll_interval}s)")

    def stop(self, timeout: float = 5.0) -> None:
        """
        Stop the polling loop.

        Args:
            timeout: Maximum time to wait for thread to stop
        """
        if not self._running:
            return
        
        self.logger.info(f"Stopping {self.__class__.__name__}...")
        self._running = False
        self._shutdown_event.set()
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
            if self._thread.is_alive():
                self.logger.warning(f"{self.__class__.__name__} thread did not stop within timeout")
            else:
                self.logger.info(f"{self.__class__.__name__} stopped")

    def _polling_loop(self) -> None:
        """Main polling loop that runs in background thread."""
        self.logger.info(f"{self.__class__.__name__} polling loop started")

        first_run = True

        try:
            while self._running:
                try:
                    if first_run:
                        self.logger.info(f"{self.__class__.__name__} running initial poll immediately")
                        first_run = False
                    self.run_once()

                    if self._shutdown_event.wait(timeout=self.poll_interval):
                        break

                except Exception as e:
                    self.logger.error(f"Error in {self.__class__.__name__} polling loop: {e}", exc_info=True)
                    if self._shutdown_event.wait(timeout=60):
                        break
        except (KeyboardInterrupt, SystemExit):
            self.logger.info(f"{self.__class__.__name__} received shutdown signal")
        except BaseException as e:
            # Catch any other fatal exceptions (C-level crashes, etc.)
            self.logger.critical(f"{self.__class__.__name__} polling loop crashed with fatal error: {e}", exc_info=True)
        finally:
            self._running = False
            self.logger.info(f"{self.__class__.__name__} polling loop stopped")

    def is_running(self) -> bool:
        """Check if poller is currently running."""
        return self._running

    def is_thread_alive(self) -> bool:
        """
        Check if the polling thread is actually alive.

        This is more reliable than is_running() for detecting silently crashed threads.
        A thread can be marked as _running=True but actually be dead.

        Returns:
            True if thread exists and is alive, False otherwise
        """
        return self._thread is not None and self._thread.is_alive()

    def is_healthy(self) -> bool:
        """
        Check if the poller is healthy (running and thread alive).

        Returns:
            True if poller should be running and thread is alive, False otherwise
        """
        # If not meant to be running, it's "healthy" in the sense that it's working as expected
        if not self._running:
            return True
        # If meant to be running, thread must be alive
        return self.is_thread_alive()

    def restart(self) -> None:
        """
        Restart the poller.

        Stops the poller if running and starts it again.
        Used by watchdog to recover from dead threads.
        """
        self.logger.info(f"Restarting {self.__class__.__name__}...")
        self.stop()
        self.start()
        self.logger.info(f"{self.__class__.__name__} restarted successfully")

    def get_state(self) -> Dict[str, Any]:
        """Get current state dictionary."""
        return self.state.copy()

