"""Thread management for EventChain architecture.

Threads are event chains that maintain conversation context and history.
"""

import logging
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import asyncio

from modules.persistence import ThreadStorage

logger = logging.getLogger(__name__)


@dataclass
class ThreadEvent:
    """Single event within a thread."""
    event: str
    result: Dict[str, Any]
    timestamp: str
    params: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None


@dataclass
class Thread:
    """Thread containing conversation context and event history."""
    thread_id: str
    summary: str
    status: str = "active"  # active | archived
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    events: List[ThreadEvent] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_event(self, event: str, result: Dict[str, Any], 
                  params: Optional[Dict[str, Any]] = None,
                  error: Optional[Dict[str, Any]] = None):
        """Add an event to the thread."""
        thread_event = ThreadEvent(
            event=event,
            result=result,
            timestamp=datetime.now(timezone.utc).isoformat(),
            params=params,
            error=error
        )
        self.events.append(thread_event)
        self.updated_at = datetime.now(timezone.utc).isoformat()
    
    def get_context(self) -> Dict[str, Any]:
        """Get thread context for event execution."""
        context = {
            'thread_id': self.thread_id,
            'summary': self.summary,
            'metadata': self.metadata,
            'thread': {
                self.thread_id: {
                    'events': [asdict(e) for e in self.events],
                    'summary': self.summary,
                    'metadata': self.metadata
                }
            }
        }
        
        # Add recent event results to context
        for event in self.events[-10:]:  # Last 10 events for efficiency
            if '.' in event.event and event.result:
                parts = event.event.split('.')
                current = context
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                current[parts[-1]] = {'result': event.result}
        
        return context
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert thread to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Thread':
        """Create thread from dictionary."""
        events_data = data.pop('events', [])
        thread = cls(**data)
        
        # Reconstruct ThreadEvent objects
        thread.events = [
            ThreadEvent(**event_data) for event_data in events_data
        ]
        
        return thread


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
            thread.add_event(
                event="thread.created",
                result={"thread_id": thread_id, "summary": summary}
            )
            
            # Save to storage
            await self._storage.save(thread_id, thread.to_dict())
            
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
            return Thread.from_dict(thread_data)
        return None
    
    
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
                thread = Thread.from_dict(thread_data)
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
            thread.add_event(
                event="thread.archived",
                result={"thread_id": thread_id}
            )
            
            # Save changes
            await self._storage.save(thread_id, thread.to_dict())
                
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
                    thread = Thread.from_dict(thread_data)
                    matches.append(thread)
                except Exception as e:
                    logger.error(f"Failed to parse thread {thread_id}: {e}")
        
        return matches
    
    
    async def add_event_to_thread(self, thread_id: str, event: ThreadEvent) -> bool:
        """Add an event to a thread.
        
        Args:
            thread_id: Thread identifier
            event: ThreadEvent object to add
            
        Returns:
            True if successful
        """
        thread = await self.get_thread(thread_id)
        if not thread:
            logger.error(f"Thread {thread_id} not found")
            return False
        
        # Add the event directly to the thread's events list
        thread.events.append(event)
        thread.updated_at = datetime.now(timezone.utc).isoformat()
        
        # Save to storage
        await self._storage.save(thread_id, thread.to_dict())
        return True
    

thread_manager = ThreadManager()