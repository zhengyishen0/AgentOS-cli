# AgentOS CLI - Event-Driven AI Agent System

A revolutionary event-driven architecture for AI agents that treats everything as services communicating through events.

## Quick Start - Hello World Demo

### Prerequisites
- Python 3.11+
- OpenAI API key

### Installation
```bash
# Install dependencies
pip install -e .
# or
pip install -r requirements.txt
```

### Running the Event-Driven Hello World

1. Set your OpenAI API key:
```bash
export OPENAI_API_KEY='your-api-key-here'
```

2. Run the demo:
```bash
python run_hello.py
```

3. Start chatting! Type messages and see the AI respond through events.

### How It Works

The demo showcases the event-driven architecture:

1. **User types a message** í CLI publishes `user.message` event
2. **LLM Agent receives event** í Processes through OpenAI API
3. **LLM Agent publishes response** í Sends `llm.response` event
4. **CLI receives and displays** í Shows the AI response

No direct coupling - everything flows through the event bus!

### Architecture

```
User Input í CLI í Event Bus í LLM Agent í OpenAI
                        ì
                  Event Bus
                        ì
User Display ê CLI ê Event Bus ê LLM Agent
```

### Event Types

- `user.message` - User sends a message
- `llm.response` - AI responds
- `system.ready` - System initialized
- `system.error` - Error occurred

### Next Steps

This is just the beginning! The full AgentOS will support:
- Multiple agents working in parallel
- Voice input/output
- Plugin system
- Knowledge management
- And much more!

See `docs/` for the complete architecture vision.