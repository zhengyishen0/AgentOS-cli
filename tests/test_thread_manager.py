"""Test file for thread_manager.py"""

import pytest
import asyncio
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone
from modules.eventbus.thread_manager import ThreadManager, Thread, ThreadEvent


class TestThreadEvent:
    """Test suite for ThreadEvent dataclass"""

    def test_thread_event_creation(self):
        """Test creating a ThreadEvent"""
        event = ThreadEvent(
            event='user.create',
            result={'user_id': 'user_123'},
            timestamp='2025-01-15T10:30:00Z',
            params={'name': 'John'}
        )
        
        assert event.event == 'user.create'
        assert event.result == {'user_id': 'user_123'}
        assert event.timestamp == '2025-01-15T10:30:00Z'
        assert event.params == {'name': 'John'}
        assert event.error is None

    def test_thread_event_with_error(self):
        """Test ThreadEvent with error"""
        event = ThreadEvent(
            event='user.create',
            result={},
            timestamp='2025-01-15T10:30:00Z',
            error={'message': 'Creation failed', 'type': 'ValueError'}
        )
        
        assert event.error == {'message': 'Creation failed', 'type': 'ValueError'}


class TestThread:
    """Test suite for Thread dataclass"""

    def test_thread_creation(self):
        """Test creating a Thread"""
        thread = Thread(
            thread_id='test_thread_1',
            summary='Test thread for user management'
        )
        
        assert thread.thread_id == 'test_thread_1'
        assert thread.summary == 'Test thread for user management'
        assert thread.status == 'active'
        assert len(thread.events) == 0
        assert thread.metadata == {}

    def test_thread_add_event(self):
        """Test adding events to a thread"""
        thread = Thread(
            thread_id='test_thread_1',
            summary='Test thread'
        )
        
        # Add an event
        thread.add_event(
            event='user.create',
            result={'user_id': 'user_123'},
            params={'name': 'John'}
        )
        
        assert len(thread.events) == 1
        assert thread.events[0].event == 'user.create'
        assert thread.events[0].result == {'user_id': 'user_123'}
        assert thread.events[0].params == {'name': 'John'}
        assert thread.events[0].error is None

    def test_thread_get_context(self):
        """Test getting thread context"""
        thread = Thread(
            thread_id='test_thread_1',
            summary='Test thread'
        )
        
        # Add some events
        thread.add_event('tools.now', {'timestamp': '2025-01-15T10:30:00Z'})
        thread.add_event('user.create', {'user_id': 'user_123'})
        
        context = thread.get_context()
        
        assert context['thread_id'] == 'test_thread_1'
        assert context['summary'] == 'Test thread'
        assert 'thread' in context
        assert 'test_thread_1' in context['thread']
        assert len(context['thread']['test_thread_1']['events']) == 2
        
        # Check that event results are in context
        assert 'tools' in context
        assert context['tools']['now']['result'] == {'timestamp': '2025-01-15T10:30:00Z'}
        assert 'user' in context
        assert context['user']['create']['result'] == {'user_id': 'user_123'}

    def test_thread_to_dict(self):
        """Test converting thread to dictionary"""
        thread = Thread(
            thread_id='test_thread_1',
            summary='Test thread'
        )
        thread.add_event('user.create', {'user_id': 'user_123'})
        
        data = thread.to_dict()
        
        assert data['thread_id'] == 'test_thread_1'
        assert data['summary'] == 'Test thread'
        assert data['status'] == 'active'
        assert len(data['events']) == 1
        assert data['events'][0]['event'] == 'user.create'

    def test_thread_from_dict(self):
        """Test creating thread from dictionary"""
        data = {
            'thread_id': 'test_thread_1',
            'summary': 'Test thread',
            'status': 'active',
            'created_at': '2025-01-15T10:30:00Z',
            'updated_at': '2025-01-15T10:30:00Z',
            'events': [
                {
                    'event': 'user.create',
                    'result': {'user_id': 'user_123'},
                    'timestamp': '2025-01-15T10:30:00Z',
                    'params': {'name': 'John'},
                    'error': None
                }
            ],
            'metadata': {}
        }
        
        thread = Thread.from_dict(data)
        
        assert thread.thread_id == 'test_thread_1'
        assert thread.summary == 'Test thread'
        assert len(thread.events) == 1
        assert thread.events[0].event == 'user.create'
        assert thread.events[0].result == {'user_id': 'user_123'}


