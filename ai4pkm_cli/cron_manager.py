"""Cron job management system."""

import json
import os
import time
from datetime import datetime
from croniter import croniter
from .config import Config
from .agent_factory import AgentFactory
from .commands.command_runner import CommandRunner


class CronManager:
    """Manages cron jobs defined in configuration file."""
    
    def __init__(self, logger, default_agent):
        """Initialize cron manager."""
        self.logger = logger
        self.default_agent = default_agent
        self.config = Config()
        self.jobs = []
        self.running = False
        self.thread = None
        self.agent_cache = {}  # Cache agents to avoid recreating them
        self._load_jobs()
        
    def _load_jobs(self):
        """Load cron jobs from configuration file."""
        try:
            self.jobs = self.config.get_cron_jobs()
            self.logger.info(f"Loaded {len(self.jobs)} cron jobs from config")
        except Exception as e:
            self.logger.error(f"Failed to load cron jobs from config: {e}")
            self.jobs = []
            
    def get_jobs(self):
        """Get list of loaded cron jobs."""
        return self.jobs
        
    def _get_agent_for_job(self, job):
        """Get the appropriate agent for a specific job."""
        job_agent_type = job.get('agent')
        
        # If no agent specified, use default
        if not job_agent_type:
            self.logger.debug(f"No agent specified for job '{job.get('inline_prompt', 'Unknown')}', using default agent: {self.default_agent.get_agent_name()}")
            return self.default_agent
            
        # Check cache first
        if job_agent_type in self.agent_cache:
            return self.agent_cache[job_agent_type]
            
        # Create new agent if not in cache
        try:
            # Create temporary config for this agent type  
            temp_config = Config()
            temp_config.config['default-agent'] = job_agent_type  # Modify in memory only
            
            agent = AgentFactory.create_agent(self.logger, temp_config)
            self.agent_cache[job_agent_type] = agent
            
            self.logger.debug(f"Created agent {job_agent_type} ({agent.get_agent_name()}) for job: {job.get('inline_prompt', 'Unknown')}")
            return agent
            
        except Exception as e:
            self.logger.warning(f"Failed to create agent {job_agent_type} for job '{job.get('inline_prompt', 'Unknown')}', using default: {e}")
            return self.default_agent
            
    def execute_job_by_id(self, job_id):
        """Execute a specific job by its index."""
        if 0 <= job_id < len(self.jobs):
            job = self.jobs[job_id]
            inline_prompt = job.get('inline_prompt')
            command = job.get('command')
            agent = self._get_agent_for_job(job)
            if inline_prompt:
                self.logger.info(f"Executing inline prompt job {job_id}: {inline_prompt} using {agent.get_agent_name()}")
                return self._run_job_with_agent(inline_prompt, agent)
            elif command:
                self.logger.info(f"Executing command job {job_id}: {command}")
                return self._run_job_with_command(command, agent)
        else:
            self.logger.error(f"Invalid job ID: {job_id}. Available jobs: 0-{len(self.jobs)-1}")
            return False
            
    def execute_jobs_batch(self, job_ids=None):
        """Execute multiple jobs in sequence or all jobs if job_ids is None."""
        if job_ids is None:
            job_ids = list(range(len(self.jobs)))
            
        results = []
        self.logger.info(f"Starting batch execution of {len(job_ids)} jobs")
        
        for job_id in job_ids:
            if 0 <= job_id < len(self.jobs):
                result = self.execute_job_by_id(job_id)
                results.append(result)
            else:
                self.logger.error(f"Skipping invalid job ID: {job_id}")
                results.append(False)
                
        successful = sum(1 for r in results if r)
        self.logger.info(f"Batch execution completed: {successful}/{len(job_ids)} jobs successful")
        return results
        
    def start(self):
        """Start the cron job scheduler."""
        if self.running:
            return
            
        self.running = True
        self.logger.info("Starting cron job scheduler")
        
        while self.running:
            try:
                self._check_and_run_jobs()
                time.sleep(60)  # Check every minute
            except Exception as e:
                self.logger.error(f"Error in cron scheduler: {e}")
                time.sleep(60)
                
    def stop(self):
        """Stop the cron job scheduler."""
        self.running = False
        self.logger.info("Stopping cron job scheduler")
        
    def _check_and_run_jobs(self):
        """Check if any jobs should run and execute them."""
        now = datetime.now()

        for job in self.jobs:
            try:
                inline_prompt = job.get('inline_prompt')
                command = job.get('command')
                cron_expr = job.get('cron')
                enabled = job.get('enabled', True)

                if (not inline_prompt and not command) or (not inline_prompt and not cron_expr):
                    self.logger.error(f"Invalid job configuration: {job}")
                    continue
                    
                # Check if job should run now 
                cron = croniter(cron_expr, now)
                prev_run = cron.get_prev(datetime)

                # If the previous run time is within the last minute, run the job
                time_diff = (now - prev_run).total_seconds()
                if 0 <= time_diff < 60:
                    if not enabled:
                        self.logger.info(f"Skipping disabled job: {job}")
                        continue

                    agent = self._get_agent_for_job(job)
                    if inline_prompt:
                        self._run_job_with_agent(inline_prompt, agent)
                    else:
                        self._run_job_with_command(command, agent)
                
            except Exception as e:
                self.logger.error(f"Error checking job {job}: {e}")

    def _run_job_with_agent(self, inline_prompt, agent):
        """Run a single inline prompt for a cron job with specified agent."""
        self.logger.info(f"Running cron job inline prompt: {inline_prompt} using {agent.get_agent_name()}")
        
        session_id = None
                   
        try:
            # Run the prompt using the specified agent
            result = agent.run_prompt(inline_prompt=inline_prompt, session_id=session_id)
            if result and result[0]:
                self.logger.info(f"Prompt completed successfully")
                return True
            else:
                self.logger.error(f"Prompt failed")
                return False
        except Exception as e:
            self.logger.error(f"Error running prompt: {e}")
            return False

    def _run_job_with_command(self, command, agent):
        """Run a single command for a cron job."""
        self.logger.info(f"Running cron job command: {command}")
        try:
            # Run the command
            result = CommandRunner(self.logger).run_command(command, agent)
            if result:
                self.logger.info(f"Command completed successfully")
                return True
            else:
                self.logger.error(f"Command failed")
                return False
        except Exception as e:
            self.logger.error(f"Error running command: {e}")
            return False
