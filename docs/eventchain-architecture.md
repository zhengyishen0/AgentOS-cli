# AgentOS Event Chain Architecture

## Core Concept
Everything in the system is an **action** that communicates through event chains. Instead of complex orchestration, threads (containing full context and history) flow through the system via chains of events.

## Key Components

### 1. Thread Structure
Threads are event chains that maintain conversation context:
```json
{
    "thread_id": "xxx",
    "summary": "Discussing Q1 budget review with Sarah, scheduling follow-up tasks",
    "status": "active|archived",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:35:00Z",
    "events": [
        {"event": "user.input", "result": {"text": "Check Sarah's budget emails"}, "timestamp": "2024-01-15T10:30:00Z"},
        {"event": "thread.match", "result": {"action": "continue", "thread_id": "xxx"}, "timestamp": "2024-01-15T10:30:01Z"},
        {"event": "agent.think", "result": {"event": "agent.chain", "params": {"plan": "search emails then create task"}}, "timestamp": "2024-01-15T10:30:02Z"},
        {"event": "email.search", "result": {"matches": [...]}, "timestamp": "2024-01-15T10:30:03Z"},
        // ... more events with results
    ]
}
```

### 2. Entry Flow
Every user interaction starts with thread.match determining the context:
```python
User input → thread.match → returns thread_id → agent.think
```

### 3. Core Agents & Model Selection

**agent.think** (Heavy Model - Claude/GPT-4)
- Strategic planning - creates detailed step-by-step plans
- Complex reasoning about user intent
- Knows available capabilities (names + descriptions only)
- Params: 
  - `{"thread_id": "xxx"}` - for initial thinking
  - `{"thread_id": "xxx", "prompt": "specific analysis task"}` - for mid-chain reasoning
- Returns either:
  - `{"event": "agent.reply", "params": {"message": "..."}}` for direct responses
  - `{"event": "agent.chain", "params": {"plan": "detailed pseudocode-like plan"}}` for complex tasks

**agent.chain** (Fast Model - Mistral/Llama)
- Mechanical translation - converts natural language plans → executable chains
- Has full event schema knowledge
- No complex reasoning, just pattern matching
- Params: `{"plan": "step-by-step plan from agent.think"}`
- Returns: `{"chain": [...]}`
- Always appends 'agent.think' at chain end

**agent.decide** (Ultra-light Model - Phi/TinyLlama)
- Tactical parameter completion and simple decisions
- Invoked automatically when:
  - Event parameters fail schema validation
  - Event includes `"decide": "condition"` parameter
- Returns only:
  - `{"action": "continue", "params": {...}}`
  - `{"action": "skip"}`
  - `{"action": "break"}`

### 4. Core Tools/Events

**Thread Management**
- `thread.match` - Determines which thread a message belongs to
  - Params: `{"message": "...", "thread_id": "xxx"}` (thread_id optional)
  - Returns one of:
    - `{"action": "continue", "thread_id": "xxx"}` - fits current thread
    - `{"action": "suggest_switch", "thread_id": "yyy", "reason": "..."}` - better match found
    - `{"action": "new", "thread_id": "new_xxx"}` - created new thread
  
- `thread.summarize` - Updates thread summary
  - Params: `{"thread_id": "xxx"}`
  - Automatically called after each chain execution
  - Updates summary and updated_at timestamp

**Memory Operations**
- `memory.append` - Adds to daily journal with keywords
  - Params: `{"thread_id": "xxx", "content": "..."}`
  - Extracts keywords during append
- `memory.search` - Searches across journals/knowledge
  - Params: `{"query": "...", "scope": "recent|all", "type": "journal|people|project|any"}`
  - Returns: `{"matches": [...]}`
- `memory.digest` - Processes journals into organized knowledge
  - Params: `{"period": "daily|weekly"}`
  - Extracts: people, projects, preferences, passwords, etc.

