# AgentOS: Event-Driven Thread-Passing Architecture

## Executive Summary

AgentOS is a revolutionary approach to AI agent systems that treats everything as event-driven services. Instead of complex orchestration, threads (conversations with context) flow through the system like a ball being passed between players, with each service processing and forwarding as needed.

## Core Philosophy

### Thread-Passing Over Orchestration
- No central orchestrator controlling agents
- Threads flow through the system finding their own path
- Like a jazz band vs classical orchestra - emergent coordination

### Everything is an Event-Driven Service
- Agents, tools, and routers are all just services
- Communicate exclusively through EventBus
- No direct connections or dependencies

### Stateless LLMs as Functions
- LLMs are pure functions, not stateful sessions
- Context lives in threads, not in agent memory
- Enables running 100+ micro-agents efficiently

## Architecture Overview

```
┌─────────────────── AgentOS Runtime ───────────────────┐
│                                                       │
│  ┌─────────── Thread Flow System ─────────┐          │
│  │                                         │          │
│  │   Thread     Event      Service         │          │
│  │   Pool   →   Bus    →  Registry         │          │
│  │                                         │          │
│  └─────────────────────────────────────────┘          │
│                        ↕                              │
│  ┌─────────── Unified Service Layer ──────┐          │
│  │                                         │          │
│  │  All Services (Agents & Tools)          │          │
│  │  Subscribe to: use.* or need.* events   │          │
│  └─────────────────────────────────────────┘          │
│                        ↕                              │
│  ┌─────────── Interface Layer ─────────┐             │
│  │  CLI │ Voice │ API │ File Watch     │             │
│  └──────────────────────────────────────┘             │
└───────────────────────────────────────────────────────┘
```

## Key Concepts

### 1. Thread as First-Class Citizen

```python
class Thread:
    """The context that flows through the system"""
    - id: Unique identifier
    - messages: Full conversation history
    - metadata: Workflow state and preferences
    - trajectory: Path through agents
    - status: Active/Waiting/Complete
```

Threads carry all context, eliminating the need for separate state management.

### 2. Event Direction Pattern

Every event has a clear direction:
- **FORWARD**: Pass to another service
- **BACKWARD**: Return to sender
- **END**: Thread complete

Rules:
- Only routers can create threads (initial forward)
- Only routers can end threads (final end)
- Tools (need.*) can only send backward
- Agents (use.*) can send forward or backward

### 3. Unified Service Pattern

All services follow the same pattern:

```python
class Service:
    def __init__(self, name):
        # Subscribe to invocation
        eventbus.subscribe(f"use.{name}", self.handle)
        # Subscribe to needs
        for need in self.capabilities:
            eventbus.subscribe(f"need.{need}", self.handle_need)
```

No distinction between agents and tools at the architecture level.

### 4. Tool Calling via Structured Events

LLMs output structured tool calls as events:
```json
{
    "event": "need.email.send",
    "data": {
        "to": ["john@example.com"],
        "subject": "Meeting Tomorrow",
        "body": "Let's meet at 2pm"
    }
}
```

Tools require rigid schemas (Pydantic validation) for reliability.

## Event Flow Examples

### Simple Flow
```
User: "What's the weather?"

1. CLI → publish("use.agent_router", thread)
2. Router → publish("need.weather", {location: "NYC"})  
3. WeatherTool → publish(BACKWARD, weather_data)
4. Router → publish(END, "It's 72°F and sunny in NYC")
```

### Complex Flow with Parallel Processing
```
User: "Research AI news and email summary to team"

1. Router → use.parallel_executor
2. Parallel → Spawns multiple searches:
   - need.web_search
   - need.academic_search  
   - need.news_search
3. Tools → BACKWARD results to parallel_executor
4. Parallel → BACKWARD aggregated results
5. Router → use.summary_agent
6. Summary → BACKWARD summary text
7. Router → use.email_composer
8. Email → need.email.send
9. EmailTool → BACKWARD confirmation
10. Router → END "Summary sent to team"
```

## Key Components

### EventBus
- Pub/sub message broker for all communication
- No explicit service registry (services self-register)
- Subscription modes:
  - Exclusive (use.*): One handler
  - Broadcast (need.*): Multiple handlers
