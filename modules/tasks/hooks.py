"""Hook manager for event-driven task execution."""

import fnmatch
from typing import Dict, List, Callable


class HookManager:
    """Minimal hook manager for event-driven tasks."""
    
    def __init__(self):
        self.hooks: Dict[str, List[Dict]] = {}
        self._running = False
        
    async def start(self):
        """Start the hook manager."""
        self._running = True
        print("Hook manager started!")
        
    def stop(self):
        """Stop the hook manager."""
        self._running = False
        print("Hook manager stopped!")
        
    def register_hook(self, hook_id: str, event_pattern: str, action: Callable, position: str = "after"):
        """Register a hook for an event pattern."""
        if event_pattern not in self.hooks:
            self.hooks[event_pattern] = []
            
        self.hooks[event_pattern].append({
            "id": hook_id,
            "pattern": event_pattern,
            "action": action,
            "position": position
        })
        print(f"Registered {position}-hook {hook_id} for pattern: {event_pattern}")
        
    def remove_hook(self, hook_id: str):
        """Remove a hook."""
        for pattern, hooks in self.hooks.items():
            self.hooks[pattern] = [h for h in hooks if h["id"] != hook_id]
        
    async def handle_event(self, event_name: str, event_data: Dict, position: str = "after"):
        """Check if any hooks match this event for the given position."""
        if not self._running:
            return
            
        executed = []
        
        # Check each registered pattern
        for pattern, hooks in self.hooks.items():
            if fnmatch.fnmatch(event_name, pattern):
                # Execute matching hooks for the specified position
                for hook in hooks:
                    if hook.get("position", "after") == position:
                        try:
                            print(f"[{position.upper()}-Hook {hook['id']}] Triggered by {event_name}")
                            result = hook["action"](event_name, event_data)
                            executed.append(hook["id"])
                        except Exception as e:
                            print(f"[Hook {hook['id']}] Error: {e}")
                        
        return executed


