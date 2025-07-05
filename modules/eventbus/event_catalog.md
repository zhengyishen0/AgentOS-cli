# AgentOS Event Catalog

This document lists all planned events in the EventChain architecture.

## Core Agent Events

### agent.think
- **Model**: Heavy (Claude/GPT-4)
- **Purpose**: Strategic planning and complex reasoning
- **Params**: 
  - `thread_id`: string (required)
  - `prompt`: string (optional) - for mid-chain reasoning
- **Returns**: Either:
  - `{event: "agent.reply", params: {message: "..."}}`
  - `{event: "agent.chain", params: {plan: "..."}}`

### agent.chain
- **Model**: Fast (Mistral/Llama)
- **Purpose**: Convert natural language plans to executable event chains
- **Params**:
  - `plan`: string - detailed pseudocode-like plan
- **Returns**: `{chain: [...]}`

### agent.decide
- **Model**: Ultra-light (Phi/TinyLlama)
- **Purpose**: Parameter completion and simple decisions
- **Params**:
  - `event`: string - event needing completion
  - `params`: object - incomplete parameters
  - `condition`: string (optional) - condition to evaluate
- **Returns**:
  - `{action: "continue", params: {...}}`
  - `{action: "skip", reason: "..."}`
  - `{action: "break"}`

### agent.reply
- **Purpose**: Send message to user
- **Params**:
  - `message`: string
  - `thread_id`: string

## Thread Management Events

### thread.match
- **Purpose**: Determine which thread a message belongs to
- **Params**:
  - `message`: string
  - `thread_id`: string (optional) - current thread
- **Returns**:
  - `{action: "continue", thread_id: "xxx"}`
  - `{action: "suggest_switch", thread_id: "yyy", reason: "..."}`
  - `{action: "new", thread_id: "new_xxx"}`

### thread.summarize
- **Purpose**: Update thread summary
- **Params**:
  - `thread_id`: string
- **Auto-called**: After each chain execution

### thread.created
- **Purpose**: Thread creation event
- **Auto-generated**: When new thread created

### thread.archived
- **Purpose**: Thread archival event
- **Auto-generated**: When thread archived

## Memory Operations

### memory.append
- **Purpose**: Add to daily journal with keywords
- **Params**:
  - `thread_id`: string
  - `content`: string
- **Side-effects**: Extracts keywords during append

### memory.search
- **Purpose**: Search across journals/knowledge
- **Params**:
  - `query`: string
  - `scope`: "recent" | "all"
  - `type`: "journal" | "people" | "project" | "any"
- **Returns**: `{matches: [...]}`

### memory.digest
- **Purpose**: Process journals into organized knowledge
- **Params**:
  - `period`: "daily" | "weekly"
- **Extracts**: people, projects, preferences, passwords, etc.

## Task Management

### task.schedule
- **Purpose**: Create all types of tasks
- **Params**:
  - `type`: "once" | "repeat" | "delay"
  - `at`: datetime (for once/repeat)
  - `interval`: string (for repeat)
  - `action`: array of events to execute
  - `decide`: string (optional) - condition
- **Returns**: `{task_id: "xxx"}`

### task.register
- **Purpose**: Hook-based task registration
- **Params**:
  - `trigger`: string - "pre:event.name" or "post:event.name"
  - `condition`: string - condition to evaluate
  - `action`: array of events to execute

### task.list
- **Purpose**: List tasks
- **Params**:
  - `filter`: object (optional)
  - `status`: "pending" | "active" | "completed" | "archived"
- **Returns**: `{tasks: [...]}`

## Tool Events

### tools.now
- **Purpose**: Get current date/time
- **Params**: none
- **Returns**: `{date: "2024-01-15", time: "10:30:00", datetime: "2024-01-15T10:30:00Z"}`

### tools.date_calc
- **Purpose**: Date calculations
- **Params**:
  - `from`: datetime or "{reference}"
  - `add`: string (optional) - "1 week", "3 days", etc.
  - `subtract`: string (optional)
  - `find`: string (optional) - "next Tuesday", "last Monday"
  - `format`: string (optional) - "week_range", "month", etc.
- **Returns**: Date/time in requested format

## Communication Events

### email.search
- **Purpose**: Search emails
- **Params**:
  - `from`: string (optional)
  - `to`: string (optional)
  - `subject`: string (optional)
  - `query`: string (optional)
  - `unread`: boolean (optional)
  - `days`: number (optional) - look back N days
- **Returns**: `{matches: [...]}`

### email.send
- **Purpose**: Send email
- **Params**:
  - `to`: string or array
  - `subject`: string
  - `body`: string
  - `attachments`: array (optional)

### email.received
- **Purpose**: Email received trigger (for hooks)
- **Auto-generated**: When new email arrives

## Calendar Events

### calendar.check
- **Purpose**: Check calendar
- **Params**:
  - `date`: date or "{reference}"
  - `date_range`: object (optional) - {start, end}
  - `query`: string (optional)
- **Returns**: `{events: [...]}`

### calendar.create
- **Purpose**: Create calendar event
- **Params**:
  - `type`: "meeting" | "reminder" | "event"
  - `title`: string
  - `attendees`: array (optional)
  - `duration`: string - "30m", "1h", etc.
  - `at`: datetime or "{reference}"
  - `decide`: string (optional) - e.g., "find next available slot"

### calendar.availability
- **Purpose**: Find available time slots
- **Params**:
  - `people`: array of person IDs
  - `date_range`: object - {start, end}
  - `duration`: string - minimum slot duration
- **Returns**: `{slots: [...]}`

### calendar.search
- **Purpose**: Search calendar events
- **Params**:
  - `team`: string (optional)
  - `person`: string (optional)
  - `date_range`: object or "{reference}"
- **Returns**: `{events: [...]}`

## Team/People Events

### team.members
- **Purpose**: Get team members
- **Params**:
  - `team`: string - team name
- **Returns**: `{members: [{id, name, email, role}...]}`

### people.info
- **Purpose**: Get person information
- **Params**:
  - `name`: string
- **Returns**: Person details from knowledge base

## Document Events

### document.create
- **Purpose**: Create document
- **Params**:
  - `type`: "presentation" | "document" | "spreadsheet"
  - `title`: string
  - `content`: string or object
- **Returns**: `{document_id: "xxx", url: "..."}`

### document.search
- **Purpose**: Search documents
- **Params**:
  - `query`: string
  - `type`: string (optional)
- **Returns**: `{documents: [...]}`

## System Events

### user.input
- **Purpose**: User input received
- **Auto-generated**: When user sends message

### user.notify
- **Purpose**: Send notification to user
- **Params**:
  - `message`: string
  - `type`: "info" | "warning" | "error" (optional)

### web.search
- **Purpose**: Search the web
- **Params**:
  - `query`: string
- **Returns**: `{results: [...]}`

## Event Patterns

### Conditional Execution
Any event can include `decide` parameter:
```json
{"event": "task.schedule", "params": {"decide": "if urgent", "type": "once", "at": "tomorrow"}}
```

### Parallel Execution
Events in arrays execute in parallel:
```json
[
  {"event": "email.search", "params": {"from": "Sarah"}},
  {"event": "calendar.check", "params": {"date": "today"}}
]
```

### Parameter Interpolation
Reference previous results:
```json
{"event": "calendar.create", "params": {"at": "{tools.date_calc.result}"}}
```

### Thread References
Access thread context:
```json
{"event": "document.create", "params": {"content": "{thread.compete_001.analysis}"}}
```