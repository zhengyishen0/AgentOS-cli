"""Test file for llm_provider.py using real API calls"""

import pytest
import os
from modules.agents.llm_provider import _get_client, get_available_models, complete, PROVIDERS


class TestLLMProvider:
    """Test suite for LLM provider functionality with real API calls"""

    def test_get_client_valid_provider(self):
        """Test client creation for valid providers"""
        client = _get_client("openai")
        assert client is not None
        assert hasattr(client, 'chat')
        assert hasattr(client, 'models')

    def test_get_client_invalid_provider(self):
        """Test error handling for invalid provider"""
        with pytest.raises(ValueError, match="Unknown provider: invalid"):
            _get_client("invalid")

    def test_get_client_all_providers(self):
        """Test client creation for all configured providers"""
        for provider in PROVIDERS.keys():
            client = _get_client(provider)
            assert client is not None
            assert hasattr(client, 'chat')
            assert hasattr(client, 'models')


    @pytest.mark.asyncio
    async def test_get_available_models_openai(self):
        """Test successful model listing with OpenAI"""
        if not os.getenv("OPENAI_API_KEY"):
            pytest.skip("OPENAI_API_KEY not set")
        
        models = await get_available_models("openai")
        print(models)
        assert isinstance(models, list)
        assert len(models) > 0
        # Check for common OpenAI models
        model_names = [model.lower() for model in models]
        assert any("gpt" in model for model in model_names)

    @pytest.mark.asyncio
    async def test_complete_basic_openai(self):
        """Test basic completion functionality with OpenAI"""
        if not os.getenv("OPENAI_API_KEY"):
            pytest.skip("OPENAI_API_KEY not set")
        
        messages = [{"role": "user", "content": "Say 'Hello World' and nothing else"}]
        result = await complete("openai", "gpt-3.5-turbo", messages)
        
        assert "content" in result
        assert "usage" in result
        assert isinstance(result["content"], str)
        assert len(result["content"]) > 0
        assert result["usage"]["prompt_tokens"] > 0
        assert result["usage"]["completion_tokens"] > 0
        assert result["usage"]["total_tokens"] > 0

    @pytest.mark.asyncio
    async def test_complete_with_system_message_openai(self):
        """Test completion with system message using OpenAI"""
        if not os.getenv("OPENAI_API_KEY"):
            pytest.skip("OPENAI_API_KEY not set")
        
        messages = [{"role": "user", "content": "What is 2+2?"}]
        system = "You are a math tutor. Always show your work."
        result = await complete("openai", "gpt-3.5-turbo", messages, system=system)
        
        assert "content" in result
        assert "usage" in result
        assert isinstance(result["content"], str)
        assert len(result["content"]) > 0
        # The response should contain the answer 4
        assert "4" in result["content"]

    @pytest.mark.asyncio
    async def test_complete_with_config_openai(self):
        """Test completion with configuration parameters using OpenAI"""
        if not os.getenv("OPENAI_API_KEY"):
            pytest.skip("OPENAI_API_KEY not set")
        
        messages = [{"role": "user", "content": "Write a very short poem"}]
        config = {"temperature": 0.1, "max_tokens": 50}
        result = await complete("openai", "gpt-3.5-turbo", messages, config=config)
        
        assert "content" in result
        assert "usage" in result
        assert isinstance(result["content"], str)
        assert len(result["content"]) > 0
        # With max_tokens=50, completion_tokens should be <= 50
        assert result["usage"]["completion_tokens"] <= 50

    @pytest.mark.asyncio
    async def test_complete_ollama_if_available(self):
        """Test completion with Ollama if available"""
        try:
            # Try to get models to see if Ollama is running
            models = await get_available_models("ollama")
            if not models:
                pytest.skip("Ollama not available or no models installed")
            
            # Use a common model that might be available
            test_model = models[0]  # Use first available model
            messages = [{"role": "user", "content": "Say 'test' and nothing else"}]
            result = await complete("ollama", test_model, messages)
            
            assert "content" in result
            assert "usage" in result
            assert isinstance(result["content"], str)
            assert len(result["content"]) > 0
            
        except Exception as e:
            pytest.skip(f"Ollama not available: {e}")

    @pytest.mark.asyncio
    async def test_complete_deepseek_if_available(self):
        """Test completion with DeepSeek if API key is available"""
        if not os.getenv("DEEPSEEK_API_KEY"):
            pytest.skip("DEEPSEEK_API_KEY not set")
        
        messages = [{"role": "user", "content": "What is 1+1?"}]
        result = await complete("deepseek", "deepseek-chat", messages)
        
        assert "content" in result
        assert "usage" in result
        assert isinstance(result["content"], str)
        assert len(result["content"]) > 0
        assert "2" in result["content"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])