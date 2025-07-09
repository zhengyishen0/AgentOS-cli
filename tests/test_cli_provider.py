"""Tests for CLI Provider functionality."""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from modules.providers.cli_provider import CLIProvider
from modules import eventbus


class TestCLIProvider:
    """Test cases for CLIProvider class."""
    
    @pytest.fixture
    def cli_provider(self):
        """Create a CLI provider instance for testing."""
        return CLIProvider()
    
    @pytest.fixture
    def mock_event_bus(self):
        """Create a mock event bus for testing."""
        mock_bus = Mock()
        mock_bus.publish = AsyncMock()
        return mock_bus
    
    def test_cli_provider_initialization(self, cli_provider):
        """Test CLI provider initialization."""
        assert cli_provider.event_bus is not None
        assert cli_provider.session_id is None
        assert cli_provider._running is False
    
    def test_cli_provider(self, mock_event_bus):
        """Test cli_provider convenience function."""
        provider = CLIProvider(mock_event_bus)
        assert provider.event_bus == mock_event_bus
    
    @patch('builtins.input')
    def test_get_user_input(self, mock_input, cli_provider):
        """Test getting user input."""
        mock_input.return_value = "test input"
        
        async def test():
            result = await cli_provider.get_user_input()
            assert result == "test input"
        
        asyncio.run(test())
    
    @patch('builtins.print')
    def test_display_output(self, mock_print, cli_provider):
        """Test displaying output with different levels."""
        cli_provider.display_output("Test message", "info")
        mock_print.assert_called_with("ℹ️ Test message")
        
        cli_provider.display_output("Warning message", "warning")
        mock_print.assert_called_with("⚠️ Warning message")
        
        cli_provider.display_output("Error message", "error")
        mock_print.assert_called_with("❌ Error message")
        
        cli_provider.display_output("Success message", "success")
        mock_print.assert_called_with("✅ Success message")
    
    def test_parse_command(self, cli_provider):
        """Test command parsing."""
        # Test special commands
        assert cli_provider.parse_command("exit") == {"type": "exit"}
        assert cli_provider.parse_command("help") == {"type": "help"}
        assert cli_provider.parse_command("debug") == {"type": "debug"}
        assert cli_provider.parse_command("clear") == {"type": "clear"}
        
        # Test custom chain command
        chain_cmd = cli_provider.parse_command("chain test chain")
        assert chain_cmd == {"type": "custom_chain", "chain": "test chain"}
        
        # Test regular input
        assert cli_provider.parse_command("regular user input") is None
    
    @pytest.mark.asyncio
    async def test_publish_event(self, mock_event_bus):
        """Test publishing events."""
        cli_provider = CLIProvider(mock_event_bus)
        mock_event_bus.publish.return_value = {"success": True}
        
        result = await cli_provider.publish_event("test.event", {"data": "test"})
        
        mock_event_bus.publish.assert_called_once_with("test.event", {"data": "test"}, "cli")
        assert result == {"success": True}
    
    @pytest.mark.asyncio
    async def test_publish_event_error(self, mock_event_bus):
        """Test publishing events with error handling."""
        cli_provider = CLIProvider(mock_event_bus)
        mock_event_bus.publish.side_effect = Exception("Test error")
        
        result = await cli_provider.publish_event("test.event", {"data": "test"})
        
        assert "error" in result
        assert "Test error" in result["error"]
    
    @pytest.mark.asyncio
    async def test_process_user_input(self, mock_event_bus):
        """Test processing user input."""
        cli_provider = CLIProvider(mock_event_bus)
        
        # Mock successful user.input event
        mock_event_bus.publish.side_effect = [
            {"success": True},  # user.input result
            {"thread_id": "test_thread"},  # thread.match result
            {"message": "Agent response"}  # agent.think result
        ]
        
        result = await cli_provider.publish_user_input("Hello")
        
        # Verify events were published
        assert mock_event_bus.publish.call_count == 3
        mock_event_bus.publish.assert_any_call("user.input", {"text": "Hello"}, "cli")
        mock_event_bus.publish.assert_any_call("thread.match", {"input": "Hello"}, "cli")
        mock_event_bus.publish.assert_any_call("agent.think", {
            "thread_id": "test_thread",
            "prompt": "Hello"
        }, "cli")
        
        assert result["success"] is True
        assert result["thread_id"] == "test_thread"
    
    def test_show_help(self, cli_provider):
        """Test help display."""
        with patch('builtins.print') as mock_print:
            cli_provider.show_help()
            mock_print.assert_called()
            # Verify help text contains expected content
            call_args = [call[0][0] for call in mock_print.call_args_list]
            help_text = "".join(call_args)
            assert "AgentOS CLI" in help_text
            assert "Available commands" in help_text
            assert "exit" in help_text
            assert "help" in help_text


class TestCLIProviderIntegration:
    """Integration tests for CLI provider with event bus."""
    
    @pytest.mark.asyncio
    async def test_cli_provider_with_real_event_bus(self):
        """Test CLI provider integration with real event bus."""
        # Create a fresh event bus for testing
        from modules.eventbus.event_bus import ConcurrentEventBus
        test_event_bus = ConcurrentEventBus()
        
        cli_provider = CLIProvider(test_event_bus)
        
        # Test that we can create the provider without errors
        assert cli_provider.event_bus == test_event_bus
        
        # Test basic event publishing (should work even without handlers)
        result = await cli_provider.publish_event("test.event", {"data": "test"})
        assert result == {}  # No handlers registered, so empty result 