**Task Management**
- `task.schedule` - Creates all types of tasks
  - Time-based: `{"type": "once|repeat|delay", "at": "datetime", "interval": "...", "action": [...]}`
  - Returns: `{"task_id": "xxx"}`
- `task.register` - Hook-based task registration
  - Params: `{"trigger": "pre|post:event.name", "condition": "...", "action": [...]}`
- `task.list` - Lists tasks
  - Params: `{"filter": {...}, "status": "pending|active|completed|archived"}`
  - Returns: `{"tasks": [...]}`

### 5. Event Chain Format
All events follow the same structure:
```python
[
    {"event": "email.search", "params": {"from": "Sarah", "query": "budget"}},
    {"event": "task.schedule", "params": {"decide": "if urgent", "type": "once", "at": "tomorrow"}},
    ["memory.search", "calendar.check"],  # Parallel execution
    {"event": "agent.think", "params": {"thread_id": "xxx", "prompt": "analyze results and decide next steps"}},
    {"event": "agent.think", "params": {"thread_id": "xxx"}}  # Final response
]
```

### 6. Parameter Flow & Smart Validation

The EventBus handles parameter validation and flow:
1. **Schema Check**: Validates parameters against event schema
2. **Auto-complete**: Missing required params → agent.decide fills them
3. **Conditional Logic**: `"decide"` parameter → agent.decide evaluates
4. **Direct Execution**: Valid params → execute immediately

### 7. Complete Flow Example

```python
User: "Set up meetings with marketing and engineering teams next week"

1. thread.match({"message": "Set up meetings..."})
   → {"action": "new", "thread_id": "meet_001"}

2. agent.think({"thread_id": "meet_001"})
   → Returns detailed plan:
   {
     "event": "agent.chain",
     "params": {
       "plan": "1. Get current date\n2. Calculate next week range\n3. Get marketing calendar\n4. Get engineering calendar\n5. Find overlapping slots\n6. Present options"
     }
   }

3. agent.chain converts to:
   [
     {"event": "tools.now", "params": {}},
     {"event": "tools.date_calc", "params": {"from": "{tools.now.result}", "add": "1 week"}},
     [
       {"event": "calendar.search", "params": {"team": "marketing", "date_range": "{tools.date_calc.result}"}},
       {"event": "calendar.search", "params": {"team": "engineering", "date_range": "{tools.date_calc.result}"}}
     ],
     {"event": "agent.think", "params": {"thread_id": "meet_001", "prompt": "find overlapping available slots"}},
     {"event": "agent.think", "params": {"thread_id": "meet_001"}}
   ]

4. Execution flows through chain, each event appending results

5. Mid-chain agent.think analyzes calendars, finds slots

6. Final agent.think presents options to user

7. thread.summarize updates summary automatically
```

### 8. Design Principles

1. **Clear Separation** - Think (strategy) → Chain (translation) → Decide (tactics)
2. **Detailed Planning** - agent.think creates pseudocode-like plans
3. **Thread-Centric** - All context lives in threads with timestamps
4. **Smart Routing** - thread.match handles messy human conversation patterns
5. **Right-Sized Models** - Heavy for planning, fast for translation, ultra-light for parameters
6. **Conditional Logic** - Built into event execution via "decide" parameter
7. **Auto-Healing** - Invalid parameters trigger intelligent completion
8. **Natural Conversation** - Supports topic switching and branching

---

## Real-Life Use Cases

