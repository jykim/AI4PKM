"""Generic handler for agent folders that have AGENT.md or agent.py files."""

import os
import importlib.util
from pathlib import Path
from ..file_watchdog import BaseFileHandler
from ...agent_factory import AgentFactory
from ...config import Config


class GenericAgentHandler(BaseFileHandler):
    """
    Generic handler for agent folders.
    
    When a file is created or modified in an agent's folder, this handler:
    1. If AGENT.md exists → executes prompts using the AI agent (takes precedence)
    2. Else if agent.py exists → calls the Python handle() function
    
    Priority: AGENT.md > agent.py
    """
    
    def __init__(self, agent_folder_path: str, logger=None, workspace_path=None):
        """
        Initialize the handler for a specific agent folder.
        
        Args:
            agent_folder_path: Path to the agent folder (e.g., "Agents/EmailSender")
            logger: Logger instance
            workspace_path: Path to the workspace root
        """
        super().__init__(logger, workspace_path)
        self.agent_folder_path = agent_folder_path
        self.agent_name = os.path.basename(agent_folder_path)
        self.config = Config()
        
        # Full paths
        self.full_agent_folder = os.path.join(workspace_path, agent_folder_path)
        self.agent_md_path = os.path.join(self.full_agent_folder, "AGENT.md")
        self.agent_py_path = os.path.join(self.full_agent_folder, "agent.py")
    
    def _read_agent_prompts(self) -> str:
        """
        Read prompts from AGENT.md if it exists.
        
        Returns:
            Contents of AGENT.md or empty string if file doesn't exist
        """
        if os.path.exists(self.agent_md_path):
            try:
                with open(self.agent_md_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                self.logger.error(f"Error reading AGENT.md from {self.agent_md_path}: {e}")
                return ""
        return ""
    
    def _call_agent_py(self, file_path: str, event_type: str, json_content: dict) -> bool:
        """
        Call agent.py if it exists.
        
        Args:
            file_path: Path to the file that triggered the event
            event_type: Type of event ('created' or 'modified')
            json_content: Parsed JSON content from the request file
            
        Returns:
            True if agent.py was called successfully, False otherwise
        """
        if not os.path.exists(self.agent_py_path):
            return False
        
        try:
            # Dynamically import agent.py
            spec = importlib.util.spec_from_file_location(
                f"{self.agent_name}_agent", 
                self.agent_py_path
            )
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Call process function if it exists
                if hasattr(module, 'process'):
                    module.process(
                        json_content=json_content,
                        file_path=file_path,
                        event_type=event_type,
                        logger=self.logger,
                        workspace_path=self.workspace_path
                    )
                    return True
                else:
                    self.logger.warning(f"agent.py in {self.agent_folder_path} does not have a 'process' function")
            return False
            
        except Exception as e:
            self.logger.error(f"Error executing agent.py from {self.agent_py_path}: {e}")
            return False
    
    def _move_to_folder(self, file_path: str, folder_name: str) -> str:
        """
        Move file to a specific folder within the agent directory.
        
        Args:
            file_path: Current file path
            folder_name: Target folder name (e.g., 'InProgress', 'Completed')
            
        Returns:
            New file path
        """
        import os
        import shutil
        from datetime import datetime
        
        # Create target folder
        target_dir = os.path.join(self.full_agent_folder, folder_name)
        os.makedirs(target_dir, exist_ok=True)
        
        # Generate new filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.basename(file_path)
        new_path = os.path.join(target_dir, f"{timestamp}_{filename}")
        
        # Move file
        shutil.move(file_path, new_path)
        self.logger.info(f"📦 Moved to {folder_name}: {new_path}")
        
        return new_path
    
    def process(self, file_path: str, event_type: str) -> None:
        """
        Process file events by executing prompts from AGENT.md or calling agent.py.
        
        Workflow:
        1. Move file to InProgress folder
        2. Process with AGENT.md (AI) or agent.py (Python)
        3. Move to Completed folder
        
        Priority:
        1. If AGENT.md exists → Execute prompts with AI agent (includes JSON content)
        2. Else if agent.py exists → Call Python function
        
        Args:
            file_path: Path to the file that triggered the event
            event_type: Type of event ('created' or 'modified')
        """
        self.logger.info(f"[{self.agent_name}] Processing {event_type} event for: {file_path}")
        
        # Check if the trigger file still exists
        import os
        if not os.path.exists(file_path):
            self.logger.debug(f"[{self.agent_name}] File no longer exists: {file_path}")
            return
        
        # Ignore files already in InProgress or Completed folders
        if '/InProgress/' in file_path or '/Completed/' in file_path:
            self.logger.debug(f"[{self.agent_name}] Ignoring file in {file_path}")
            return
        
        in_progress_path = None
        
        try:
            # Step 1: Move to InProgress
            in_progress_path = self._move_to_folder(file_path, 'InProgress')
            
            # Step 2: Read and parse JSON content
            json_content = {}
            try:
                with open(in_progress_path, 'r', encoding='utf-8') as f:
                    json_content = json.load(f)
            except Exception as e:
                self.logger.error(f"Failed to parse JSON from {in_progress_path}: {e}")
                return
            
            # Step 3: Read prompts from AGENT.md
            prompts = self._read_agent_prompts()
            
            # Step 4: Process based on what's available
            success = False
            
            # AGENT.md takes precedence - if it exists, use AI agent with prompts
            if prompts:
                success = self._execute_prompts(in_progress_path, event_type, prompts, json_content)
            # If no AGENT.md, try to call agent.py
            elif self._call_agent_py(in_progress_path, event_type, json_content):
                self.logger.info(f"[{self.agent_name}] Successfully executed agent.py")
                success = True
            else:
                # Neither found or both failed
                self.logger.warning(
                    f"[{self.agent_name}] Agent execution failed or no handler configured"
                )
            
            # Step 5: Move to Completed
            if in_progress_path and os.path.exists(in_progress_path):
                self._move_to_folder(in_progress_path, 'Completed')
                
        except Exception as e:
            self.logger.error(f"[{self.agent_name}] Error processing file {file_path}: {e}")
            # If there was an error, still try to move from InProgress to Completed
            if in_progress_path and os.path.exists(in_progress_path):
                try:
                    self._move_to_folder(in_progress_path, 'Completed')
                except:
                    pass
    
    def _execute_prompts(self, file_path: str, event_type: str, prompts: str, json_content: dict) -> bool:
        """
        Execute prompts directly using the AI agent.
        
        Args:
            file_path: Path to the file that triggered the event
            event_type: Type of event ('created' or 'modified')
            prompts: Contents of AGENT.md
            json_content: Parsed JSON content from the request file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            import os
            import json
            
            # Format JSON content for prompt
            json_str = json.dumps(json_content, indent=2)
            
            # Create agent
            agent = AgentFactory.create_agent(self.logger, self.config)
            
            # Construct prompt with JSON content
            full_prompt = f"""
{prompts}

---

Request File: {os.path.basename(file_path)}

JSON Content:
```json
{json_str}
```

Please process this request according to the instructions above.
"""
            
            self.logger.info(f"🤖 Executing {self.agent_name} agent with AI")
            self.logger.info(f"File: {os.path.basename(file_path)} ({event_type})")
            
            # Execute the agent using run_prompt
            result = agent.run_prompt(inline_prompt=full_prompt)
            
            if result:
                response_text, session_id = result
                self.logger.info(f"✅ {self.agent_name} AI execution completed successfully")
                if session_id:
                    self.logger.info(f"Session ID: {session_id}")
                return True
            else:
                self.logger.warning(f"⚠️ {self.agent_name} AI execution completed with no response")
                return False
                
        except Exception as e:
            self.logger.error(f"Error executing {self.agent_name} prompts: {e}")
            return False

