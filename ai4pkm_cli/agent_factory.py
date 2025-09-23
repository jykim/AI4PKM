"""Factory for creating AI agents based on configuration."""

from typing import Optional
from .config import Config
from .agents import BaseAgent, ClaudeAgent, GeminiAgent, CodexAgent


class AgentFactory:
    """Factory for creating AI agents."""
    
    AGENT_CLASSES = {
        'claude_code': ClaudeAgent,
        'gemini_cli': GeminiAgent,
        'codex_cli': CodexAgent
    }
    
    @classmethod
    def create_agent(cls, logger, config: Optional[Config] = None) -> BaseAgent:
        """Create an agent based on configuration.
        
        Args:
            logger: Logger instance
            config: Configuration instance (will create default if None)
            
        Returns:
            BaseAgent instance
            
        Raises:
            ValueError: If agent type is unknown or agent is not available
        """
        if config is None:
            config = Config()
            
        agent_type = config.get_agent()
        agent_config = config.get_agent_config(agent_type)
        
        # Add global prompt to agent config
        global_prompt = config.get_global_prompt(agent_type)
        if global_prompt:
            agent_config['global_prompt'] = global_prompt
        
        if agent_type not in cls.AGENT_CLASSES:
            raise ValueError(f"Unknown agent type: {agent_type}. Available: {list(cls.AGENT_CLASSES.keys())}")
            
        # Create the agent
        agent_class = cls.AGENT_CLASSES[agent_type]
        agent = agent_class(logger, agent_config)
        
        # Check if agent is available
        if not agent.is_available():
            logger.warning(f"Agent {agent.get_agent_name()} is not available")
            # Try to fallback to other available agents
            return cls._create_fallback_agent(logger, config, exclude=agent_type)
            
        logger.info(f"🤖 Using agent: {agent.get_agent_name()}")
        return agent
        
    @classmethod
    def _create_fallback_agent(cls, logger, config: Config, exclude: str) -> BaseAgent:
        """Create fallback agent if primary agent is not available."""
        fallback_order = ['claude_code', 'gemini_cli', 'codex_cli']
        
        for agent_type in fallback_order:
            if agent_type == exclude:
                continue
                
            try:
                agent_config = config.get_agent_config(agent_type)
                
                # Add global prompt to agent config
                global_prompt = config.get_global_prompt(agent_type)
                if global_prompt:
                    agent_config['global_prompt'] = global_prompt
                
                agent_class = cls.AGENT_CLASSES[agent_type]
                agent = agent_class(logger, agent_config)
                
                if agent.is_available():
                    logger.info(f"🔄 Falling back to agent: {agent.get_agent_name()}")
                    return agent
                    
            except Exception as e:
                logger.debug(f"Failed to create fallback agent {agent_type}: {e}")
                continue
                
        # If no fallback is available, return the original agent anyway
        # (it may have a fallback mode)
        logger.warning("No available agents found, using original agent with potential fallback mode")
        agent_config = config.get_agent_config(exclude)
        
        # Add global prompt to agent config
        global_prompt = config.get_global_prompt(exclude)
        if global_prompt:
            agent_config['global_prompt'] = global_prompt
        
        agent_class = cls.AGENT_CLASSES[exclude]
        return agent_class(logger, agent_config)
        
    @classmethod
    def list_available_agents(cls, logger) -> list:
        """List all available agents with their status."""
        available_agents = []
        
        for agent_type, agent_class in cls.AGENT_CLASSES.items():
            try:
                # Create temporary config for testing
                temp_config = {}
                agent = agent_class(logger, temp_config)
                status = "✅ Available" if agent.is_available() else "❌ Not Available"
                available_agents.append({
                    'type': agent_type,
                    'name': agent.get_agent_name(),
                    'status': status,
                    'available': agent.is_available()
                })
            except Exception as e:
                available_agents.append({
                    'type': agent_type,
                    'name': f"Error: {e}",
                    'status': "❌ Error",
                    'available': False
                })
                
        return available_agents