- Enables parallel processing and complete decoupling

### Service Types

#### Routers
- **agent_router**: Main entry point, routes threads
- **parallel_executor**: Handles parallel task execution
- Can have specialized routers (email_router, research_router)

#### Core Agents (Micro-Services)
- **intent_classifier**: Understands user intent
- **context_builder**: Enriches thread with memories
- **summary_agent**: Summarizes content
- **email_composer**: Composes emails
- **task_extractor**: Finds tasks in conversations

#### Core Tools
- **search_service**: Web and local search
- **email_service**: Send/receive emails
- **calendar_service**: Calendar operations
- **file_service**: File I/O operations
- **memory_service**: Persistent storage

### Thread Management
- Threads maintain their own state
- Can branch for parallel processing
- Self-determine completion
- Full trajectory tracking for debugging

## Implementation Patterns

### Service Implementation
```python
@eventbus.subscribe("use.summary_agent")
async def summary_agent(event_data):
    thread = Thread.from_dict(event_data["thread"])
    
    # Process with LLM
    summary = await llm.generate(f"Summarize: {thread.content}")
    
    # Add to thread
    thread.add_message("summary", summary)
    
    # Route appropriately
    if thread.needs_more_processing():
        await publish_forward(next_agent, thread)
    else:
        await publish_backward(event_data["return_to"], result)
```

### Parallel Processing
```python
await eventbus.publish("use.parallel_executor", {
    "tasks": [
        {"event": "need.search", "params": {"query": "AI news"}},
        {"event": "need.weather", "params": {"location": "NYC"}},
        {"event": "use.summary_agent", "params": {"content": text}}
    ],
    "return_to": "use.agent_router"
})
```

### Multiple Router Pattern
- Main router for general requests
- Specialized routers for domains (email, research, etc.)
- Routers can invoke each other
- Enables A/B testing of routing strategies

## Key Advantages

### 1. Swarm Intelligence
- 100+ micro-agents vs one complex agent
- Each agent does one thing well
- Intelligence emerges from interactions

### 2. Complete Decoupling
- Services don't know about each other
- Add/remove services without changing others
- Natural fault isolation

### 3. Natural Parallelism
- Events enable parallel processing
- No complex coordination needed
- Automatic load distribution

### 4. Debugging & Observability
- Follow thread trajectory
- Replay event sequences
- Time-travel debugging possible

### 5. Scalability
- Stateless services scale horizontally
- Event queuing handles load spikes
- Resource-efficient micro-agents

## Comparison with Traditional Approaches

### vs. LangChain/AutoGPT
- **Focus**: Orchestration vs making LLMs smarter
- **Architecture**: Event-driven vs sequential chains
- **State**: In threads vs in agents
- **Scaling**: Micro-agents vs monolithic agents

### vs. Classic Tool Use
- **Execution**: Async events vs direct calls
- **Coupling**: Loose vs tight
- **Handlers**: Multiple vs single
- **Context**: Thread-aware vs parameter-only

## Design Principles

1. **Stateless by Default**: Agents don't maintain session state
2. **Event-Driven Communication**: All interaction via EventBus
3. **Thread-Centric Context**: Threads carry all necessary context
4. **Micro-Agent Philosophy**: Many simple agents over few complex ones
5. **Natural Language Routing**: Agents communicate intent naturally
6. **Rigid Tool Contracts**: Tools require validated schemas
7. **Emergent Intelligence**: Complex behavior from simple rules

## Implementation Roadmap

### Phase 1: Core Infrastructure
- EventBus implementation
- Thread management system  
- Basic agent_router
- 5-10 essential services
- CLI interface

### Phase 2: Service Expansion
- Parallel executor
- Specialized routers
- 20-30 domain services
- Memory persistence
- Voice interface

### Phase 3: Advanced Features
- Service discovery
- Dynamic loading
- Distributed deployment
- Performance optimization
- Community marketplace

## Conclusion

AgentOS represents a paradigm shift in AI agent architectures. By treating everything as event-driven services and using thread-passing instead of orchestration, it enables true swarm intelligence while maintaining simplicity, debuggability, and scalability.

The key insight: **Intelligence emerges from the interaction patterns of simple services, not from complex individual agents.**