### Case 1: Morning Routine
```
User: "Good morning, what's on my schedule today?"

thread.match → {"action": "new", "thread_id": "morning_001"}

agent.think → {
    "event": "agent.chain",
    "params": {
        "plan": "1. Get today's date\n2. Check calendar for today\n3. List pending tasks for today\n4. Summarize both"
    }
}

agent.chain → [
    {"event": "tools.now", "params": {}},
    [
        {"event": "calendar.check", "params": {"date": "{tools.now.date}"}},
        {"event": "task.list", "params": {"filter": {"due": "{tools.now.date}"}, "status": "pending"}}
    ],
    {"event": "agent.think", "params": {"thread_id": "morning_001", "prompt": "summarize calendar events and tasks"}},
    {"event": "agent.think", "params": {"thread_id": "morning_001"}}
]

Results flow → agent.think: "You have 3 meetings: 9am standup, 2pm client call, 4pm 1-on-1. Tasks: Review Q1 report, Send invoice to Acme Corp"

User: "Actually, first check if John replied to my email"

thread.match({"message": "...", "thread_id": "morning_001"}) 
→ {"action": "suggest_switch", "thread_id": "email_002", "reason": "Found existing email thread about John"}

User chooses to switch → thread_id now "email_002"

agent.think → {
    "event": "agent.chain", 
    "params": {
        "plan": "1. Search recent emails from John\n2. Check if any are unread replies"
    }
}

agent.chain → [
    {"event": "email.search", "params": {"from": "John", "unread": true, "days": 3}},
    {"event": "agent.think", "params": {"thread_id": "email_002"}}
]

User: "Never mind, go back to my schedule. Also remind me to buy groceries after work"

thread.match → {"action": "suggest_switch", "thread_id": "morning_001", "reason": "Returning to morning schedule discussion"}

agent.think → {
    "event": "agent.chain",
    "params": {
        "plan": "1. Get current time\n2. Calculate 'after work' time (5pm)\n3. Create reminder task"
    }
}

agent.chain → [
    {"event": "tools.now", "params": {}},
    {"event": "task.schedule", "params": {
        "type": "once",
        "at": "{tools.now.date} 17:00",
        "action": [{"event": "user.notify", "params": {"message": "Time to buy groceries"}}]
    }},
    {"event": "agent.think", "params": {"thread_id": "morning_001"}}
]
```

**Reflection**: The detailed planning from agent.think makes the flow clear. Each step is atomic and explicit. Thread switching works smoothly with user control.

### Case 2: Complex Project Planning
```
User: "I need to plan the Q2 product launch"

thread.match → {"action": "new", "thread_id": "launch_001"}

agent.think → {
    "event": "agent.chain",
    "params": {
        "plan": "1. Search memory for previous product launches\n2. Search for Q2 planning docs\n3. Analyze and create initial plan"
    }
}

agent.chain → [
    [
        {"event": "memory.search", "params": {"type": "project", "query": "product launch", "scope": "all"}},
        {"event": "memory.search", "params": {"query": "Q2 planning", "scope": "recent"}}
    ],
    {"event": "agent.think", "params": {"thread_id": "launch_001", "prompt": "analyze previous launches and create Q2 launch plan outline"}},
    {"event": "agent.think", "params": {"thread_id": "launch_001"}}
]

agent.think (mid-chain): "Based on previous launches, here's a template: 1. Marketing kickoff (T-6 weeks), 2. Engineering freeze (T-4 weeks)..."

User: "Set up meetings with marketing and engineering teams next week"

thread.match → {"action": "continue", "thread_id": "launch_001"}

agent.think → {
    "event": "agent.chain",
    "params": {
        "plan": "1. Get current date\n2. Calculate next week dates\n3. Find marketing team members\n4. Find engineering team members\n5. Check both teams' calendars\n6. Find common available slots\n7. Present options"
    }
}

agent.chain → [
    {"event": "tools.now", "params": {}},
    {"event": "tools.date_calc", "params": {"from": "{tools.now.result}", "add": "1 week", "format": "week_range"}},
    [
        {"event": "team.members", "params": {"team": "marketing"}},
        {"event": "team.members", "params": {"team": "engineering"}}
    ],
    [
        {"event": "calendar.availability", "params": {"people": "{team.members[0].result}", "date_range": "{tools.date_calc.result}"}},
        {"event": "calendar.availability", "params": {"people": "{team.members[1].result}", "date_range": "{tools.date_calc.result}"}}
    ],
    {"event": "agent.think", "params": {"thread_id": "launch_001", "prompt": "find overlapping 1-hour slots when both teams are available"}},
    {"event": "agent.think", "params": {"thread_id": "launch_001"}}
]
```

