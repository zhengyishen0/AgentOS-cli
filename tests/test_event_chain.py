"""Test file for event_chain.py"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from modules.eventbus.event_chain import EventChainExecutor, EventChainBuilder, ChainEventSpec
from modules.eventbus.event_bus import InMemoryEventBus, Event


class TestEventChainExecutor:
    """Test suite for EventChainExecutor"""

    @pytest.fixture
    def mock_event_bus(self):
        """Create a mock event bus for testing"""
        mock_bus = AsyncMock(spec=InMemoryEventBus)
        
        # Default mock responses
        async def mock_publish(event_type, data, source=None):
            if event_type == 'tools.now':
                return {'timestamp': '2025-01-15T10:30:00Z'}
            elif event_type == 'user.create':
                return {'user_id': 'user_123', 'status': 'created'}
            elif event_type == 'agent.decide':
                if 'Correct the following parameters' in data.get('prompt', ''):
                    return {'params': {**data['params'], 'fixed': True}}
                else:
                    return {'action': 'continue', 'params': data['params']}
            else:
                return {'status': 'completed'}
        
        mock_bus.publish = mock_publish
        return mock_bus

    @pytest.fixture
    def executor(self, mock_event_bus):
        """Create executor with mock event bus"""
        return EventChainExecutor(mock_event_bus)

    @pytest.mark.asyncio
    async def test_execute_single_event(self, executor):
        """Test executing a single event"""
        chain = [{'event': 'tools.now'}]
        result = await executor.execute_chain(chain, 'test_thread')
        
        assert result.success is True
        assert len(result.events) == 1
        assert result.events[0].event == 'tools.now'
        assert result.events[0].result == {'timestamp': '2025-01-15T10:30:00Z'}

    @pytest.mark.asyncio
    async def test_execute_sequential_chain(self, executor):
        """Test executing sequential events"""
        chain = [
            {'event': 'tools.now'},
            {'event': 'user.create', 'params': {'name': 'John'}}
        ]
        result = await executor.execute_chain(chain, 'test_thread')
        
        assert result.success is True
        assert len(result.events) == 2
        assert result.events[0].event == 'tools.now'
        assert result.events[1].event == 'user.create'
        assert result.events[1].result == {'user_id': 'user_123', 'status': 'created'}

    @pytest.mark.asyncio
    async def test_execute_parallel_events(self, executor):
        """Test executing parallel events"""
        chain = [
            {'event': 'tools.now'},
            [
                {'event': 'user.create', 'params': {'name': 'Alice'}},
                {'event': 'user.create', 'params': {'name': 'Bob'}}
            ]
        ]
        result = await executor.execute_chain(chain, 'test_thread')
        
        assert result.success is True
        assert len(result.events) == 3  # 1 sequential + 2 parallel
        assert result.events[0].event == 'tools.now'
        assert result.events[1].event == 'user.create'
        assert result.events[2].event == 'user.create'

    @pytest.mark.asyncio
    async def test_conditional_event_continue(self, executor):
        """Test conditional event that continues"""
        chain = [
            {'event': 'user.create', 'params': {'name': 'Test'}, 'decide': 'Should we create user?'}
        ]
        result = await executor.execute_chain(chain, 'test_thread')
        
        assert result.success is True
        assert len(result.events) == 1
        assert result.events[0].event == 'user.create'
        # Should have executed normally since mock returns 'continue'

    @pytest.mark.asyncio
    async def test_conditional_event_skip(self, executor, mock_event_bus):
        """Test conditional event that skips"""
        # Mock decide to return skip
        async def mock_decide(event_type, data, source=None):
            if event_type == 'agent.decide':
                return {'action': 'skip', 'reason': 'User not needed'}
            return {'status': 'completed'}
        
        mock_event_bus.publish = mock_decide
        
        chain = [
            {'event': 'user.create', 'params': {'name': 'Test'}, 'decide': 'Should we create user?'}
        ]
        result = await executor.execute_chain(chain, 'test_thread')
        
        assert result.success is True
        assert len(result.events) == 1
        assert result.events[0].result == {'skipped': True, 'reason': 'User not needed'}

    @pytest.mark.asyncio
    async def test_parameter_completion_on_validation_error(self, executor):
        """Test parameter completion when validation fails"""
        # Mock the event registry to raise validation error
        from modules.eventbus import event_registry
        original_validate = event_registry.validate_event_data
        
        def mock_validate(event_type, data):
            if event_type == 'user.create' and 'email' not in data:
                raise ValueError("Missing required field: email")
        
        event_registry.validate_event_data = mock_validate
        
        try:
            chain = [
                {'event': 'user.create', 'params': {'name': 'John'}}
            ]
            result = await executor.execute_chain(chain, 'test_thread')
            
            assert result.success is True
            assert len(result.events) == 1
            # Should have been fixed by agent.decide
            
        finally:
            event_registry.validate_event_data = original_validate

    @pytest.mark.asyncio
    async def test_chain_with_error(self, executor, mock_event_bus):
        """Test chain execution with error"""
        # Mock to raise error
        async def mock_error(event_type, data, source=None):
            if event_type == 'user.create':
                raise ValueError("User creation failed")
            return {'status': 'completed'}
        
        mock_event_bus.publish = mock_error
        
        chain = [
            {'event': 'tools.now'},
            {'event': 'user.create', 'params': {'name': 'Test'}}
        ]
        result = await executor.execute_chain(chain, 'test_thread')
        
        assert result.success is False
        assert len(result.events) == 2
        assert result.events[1].error is not None
        assert "User creation failed" in result.error

    @pytest.mark.asyncio
    async def test_context_interpolation(self, executor):
        """Test parameter interpolation between events"""
        # This test would require implementing parameter interpolation
        # For now, just test that the interpolator is created
        chain = [{'event': 'tools.now'}]
        result = await executor.execute_chain(chain, 'test_thread')
        
        assert executor._interpolator is not None
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execution_time_tracking(self, executor):
        """Test that execution times are tracked"""
        chain = [{'event': 'tools.now'}]
        result = await executor.execute_chain(chain, 'test_thread')
        
        assert result.total_execution_time_ms > 0
        assert result.events[0].execution_time_ms > 0

    @pytest.mark.asyncio
    async def test_thread_context_usage(self, executor):
        """Test that thread context is properly used"""
        initial_context = {'user_id': 'user_123'}
        chain = [{'event': 'tools.now'}]
        result = await executor.execute_chain(chain, 'test_thread', initial_context)
        
        assert result.success is True
        assert 'user_id' in executor._execution_context
        assert executor._execution_context['user_id'] == 'user_123'


class TestEventChainBuilder:
    """Test suite for EventChainBuilder"""

    def test_build_single_event(self):
        """Test building a single event chain"""
        builder = EventChainBuilder()
        chain = builder.add_event('tools.now').build()
        
        assert len(chain) == 1
        assert chain[0]['event'] == 'tools.now'

    def test_build_event_with_params(self):
        """Test building event with parameters"""
        builder = EventChainBuilder()
        chain = builder.add_event('user.create', {'name': 'John'}).build()
        
        assert len(chain) == 1
        assert chain[0]['event'] == 'user.create'
        assert chain[0]['params'] == {'name': 'John'}

    def test_build_event_with_decide(self):
        """Test building event with conditional logic"""
        builder = EventChainBuilder()
        chain = builder.add_event('user.create', {'name': 'John'}, 'Should create?').build()
        
        assert len(chain) == 1
        assert chain[0]['event'] == 'user.create'
        assert chain[0]['decide'] == 'Should create?'

    def test_build_sequential_events(self):
        """Test building sequential events"""
        builder = EventChainBuilder()
        chain = (builder
                .add_event('tools.now')
                .add_event('user.create', {'name': 'John'})
                .build())
        
        assert len(chain) == 2
        assert chain[0]['event'] == 'tools.now'
        assert chain[1]['event'] == 'user.create'

    def test_build_parallel_events(self):
        """Test building parallel events"""
        builder = EventChainBuilder()
        chain = (builder
                .add_event('tools.now')
                .add_parallel(
                    {'event': 'user.create', 'params': {'name': 'Alice'}},
                    {'event': 'user.create', 'params': {'name': 'Bob'}}
                )
                .build())
        
        assert len(chain) == 2
        assert chain[0]['event'] == 'tools.now'
        assert isinstance(chain[1], list)
        assert len(chain[1]) == 2
        assert chain[1][0]['event'] == 'user.create'
        assert chain[1][1]['event'] == 'user.create'

    def test_build_complex_chain(self):
        """Test building complex chain with mixed sequential and parallel"""
        builder = EventChainBuilder()
        chain = (builder
                .add_event('tools.now')
                .add_parallel(
                    {'event': 'user.create', 'params': {'name': 'Alice'}},
                    {'event': 'user.create', 'params': {'name': 'Bob'}}
                )
                .add_event('email.send', {'subject': 'Welcome'})
                .build())
        
        assert len(chain) == 3
        assert chain[0]['event'] == 'tools.now'
        assert isinstance(chain[1], list)  # Parallel events
        assert chain[2]['event'] == 'email.send'


class TestChainEvent:
    """Test suite for ChainEvent dataclass"""

    def test_chain_event_creation(self):
        """Test creating a ChainEvent"""
        event = ChainEventSpec(
            event='tools.now',
            params={'test': True},
            decide='Should run?'
        )
        
        assert event.event == 'tools.now'
        assert event.params == {'test': True}
        assert event.decide == 'Should run?'
        assert event.result is None
        assert event.error is None

    def test_chain_event_with_result(self):
        """Test ChainEvent with result"""
        event = ChainEventSpec(
            event='tools.now',
            result={'timestamp': '2025-01-15T10:30:00Z'}
        )
        
        assert event.result == {'timestamp': '2025-01-15T10:30:00Z'}

    def test_chain_event_with_error(self):
        """Test ChainEvent with error"""
        event = ChainEventSpec(
            event='tools.now',
            error={'message': 'Failed', 'type': 'ValueError'}
        )
        
        assert event.error == {'message': 'Failed', 'type': 'ValueError'}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])