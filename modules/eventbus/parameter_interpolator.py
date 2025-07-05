"""Parameter interpolation engine for event chains.

Handles complex parameter references like:
- {tools.now.result}
- {tools.date_calc.result.date}
- {team.members[0].result}
- {thread.xxx.analysis}
"""

import re
import logging
from typing import Any, Dict, List, Optional, Union
import json

logger = logging.getLogger(__name__)


class ParameterInterpolator:
    """Interpolates parameters with values from execution context."""
    
    # Regex pattern to match interpolation expressions
    # Matches: {path.to.value}, {path[0].value}, {path.to[index].value}
    INTERPOLATION_PATTERN = re.compile(r'\{([^}]+)\}')
    
    def __init__(self, context: Dict[str, Any]):
        """Initialize with execution context.
        
        Args:
            context: Dictionary containing execution results and thread data
        """
        self.context = context
    
    def interpolate(self, value: Any) -> Any:
        """Recursively interpolate a value.
        
        Args:
            value: Value to interpolate (can be string, dict, list, etc.)
            
        Returns:
            Interpolated value
        """
        if isinstance(value, str):
            return self._interpolate_string(value)
        elif isinstance(value, dict):
            return {k: self.interpolate(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self.interpolate(item) for item in value]
        else:
            # Primitive values pass through unchanged
            return value
    
    def _interpolate_string(self, text: str) -> Union[str, Any]:
        """Interpolate a string value.
        
        If the entire string is a single interpolation expression,
        return the actual value (not stringified).
        Otherwise, replace all expressions with their string representations.
        """
        matches = list(self.INTERPOLATION_PATTERN.finditer(text))
        
        # Special case: entire string is a single expression
        if len(matches) == 1 and matches[0].group(0) == text:
            path = matches[0].group(1)
            try:
                return self._resolve_path(path)
            except Exception as e:
                logger.warning(f"Failed to resolve path '{path}': {e}")
                return text
        
        # Multiple expressions or partial string
        def replace_match(match):
            path = match.group(1)
            try:
                value = self._resolve_path(path)
                # Convert to string for embedding
                if isinstance(value, (dict, list)):
                    return json.dumps(value)
                return str(value)
            except Exception as e:
                logger.warning(f"Failed to resolve path '{path}': {e}")
                return match.group(0)  # Keep original on error
        
        return self.INTERPOLATION_PATTERN.sub(replace_match, text)
    
    def _resolve_path(self, path: str) -> Any:
        """Resolve a dot/bracket notation path in the context.
        
        Args:
            path: Path like "tools.now.result" or "team.members[0].name"
            
        Returns:
            Resolved value
            
        Raises:
            KeyError: If path cannot be resolved
        """
        # Parse the path into segments
        segments = self._parse_path(path)
        
        # Navigate through context
        current = self.context
        for segment in segments:
            if isinstance(segment, int):
                # Array index
                if not isinstance(current, list) or segment >= len(current):
                    raise KeyError(f"Invalid array index {segment} in path '{path}'")
                current = current[segment]
            else:
                # Object key
                if not isinstance(current, dict) or segment not in current:
                    raise KeyError(f"Key '{segment}' not found in path '{path}'")
                current = current[segment]
        
        return current
    
    def _parse_path(self, path: str) -> List[Union[str, int]]:
        """Parse a path into segments.
        
        Examples:
            "tools.now.result" -> ["tools", "now", "result"]
            "team.members[0]" -> ["team", "members", 0]
            "data[0].items[1].name" -> ["data", 0, "items", 1, "name"]
        """
        segments = []
        current_segment = ""
        
        i = 0
        while i < len(path):
            char = path[i]
            
            if char == '.':
                if current_segment:
                    segments.append(current_segment)
                    current_segment = ""
            elif char == '[':
                if current_segment:
                    segments.append(current_segment)
                    current_segment = ""
                # Find matching ]
                j = i + 1
                while j < len(path) and path[j] != ']':
                    j += 1
                if j >= len(path):
                    raise ValueError(f"Unmatched '[' in path '{path}'")
                # Extract index
                index_str = path[i+1:j]
                try:
                    index = int(index_str)
                    segments.append(index)
                except ValueError:
                    raise ValueError(f"Invalid array index '{index_str}' in path '{path}'")
                i = j  # Skip to ]
            else:
                current_segment += char
            
            i += 1
        
        if current_segment:
            segments.append(current_segment)
        
        return segments
    
    def add_result(self, event_name: str, result: Any):
        """Add an event result to the context.
        
        Args:
            event_name: Name like "tools.now" or "email.search"
            result: Result value to store
        """
        parts = event_name.split('.')
        
        # Navigate/create nested structure
        current = self.context
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        # Store result
        current[parts[-1]] = {'result': result}
    
    def has_interpolations(self, value: Any) -> bool:
        """Check if a value contains any interpolation expressions.
        
        Args:
            value: Value to check
            
        Returns:
            True if interpolations found
        """
        if isinstance(value, str):
            return bool(self.INTERPOLATION_PATTERN.search(value))
        elif isinstance(value, dict):
            return any(self.has_interpolations(v) for v in value.values())
        elif isinstance(value, list):
            return any(self.has_interpolations(item) for item in value)
        return False


def create_interpolator(thread_context: Optional[Dict[str, Any]] = None) -> ParameterInterpolator:
    """Create a parameter interpolator with initial context.
    
    Args:
        thread_context: Optional thread-specific context
        
    Returns:
        ParameterInterpolator instance
    """
    context = thread_context or {}
    return ParameterInterpolator(context)