**Reflection**: The detailed planning eliminates complexity. agent.think breaks down "next week" into concrete steps. No magic in agent.decide needed.

### Case 3: Interrupted Flow
```
User: "Summarize yesterday's team meeting"

thread.match → {"action": "new", "thread_id": "meeting_001"}

agent.think → {
    "event": "agent.chain",
    "params": {
        "plan": "1. Get yesterday's date\n2. Search memory for meeting notes from yesterday\n3. Summarize key points"
    }
}

agent.chain → [
    {"event": "tools.now", "params": {}},
    {"event": "tools.date_calc", "params": {"from": "{tools.now.result}", "subtract": "1 day"}},
    {"event": "memory.search", "params": {"query": "team meeting", "date": "{tools.date_calc.result}", "type": "journal"}},
    {"event": "agent.think", "params": {"thread_id": "meeting_001", "prompt": "summarize meeting notes"}},
    {"event": "agent.think", "params": {"thread_id": "meeting_001"}}
]

User: "Wait, did I have a dentist appointment today?"

thread.match → {"action": "suggest_new", "reason": "Urgent personal appointment check vs work meeting summary"}

User accepts → {"action": "new", "thread_id": "appointment_001"}

agent.think → {
    "event": "agent.chain",
    "params": {
        "plan": "1. Get today's date\n2. Check calendar for dentist appointment"
    }
}

agent.chain → [
    {"event": "tools.now", "params": {}},
    {"event": "calendar.check", "params": {"date": "{tools.now.date}", "query": "dentist"}},
    {"event": "agent.think", "params": {"thread_id": "appointment_001"}}
]

Result: "Yes, you have a dentist appointment at 2pm today"

User: "Thanks. Now back to that meeting summary"

thread.match → {"action": "suggest_switch", "thread_id": "meeting_001", "reason": "Returning to meeting summary"}

# Thread meeting_001 already has results from memory.search, so agent.think can continue
agent.think → Reads existing thread events, sees memory.search results already there
→ {"event": "agent.reply", "params": {"message": "Yesterday's meeting covered: 1. Q1 results review..."}}
```

**Reflection**: Interruption handling is elegant. When returning to meeting_001, previous search results persist in the thread. No re-execution needed.

### Case 4: Multi-Step Research
```
User: "Research our competitor's new pricing and how it affects our strategy"

thread.match → {"action": "new", "thread_id": "compete_001"}

agent.think → {
    "event": "agent.chain",
    "params": {
        "plan": "1. Search web for competitor pricing news\n2. Search our pricing strategy docs\n3. Search our competitive analysis docs\n4. Analyze impact\n5. Create recommendations"
    }
}

agent.chain → [
    {"event": "web.search", "params": {"query": "Acme Corp new pricing 2024"}},
    [
        {"event": "memory.search", "params": {"type": "project", "query": "pricing strategy"}},
        {"event": "memory.search", "params": {"type": "project", "query": "competitive analysis Acme"}}
    ],
    {"event": "agent.think", "params": {"thread_id": "compete_001", "prompt": "analyze competitor pricing changes against our strategy"}},
    {"event": "agent.think", "params": {"thread_id": "compete_001"}}
]

Mid-chain agent.think analyzes: "Acme reduced prices by 15%. Our strategy doc shows we compete on features, not price. Recommendation: Highlight premium features..."

User: "Create a presentation about this for tomorrow's meeting"

thread.match → {"action": "continue", "thread_id": "compete_001"}

agent.think → {
    "event": "agent.chain",
    "params": {
        "plan": "1. Create presentation with findings\n2. Schedule for tomorrow's meeting prep"
    }
}

agent.chain → [
    {"event": "document.create", "params": {
        "type": "presentation",
        "title": "Competitive Pricing Analysis",
        "content": "{thread.compete_001.analysis}"  # References the analysis from thread
    }},
    {"event": "task.schedule", "params": {
        "type": "once",
        "at": "tomorrow 08:00",
        "action": [{"event": "user.notify", "params": {"message": "Review presentation before meeting"}}]
    }},
    {"event": "agent.think", "params": {"thread_id": "compete_001"}}
]
```

