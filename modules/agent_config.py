# agent_config.py
import yaml
import os
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def load_agent_config(name: str, config_dir: str = "configs/agents") -> Optional[Dict[str, str]]:
    """Load a single agent configuration by name
    
    Args:
        name: The name of the agent to load
        config_dir: Directory containing agent config files
        
    Returns:
        Agent config dict with keys: name, provider, model, system_prompt
        Returns None if agent not found
    """
    config_path = Path(config_dir) / f"{name}.yaml"
    
    if not config_path.exists():
        logger.warning(f"Agent config not found: {config_path}")
        return None
        
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            
        # Validate required fields
        required_fields = ['provider', 'model', 'system_prompt']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field '{field}' in agent config {name}")
        
        # Return only the essential fields
        return {
            'name': name,
            'provider': data['provider'],
            'model': data['model'],
            'system_prompt': data['system_prompt']
        }
        
    except Exception as e:
        logger.error(f"Failed to load agent config {name}: {e}")
        return None

def save_agent_config(name: str, provider: str, model: str, system_prompt: str, config_dir: str = "configs/agents") -> bool:
    """Save an agent configuration to a YAML file
    
    Args:
        name: The name of the agent
        provider: The LLM provider (e.g., 'openai', 'anthropic')
        model: The model name (e.g., 'gpt-4', 'claude-3')
        system_prompt: The system prompt for the agent
        config_dir: Directory to save the config file
        
    Returns:
        True if saved successfully, False otherwise
    """
    try:
        config_path = Path(config_dir)
        config_path.mkdir(parents=True, exist_ok=True)
        
        file_path = config_path / f"{name}.yaml"
        
        data = {
            'provider': provider,
            'model': model,
            'system_prompt': system_prompt
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, indent=2)
            
        logger.info(f"Saved agent config: {name}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to save agent config {name}: {e}")
        return False

def delete_agent_config(name: str, config_dir: str = "configs/agents") -> bool:
    """Delete an agent configuration file
    
    Args:
        name: The name of the agent to delete
        config_dir: Directory containing agent config files
        
    Returns:
        True if deleted successfully, False otherwise
    """
    try:
        config_path = Path(config_dir) / f"{name}.yaml"
        
        if not config_path.exists():
            logger.warning(f"Agent config not found: {config_path}")
            return False
            
        config_path.unlink()
        logger.info(f"Deleted agent config: {name}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to delete agent config {name}: {e}")
        return False

def list_agent_configs(config_dir: str = "configs/agents") -> List[str]:
    """List all available agent configuration names
    
    Args:
        config_dir: Directory containing agent config files
        
    Returns:
        List of agent names
    """
    try:
        config_path = Path(config_dir)
        
        if not config_path.exists():
            return []
            
        agent_names = []
        for yaml_file in config_path.glob("*.yaml"):
            agent_names.append(yaml_file.stem)
            
        return sorted(agent_names)
        
    except Exception as e:
        logger.error(f"Failed to list agent configs: {e}")
        return []

def update_agent_config(name: str, provider: str = None, model: str = None, system_prompt: str = None, config_dir: str = "configs/agents") -> bool:
    """Update an existing agent configuration
    
    Args:
        name: The name of the agent to update
        provider: New provider (optional)
        model: New model (optional)
        system_prompt: New system prompt (optional)
        config_dir: Directory containing agent config files
        
    Returns:
        True if updated successfully, False otherwise
    """
    try:
        # Load existing config
        existing_config = load_agent_config(name, config_dir)
        if not existing_config:
            logger.error(f"Agent config not found: {name}")
            return False
        
        # Update only provided fields
        if provider is not None:
            existing_config['provider'] = provider
        if model is not None:
            existing_config['model'] = model
        if system_prompt is not None:
            existing_config['system_prompt'] = system_prompt
        
        # Save updated config
        return save_agent_config(
            name=existing_config['name'],
            provider=existing_config['provider'],
            model=existing_config['model'],
            system_prompt=existing_config['system_prompt'],
            config_dir=config_dir
        )
        
    except Exception as e:
        logger.error(f"Failed to update agent config {name}: {e}")
        return False 