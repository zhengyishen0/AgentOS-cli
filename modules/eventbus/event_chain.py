"""Event Chain execution engine for AgentOS.

This module implements the core event chain execution logic, including:
- Sequential and parallel event execution
- Parameter interpolation between events
- Result storage and propagation
- Error handling and recovery
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union, Type
from datetime import datetime, timezone
from pydantic import BaseModel

from .event_bus import Event, eventbus
from .parameter_interpolator import ParameterInterpolator
from ..providers.thread_manager import thread_manager
from .event_schemas import ChainEventSpec

logger = logging.getLogger(__name__)



@dataclass
class EventChainResult:
    """Result of executing an event chain."""
    thread_id: str
    events: List[ChainEventSpec]
    success: bool
    error: Optional[str] = None
    total_execution_time_ms: float = 0.0


class EventChainExecutor:
    """Executes event chains with parameter interpolation and result propagation."""
    
    def __init__(self):
        self.event_bus = eventbus
        self.thread_manager = thread_manager
        self._interpolator: Optional[ParameterInterpolator] = None
        
    async def execute_chain(
        self,
        chain: List[Union[Dict, List[Dict]]],
        thread_id: str,
    ) -> EventChainResult:
        """Execute an event chain.
        
        Args:
            chain: List of events or parallel event arrays
            thread_id: Thread ID for context
        Returns:
            EventChainResult with all execution details
        """
        # Load thread context if available
        thread_context = {}
        if self.thread_manager:
            thread = await self.thread_manager.get_thread(thread_id)
            if thread:
                thread_context = thread.get_context()
        
        # Create interpolator with context - it owns the context
        self._interpolator = ParameterInterpolator(thread_context)
        
        executed_events: List[ChainEventSpec] = []
        start_time = asyncio.get_event_loop().time()
        
        try:
            for item in chain:
                if isinstance(item, list):
                    # Parallel execution
                    parallel_results = await self._execute_parallel(item, thread_id)
                    executed_events.extend(parallel_results)
                else:
                    # Sequential execution
                    event_result = await self._execute_single(item, thread_id)
                    executed_events.append(event_result)
                    
                    # Check for errors
                    if event_result.error:
                        return EventChainResult(
                            thread_id=thread_id,
                            events=executed_events,
                            success=False,
                            error=f"Event {event_result.event} failed: {event_result.error['message']}",
                            total_execution_time_ms=(asyncio.get_event_loop().time() - start_time) * 1000
                        )
                        
            return EventChainResult(
                thread_id=thread_id,
                events=executed_events,
                success=True,
                total_execution_time_ms=(asyncio.get_event_loop().time() - start_time) * 1000
            )
            
        except Exception as e:
            logger.error(f"Chain execution failed: {e}")
            return EventChainResult(
                thread_id=thread_id,
                events=executed_events,
                success=False,
                error=str(e),
                total_execution_time_ms=(asyncio.get_event_loop().time() - start_time) * 1000
            )
    
    async def _execute_single(self, event_spec: Dict, thread_id: str) -> ChainEventSpec:
        """Execute a single event."""
        start_time = asyncio.get_event_loop().time()
        
        # Create ChainEvent
        chain_event = ChainEventSpec(
            event=event_spec['event'],
            params=event_spec.get('params', {}),
            decide=event_spec.get('decide', None),
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        try:
            # Interpolate parameters
            interpolated_params = await self._interpolate_params(chain_event.params)
            event_schema = eventbus.get_schema(chain_event.event)
            
            # Handle conditional logic
            if chain_event.decide:
                decision = await self._handle_decide(
                    thread_id=thread_id,
                    prompt=chain_event.decide,
                    params=interpolated_params,
                    schema=event_schema
                )
                if decision['action'] == 'skip':
                    chain_event.result = {'skipped': True, 'reason': decision.get('reason')}
                    return chain_event
                elif decision['action'] == 'continue' and 'params' in decision:
                    interpolated_params.update(decision['params'])
            
            # Validate parameters
            try:
                event_schema(**interpolated_params)
            except Exception as e:
                # Trigger agent.decide for parameter completion
                completed_params = await self._complete_params(
                    thread_id=thread_id,
                    params=interpolated_params,
                    schema=event_schema,
                    validation_error=str(e)
                )
                interpolated_params = completed_params
            
            # Publish event and get result
            event = Event(
                type=chain_event.event,
                data={
                    **interpolated_params,
                    '_thread_id': thread_id,
                    '_chain_execution': True
                }
            )
            
            # Wait for event result (this needs enhancement in event_bus.py)
            result = await self._publish_and_wait(event)
            chain_event.result = result
            
            # Store event result in interpolator's context.
            self._interpolator.add_result(chain_event.event, result)
            
        except Exception as e:
            logger.error(f"Event execution failed: {e}")
            chain_event.error = {
                'message': str(e),
                'type': type(e).__name__
            }
            
        chain_event.execution_time_ms = (asyncio.get_event_loop().time() - start_time) * 1000
        return chain_event
    
    async def _execute_parallel(self, events: List[Dict], thread_id: str) -> List[ChainEventSpec]:
        """Execute multiple events in parallel."""
        tasks = [self._execute_single(event, thread_id) for event in events]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        chain_events = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Create error event
                chain_event = ChainEventSpec(
                    event=events[i]['event'],
                    params=events[i].get('params', {}),
                    error={'message': str(result), 'type': type(result).__name__},
                    timestamp=datetime.now(timezone.utc).isoformat()
                )
                chain_events.append(chain_event)
            else:
                chain_events.append(result)
                
        return chain_events
    
    async def _interpolate_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Interpolate parameters with execution context.
        
        Handles patterns like:
        - {tools.now.result}
        - {tools.date_calc.result.date}
        - {team.members[0].result}
        """
        if not self._interpolator:
            return params
            
        return self._interpolator.interpolate(params)
    
    async def _handle_decide(self, thread_id: str, prompt: str, params: Dict[str, Any], schema: dict) -> Dict[str, str]:
        """Handle conditional logic via agent.decide.

        Args:
            prompt: The condition to evaluate
            params: The parameters to pass to the condition
            schema: The json schema of the event being evaluated
        Returns:
            decision: 
                'action': 'continue' or 'skip'
                'params': the updated params
                'reason': 'reason for skipping'
            
        """
        # Placeholder - will integrate with agent.decide
        decision = await self.event_bus.publish(
            event_type='agent.decide',
            data={
                'thread_id': thread_id,
                'prompt': prompt,
                'params': params,
                'schema': schema
            }
        )   
        return decision
    
    async def _complete_params(
        self,
        params: Dict[str, Any],
        schema: dict,
        validation_error: str,
        thread_id: str
    ) -> Dict[str, Any]:
        """Complete missing parameters via agent.decide.
        
        Args:
            params: The parameters to complete
            schema: The json schema of the event being completed
            validation_error: The error message from parameter validation
        
        Returns:
            completed_params: The completed parameters
        """

        decision = await self.event_bus.publish(
            event_type='agent.decide',
            data={
                'thread_id': thread_id,
                'prompt': "Correct the following parameters to match the schema. Current error: " + validation_error,
                'params': params,
                'schema': schema
            }
        )   

        completed_params = decision.get('params', params)  # fallback to original params
        return completed_params
    
    async def _publish_and_wait(self, event: Event) -> Any:
        """Publish event and wait for result.
        
        The event_bus returns:
        - Empty dict if no handlers
        - Direct result if single handler  
        - Dict with handler names as keys if multiple handlers
        
        For EventChain, we typically expect single handlers (function-like events).
        If there are multiple handlers, we'll return the full dict.
        """
        result = await self.event_bus.publish(
            event_type=event.type,
            data=event.data,
            source=event.source
        )
        
        return result

class EventChainBuilder:
    """Helper class to build event chains programmatically."""
    
    def __init__(self):
        self.chain: List[Union[Dict, List[Dict]]] = []
    
    def add_event(self, event: str, params: Optional[Dict] = None, decide: Optional[str] = None):
        """Add a single event to the chain."""
        event_spec = {'event': event}
        if params:
            event_spec['params'] = params
        if decide:
            event_spec['decide'] = decide
        self.chain.append(event_spec)
        return self
    
    def add_parallel(self, *events: Dict):
        """Add parallel events to the chain."""
        self.chain.append(list(events))
        return self
    
    def build(self) -> List[Union[Dict, List[Dict]]]:
        """Build and return the event chain."""
        return self.chain