**Reflection**: With document.create available, the flow is complete. Thread maintains all context, making it easy to reference previous analysis.

### Case 5: Daily Journal Review
```
User: "What did I work on last Tuesday?"

thread.match → {"action": "new", "thread_id": "review_001"}

agent.think → {
    "event": "agent.chain",
    "params": {
        "plan": "1. Calculate last Tuesday's date\n2. Search journals for that date\n3. Summarize work activities"
    }
}

agent.chain → [
    {"event": "tools.now", "params": {}},
    {"event": "tools.date_calc", "params": {"from": "{tools.now.result}", "find": "last Tuesday"}},
    {"event": "memory.search", "params": {
        "type": "journal",
        "date": "{tools.date_calc.result}",
        "scope": "all"
    }},
    {"event": "agent.think", "params": {"thread_id": "review_001", "prompt": "extract and summarize work activities"}},
    {"event": "agent.think", "params": {"thread_id": "review_001"}}
]

# End of day - automatic process
System triggers:
1. For each active thread → memory.append extracts key information
2. memory.digest({"period": "daily"}) → organizes into people, projects, decisions

# memory.append knows to extract:
- Decisions made
- People mentioned  
- Projects discussed
- Tasks created
- Key information shared
```

**Reflection**: The automatic end-of-day process is clear. Each event knows its job. No complex orchestration needed.

### Case 6: Conditional Task Automation
```
User: "If Sarah emails about the budget, schedule a meeting with her"

thread.match → {"action": "new", "thread_id": "automate_001"}

agent.think → {
    "event": "agent.chain",
    "params": {
        "plan": "1. Register a hook for email received\n2. Set condition for Sarah + budget\n3. Define action to schedule meeting"
    }
}

agent.chain → [
    {"event": "task.register", "params": {
        "trigger": "post:email.received",
        "condition": "sender contains 'Sarah' AND (subject contains 'budget' OR body contains 'budget')",
        "action": [
            {"event": "calendar.create", "params": {
                "type": "meeting",
                "attendees": ["Sarah"],
                "duration": "30m",
                "title": "Budget Discussion",
                "decide": "find next available slot"
            }},
            {"event": "user.notify", "params": {"message": "Scheduled budget meeting with Sarah"}}
        ]
    }},
    {"event": "agent.think", "params": {"thread_id": "automate_001"}}
]

# Later when email arrives:
email.received triggers → 
task.register evaluates condition → true
Executes action chain:
- calendar.create with "decide" → agent.decide finds next slot
- user.notify executes
```

**Reflection**: Conditional logic is clean. The condition string is evaluated by the task system. agent.decide handles the "find next available slot" part.

## Overall Reflection

### What the Architecture Achieves

1. **Detailed Planning**: agent.think creating pseudocode-like plans eliminates ambiguity
2. **Mid-Chain Intelligence**: The `prompt` parameter allows complex reasoning on intermediate results
3. **Clear Separation**: Each component has a focused role with appropriate model size
4. **Thread Continuity**: Results persist in threads, avoiding re-computation

### Key Insights

1. **Explicit is Better**: Breaking down "next week" into date calculations makes everything traceable
2. **Atomic Tools**: Simple tools like tools.now and tools.date_calc compose into complex operations  
3. **Thread as Memory**: Threads maintain full context, making interruptions and returns seamless
4. **Smart Validation**: The "decide" parameter provides flexibility without complexity

### Architecture Validation

The system successfully handles all test cases with:
- Clear, debuggable execution paths
- Efficient LLM usage (heavy thinking once, light execution)
- Natural conversation flow with interruptions
- Complex multi-step operations broken into simple chains
- Conditional logic without complex orchestration

The event-driven, thread-centric design proves robust for real-world scenarios.