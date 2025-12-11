"""Poller manager for orchestrator - manages enabled pollers."""

from pathlib import Path
from typing import Any, Dict, Optional
from ..logger import Logger

logger = Logger()


class PollerManager:
    """Manages poller instances based on orchestrator.yaml configuration."""

    def __init__(self, vault_path: Path, config: 'Config'):
        """
        Initialize poller manager.

        Args:
            vault_path: Path to vault root
            config: Config instance
            logger_instance: Logger instance (optional, uses module logger if None)
        """
        self.vault_path = Path(vault_path)
        self.config = config
        
        # Map of poller name -> poller instance
        self.pollers: Dict[str, 'BasePoller'] = {}
        
        # Load and initialize enabled pollers
        self._load_pollers()

    def _load_pollers(self) -> None:
        """Load and initialize enabled pollers from config."""
        pollers_config = self.config.get_pollers_config()

        if not pollers_config:
            logger.debug("No pollers configuration found")
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
                logger.debug(f"Poller '{poller_name}' is disabled, skipping")
                continue
            
            if poller_name not in poller_classes:
                logger.warning(f"Unknown poller name: {poller_name}")
                continue
            
            try:
                target_dir = poller_config.get('target_dir')
                if not target_dir:
                    logger.error(f"Poller '{poller_name}' missing required 'target_dir'")
                    continue
                
                poll_interval = poller_config.get('poll_interval', 3600)
                
                # Instantiate poller (each poller uses its own module-level logger)
                poller_class = poller_classes[poller_name]
                poller = poller_class(
                    poller_config=poller_config,
                    vault_path=self.vault_path
                )
                
                self.pollers[poller_name] = poller
                logger.info(f"Loaded poller: {poller_name} (target: {target_dir}, interval: {poll_interval}s)", console=True)
                
            except Exception as e:
                logger.error(f"Failed to load poller '{poller_name}': {e}", exc_info=True)

    def start_all(self) -> None:
        """Start all enabled pollers."""
        if not self.pollers:
            logger.info("No pollers to start")
            return
        
        logger.info(f"Starting {len(self.pollers)} poller(s)...")
        for name, poller in self.pollers.items():
            try:
                poller.start()
            except Exception as e:
                logger.error(f"Failed to start poller '{name}': {e}", exc_info=True)

    def stop_all(self) -> None:
        """Stop all running pollers."""
        if not self.pollers:
            return
        
        logger.info(f"Stopping {len(self.pollers)} poller(s)...")
        for name, poller in self.pollers.items():
            try:
                poller.stop()
            except Exception as e:
                logger.error(f"Failed to stop poller '{name}': {e}", exc_info=True)

    def get_status(self) -> Dict[str, Dict]:
        """
        Get status of all pollers.

        Returns:
            Dictionary mapping poller names to their status
        """
        status = {}
        for name, poller in self.pollers.items():
            status[name] = {
                'running': poller.is_running(),
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
        
        Stops all running pollers, reloads config, and starts newly configured pollers.
        """
        logger.info("Reloading poller configuration...")
        
        # Stop all running pollers
        self.stop_all()
        
        # Clear existing pollers
        self.pollers.clear()
        
        # Reload pollers from config
        self._load_pollers()
        
        # Start all newly configured pollers
        self.start_all()
        
        logger.info(f"Poller reload complete: {len(self.pollers)} poller(s) loaded")

