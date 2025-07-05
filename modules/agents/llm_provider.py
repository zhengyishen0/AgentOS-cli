# llm_provider.py
from openai import AsyncOpenAI
from typing import List, Dict
import os

# Provider configurations
PROVIDERS = {
    "openai": {"base_url": None, "api_key_env": "OPENAI_API_KEY"},
    "anthropic": {"base_url": "https://api.anthropic.com/v1/", "api_key_env": "ANTHROPIC_API_KEY"},
    "gemini": {"base_url": "https://generativelanguage.googleapis.com/v1beta/", "api_key_env": "GEMINI_API_KEY"},
    "deepseek": {"base_url": "https://api.deepseek.com/v1", "api_key_env": "DEEPSEEK_API_KEY"},
    "ollama": {"base_url": "http://localhost:11434/v1", "api_key_env": None},
    "together": {"base_url": "https://api.together.xyz/v1", "api_key_env": "TOGETHER_API_KEY"},
    "groq": {"base_url": "https://api.groq.com/openai/v1", "api_key_env": "GROQ_API_KEY"},
    "perplexity": {"base_url": "https://api.perplexity.ai", "api_key_env": "PERPLEXITY_API_KEY"},
}

def _get_client(provider: str) -> AsyncOpenAI:
    """Get OpenAI client for the specified provider"""
    if provider not in PROVIDERS:
        raise ValueError(f"Unknown provider: {provider}")
    
    config = PROVIDERS[provider]
    
    return AsyncOpenAI(
        api_key=os.getenv(config["api_key_env"]) if config["api_key_env"] else None,
        base_url=config["base_url"]
    )

async def get_available_models(provider: str) -> List[str]:
    """Get available models for a provider
    
    Args:
        provider: The provider to use

    Returns:
        A list of available models
    """    
    client = _get_client(provider)
    models = await client.models.list()
    return [model.id for model in models.data]

async def complete(provider: str, model: str, messages: List[Dict], system: str = "", response_format: any = None, config: Dict = None) -> str:
    """Complete a chat request using the specified provider and model
    
    Args:
        provider: The provider to use
        model: The model to use
        messages: The messages to send to the model
        system: The system message to send to the model
        response_format: The output type to use for the response
        config: The configuration to use, including temperature, max_tokens, etc.

    Returns:
        The response from the model, including the content and usage
    """
    
    # Add system message if provided
    if system:
        messages = [{"role": "system", "content": system}] + messages
    
    # Get client and make the call
    client = _get_client(provider)
    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        response_format=response_format,
        **(config or {})
    )
    
    return {
        "content": response.choices[0].message.content,
        "usage": {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }
    }