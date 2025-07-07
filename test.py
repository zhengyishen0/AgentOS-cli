import asyncio
from modules.handlers.agent_handlers import agent_think
from modules.eventbus.event_bus import Event

event = Event(
    type="agent.think",
    data={
        "thread_id": "thread_20250705_164835_149647",
        "prompt": "what did we just talk about?"
    },
)

asyncio.run(agent_think(event))