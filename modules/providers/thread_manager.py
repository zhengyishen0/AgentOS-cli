"""Thread management for EventChain architecture.

Threads are event chains that maintain conversation context and history.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import asyncio

from modules.persistence import ThreadStorage
from modules.eventbus.models import Thread, Event

logger = logging.getLogger(__name__)


class ThreadManager:
    """Manages thread persistence and retrieval."""
    
    def __init__(self, storage_path: str = "data/threads"):
        """Initialize thread manager.
        
        Args:
            storage_path: Directory to store thread files
        """
        self._storage = ThreadStorage(storage_path=storage_path)
        self._lock = asyncio.Lock()
    
    async def create_thread(self, thread_id: Optional[str] = None, summary: Optional[str] = None) -> Thread:
        """Create a new thread.
        
        Args:
            thread_id: Optional unique identifier. Auto-generated if not provided.
            summary: Optional thread summary. Auto-generated if not provided.
            
        Returns:
            Created Thread object
        """
        async with self._lock:
            # Generate thread_id if not provided
            if not thread_id:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                short_uuid = uuid.uuid4().hex[:6]
                thread_id = f"thread_{timestamp}_{short_uuid}"
            
            # Generate summary if not provided
            if not summary:
                summary = f"Thread created at {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
            # Check uniqueness
            if await self._storage.exists(thread_id):
                raise ValueError(f"Thread {thread_id} already exists")
            
            thread = Thread(
                thread_id=thread_id,
                summary=summary
            )
            
            # Add creation event
            creation_event = Event(
                name="thread.created",
                data={"thread_id": thread_id, "summary": summary},
                result={"thread_id": thread_id, "summary": summary},
                status="completed",
                source="thread_manager"
            )
            thread.add_event(creation_event)
            
            # Save to storage
            await self._storage.save(thread_id, thread.model_dump(mode='json'))
            
            logger.info(f"Created thread {thread_id}")
            return thread
    
    async def get_thread(self, thread_id: str) -> Optional[Thread]:
        """Get a thread by ID.
        
        Args:
            thread_id: Thread identifier
            
        Returns:
            Thread object or None if not found
        """
        # Load from storage
        thread_data = await self._storage.load(thread_id)
        if thread_data:
            return Thread(**thread_data)
        return None
    
    async def thread_summary(self) -> List[str]:
        """Get the summary of current active thread
            
        Returns:
            List of thread summaries
        """
        # Load from storage
        threads = await self.list_threads(status="active")
        return [f"{thread.thread_id}: {thread.summary}" for thread in threads]
    
    
    async def list_threads(self, status: Optional[str] = None) -> List[Thread]:
        """List all threads.
        
        Args:
            status: Filter by status (active/archived)
            
        Returns:
            List of Thread objects
        """
        threads = []
        
        # Stream threads from storage
        async for thread_id, thread_data in self._storage.stream_all(status):
            try:
                thread = Thread(**thread_data)
                threads.append(thread)
            except Exception as e:
                logger.error(f"Failed to parse thread {thread_id}: {e}")
        
        return threads
    
    async def archive_thread(self, thread_id: str) -> bool:
        """Archive a thread.
        
        Args:
            thread_id: Thread to archive
            
        Returns:
            True if successful
        """
        thread = await self.get_thread(thread_id)
        if thread:
            thread.status = "archived"
            archive_event = Event(
                name="thread.archived",
                data={"thread_id": thread_id},
                result={"thread_id": thread_id},
                status="completed",
                source="thread_manager"
            )
            thread.add_event(archive_event)
            
            # Save changes
            await self._storage.save(thread_id, thread.model_dump(mode='json'))
                
            return True
        return False
    
    async def search_threads(self, query: str, limit: int = 10) -> List[Thread]:
        """Search threads by content.
        
        Args:
            query: Search query
            limit: Maximum results
            
        Returns:
            List of matching threads
        """
        matches = []
        
        # Use storage search capabilities
        search_results = await self._storage.search(query, limit)
        
        for thread_id, metadata in search_results:
            thread_data = await self._storage.load(thread_id)
            if thread_data:
                try:
                    thread = Thread(**thread_data)
                    matches.append(thread)
                except Exception as e:
                    logger.error(f"Failed to parse thread {thread_id}: {e}")
        
        return matches
    
    
    async def add_event_to_thread(self, thread_id: str, event: Event) -> bool:
        """Add an event to a thread.
        
        Args:
            thread_id: Thread identifier
            event: Event object to add
            
        Returns:
            True if successful
        """
        thread = await self.get_thread(thread_id)
        if not thread:
            logger.error(f"Thread {thread_id} not found")
            return False
        
        # Add the event to the thread
        thread.add_event(event)
        
        # Save to storage
        await self._storage.save(thread_id, thread.model_dump(mode='json'))
        return True
    

thread_manager = ThreadManager()