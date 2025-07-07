import asyncio
from modules.handlers.agent_handlers import agent_decide, agent_think
from modules.eventbus.event_bus import Event
from modules.eventbus.event_schemas import AgentThinkInput
from pprint import pprint
from modules import eventbus

event_think = Event(
    type="agent.think",
    data={
        "thread_id": "thread_20250705_164835_149647",
        "prompt": "find the top 20 links about llm and read them and then recall the memory about the llm, provide an updated verison of llm study, and update the memory",
    },
)

# Run tests
asyncio.run(agent_think(event_think))

# pprint(eventbus.list_schemas(brief=True))
