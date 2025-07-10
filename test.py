import asyncio
from modules.handlers.agent_handlers import agent_decide, agent_think, agent_chain
from modules.eventbus.event_bus import Event
from modules.eventbus.schemas import AgentThinkInput
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
        "thread_id": "thread_20250710_123000_7caf52",
        "prompt": prompt_think,
    },
)

event_chain = Event(
    type="agent.chain",
    data={
        "thread_id": "thread_20250710_123000_7caf52",
        "message": prompt_chain,
    },
)

new_think_prompt = """
you will create a series of convesation with agent.think, ask the first agent.think to come up with a ramdom word and pass it to the next one.
The agent.think will get the word from the previous agent.think and extend one more word after it, and then pass the a word to the next one.
The convesation continues to the third agent.think and do the same.
the last agent will be ask to repeat the whole conversation without been told the previous conversation.
"""

new_think_event = Event(
    type="agent.think",
    data={
        "thread_id": "thread_20250710_123000_7caf52",
        "prompt": new_think_prompt,
    },
)

new_chain_prompt = """
1. call agent.think with the prompt: "you are a helpful assistant"
2. call agent.chain with the prompt: "tell a joke'"
3. call agent.think with the prompt: "do you like apple or orange?"
"""

new_chain_event = Event(
    type="agent.chain",
    data={
        "thread_id": "thread_20250710_123000_7caf52",
        "message": new_chain_prompt,
    },
)

# Run tests
# asyncio.run(agent_chain(event_chain))
# asyncio.run(agent_think(event_think))
asyncio.run(agent_think(new_think_event))
# asyncio.run(agent_chain(new_chain_event))


# pprint(eventbus.list_schemas(brief=True))

# print(eventbus.get_schema("agent.think"))
