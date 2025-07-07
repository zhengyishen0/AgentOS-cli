import asyncio
from modules.handlers.agent_handlers import agent_decide, agent_think
from modules.eventbus.event_bus import Event



# Test 1: Basic parameter completion with context
event_decide_1 = Event(
    type="agent.decide",
    data={
        "thread_id": "thread_20250705_164835_149647",
        "prompt": "",
        "params": {"name": "Alice"},
        "event_schema": {"name": {"type": "string"}, "age": {"type": "integer"}}
    },
)

# Test 2: Missing required parameters with context
event_decide_2 = Event(
    type="agent.decide",
    data={
        "thread_id": "thread_20250705_164835_149647",
        "prompt": "A new user is trying to register but only provided their email. The system requires both name and age. Can we proceed or should we skip?",
        "params": {},
        "event_schema": {"name": {"type": "string"}, "age": {"type": "integer"}}
    },
)


# Run tests
print("=== Test 1: Basic parameter completion with context ===")
print("Expected: {'action': 'continue', 'params': {'name': 'Alice', 'age': 25}, 'reason': 'Parameters can be completed'}")
result = asyncio.run(agent_decide(event_decide_1))
print(result)

print("\n=== Test 2: Missing required parameters with context ===")
print("Expected: {'action': 'skip', 'params': {}, 'reason': 'Required parameters cannot be completed'}")
result = asyncio.run(agent_decide(event_decide_2))
print(result)

