# AgentOS System Design

This document consolidates the system overview and all key design decisions for AgentOS, including architecture, technology choices, and module specifications.

## What is AgentOS?

Operating system for AI agents that runs locally. Like iOS manages apps, AgentOS manages AI agents - running them locally and keeping them synchronized.

## System Overview

### Core Concept & Benefits

- **Event-Driven Architecture** - Services communicate through events, no direct coupling
- **Multiple specialized agents** working simultaneously with shared knowledge
- **Voice-controlled interaction** with speaker recognition
- **Hot-reloadable plugins** - Workspace capabilities can be updated without restart
- **Local privacy** - Your agents, your data, your rules with file-based storage
- **Core Type Declaration** - Explicit function vs service core types for predictable behavior

### User Experience

**Voice Mode**
```bash
$ agentos chat --voice
🎤 Voice mode enabled
👤 Speaker: John (92% confidence)
📝 "What tasks do I have for today?"
🤖 "You have 3 tasks: Call dentist at 2pm..."
```

**CLI Mode**
```bash
$ agentos chat
local> Can you help me analyze the budget?
[ResearchAgent] I'll create a detailed analysis...
[System] ✅ Task created: "Budget analysis" → ResearchAgent
```

---

## Event-Driven Architecture

### Communication Pattern

```
            EventBus (Message Broker)
           /    |    |    |    \
         CLI   Work  Agent Voice Plugins
```

**All services communicate through EventBus** - no direct service-to-service connections.

### Core Type System

```python
class CoreType(Enum):
    FUNCTION = "function"    # Stateless, pure functions
    SERVICE = "service"      # Stateful, long-running processes

class FunctionCore(CoreBase):
    # Pure functions: agent execution, transcription, knowledge lookup
    
class ServiceCore(CoreBase):
    # Stateful services: real-time audio, task scheduler
    def start(self): ...
    def stop(self): ...
    def health_check(self): ...
```

---

## Module Specifications

### Workspace (Primary Coordinator)

**Purpose**: Central conversation coordinator managing threads and orchestrating all services via EventBus.

**Architecture**: Three-layer with event coordination
```
workspace/
├── core/
│   ├── thread_manager.py     # Thread lifecycle management
│   ├── message_router.py     # Message routing logic
│   └── agent_assignment.py   # Agent-to-thread assignment
├── repository.py             # Thread/message persistence (JSON Lines)
└── service.py                # Socket.IO + Supervisor + EventBus integration
```

**Key APIs**:
- `create_thread(title, agents)` - Create conversation thread
- `assign_agent(thread_id, agent_id)` - Agent assignment
- `route_message(thread_id, message)` - Message processing
- Event publishing: `workspace.message_received`, `workspace.thread_created`

**Technology Stack**: Socket.IO, Supervisor, python-socketio

### Agent Runtime

**Purpose**: Stateless agent execution engine using LiteLLM for universal LLM provider support.

**Architecture**: Three-layer with function cores
```
agent_runtime/
├── core/
│   ├── llm_runtime.py        # LiteLLM execution (FunctionCore)
│   ├── conversation.py       # Conversation processing (FunctionCore)
│   └── handoff.py           # Agent-to-agent handoff (FunctionCore)
├── repository.py            # Agent config hot-loading, lifecycle management
├── wrappers/
│   ├── permission_wrapper.py # Agent permission validation
│   └── tool_wrapper.py       # Available tool checking
└── service.py               # EventBus integration, inter-agent coordination
```

**Core APIs**:
- `execute_conversation(agent, messages, context)` - Process conversation
- `handle_handoff(from_agent, to_agent, context)` - Agent transitions
- `reload_agent(agent_id)` - Hot-reload configuration
- Event handling: `workspace.message_received` → `agent.response_generated`

**Technology Stack**: LiteLLM, Pydantic, watchfiles, asyncio

### Plugins

**Purpose**: Hot-reloadable workspace capabilities including task management and knowledge operations.

**Architecture**: Three-layer with mixed core types
```
plugins/
├── core/
│   ├── task_manager.py       # APScheduler service (ServiceCore)
│   └── knowledge_manager.py  # Markdown operations (FunctionCore)
├── repository.py             # Plugin hot-reload, lifecycle management
└── service.py                # EventBus integration
```

**Core APIs**:
- `reload_plugin(plugin_name)` - Hot-reload without workspace restart
- `execute_plugin(plugin_name, event_data)` - Plugin execution
- Task APIs: `create_task()`, `schedule_reminder()`
- Knowledge APIs: `get_context()`, `extract_knowledge()`
- Event handling: Multiple workspace events → plugin-specific results

**Technology Stack**: APScheduler, watchfiles, importlib

### CLI Interface

**Purpose**: Terminal interface for workspace management and system administration.

