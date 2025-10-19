"""
Scheduler Agent

Schedules one-time request file creation for other agents at specified times.
"""

import os
import yaml
import threading
from datetime import datetime
from pathlib import Path


def process(request, logger, workspace_path):
    """
    Schedule a one-time request file creation for another agent.
    
    Args:
        request: Parsed YAML with scheduling details
        logger: Logger instance
        workspace_path: Workspace root path
        
    Returns:
        Response dict with schedule confirmation
        
    Request format:
        target_agent: EmailSender  # Agent to send request to
        scheduled_time: "2025-10-18 20:00:00"  # When to create the request
        request_data:  # Data to send to target agent
          to: user@example.com
          subject: Scheduled Email
          body: This was scheduled!
    """
    logger.info("Scheduler: Processing schedule request")
    
    try:
        # Extract scheduling details
        target_agent = request.get('target_agent', '')
        scheduled_time_str = request.get('scheduled_time', '')
        request_data = request.get('request_data', {})
        
        # Validate required fields
        if not target_agent:
            raise ValueError("Missing 'target_agent' field")
        if not scheduled_time_str:
            raise ValueError("Missing 'scheduled_time' field")
        if not request_data:
            raise ValueError("Missing 'request_data' field")
        
        # Prevent scheduling to Scheduler itself (infinite loop)
        if target_agent.lower() == 'scheduler':
            raise ValueError("Cannot schedule requests to Scheduler agent (would cause infinite loop)")
        
        # Validate target agent exists
        target_agent_path = os.path.join(workspace_path, 'Agents', target_agent)
        if not os.path.exists(target_agent_path):
            raise ValueError(f"Target agent '{target_agent}' does not exist at {target_agent_path}")
        
        # Parse scheduled time
        try:
            scheduled_time = datetime.strptime(scheduled_time_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            try:
                # Try ISO format as well
                scheduled_time = datetime.fromisoformat(scheduled_time_str)
            except ValueError:
                raise ValueError(f"Invalid time format: {scheduled_time_str}. Use 'YYYY-MM-DD HH:MM:SS' or ISO format")
        
        # Check if time is in the future
        now = datetime.now()
        if scheduled_time <= now:
            raise ValueError(f"Scheduled time must be in the future. Given: {scheduled_time}, Now: {now}")
        
        # Calculate delay in seconds
        delay = (scheduled_time - now).total_seconds()
        
        logger.info(f"📅 Scheduling details:")
        logger.info(f"  - Target agent: {target_agent}")
        logger.info(f"  - Scheduled time: {scheduled_time}")
        logger.info(f"  - Delay: {delay:.1f} seconds ({delay/60:.1f} minutes)")
        
        # Create the scheduled task
        def create_request_file():
            """Create the request file at the scheduled time."""
            try:
                # Create target agent's Requests folder
                requests_dir = os.path.join(workspace_path, 'Agents', target_agent, 'Requests')
                os.makedirs(requests_dir, exist_ok=True)
                
                # Generate filename with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{timestamp}_scheduled.yaml"
                file_path = os.path.join(requests_dir, filename)
                
                # Write request data to YAML file
                with open(file_path, 'w', encoding='utf-8') as f:
                    yaml.dump(request_data, f, default_flow_style=False, allow_unicode=True)
                
                logger.info(f"✅ Scheduled request created: {file_path}")
                logger.info(f"   Agent '{target_agent}' will now process this request")
                
            except Exception as e:
                logger.error(f"❌ Error creating scheduled request: {e}")
        
        # Schedule the task using threading.Timer
        timer = threading.Timer(delay, create_request_file)
        timer.daemon = True  # Allow program to exit even if timer is pending
        timer.start()
        
        logger.info(f"✅ Schedule created successfully")
        logger.info(f"   Request will be created at {scheduled_time}")
        
        # Return confirmation
        return {
            "status": "scheduled",
            "target_agent": target_agent,
            "scheduled_time": scheduled_time.isoformat(),
            "delay_seconds": delay,
            "message": f"Request will be sent to {target_agent} at {scheduled_time}"
        }
        
    except Exception as e:
        logger.error(f"❌ Error scheduling request: {e}")
        raise

