"""Domain-specific storage for events."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, AsyncGenerator
from datetime import datetime, date, timedelta
import asyncio

logger = logging.getLogger(__name__)


class EventStorage:
    """Domain-specific storage for event management with daily partitioning."""
    
    def __init__(self, 
                 storage_path: str = "data/events",
                 daily_partitions: bool = True,
                 retention_days: Optional[int] = 30):
        """Initialize event storage.
        
        Args:
            storage_path: Directory to store event files
            daily_partitions: Enable daily partitioning
            retention_days: Number of days to retain events (None for no cleanup)
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.daily_partitions = daily_partitions
        self.retention_days = retention_days
        self._lock = asyncio.Lock()
    
    def _get_partition_path(self, timestamp: Optional[datetime] = None) -> Path:
        """Get the file path for a given timestamp.
        
        Args:
            timestamp: Event timestamp (defaults to now)
            
        Returns:
            Path to the partition file
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        if self.daily_partitions:
            date_str = timestamp.strftime("%Y-%m-%d")
            partition_dir = self.storage_path / date_str
            partition_dir.mkdir(exist_ok=True)
            return partition_dir / "events.jsonl"
        else:
            return self.storage_path / "events.jsonl"
    
    async def save_event(self, 
                        type: str, 
                        data: Dict[str, Any], 
                        source: str = "system",
                        timestamp: Optional[datetime] = None) -> bool:
        """Save an event.
        
        Args:
            type: Type of event (e.g., "user.login")
            data: Event data payload
            source: Source of the event
            timestamp: Event timestamp (defaults to now)
            
        Returns:
            True if successful
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        event_record = {
            "type": type,
            "data": data,
            "timestamp": timestamp.isoformat(),
            "source": source
        }
        
        try:
            async with self._lock:
                partition_file = self._get_partition_path(timestamp)
                
                def _append_event():
                    # Ensure parent directory exists
                    partition_file.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Append event as JSON line
                    with open(partition_file, 'a', encoding='utf-8') as f:
                        f.write(json.dumps(event_record, ensure_ascii=False) + '\n')
                
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, _append_event)
                
                logger.debug(f"Saved event {type} to {partition_file}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to save event {type}: {e}")
            return False
    
    async def load_events_from_date(self, date_str: str) -> List[Dict[str, Any]]:
        """Load all events from a specific date.
        
        Args:
            date_str: Date string in YYYY-MM-DD format
            
        Returns:
            List of event dictionaries
        """
        if not self.daily_partitions:
            # For non-partitioned storage, we'd need to filter by date
            return await self._load_events_filtered_by_date(date_str)
        
        partition_dir = self.storage_path / date_str
        partition_file = partition_dir / "events.jsonl"
        
        if not partition_file.exists():
            return []
        
        return await self._read_events_from_file(partition_file)
    
    async def load_events_from_range(self, 
                                   start_date: str, 
                                   end_date: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Load events from a date range.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Yields:
            Event dictionaries in chronological order
        """
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
        
        current_date = start
        while current_date <= end:
            date_str = current_date.strftime("%Y-%m-%d")
            events = await self.load_events_from_date(date_str)
            
            for event in events:
                yield event
            
            current_date += timedelta(days=1)
    
    async def load_recent_events(self, days: int = 7) -> AsyncGenerator[Dict[str, Any], None]:
        """Load recent events from the last N days.
        
        Args:
            days: Number of days to look back
            
        Yields:
            Event dictionaries
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days - 1)
        
        async for event in self.load_events_from_range(
            start_date.isoformat(), 
            end_date.isoformat()
        ):
            yield event
    
    async def load_today_events(self) -> List[Dict[str, Any]]:
        """Load events from today.
        
        Returns:
            List of today's events
        """
        today_str = date.today().strftime("%Y-%m-%d")
        return await self.load_events_from_date(today_str)
    
    async def _read_events_from_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Read events from a JSONL file.
        
        Args:
            file_path: Path to the JSONL file
            
        Returns:
            List of event dictionaries
        """
        try:
            def _read_file():
                events = []
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            event = json.loads(line)
                            events.append(event)
                        except json.JSONDecodeError as e:
                            logger.warning(f"Invalid JSON on line {line_num} in {file_path}: {e}")
                return events
            
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, _read_file)
            
        except Exception as e:
            logger.error(f"Failed to read events from {file_path}: {e}")
            return []
    
    async def _load_events_filtered_by_date(self, date_str: str) -> List[Dict[str, Any]]:
        """Load events filtered by date from non-partitioned storage.
        
        Args:
            date_str: Date string in YYYY-MM-DD format
            
        Returns:
            List of event dictionaries from that date
        """
        events_file = self.storage_path / "events.jsonl"
        if not events_file.exists():
            return []
        
        all_events = await self._read_events_from_file(events_file)
        filtered_events = []
        
        for event in all_events:
            event_timestamp = event.get("timestamp", "")
            if event_timestamp.startswith(date_str):
                filtered_events.append(event)
        
        return filtered_events
    
    async def count_events(self, date_str: Optional[str] = None) -> int:
        """Count events, optionally for a specific date.
        
        Args:
            date_str: Date string in YYYY-MM-DD format (None for all events)
            
        Returns:
            Number of events
        """
        if date_str:
            events = await self.load_events_from_date(date_str)
            return len(events)
        else:
            total = 0
            partitions = await self.list_partitions()
            for partition in partitions:
                events = await self.load_events_from_date(partition)
                total += len(events)
            return total
    
    async def list_partitions(self) -> List[str]:
        """List all available date partitions.
        
        Returns:
            List of date strings (YYYY-MM-DD format)
        """
        if not self.daily_partitions:
            # For non-partitioned storage, return dates based on content
            return await self._get_dates_from_content()
        
        try:
            partitions = []
            for item in self.storage_path.iterdir():
                if item.is_dir() and len(item.name) == 10:  # YYYY-MM-DD format
                    try:
                        # Validate date format
                        date.fromisoformat(item.name)
                        partitions.append(item.name)
                    except ValueError:
                        continue
            
            return sorted(partitions)
            
        except Exception as e:
            logger.error(f"Failed to list partitions: {e}")
            return []
    
    async def _get_dates_from_content(self) -> List[str]:
        """Get unique dates from event content (for non-partitioned storage).
        
        Returns:
            List of date strings found in events
        """
        events_file = self.storage_path / "events.jsonl"
        if not events_file.exists():
            return []
        
        dates = set()
        all_events = await self._read_events_from_file(events_file)
        
        for event in all_events:
            timestamp = event.get("timestamp", "")
            if len(timestamp) >= 10:
                date_part = timestamp[:10]  # Extract YYYY-MM-DD
                try:
                    date.fromisoformat(date_part)
                    dates.add(date_part)
                except ValueError:
                    continue
        
        return sorted(list(dates))
    
    async def cleanup_old_events(self) -> List[str]:
        """Clean up old event partitions based on retention policy.
        
        Returns:
            List of deleted partition dates
        """
        if self.retention_days is None:
            return []
        
        cutoff_date = date.today() - timedelta(days=self.retention_days)
        deleted_partitions = []
        
        try:
            partitions = await self.list_partitions()
            
            for partition_date in partitions:
                try:
                    partition_date_obj = date.fromisoformat(partition_date)
                    if partition_date_obj < cutoff_date:
                        success = await self._delete_partition(partition_date)
                        if success:
                            deleted_partitions.append(partition_date)
                except ValueError:
                    continue
            
            if deleted_partitions:
                logger.info(f"Cleaned up {len(deleted_partitions)} old event partitions")
            
            return deleted_partitions
            
        except Exception as e:
            logger.error(f"Failed to cleanup old events: {e}")
            return []
    
    async def _delete_partition(self, date_str: str) -> bool:
        """Delete a specific date partition.
        
        Args:
            date_str: Date string in YYYY-MM-DD format
            
        Returns:
            True if successful
        """
        try:
            if self.daily_partitions:
                partition_dir = self.storage_path / date_str
                if partition_dir.exists():
                    # Remove all files in the partition directory
                    for file_path in partition_dir.iterdir():
                        if file_path.is_file():
                            file_path.unlink()
                    
                    # Remove directory if empty
                    try:
                        partition_dir.rmdir()
                    except OSError:
                        pass  # Directory not empty, that's okay
                    
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete partition {date_str}: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics.
        
        Returns:
            Dictionary with storage stats
        """
        try:
            partitions = await self.list_partitions()
            total_events = await self.count_events()
            
            # Calculate total size
            total_size = 0
            if self.daily_partitions:
                for partition in partitions:
                    partition_dir = self.storage_path / partition
                    for file_path in partition_dir.glob("*.jsonl"):
                        total_size += file_path.stat().st_size
            else:
                events_file = self.storage_path / "events.jsonl"
                if events_file.exists():
                    total_size = events_file.stat().st_size
            
            return {
                "storage_path": str(self.storage_path),
                "daily_partitions": self.daily_partitions,
                "retention_days": self.retention_days,
                "total_partitions": len(partitions),
                "total_events": total_events,
                "total_size_bytes": total_size,
                "oldest_partition": partitions[0] if partitions else None,
                "newest_partition": partitions[-1] if partitions else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get storage stats: {e}")
            return {"error": str(e)}