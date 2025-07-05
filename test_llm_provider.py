"""Test file for llm_provider.py"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from modules.agents.llm_provider import _get_client, get_available_models, complete, PROVIDERS


class TestLLMProvider:
    """Test suite for LLM provider functionality"""

    def test_get_client_valid_provider(self):
        """Test client creation for valid providers"""
        with patch('modules.agents.llm_provider.AsyncOpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client
            
            client = _get_client("openai")
            
            mock_openai.assert_called_once()
            assert client == mock_client

    def test_get_client_invalid_provider(self):
        """Test error handling for invalid provider"""
        with pytest.raises(ValueError, match="Unknown provider: invalid"):
            _get_client("invalid")

    def test_get_client_all_providers(self):
        """Test client creation for all configured providers"""
        with patch('modules.agents.llm_provider.AsyncOpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client
            
            for provider in PROVIDERS.keys():
                client = _get_client(provider)
                assert client == mock_client

    @pytest.mark.asyncio
    async def test_get_available_models_success(self):
        """Test successful model listing"""
        mock_models = MagicMock()
        mock_models.data = [
            MagicMock(id="model1"),
            MagicMock(id="model2"),
            MagicMock(id="model3")
        ]
        
        with patch('modules.agents.llm_provider._get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.models.list.return_value = mock_models
            mock_get_client.return_value = mock_client
            
            models = await get_available_models("openai")
            
            assert models == ["model1", "model2", "model3"]
            mock_client.models.list.assert_called_once()

    @pytest.mark.asyncio
    async def test_complete_basic(self):
        """Test basic completion functionality"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15
        
        with patch('modules.agents.llm_provider._get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_get_client.return_value = mock_client
            
            messages = [{"role": "user", "content": "Hello"}]
            result = await complete("openai", "gpt-4", messages)
            
            assert result["content"] == "Test response"
            assert result["usage"]["prompt_tokens"] == 10
            assert result["usage"]["completion_tokens"] == 5
            assert result["usage"]["total_tokens"] == 15

    @pytest.mark.asyncio
    async def test_complete_with_system_message(self):
        """Test completion with system message"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15
        
        with patch('modules.agents.llm_provider._get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_get_client.return_value = mock_client
            
            messages = [{"role": "user", "content": "Hello"}]
            system = "You are a helpful assistant"
            result = await complete("openai", "gpt-4", messages, system=system)
            
            # Check that system message was added
            call_args = mock_client.chat.completions.create.call_args
            called_messages = call_args[1]['messages']
            assert called_messages[0]["role"] == "system"
            assert called_messages[0]["content"] == system
            assert called_messages[1]["role"] == "user"

    @pytest.mark.asyncio
    async def test_complete_with_config(self):
        """Test completion with configuration parameters"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15
        
        with patch('modules.agents.llm_provider._get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_get_client.return_value = mock_client
            
            messages = [{"role": "user", "content": "Hello"}]
            config = {"temperature": 0.7, "max_tokens": 100}
            result = await complete("openai", "gpt-4", messages, config=config)
            
            # Check that config was passed
            call_args = mock_client.chat.completions.create.call_args
            assert call_args[1]['temperature'] == 0.7
            assert call_args[1]['max_tokens'] == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])