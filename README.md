# AgentOS CLI - Event-Driven AI Agent System

A revolutionary event-driven architecture for AI agents that treats everything as services communicating through events.


### Architecture

```
User Input � CLI � Event Bus � LLM Agent � OpenAI
                        �
                  Event Bus
                        �
User Display � CLI � Event Bus � LLM Agent
```

### Event Types

- `user.message` - User sends a message
- `llm.response` - AI responds
- `system.ready` - System initialized
- `system.error` - Error occurred

### AgentOS vs Claude Code: Key Differences

1. claude code is agentic, building everything around the agent; agentos is context centric. so no worry about shut down sessions or thread/context switch
2. claude code is essentially sequencial but also parallel capable; agentos is essentially parallel but operates in a sequencial way in most cases
3. claude code is "work w/ you" although it clain the abilty to run autonomously while agentos is "work w/o you" as the trigger system (the task ability) let it run by itself
4. the main use case of claude code is "focus mode" while agentos is "ambient mode"

### AgentOS in the Trend of Operation System Revolution

```
   CLI      ->      Windows      ->      iOS      ->     AgentOS
    |                  |                  |                 |
keyboard             mouse           touch screen     thought(voice)
```