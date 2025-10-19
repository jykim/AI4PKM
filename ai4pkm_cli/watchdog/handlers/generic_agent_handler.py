"""Generic handler for agent folders that have AGENT.md or agent.py files."""

import os
import importlib.util
import yaml
from pathlib import Path
from datetime import datetime
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
    
    def _read_framework_prompts(self) -> str:
        """
        Read framework-level prompts from Agents/AGENT.md.
        
        Returns:
            Contents of framework AGENT.md or empty string if file doesn't exist
        """
        framework_agent_md = os.path.join(self.workspace_path, "Agents", "AGENT.md")
        if os.path.exists(framework_agent_md):
            try:
                with open(framework_agent_md, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                self.logger.error(f"Error reading framework AGENT.md from {framework_agent_md}: {e}")
                return ""
        return ""
    
    def _call_agent_py(self, file_path: str, request_data: dict) -> tuple[bool, any]:
        """
        Call agent.py if it exists.
        
        Args:
            file_path: Path to the file that triggered the event
            request_data: Parsed YAML content from the request file
            
        Returns:
            Tuple of (success: bool, response/error: any)
        """
        if not os.path.exists(self.agent_py_path):
            return False, "agent.py not found"
        
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
                    result = module.process(
                        request=request_data,
                        logger=self.logger,
                        workspace_path=self.workspace_path
                    )
                    return True, result
                else:
                    error_msg = f"agent.py in {self.agent_folder_path} does not have a 'process' function"
                    self.logger.warning(error_msg)
                    return False, error_msg
            return False, "Failed to load module"
            
        except Exception as e:
            error_msg = f"Error executing agent.py: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
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
    
    def _save_to_completed(self, request_data: dict, response_or_error: any, is_error: bool, original_filename: str):
        """
        Save request/response or request/error pair to Completed folder.
        
        Args:
            request_data: Original request data
            response_or_error: Response data or error message
            is_error: Whether this is an error or successful response
            original_filename: Original filename without timestamp
        """
        import os
        
        # Create completed folder
        completed_dir = os.path.join(self.full_agent_folder, 'Completed')
        os.makedirs(completed_dir, exist_ok=True)
        
        # Create result dictionary
        result = {
            'request': request_data,
            'timestamp': datetime.now().isoformat(),
        }
        
        if is_error:
            result['error'] = str(response_or_error)
        else:
            result['response'] = response_or_error
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = os.path.splitext(original_filename)[0]
        result_path = os.path.join(completed_dir, f"{timestamp}_{base_name}.yaml")
        
        # Custom representer for multiline strings
        def represent_str(dumper, data):
            if '\n' in data:
                return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
            return dumper.represent_scalar('tag:yaml.org,2002:str', data)
        
        # Custom representer for long strings without newlines
        def represent_long_str(dumper, data):
            if len(data) > 80 and '\n' not in data:
                return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='>')
            return represent_str(dumper, data)
        
        # Add custom representer for all strings
        yaml.add_representer(str, represent_str)
        
        with open(result_path, 'w', encoding='utf-8') as f:
            yaml.dump(result, f, default_flow_style=False, allow_unicode=True, sort_keys=False, width=1000)
        
        status = "error" if is_error else "completed"
        self.logger.info(f"📦 Saved {status} to: {result_path}")
    
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
        # Check if the trigger file still exists
        import os
        if not os.path.exists(file_path):
            self.logger.debug(f"[{self.agent_name}] File no longer exists: {file_path}")
            return
        
        # Ignore files already in InProgress or Completed folders
        if '/InProgress/' in file_path or '/Completed/' in file_path:
            self.logger.debug(f"[{self.agent_name}] Ignoring file in {file_path}")
            return
        
        self.logger.info(f"[{self.agent_name}] Processing {event_type} event for: {file_path}")
        
        original_filename = os.path.basename(file_path)
        in_progress_path = None
        
        try:
            # Step 1: Move to InProgress folder FIRST (atomic operation, prevents data loss)
            in_progress_path = self._move_to_folder(file_path, 'InProgress')
            
            # Step 2: Read and parse YAML content from InProgress
            request_data = {}
            try:
                with open(in_progress_path, 'r', encoding='utf-8') as f:
                    request_data = yaml.safe_load(f)
            except Exception as e:
                error_msg = f"Failed to parse YAML from {in_progress_path}: {e}"
                self.logger.error(error_msg)
                self._save_to_completed(request_data or {}, error_msg, True, original_filename)
                if os.path.exists(in_progress_path):
                    os.remove(in_progress_path)
                return
            
            # Step 3: Read prompts from AGENT.md
            prompts = self._read_agent_prompts()
            
            # Step 4: Process based on what's available
            response_or_error = None
            is_error = False
            
            # AGENT.md takes precedence - if it exists, use AI agent with prompts
            if prompts:
                response_or_error, is_error = self._execute_prompts(in_progress_path, prompts, request_data)
            # If no AGENT.md, try to call agent.py
            elif os.path.exists(self.agent_py_path):
                success, result = self._call_agent_py(in_progress_path, request_data)
                is_error = not success
                response_or_error = result
            else:
                # Neither found
                error_msg = f"Agent execution failed or no handler configured"
                self.logger.warning(f"[{self.agent_name}] {error_msg}")
                response_or_error = error_msg
                is_error = True
            
            # Step 5: Save to Completed with request/response or request/error
            self._save_to_completed(request_data, response_or_error, is_error, original_filename)
            
            # Step 6: Remove file from InProgress (now safely in Completed)
            if in_progress_path and os.path.exists(in_progress_path):
                os.remove(in_progress_path)
                
        except Exception as e:
            error_msg = f"Error processing file {file_path}: {e}"
            self.logger.error(f"[{self.agent_name}] {error_msg}")
            # Save error to Completed
            try:
                self._save_to_completed(request_data if 'request_data' in locals() else {}, error_msg, True, original_filename)
                # Clean up InProgress file
                if in_progress_path and os.path.exists(in_progress_path):
                    os.remove(in_progress_path)
            except Exception as cleanup_error:
                self.logger.error(f"Error during cleanup: {cleanup_error}")
    
    def _execute_prompts(self, file_path: str, prompts: str, request_data: dict) -> tuple[any, bool]:
        """
        Execute prompts using the AI agent with framework context.
        
        Args:
            file_path: Path to the file that triggered the event
            prompts: Contents of agent's AGENT.md
            request_data: Parsed YAML content from the request file
            
        Returns:
            Tuple of (response, is_error: bool)
        """
        try:
            import os
            
            # Format YAML content for prompt
            yaml_str = yaml.dump(request_data, default_flow_style=False, allow_unicode=True)
            
            # Read framework-level prompts
            framework_prompts = self._read_framework_prompts()
            
            # Create agent
            agent = AgentFactory.create_agent(self.logger, self.config)
            
            # Construct prompt with framework context and request data
            full_prompt = f"""
# Agent Framework Context

{framework_prompts}

---

# Agent-Specific Instructions

{prompts}

---

# Request

Request File: {os.path.basename(file_path)}

Request Data:
```yaml
{yaml_str}
```

Please process this request according to the instructions above and return your response.
"""
            
            self.logger.info(f"🤖 Executing {self.agent_name} agent with AI")
            self.logger.info(f"File: {os.path.basename(file_path)}")
            
            # Execute the agent using run_prompt
            result = agent.run_prompt(inline_prompt=full_prompt)
            
            if result:
                response_text, session_id = result
                self.logger.info(f"✅ {self.agent_name} AI execution completed successfully")
                if session_id:
                    self.logger.info(f"Session ID: {session_id}")
                return response_text, False  # Success
            else:
                error_msg = "AI execution completed with no response"
                self.logger.warning(f"⚠️ {self.agent_name} {error_msg}")
                return error_msg, True  # Error
                
        except Exception as e:
            error_msg = f"Error executing {self.agent_name} prompts: {str(e)}"
            self.logger.error(error_msg)
            return error_msg, True  # Error

