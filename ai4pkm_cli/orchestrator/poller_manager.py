"""Poller manager for orchestrator - manages enabled pollers."""

import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional
from ..logger import Logger

logger = Logger()

# Default watchdog check interval in seconds
DEFAULT_WATCHDOG_INTERVAL = 60


class PollerManager:
    """Manages poller instances based on orchestrator.yaml configuration."""

    def __init__(self, vault_path: Path, config: 'Config', logger_instance: Optional[Any] = None,
                 watchdog_interval: int = DEFAULT_WATCHDOG_INTERVAL):
        """
        Initialize poller manager.

        Args:
            vault_path: Path to vault root
            config: Config instance
            logger_instance: Logger instance (optional, uses module logger if None)
            watchdog_interval: Interval in seconds for watchdog health checks (default: 60)
        """
        self.vault_path = Path(vault_path)
        self.config = config
        self.logger = logger_instance or logger
        self.watchdog_interval = watchdog_interval

        # Map of poller name -> poller instance
        self.pollers: Dict[str, 'BasePoller'] = {}

        # Watchdog thread state
        self._watchdog_running = False
        self._watchdog_thread: Optional[threading.Thread] = None
        self._watchdog_shutdown_event = threading.Event()

        # Load and initialize enabled pollers
        self._load_pollers()

    def _load_pollers(self) -> None:
        """Load and initialize enabled pollers from config."""
        pollers_config = self.config.get_pollers_config()
        
        if not pollers_config:
            self.logger.debug("No pollers configuration found")
            return
        
        # Import poller classes
        from ..pollers.apple_photos import ApplePhotosPoller
        from ..pollers.apple_notes import AppleNotesPoller
        from ..pollers.gobi import GobiPoller
        from ..pollers.gobi_by_tags import GobiByTagsPoller
        from ..pollers.limitless import LimitlessPoller
        
        # Map poller names to classes
        poller_classes = {
            'apple_photos': ApplePhotosPoller,
            'apple_notes': AppleNotesPoller,
            'gobi': GobiPoller,
            'gobi_by_tags': GobiByTagsPoller,
            'limitless': LimitlessPoller,
        }
        
        for poller_name, poller_config in pollers_config.items():
            if not poller_config.get('enabled', False):
                self.logger.debug(f"Poller '{poller_name}' is disabled, skipping")
                continue
            
            if poller_name not in poller_classes:
                self.logger.warning(f"Unknown poller name: {poller_name}")
                continue
            
            try:
                target_dir = poller_config.get('target_dir')
                if not target_dir:
                    self.logger.error(f"Poller '{poller_name}' missing required 'target_dir'")
                    continue
                
                poll_interval = poller_config.get('poll_interval', 3600)
                
                # Instantiate poller (each poller uses its own module-level logger)
                poller_class = poller_classes[poller_name]
                poller = poller_class(
                    poller_config=poller_config,
                    vault_path=self.vault_path
                )
                
                self.pollers[poller_name] = poller
                self.logger.info(f"Loaded poller: {poller_name} (target: {target_dir}, interval: {poll_interval}s)")
                
            except Exception as e:
                self.logger.error(f"Failed to load poller '{poller_name}': {e}", exc_info=True)

    def start_all(self) -> None:
        """Start all enabled pollers and the watchdog."""
        if not self.pollers:
            self.logger.info("No pollers to start")
            return

        self.logger.info(f"Starting {len(self.pollers)} poller(s)...")
        for name, poller in self.pollers.items():
            try:
                poller.start()
            except Exception as e:
                self.logger.error(f"Failed to start poller '{name}': {e}", exc_info=True)

        # Start watchdog to monitor poller health
        self._start_watchdog()

    def stop_all(self) -> None:
        """Stop all running pollers and the watchdog."""
        # Stop watchdog first to prevent it from restarting pollers
        self._stop_watchdog()

        if not self.pollers:
            return

        self.logger.info(f"Stopping {len(self.pollers)} poller(s)...")
        for name, poller in self.pollers.items():
            try:
                poller.stop()
            except Exception as e:
                self.logger.error(f"Failed to stop poller '{name}': {e}", exc_info=True)

    def _start_watchdog(self) -> None:
        """Start the watchdog thread to monitor poller health."""
        if self._watchdog_running:
            self.logger.warning("Watchdog is already running")
            return

        self._watchdog_running = True
        self._watchdog_shutdown_event.clear()
        self._watchdog_thread = threading.Thread(target=self._watchdog_loop, daemon=True)
        self._watchdog_thread.start()
        self.logger.info(f"Poller watchdog started (check interval: {self.watchdog_interval}s)")

    def _stop_watchdog(self, timeout: float = 5.0) -> None:
        """
        Stop the watchdog thread.

        Args:
            timeout: Maximum time to wait for thread to stop
        """
        if not self._watchdog_running:
            return

        self.logger.info("Stopping poller watchdog...")
        self._watchdog_running = False
        self._watchdog_shutdown_event.set()

        if self._watchdog_thread and self._watchdog_thread.is_alive():
            self._watchdog_thread.join(timeout=timeout)
            if self._watchdog_thread.is_alive():
                self.logger.warning("Watchdog thread did not stop within timeout")
            else:
                self.logger.info("Poller watchdog stopped")

    def _watchdog_loop(self) -> None:
        """
        Main watchdog loop that monitors poller health and restarts dead threads.

        Runs periodically based on watchdog_interval, checking each poller's
        thread status and restarting any that have died silently.
        """
        self.logger.info("Poller watchdog loop started")

        while self._watchdog_running:
            try:
                self._check_poller_health()

                # Wait for next check or shutdown signal
                if self._watchdog_shutdown_event.wait(timeout=self.watchdog_interval):
                    break

            except Exception as e:
                self.logger.error(f"Error in watchdog loop: {e}", exc_info=True)
                # Still wait before retrying
                if self._watchdog_shutdown_event.wait(timeout=self.watchdog_interval):
                    break

        self.logger.info("Poller watchdog loop stopped")

    def _check_poller_health(self) -> None:
        """
        Check health of all pollers and restart any dead ones.

        A poller is considered dead if:
        - It was started (is_running returns True or should be running)
        - But its thread is no longer alive (is_thread_alive returns False)
        """
        for name, poller in self.pollers.items():
            try:
                if not poller.is_healthy():
                    self.logger.warning(
                        f"Poller '{name}' thread died unexpectedly. "
                        f"is_running={poller.is_running()}, "
                        f"is_thread_alive={poller.is_thread_alive()}. "
                        f"Attempting restart..."
                    )
                    poller.restart()
                    self.logger.info(f"Poller '{name}' successfully restarted by watchdog")
            except Exception as e:
                self.logger.error(f"Failed to restart poller '{name}': {e}", exc_info=True)

    def get_status(self) -> Dict[str, Dict]:
        """
        Get status of all pollers including health information.

        Returns:
            Dictionary mapping poller names to their status
        """
        status = {
            '_watchdog': {
                'running': self._watchdog_running,
                'thread_alive': self._watchdog_thread is not None and self._watchdog_thread.is_alive(),
                'interval': self.watchdog_interval,
            },
            'pollers': {}
        }
        for name, poller in self.pollers.items():
            status['pollers'][name] = {
                'running': poller.is_running(),
                'thread_alive': poller.is_thread_alive(),
                'healthy': poller.is_healthy(),
                'state': poller.get_state(),
                'target_dir': str(poller.target_dir),
                'poll_interval': poller.poll_interval,
            }
        return status

    def get_poller(self, name: str) -> Optional['BasePoller']:
        """
        Get a specific poller by name.

        Args:
            name: Poller name

        Returns:
            Poller instance or None if not found
        """
        return self.pollers.get(name)

    def reload(self) -> None:
        """
        Reload poller configuration from config and restart pollers.

        Stops all running pollers (and watchdog), reloads config,
        and starts newly configured pollers (with watchdog).
        """
        self.logger.info("Reloading poller configuration...")

        # Stop all running pollers and watchdog
        self.stop_all()

        # Clear existing pollers
        self.pollers.clear()

        # Reload pollers from config
        self._load_pollers()

        # Start all newly configured pollers and watchdog
        self.start_all()

        self.logger.info(f"Poller reload complete: {len(self.pollers)} poller(s) loaded")

