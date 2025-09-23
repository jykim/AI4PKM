"""Abstract base class for AI agents."""

from abc import ABC, abstractmethod
from typing import Optional, Tuple, Dict, Any


class BaseAgent(ABC):
    """Abstract base class for AI agents."""
    
    def __init__(self, logger, config: Dict[str, Any]):
        """Initialize agent with logger and configuration."""
        self.logger = logger
        self.config = config
        
    @abstractmethod
    def run_prompt(self, inline_prompt: Optional[str] = None, prompt_name: Optional[str] = None, 
                   params: Optional[Dict[str, Any]] = None, context: Optional[str] = None, 
                   session_id: Optional[str] = None) -> Optional[Tuple[str, Optional[str]]]:
        """Run a prompt and return (result, session_id).
        
        Args:
            inline_prompt: Direct prompt text to execute
            prompt_name: Name of prompt file in _Settings_/Prompts/
            params: Template parameters for prompt substitution
            context: Additional context to append to prompt
            session_id: Session ID for continued conversations
            
        Returns:
            Tuple of (result_text, session_id) or None if failed
        """
        pass
        
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this agent is available and properly configured."""
        pass
        
    @abstractmethod
    def get_agent_name(self) -> str:
        """Get the display name of this agent."""
        pass
        
    def _load_prompt_content(self, prompt_name: str) -> Optional[str]:
        """Load prompt content from file."""
        import os
        
        prompt_file = f"_Settings_/Prompts/{prompt_name}.md"
        if not os.path.exists(prompt_file):
            self.logger.error(f"Prompt file not found: {prompt_file}")
            return None
            
        try:
            with open(prompt_file, 'r') as f:
                return f.read()
        except Exception as e:
            self.logger.error(f"Error reading prompt file {prompt_file}: {e}")
            return None
            
    def _replace_template_params(self, content: str, params: Dict[str, Any]) -> str:
        """Replace template parameters in content."""
        if not params:
            return content
            
        for key, value in params.items():
            placeholder = f"{{{key}}}"
            content = content.replace(placeholder, str(value))
            
        return content
        
    def _prepare_prompt_content(self, inline_prompt: Optional[str] = None, 
                               prompt_name: Optional[str] = None,
                               params: Optional[Dict[str, Any]] = None, 
                               context: Optional[str] = None) -> Optional[str]:
        """Prepare final prompt content with parameters and context."""
        if inline_prompt:
            prompt_content = inline_prompt
        elif prompt_name:
            prompt_content = self._load_prompt_content(prompt_name)
            if prompt_content is None:
                return None
        else:
            self.logger.error("Either inline_prompt or prompt_name must be provided")
            return None
            
        # Replace template parameters
        if params:
            prompt_content = self._replace_template_params(prompt_content, params)
        
        # Prepend global prompt if available
        global_prompt = self.config.get('global_prompt', '')
        if global_prompt.strip():
            prompt_content = f"{global_prompt.strip()}\n\n{prompt_content}"
            
        # Add context if provided
        if context:
            prompt_content = f"{prompt_content}\n\nContext:\n{context}"
            
        return prompt_content
