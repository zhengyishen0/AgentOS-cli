"""Thread management for EventChain architecture.

Threads are event chains that maintain conversation context and history.
"""

import json
import logging
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import asyncio
from pathlib import Path

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
    
    def __init__(self, storage_path: str = "./threads"):
        """Initialize thread manager.
        
        Args:
            storage_path: Directory to store thread files
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        self._thread_cache: Dict[str, Thread] = {}
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
            
            # Check uniqueness in cache
            if thread_id in self._thread_cache:
                raise ValueError(f"Thread {thread_id} already exists in cache")
            
            # Check uniqueness on disk
            thread_file = self.storage_path / f"{thread_id}.json"
            if thread_file.exists():
                raise ValueError(f"Thread {thread_id} already exists on disk")
            
            thread = Thread(
                thread_id=thread_id,
                summary=summary
            )
            
            # Add creation event
            thread.add_event(
                event="thread.created",
                result={"thread_id": thread_id, "summary": summary}
            )
            
            # Save to disk and cache
            await self._save_thread(thread)
            self._thread_cache[thread_id] = thread
            
            logger.info(f"Created thread {thread_id}")
            return thread
    
    async def get_thread(self, thread_id: str) -> Optional[Thread]:
        """Get a thread by ID.
        
        Args:
            thread_id: Thread identifier
            
        Returns:
            Thread object or None if not found
        """
        async with self._lock:
            # Check cache first
            if thread_id in self._thread_cache:
                return self._thread_cache[thread_id]
            
            # Try loading from disk
            thread_file = self.storage_path / f"{thread_id}.json"
            if thread_file.exists():
                try:
                    with open(thread_file, 'r') as f:
                        data = json.load(f)
                    thread = Thread.from_dict(data)
                    self._thread_cache[thread_id] = thread
                    return thread
                except Exception as e:
                    logger.error(f"Failed to load thread {thread_id}: {e}")
                    return None
            
            return None
    
    
    async def list_threads(self, status: Optional[str] = None) -> List[Thread]:
        """List all threads.
        
        Args:
            status: Filter by status (active/archived)
            
        Returns:
            List of Thread objects
        """
        threads = []
        
        # Load all thread files
        for thread_file in self.storage_path.glob("*.json"):
            try:
                with open(thread_file, 'r') as f:
                    data = json.load(f)
                thread = Thread.from_dict(data)
                
                if status is None or thread.status == status:
                    threads.append(thread)
                    
            except Exception as e:
                logger.error(f"Failed to load thread from {thread_file}: {e}")
        
        # Sort by updated_at descending
        threads.sort(key=lambda t: t.updated_at, reverse=True)
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
            
            # Save changes and remove from cache
            await self._save_thread(thread)
            
            # Remove from cache to save memory
            if thread_id in self._thread_cache:
                del self._thread_cache[thread_id]
                
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
        query_lower = query.lower()
        
        for thread in await self.list_threads(status="active"):
            # Search in summary
            if query_lower in thread.summary.lower():
                matches.append(thread)
                continue
                
            # Search in recent events
            for event in thread.events[-20:]:  # Search last 20 events
                if query_lower in json.dumps(event.result).lower():
                    matches.append(thread)
                    break
            
            if len(matches) >= limit:
                break
        
        return matches[:limit]
    
    async def _save_thread(self, thread: Thread):
        """Save thread to disk."""
        thread_file = self.storage_path / f"{thread.thread_id}.json"
        try:
            with open(thread_file, 'w') as f:
                json.dump(thread.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save thread {thread.thread_id}: {e}")
            raise
    
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
        
        # Save to disk and update cache
        await self._save_thread(thread)
        self._thread_cache[thread_id] = thread
        return True
    

thread_manager = ThreadManager()