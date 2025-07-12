"""Domain-specific storage for thread management."""

import json
import logging
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, AsyncIterator
from datetime import datetime
import aiofiles
import time

logger = logging.getLogger(__name__)


class ThreadStorage:
    """Domain-specific storage for thread management.
    
    Features:
    - Dictionary-based API (no Thread class dependencies)
    - Built-in caching with TTL
    - Metadata indexing for fast search
    - Async streaming for large datasets
    - Atomic operations
    """
    
    def __init__(self, 
                 storage_path: str = "data/threads",
                 cache_ttl_seconds: int = 300,
                 max_cache_size: int = 100):
        """Initialize thread storage.
        
        Args:
            storage_path: Directory to store thread files
            cache_ttl_seconds: Cache time-to-live in seconds
            max_cache_size: Maximum number of threads to cache
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.cache_ttl = cache_ttl_seconds
        self.max_cache_size = max_cache_size
        
        # Cache structure: thread_id -> (thread_dict, timestamp)
        self._cache: Dict[str, Tuple[Dict[str, Any], float]] = {}
        
        # Metadata index: thread_id -> {summary, status, updated_at}
        self._metadata_index: Dict[str, Dict[str, Any]] = {}
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
        
        # Flag to track initialization
        self._initialized = False
    
    async def _ensure_initialized(self):
        """Ensure metadata index is initialized."""
        if not self._initialized:
            await self._init_metadata_index()
    
    async def _init_metadata_index(self):
        """Initialize metadata index from existing files."""
        try:
            async with self._lock:
                if self._initialized:
                    return
                    
                for thread_file in self.storage_path.glob("*.json"):
                    thread_id = thread_file.stem
                    try:
                        # Read just enough to get metadata
                        thread_data = await self._read_file(thread_file)
                        if thread_data:
                            self._metadata_index[thread_id] = {
                                "title": thread_data.get("title", ""),
                                "summary": thread_data.get("summary", ""),
                                "status": thread_data.get("status", "active"),
                                "updated_at": thread_data.get("updated_at", ""),
                                "created_at": thread_data.get("created_at", "")
                            }
                    except Exception as e:
                        logger.error(f"Failed to index {thread_id}: {e}")
                
                self._initialized = True
                logger.info(f"Initialized metadata index with {len(self._metadata_index)} threads")
        except Exception as e:
            logger.error(f"Failed to initialize metadata index: {e}")
    
    async def save(self, thread_id: str, thread_data: Dict[str, Any]) -> bool:
        """Save thread data atomically.
        
        Args:
            thread_id: Unique thread identifier
            thread_data: Thread data dictionary
            
        Returns:
            True if successful
        """
        try:
            async with self._lock:
                # Prepare file path
                thread_file = self.storage_path / f"{thread_id}.json"
                temp_file = thread_file.with_suffix(".tmp")
                
                # Write to temp file first (atomic operation)
                async with aiofiles.open(temp_file, 'w') as f:
                    await f.write(json.dumps(thread_data, indent=2))
                
                # Atomic rename
                temp_file.replace(thread_file)
                
                # Update cache
                self._cache[thread_id] = (thread_data, time.time())
                self._enforce_cache_limit()
                
                # Update metadata index
                self._metadata_index[thread_id] = {
                    "title": thread_data.get("title", ""),
                    "summary": thread_data.get("summary", ""),
                    "status": thread_data.get("status", "active"),
                    "updated_at": thread_data.get("updated_at", ""),
                    "created_at": thread_data.get("created_at", "")
                }
                
                logger.debug(f"Saved thread {thread_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to save thread {thread_id}: {e}")
            return False
    
    async def load(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """Load thread data with caching.
        
        Args:
            thread_id: Thread identifier
            
        Returns:
            Thread data dictionary or None
        """
        try:
            async with self._lock:
                # Check cache first
                if thread_id in self._cache:
                    thread_data, timestamp = self._cache[thread_id]
                    if time.time() - timestamp < self.cache_ttl:
                        logger.debug(f"Cache hit for thread {thread_id}")
                        return thread_data
                    else:
                        # Cache expired
                        del self._cache[thread_id]
                
                # Load from disk
                thread_file = self.storage_path / f"{thread_id}.json"
                if not thread_file.exists():
                    return None
                
                thread_data = await self._read_file(thread_file)
                if thread_data:
                    # Update cache
                    self._cache[thread_id] = (thread_data, time.time())
                    self._enforce_cache_limit()
                    
                return thread_data
                
        except Exception as e:
            logger.error(f"Failed to load thread {thread_id}: {e}")
            return None
    
    async def exists(self, thread_id: str) -> bool:
        """Check if thread exists (uses metadata index).
        
        Args:
            thread_id: Thread identifier
            
        Returns:
            True if thread exists
        """
        await self._ensure_initialized()
        
        # First check metadata index (fast)
        if thread_id in self._metadata_index:
            return True
        
        # Fallback to filesystem check
        thread_file = self.storage_path / f"{thread_id}.json"
        return thread_file.exists()
    
    async def list_ids(self, status: Optional[str] = None) -> List[str]:
        """List thread IDs filtered by status (uses index).
        
        Args:
            status: Filter by status (active/archived)
            
        Returns:
            List of thread IDs
        """
        await self._ensure_initialized()
        
        if status is None:
            return list(self._metadata_index.keys())
        
        return [
            thread_id 
            for thread_id, metadata in self._metadata_index.items()
            if metadata.get("status") == status
        ]
    
    async def search(self, query: str, limit: int = 10) -> List[Tuple[str, Dict[str, Any]]]:
        """Search threads using metadata index + content sampling.
        
        Args:
            query: Search query
            limit: Maximum results
            
        Returns:
            List of (thread_id, metadata) tuples
        """
        await self._ensure_initialized()
        
        query_lower = query.lower()
        matches = []
        
        # First pass: search in metadata (fast)
        for thread_id, metadata in self._metadata_index.items():
            if query_lower in metadata.get("summary", "").lower():
                matches.append((thread_id, metadata))
                if len(matches) >= limit:
                    break
        
        # Second pass: search in content if needed
        if len(matches) < limit:
            # Get active threads not yet matched
            remaining_ids = [
                tid for tid, meta in self._metadata_index.items()
                if meta.get("status") == "active" and tid not in [m[0] for m in matches]
            ]
            
            # Sample content from remaining threads
            for thread_id in remaining_ids[:limit * 2]:  # Check 2x limit for efficiency
                thread_data = await self.load(thread_id)
                if thread_data:
                    # Search in recent events
                    events = thread_data.get("events", [])[-20:]  # Last 20 events
                    for event in events:
                        if query_lower in json.dumps(event.get("result", {})).lower():
                            matches.append((thread_id, self._metadata_index[thread_id]))
                            break
                
                if len(matches) >= limit:
                    break
        
        # Sort by updated_at descending
        matches.sort(key=lambda x: x[1].get("updated_at", ""), reverse=True)
        return matches[:limit]
    
    async def stream_all(self, status: Optional[str] = None) -> AsyncIterator[Tuple[str, Dict[str, Any]]]:
        """Stream all threads without loading everything into memory.
        
        Args:
            status: Filter by status (active/archived)
            
        Yields:
            (thread_id, thread_data) tuples
        """
        # Get filtered thread IDs (will ensure initialization)
        thread_ids = await self.list_ids(status)
        
        # Sort by updated_at for consistent ordering
        sorted_ids = sorted(
            thread_ids,
            key=lambda tid: self._metadata_index.get(tid, {}).get("updated_at", ""),
            reverse=True
        )
        
        # Stream threads one by one
        for thread_id in sorted_ids:
            thread_data = await self.load(thread_id)
            if thread_data:
                yield (thread_id, thread_data)
    
    async def update_metadata(self, thread_id: str, metadata: Dict[str, Any]) -> bool:
        """Update just the metadata without loading full thread.
        
        Args:
            thread_id: Thread identifier
            metadata: Metadata fields to update
            
        Returns:
            True if successful
        """
        try:
            # Load current thread data
            thread_data = await self.load(thread_id)
            if not thread_data:
                return False
            
            # Update metadata fields
            for key, value in metadata.items():
                thread_data[key] = value
            
            # Save back
            return await self.save(thread_id, thread_data)
            
        except Exception as e:
            logger.error(f"Failed to update metadata for {thread_id}: {e}")
            return False
    
    async def delete(self, thread_id: str) -> bool:
        """Delete thread and update indexes.
        
        Args:
            thread_id: Thread identifier
            
        Returns:
            True if successful
        """
        try:
            async with self._lock:
                # Remove file
                thread_file = self.storage_path / f"{thread_id}.json"
                if thread_file.exists():
                    thread_file.unlink()
                
                # Remove from cache
                if thread_id in self._cache:
                    del self._cache[thread_id]
                
                # Remove from metadata index
                if thread_id in self._metadata_index:
                    del self._metadata_index[thread_id]
                
                logger.info(f"Deleted thread {thread_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to delete thread {thread_id}: {e}")
            return False
    
    async def _read_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Read JSON file asynchronously.
        
        Args:
            file_path: Path to JSON file
            
        Returns:
            Parsed JSON data or None
        """
        try:
            async with aiofiles.open(file_path, 'r') as f:
                content = await f.read()
                return json.loads(content)
        except Exception as e:
            logger.error(f"Failed to read {file_path}: {e}")
            return None
    
    def _enforce_cache_limit(self):
        """Enforce cache size limit by removing oldest entries."""
        if len(self._cache) > self.max_cache_size:
            # Sort by timestamp and remove oldest
            sorted_items = sorted(self._cache.items(), key=lambda x: x[1][1])
            for thread_id, _ in sorted_items[:len(self._cache) - self.max_cache_size]:
                del self._cache[thread_id]
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics.
        
        Returns:
            Dictionary with storage stats
        """
        await self._ensure_initialized()
        
        total_threads = len(self._metadata_index)
        active_threads = sum(1 for m in self._metadata_index.values() if m.get("status") == "active")
        archived_threads = sum(1 for m in self._metadata_index.values() if m.get("status") == "archived")
        
        # Calculate total size
        total_size = sum(
            (self.storage_path / f"{tid}.json").stat().st_size
            for tid in self._metadata_index
            if (self.storage_path / f"{tid}.json").exists()
        )
        
        return {
            "storage_path": str(self.storage_path),
            "total_threads": total_threads,
            "active_threads": active_threads,
            "archived_threads": archived_threads,
            "cache_size": len(self._cache),
            "cache_ttl_seconds": self.cache_ttl,
            "total_size_bytes": total_size
        }