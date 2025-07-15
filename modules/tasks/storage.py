"""Task storage using JSON files for persistence."""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime


class TaskStorage:
    """Minimal task storage using JSON files."""
    
    def __init__(self, storage_dir: str = "./data/tasks"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
    def save_task(self, task_id: str, task_data: Dict) -> bool:
        """Save a task to a JSON file."""
        try:
            # Add metadata
            task_data["id"] = task_id
            task_data["saved_at"] = datetime.now().isoformat()
            
            # Save to file
            file_path = self.storage_dir / f"{task_id}.json"
            with open(file_path, "w") as f:
                json.dump(task_data, f, indent=2, default=str)
            
            return True
        except Exception as e:
            print(f"Error saving task {task_id}: {e}")
            return False
    
    def load_task(self, task_id: str) -> Optional[Dict]:
        """Load a task from JSON file."""
        try:
            file_path = self.storage_dir / f"{task_id}.json"
            if file_path.exists():
                with open(file_path) as f:
                    return json.load(f)
            return None
        except Exception as e:
            print(f"Error loading task {task_id}: {e}")
            return None
    
    def list_tasks(self) -> List[Dict]:
        """List all tasks."""
        tasks = []
        for file_path in self.storage_dir.glob("*.json"):
            try:
                with open(file_path) as f:
                    task = json.load(f)
                    tasks.append(task)
            except:
                pass
        return tasks
    
    def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        try:
            file_path = self.storage_dir / f"{task_id}.json"
            if file_path.exists():
                file_path.unlink()
                return True
            return False
        except Exception as e:
            print(f"Error deleting task {task_id}: {e}")
            return False

