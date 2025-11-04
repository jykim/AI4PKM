"""
Cron scheduler for orchestrator.

Handles time-based agent execution using cron expressions.
Re-implements cron logic within orchestrator folder.
"""
import logging
import threading
import time
from datetime import datetime
from queue import Queue
from typing import Optional
from croniter import croniter

from .models import TriggerEvent
from .agent_registry import AgentRegistry

logger = logging.getLogger(__name__)


class CronScheduler:
    """
    Manages cron-based scheduling for agents with cron expressions.
    
    Checks every minute if any agents should be triggered based on their cron expressions.
    Creates synthetic TriggerEvent objects and queues them for processing.
    """

    def __init__(self, agent_registry: AgentRegistry, event_queue: Queue):
        """
        Initialize cron scheduler.

        Args:
            agent_registry: AgentRegistry instance to get agents with cron expressions
            event_queue: Queue to put scheduled TriggerEvent objects
        """
        self.agent_registry = agent_registry
        self.event_queue = event_queue
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        """Start the cron scheduler thread."""
        if self._running:
            logger.warning("Cron scheduler already running")
            return

        self._running = True
        self._thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._thread.start()
        logger.info("Cron scheduler started")

    def stop(self):
        """Stop the cron scheduler thread."""
        if not self._running:
            return

        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        logger.info("Cron scheduler stopped")

    def _scheduler_loop(self):
        """
        Main scheduler loop that checks cron expressions every minute.
        """
        logger.info("Cron scheduler loop started")

        while self._running:
            try:
                self._check_and_trigger_jobs()
                # Sleep for 60 seconds (1 minute)
                time.sleep(60)
            except Exception as e:
                logger.error(f"Error in cron scheduler loop: {e}", exc_info=True)
                time.sleep(60)

        logger.info("Cron scheduler loop stopped")

    def _check_and_trigger_jobs(self):
        """
        Check if any agents with cron expressions should be triggered now.
        """
        now = datetime.now()

        # Get all agents with cron expressions
        agents_with_cron = [
            agent for agent in self.agent_registry.agents.values()
            if agent.cron is not None
        ]

        if not agents_with_cron:
            return

        for agent in agents_with_cron:
            print(agent.cron)
            try:
                # Check if this agent's cron expression should trigger now
                cron = croniter(agent.cron, now)
                prev_run = cron.get_prev(datetime)

                # If the previous run time is within the last minute, trigger the job
                time_diff = (now - prev_run).total_seconds()
                if 0 <= time_diff < 60:
                    logger.info(f"Triggering scheduled agent: {agent.abbreviation} ({agent.name})")
                    self._trigger_agent(agent)
            except Exception as e:
                logger.error(f"Error checking cron for agent {agent.abbreviation}: {e}")

    def _trigger_agent(self, agent):
        """
        Create a synthetic TriggerEvent for a scheduled agent and queue it.

        Args:
            agent: AgentDefinition with cron expression
        """
        # Create synthetic TriggerEvent for scheduled execution
        trigger_event = TriggerEvent(
            path="",  # No file path for scheduled events
            event_type="scheduled",
            is_directory=False,
            timestamp=datetime.now(),
            frontmatter={}
        )

        # Queue the event for processing
        self.event_queue.put(trigger_event)
        logger.debug(f"Queued scheduled event for agent: {agent.abbreviation}")