class TestThreadManager:
    """Test suite for ThreadManager"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def thread_manager(self, temp_dir):
        """Create ThreadManager with temporary storage"""
        return ThreadManager(storage_path=temp_dir)

    @pytest.mark.asyncio
    async def test_create_thread_auto_id(self, thread_manager):
        """Test creating thread with auto-generated ID"""
        thread = await thread_manager.create_thread(summary='Test thread')
        
        assert thread.thread_id.startswith('thread_')
        assert thread.summary == 'Test thread'
        assert thread.status == 'active'
        assert len(thread.events) == 1  # Creation event
        assert thread.events[0].event == 'thread.created'

    @pytest.mark.asyncio
    async def test_create_thread_custom_id(self, thread_manager):
        """Test creating thread with custom ID"""
        thread = await thread_manager.create_thread(
            thread_id='custom_thread_1',
            summary='Custom thread'
        )
        
        assert thread.thread_id == 'custom_thread_1'
        assert thread.summary == 'Custom thread'

    @pytest.mark.asyncio
    async def test_create_thread_duplicate_id(self, thread_manager):
        """Test creating thread with duplicate ID"""
        await thread_manager.create_thread(thread_id='duplicate_thread')
        
        with pytest.raises(ValueError, match="Thread duplicate_thread already exists"):
            await thread_manager.create_thread(thread_id='duplicate_thread')

    @pytest.mark.asyncio
    async def test_get_thread_from_cache(self, thread_manager):
        """Test getting thread from cache"""
        # Create thread (will be cached)
        original_thread = await thread_manager.create_thread(thread_id='cached_thread')
        
        # Get from cache
        retrieved_thread = await thread_manager.get_thread('cached_thread')
        
        assert retrieved_thread is not None
        assert retrieved_thread.thread_id == 'cached_thread'
        assert retrieved_thread.summary == original_thread.summary

    @pytest.mark.asyncio
    async def test_get_thread_from_disk(self, thread_manager):
        """Test getting thread from disk"""
        # Create thread
        original_thread = await thread_manager.create_thread(thread_id='disk_thread')
        
        # Clear cache
        thread_manager._thread_cache.clear()
        
        # Get from disk
        retrieved_thread = await thread_manager.get_thread('disk_thread')
        
        assert retrieved_thread is not None
        assert retrieved_thread.thread_id == 'disk_thread'
        assert retrieved_thread.summary == original_thread.summary

    @pytest.mark.asyncio
    async def test_get_thread_not_found(self, thread_manager):
        """Test getting non-existent thread"""
        thread = await thread_manager.get_thread('nonexistent_thread')
        assert thread is None

    @pytest.mark.asyncio
    async def test_list_threads_empty(self, thread_manager):
        """Test listing threads when none exist"""
        threads = await thread_manager.list_threads()
        assert threads == []

    @pytest.mark.asyncio
    async def test_list_threads_with_data(self, thread_manager):
        """Test listing threads with data"""
        # Create multiple threads
        await thread_manager.create_thread(thread_id='thread_1', summary='First thread')
        await thread_manager.create_thread(thread_id='thread_2', summary='Second thread')
        
        threads = await thread_manager.list_threads()
        
        assert len(threads) == 2
        thread_ids = [t.thread_id for t in threads]
        assert 'thread_1' in thread_ids
        assert 'thread_2' in thread_ids

    @pytest.mark.asyncio
    async def test_list_threads_by_status(self, thread_manager):
        """Test listing threads filtered by status"""
        # Create active thread
        await thread_manager.create_thread(thread_id='active_thread')
        
        # Create and archive another thread
        await thread_manager.create_thread(thread_id='archived_thread')
        await thread_manager.archive_thread('archived_thread')
        
        # List active threads
        active_threads = await thread_manager.list_threads(status='active')
        assert len(active_threads) == 1
        assert active_threads[0].thread_id == 'active_thread'
        
        # List archived threads
        archived_threads = await thread_manager.list_threads(status='archived')
        assert len(archived_threads) == 1
        assert archived_threads[0].thread_id == 'archived_thread'

    @pytest.mark.asyncio
    async def test_archive_thread(self, thread_manager):
        """Test archiving a thread"""
        # Create thread
        await thread_manager.create_thread(thread_id='thread_to_archive')
        
        # Archive it
        success = await thread_manager.archive_thread('thread_to_archive')
        assert success is True
        
        # Check it was archived
        thread = await thread_manager.get_thread('thread_to_archive')
        assert thread.status == 'archived'
        
        # Check archive event was added
        archive_events = [e for e in thread.events if e.event == 'thread.archived']
        assert len(archive_events) == 1

    @pytest.mark.asyncio
    async def test_archive_nonexistent_thread(self, thread_manager):
        """Test archiving non-existent thread"""
        success = await thread_manager.archive_thread('nonexistent_thread')
        assert success is False

    @pytest.mark.asyncio
    async def test_search_threads_by_summary(self, thread_manager):
        """Test searching threads by summary"""
        # Create threads with different summaries
        await thread_manager.create_thread(thread_id='thread_1', summary='User management system')
        await thread_manager.create_thread(thread_id='thread_2', summary='Email notification service')
        await thread_manager.create_thread(thread_id='thread_3', summary='User authentication')
        
        # Search for "user"
        matches = await thread_manager.search_threads('user')
        
        assert len(matches) == 2
        thread_ids = [t.thread_id for t in matches]
        assert 'thread_1' in thread_ids
        assert 'thread_3' in thread_ids

    @pytest.mark.asyncio
    async def test_search_threads_by_event_content(self, thread_manager):
        """Test searching threads by event content"""
        # Create thread and add events
        thread = await thread_manager.create_thread(thread_id='search_thread')
        thread.add_event('user.create', {'user_id': 'john_doe', 'name': 'John Doe'})
        thread.add_event('email.send', {'to': 'john@example.com', 'subject': 'Welcome'})
        await thread_manager._save_thread(thread)
        
        # Search for "john"
        matches = await thread_manager.search_threads('john')
        
        assert len(matches) == 1
        assert matches[0].thread_id == 'search_thread'

    @pytest.mark.asyncio
    async def test_search_threads_limit(self, thread_manager):
        """Test search limit functionality"""
        # Create many threads
        for i in range(5):
            await thread_manager.create_thread(
                thread_id=f'thread_{i}',
                summary=f'Test thread {i}'
            )
        
        # Search with limit
        matches = await thread_manager.search_threads('test', limit=3)
        
        assert len(matches) == 3

    @pytest.mark.asyncio
    async def test_add_event_to_thread(self, thread_manager):
        """Test adding event to existing thread"""
        # Create thread
        thread = await thread_manager.create_thread(thread_id='event_thread')
        initial_event_count = len(thread.events)
        
        # Add event
        event = ThreadEvent(
            event='user.update',
            result={'user_id': 'user_123', 'updated': True},
            timestamp=datetime.now(timezone.utc).isoformat(),
            params={'name': 'Jane Doe'}
        )
        
        success = await thread_manager.add_event_to_thread('event_thread', event)
        assert success is True
        
        # Verify event was added
        updated_thread = await thread_manager.get_thread('event_thread')
        assert len(updated_thread.events) == initial_event_count + 1
        assert updated_thread.events[-1].event == 'user.update'

    @pytest.mark.asyncio
    async def test_add_event_to_nonexistent_thread(self, thread_manager):
        """Test adding event to non-existent thread"""
        event = ThreadEvent(
            event='user.update',
            result={'user_id': 'user_123'},
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        success = await thread_manager.add_event_to_thread('nonexistent_thread', event)
        assert success is False

    @pytest.mark.asyncio
    async def test_storage_persistence(self, thread_manager):
        """Test that threads persist across manager instances"""
        # Create thread with first manager
        await thread_manager.create_thread(thread_id='persistent_thread')
        
        # Create new manager with same storage path
        new_manager = ThreadManager(storage_path=thread_manager.storage_path)
        
        # Should be able to retrieve thread
        thread = await new_manager.get_thread('persistent_thread')
        assert thread is not None
        assert thread.thread_id == 'persistent_thread'

    @pytest.mark.asyncio
    async def test_concurrent_access(self, thread_manager):
        """Test concurrent thread operations"""
        # Create multiple threads concurrently
        tasks = [
            thread_manager.create_thread(thread_id=f'concurrent_thread_{i}')
            for i in range(5)
        ]
        
        threads = await asyncio.gather(*tasks)
        
        # All threads should be created successfully
        assert len(threads) == 5
        for i, thread in enumerate(threads):
            assert thread.thread_id == f'concurrent_thread_{i}'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])