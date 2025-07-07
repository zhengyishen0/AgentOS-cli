import asyncio
from modules.handlers.agent_handlers import agent_decide, agent_think, agent_chain
from modules.eventbus.event_bus import Event
from modules.eventbus.event_schemas import AgentThinkInput
from pprint import pprint
from modules import eventbus

prompt_think = """
find the top 3 links about llm and read them and then recall the memory about the llm, 
provide an updated verison of llm study, and update the memory
"""

prompt_chain = """
'- Search for the top 3 links related to LLMs.\n'
'- Read each link and extract relevant information.\n'
'- Recall any existing memory about LLMs.\n'
'- Generate an updated study report on LLMs.\n'
'- Update the memory with the new information.'}}
"""

event_think = Event(
    type="agent.think",
    data={
        "thread_id": "thread_20250705_164835_149647",
        "prompt": prompt_think,
    },
)

event_chain = Event(
    type="agent.chain",
    data={
        "thread_id": "thread_20250705_164835_149647",
        "message": prompt_chain,
    },
)

new_think_prompt = """
you will create a fake convesation, starting with a ramdom word. Then you will pass the a word to the next one and ask it to extend with another word, and so on.
the last agent will be ask to repeat the whole conversation without been told the previous conversation.
"""

new_think_event = Event(
    type="agent.think",
    data={
        "thread_id": "thread_20250705_164835_149647",
        "prompt": new_think_prompt,
    },
)

# Run tests
# asyncio.run(agent_chain(event_chain))
# asyncio.run(agent_think(event_think))
asyncio.run(agent_think(new_think_event))

# pprint(eventbus.list_schemas(brief=True))