**Architecture**: Three-layer with function cores
```
cli_interface/
├── core/
│   ├── command_processor.py  # Command parsing engine (FunctionCore)
│   ├── admin_commands.py    # Administrative functions (FunctionCore)
│   └── user_commands.py     # User interaction functions (FunctionCore)
├── repository.py            # CLI feature toggles, active/disabled functions
└── service.py               # EventBus integration
```

**Core Commands**:
- `agentos chat` - Interactive conversation
- `agentos workspace create/list/switch` - Workspace management
- `agentos agent load/remove/status` - Agent management
- `agentos plugins reload/install/disable` - Plugin management
- `agentos monitor` - Real-time system monitoring

**Technology Stack**: Typer, Rich, EventBus

### Voice Interface

**Purpose**: Multi-modal voice interaction with speaker recognition and real-time audio processing.

**Architecture**: Three-layer with mixed core types
```
voice_interface/
├── core/
│   ├── transcription.py      # Whisper integration (FunctionCore)
│   ├── speaker_recognition.py # PyAnnote speaker ID (FunctionCore)
│   └── realtime_audio.py     # OpenAI Realtime API (ServiceCore)
├── repository.py             # Speaker profile management, embedding updates
└── service.py                # EventBus integration, real-time coordination
```

**Core APIs**:
- `transcribe_audio(audio_data)` - Speech-to-text processing
- `identify_speaker(audio_data)` - Speaker recognition with confidence
- `process_realtime_audio()` - Continuous audio stream processing
- `register_speaker(name, audio_sample)` - Add speaker profile
- Event handling: `voice.audio_received` → `workspace.message_received`

**Technology Stack**: OpenAI Realtime API, PyAnnote.audio, sounddevice, asyncio

---

## Event Communication Patterns

### EventBus Implementation
```python
class EventBus:
    async def publish(self, event_type: str, data: dict): ...
    async def subscribe(self, event_type: str, handler: Callable): ...
```

### Core Event Types
- **Workspace**: `workspace.message_received`, `workspace.thread_created`
- **Agent**: `agent.response_generated`, `agent.handoff_requested`
- **Voice**: `voice.audio_received`, `voice.speaker_identified`
- **Plugin**: `plugin.task_created`, `plugin.knowledge_updated`
- **CLI**: `cli.command_executed`, `cli.workspace_switched`

### Example Event Flow
1. **Voice Input** → Voice Interface transcribes → `voice.audio_received`
2. **Workspace** handles event → adds to thread → `workspace.message_received`
3. **Agent Runtime** processes → generates response → `agent.response_generated`
4. **Plugins** extract tasks/knowledge → `plugin.task_created`
5. **Workspace** updates thread → broadcasts to connected clients

---

## File Organization Standards

### Module Structure
```
{module_name}/
├── core/                    # Core functionality (functions or services)
│   ├── __init__.py
│   └── {specific_cores}.py
├── repository.py            # Data persistence and lifecycle
├── wrappers/               # Cross-cutting concerns (optional)
│   └── {wrapper_name}.py
├── service.py              # EventBus integration and coordination
└── demo.py                 # Standalone demonstration
```

### Storage Structure
```
data/
├── workspaces/
│   └── {workspace_name}/
│       ├── threads/
│       │   └── {thread_id}.jsonl    # Message history
│       └── metadata.yaml            # Workspace configuration
├── agents/
│   └── {agent_name}.yaml           # Agent configurations
├── plugins/
│   └── {plugin_name}/
│       ├── config.yaml
│       └── data/
└── knowledge/
    ├── contacts.md                 # People and relationships
    ├── facts.md                    # Important information
    ├── procedures.md               # How-to guides
    └── journal/
        └── {date}.md               # Daily summaries
```

---

## Development Standards

### Technology Requirements
- **Python 3.11+** for modern async/await patterns
- **Type hints** mandatory for all public APIs
- **Pydantic** for data validation at module boundaries
- **Structured logging** using structlog
- **File-based storage** only - no databases
- **Project-wide pyproject.toml** for dependency management

### Testing Strategy
- **Function cores**: Pure unit tests with no I/O
- **Service cores**: Integration tests with mock dependencies
- **Event flows**: End-to-end tests through EventBus
- **Plugin system**: Hot-reload and lifecycle tests

### Quality Standards
- **Type checking**: mypy strict mode
- **Code formatting**: black + ruff
- **Coverage**: >90% for core functionality
- **Documentation**: Detailed docstrings for all public APIs

### Git Workflow
- Branch naming: `module/{module-name}`
- Commit format: `module: Short description`
- Progress tracking: Update project status after milestones

---

## Getting Started

1. **Understand the event-driven architecture** - All communication flows through EventBus
2. **Choose a module** from the specifications above
3. **Implement core type interface** - Declare function vs service cores
4. **Build EventBus integration** - Subscribe to relevant events, publish results
5. **Test independently** - Each module should work in isolation

This system design emphasizes simplicity, transparency, and proven technologies while providing a flexible foundation for AI agent coordination and management.