"""Event Chain execution engine for AgentOS.

This module implements the core event chain execution logic, including:
- Sequential and parallel event execution
- Parameter interpolation between events
- Result storage and propagation
- Error handling and recovery
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union, Type
from pydantic import BaseModel
from .models import Event, ExecutionResult
from .interpolator import ParameterInterpolator


logger = logging.getLogger(__name__)


class EventChainExecutor:
    """Executes event chains with parameter interpolation and result propagation."""
    
    def __init__(self, event_bus=None, thread_manager=None):
        self.event_bus = event_bus
        self.thread_manager = thread_manager
        self._interpolator: Optional[ParameterInterpolator] = None
        
    async def execute_chain(
        self,
        chain: List[Union[Event, List[Event]]],
        thread_id: str,
    ) -> ExecutionResult:
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
        
        executed_events: List[Event] = []
        start_time = asyncio.get_event_loop().time()
        
        try:
            for event_task in chain:
                if isinstance(event_task, list):
                    # Parallel execution
                    parallel_results = await self._execute_parallel(event_task, thread_id)
                    executed_events.extend(parallel_results)
                else:
                    # Sequential execution
                    event_result = await self._execute_single(event_task, thread_id)
                    executed_events.append(event_result)
                    
                    # Check for errors
                    if event_result.error:
                        return ExecutionResult(
                            thread_id=thread_id,
                            events=executed_events,
                            success=False,
                            error=f"Event {event_result.name} failed: {event_result.error}",
                            total_execution_time_ms=(asyncio.get_event_loop().time() - start_time) * 1000
                        )
                        
            return ExecutionResult(
                thread_id=thread_id,
                events=executed_events,
                success=True,
                total_execution_time_ms=(asyncio.get_event_loop().time() - start_time) * 1000
            )
            
        except Exception as e:
            logger.error(f"Chain execution failed: {e}")
            return ExecutionResult(
                thread_id=thread_id,
                events=executed_events,
                success=False,
                error=str(e),
                total_execution_time_ms=(asyncio.get_event_loop().time() - start_time) * 1000
            )
    
    async def _execute_single(self, event: Event, thread_id: str) -> Event:
        """Execute a single event."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Interpolate parameters
            print(f"chain_event.data: {event.data}")
            interpolated_params = await self._interpolate_params(event.data)
            print(f"interpolated_params: {interpolated_params}")
            try:
                # Get the actual Pydantic model class, not the JSON schema
                event_schema = self.event_bus._schemas.get(event.name)
            except Exception as e:
                print(f"Error getting schema for {event.name}: {e}")
                event_schema = None
        
            # Handle conditional logic
            if event.data.get('decide'):
                decision = await self._handle_decide(
                    thread_id=thread_id,
                    prompt=event.data['decide'],
                    params=interpolated_params,
                    event=event
                )
                if decision['action'] == 'skip':
                    event.result = {'skipped': True, 'reason': decision.get('reason')}
                    event.status = "completed"
                    return event
                elif decision['action'] == 'continue' and 'params' in decision:
                    interpolated_params.update(decision['params'])
            
            # Validate parameters
            try:
                event_schema(**interpolated_params)
            except Exception as e:
                print(f"Validation failed for {event.name}: {e}")
                print(f"Params: {interpolated_params}")
                # Trigger agent.decide for parameter completion
                completed_params = await self._complete_params(
                    params=interpolated_params,
                    event_name=event.name,
                    validation_error=str(e),
                    thread_id=thread_id
                )
                print(f"Completed params: {completed_params}")
                interpolated_params = completed_params
            
            # Handle special "current" thread_id replacement
            if 'thread_id' in interpolated_params and interpolated_params['thread_id'] == "current":
                interpolated_params['thread_id'] = thread_id
            
            # Update event data with interpolated params
            # Ensure we preserve the validated structure
            event.data = interpolated_params.copy()

            # Wait for event result (this needs enhancement in event_bus.py)
            result = await self._publish_and_wait(event)
            event.result = result
            
            # Store event result in interpolator's context.
            self._interpolator.add_result(event.name, result)
            
        except Exception as e:
            logger.error(f"Event execution failed: {e}")
            event.error = str(e)
            event.status = "failed"
            
        event.execution_time_ms = (asyncio.get_event_loop().time() - start_time) * 1000
        return event
    
    async def _execute_parallel(self, events: List[Event], thread_id: str) -> List[Event]:
        """Execute multiple events in parallel."""
        tasks = [self._execute_single(event, thread_id) for event in events]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        chain_events = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Create error event
                chain_event = Event(
                    name=events[i].name,
                    data=events[i].data,
                    error=str(result),
                    status="failed",
                    source="chain"
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
    
    async def _handle_decide(self, thread_id: str, prompt: str, params: Dict[str, Any], event: Event) -> Dict[str, str]:
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
            name='agent.decide',
            data={
                'thread_id': thread_id,
                'prompt': prompt,
                'params': params,
                'event_name': event.name
            }
        )   
        return decision
    
    async def _complete_params(
        self,
        params: Dict[str, Any],
        event_name: str,
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
            name='agent.decide',
            data={
                'thread_id': thread_id,
                'prompt': "Correct the following parameters to match the schema. Current error: " + validation_error,
                'params': params,
                'event_name': event_name
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
            name=event.name,
            data=event.data,
            source=event.source
        )
        
        return result