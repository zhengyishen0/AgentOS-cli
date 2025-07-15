## Most Important Rules

1. Always aim for small wins rather than big shots.
2. Make sure you use use cases for testing, not traditional unit tests.

## General Rules

1. we use `uv` for package management, always use `uv add`to install packages, and `uv run` to run scripts. other commands in `uv` are also preferred.
2. do not code unless the user asks to.
3. always spin up subagents for multiple tasks that can be done in parallel, like reading 10 urls or read 5 code scripts, etc.
4. always write pseudo codes (classes and function with only names, parameters, and descriptions but no real implementations ) first and explain your pseudo codes to the user and get approval before writing real implementation codes.
5. always create temperary test codes to make sure each function and class work as described.

## AgentOS EventChain Architecture Progress

### Completed Components:

1. **modules/eventbus/** - Core event infrastructure organized in dedicated folder
   - `event_bus.py` - Basic pub/sub system with validation (existing)
   - `event_registry.py` - Schema registration with Pydantic (existing)
   - `event_chain.py` - Event chain execution engine (new)
   - `parameter_interpolator.py` - Parameter interpolation engine (new)
   - `thread_manager.py` - Thread persistence and management (new)

### Architecture Overview:

- **EventChain**: Everything flows through event chains - sequential or parallel
- **Threads**: Persistent event chains with full context and history
- **Three-Model Strategy**: Heavy (think), Fast (chain), Ultra-light (decide)
- **Parameter Flow**: Results flow between events via interpolation ({event.result})
