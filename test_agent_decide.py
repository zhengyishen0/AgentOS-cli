"""Test file for agent_decide function in agent_handlers.py"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from modules.eventbus.event_bus import Event
from modules.eventbus.event_handlers.agent_handlers import agent_decide


class TestAgentDecide:
    """Test suite for agent_decide function"""

    @pytest.mark.asyncio
    async def test_agent_decide_continue_action(self):
        """Test agent_decide returning continue action"""
        # Mock the complete function response
        mock_response = {
            "content": '{"action": "continue", "params": {"completed_param": "value"}}',
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
        }
        
        # Create test event
        event_data = {
            "schema": {"required": ["param1"], "properties": {"param1": {"type": "string"}}},
            "prompt": "Complete missing parameters",
            "params": {"param1": "existing_value"}
        }
        event = Event(type="agent.decide", data=event_data)
        
        with patch('modules.eventbus.event_handlers.agent_handlers.complete', return_value=mock_response):
            result = await agent_decide(event)
            
            assert result == mock_response

    @pytest.mark.asyncio
    async def test_agent_decide_skip_action(self):
        """Test agent_decide returning skip action"""
        # Mock the complete function response
        mock_response = {
            "content": '{"action": "skip", "params": {"param1": "value"}, "reason": "Condition not met"}',
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
        }
        
        # Create test event
        event_data = {
            "schema": {"required": ["param1"], "properties": {"param1": {"type": "string"}}},
            "prompt": "Evaluate condition: user_active == true",
            "params": {"param1": "value", "user_active": False}
        }
        event = Event(type="agent.decide", data=event_data)
        
        with patch('modules.eventbus.event_handlers.agent_handlers.complete', return_value=mock_response):
            result = await agent_decide(event)
            
            assert result == mock_response

    @pytest.mark.asyncio
    async def test_agent_decide_parameter_completion(self):
        """Test agent_decide completing missing parameters"""
        # Mock the complete function response
        mock_response = {
            "content": '{"action": "continue", "params": {"missing_param": "inferred_value", "existing_param": "value"}}',
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
        }
        
        # Create test event with missing parameters
        event_data = {
            "schema": {
                "required": ["missing_param", "existing_param"],
                "properties": {
                    "missing_param": {"type": "string"},
                    "existing_param": {"type": "string"}
                }
            },
            "prompt": "Complete missing parameters based on context",
            "params": {"existing_param": "value"}
        }
        event = Event(type="agent.decide", data=event_data)
        
        with patch('modules.eventbus.event_handlers.agent_handlers.complete', return_value=mock_response):
            result = await agent_decide(event)
            
            assert result == mock_response

    @pytest.mark.asyncio
    async def test_agent_decide_empty_params(self):
        """Test agent_decide with empty parameters"""
        # Mock the complete function response
        mock_response = {
            "content": '{"action": "continue", "params": {}}',
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
        }
        
        # Create test event with empty parameters
        event_data = {
            "schema": {},
            "prompt": "No parameters needed",
            "params": {}
        }
        event = Event(type="agent.decide", data=event_data)
        
        with patch('modules.eventbus.event_handlers.agent_handlers.complete', return_value=mock_response):
            result = await agent_decide(event)
            
            assert result == mock_response

    @pytest.mark.asyncio
    async def test_agent_decide_with_complex_schema(self):
        """Test agent_decide with complex schema requirements"""
        # Mock the complete function response
        mock_response = {
            "content": '{"action": "continue", "params": {"user_id": 123, "preferences": {"theme": "dark", "notifications": true}}}',
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
        }
        
        # Create test event with complex schema
        event_data = {
            "schema": {
                "required": ["user_id", "preferences"],
                "properties": {
                    "user_id": {"type": "integer"},
                    "preferences": {
                        "type": "object",
                        "properties": {
                            "theme": {"type": "string"},
                            "notifications": {"type": "boolean"}
                        }
                    }
                }
            },
            "prompt": "Complete user preferences",
            "params": {"user_id": 123}
        }
        event = Event(type="agent.decide", data=event_data)
        
        with patch('modules.eventbus.event_handlers.agent_handlers.complete', return_value=mock_response):
            result = await agent_decide(event)
            
            assert result == mock_response

    @pytest.mark.asyncio
    async def test_agent_decide_message_construction(self):
        """Test that agent_decide constructs the correct message for the LLM"""
        # Mock the complete function to capture the call
        mock_complete = AsyncMock()
        mock_complete.return_value = {
            "content": '{"action": "continue", "params": {}}',
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
        }
        
        # Create test event
        event_data = {
            "schema": {"required": ["param1"]},
            "prompt": "Test prompt",
            "params": {"param1": "value"}
        }
        event = Event(type="agent.decide", data=event_data)
        
        with patch('modules.eventbus.event_handlers.agent_handlers.complete', mock_complete):
            result = await agent_decide(event)
            
            # Verify the complete function was called with correct parameters
            mock_complete.assert_called_once()
            call_args = mock_complete.call_args
            
            # Check provider and model
            assert call_args[1]['provider'] == "openai"
            assert call_args[1]['model'] == "gpt-4.1-nano"
            
            # Check message content includes all required parts
            message_content = call_args[1]['messages'][0]['content']
            assert "Test prompt" in message_content
            assert "param1" in message_content
            assert "value" in message_content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])