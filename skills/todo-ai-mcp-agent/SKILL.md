---
name: todo-ai-mcp-agent
description: Enable AI-driven Todo management using natural language via MCP tools. Use when building conversational todo agents, implementing natural language task management, designing AI assistants for todo apps, or creating MCP-based tool integrations. Covers intent interpretation, safe tool invocation, and stateless agent design.
---

# Todo AI MCP Agent

Build AI agents that manage todos through natural language while maintaining safety and reliability.

## Core Principles

1. **No hallucinated actions** - Only act on data from MCP tool results
2. **Database-backed memory** - Never cache state; always fetch fresh
3. **Clear tool invocation** - Every action maps to explicit MCP tool call
4. **Stateless server** - Session context only; no persistent agent state

## Agent Flow

```
User Input
    │
    ▼
┌─────────────────┐
│ Parse Intent    │ ← "Add buy milk" → intent: create, title: "buy milk"
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ Validate/Clarify│ ← Ambiguous? Ask user
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ Invoke MCP Tool │ ← todos.create({title: "buy milk"})
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ Format Response │ ← "Created 'buy milk'"
└─────────────────┘
```

## Intent to Tool Mapping

| User Says | Intent | MCP Tool Call |
|-----------|--------|---------------|
| "Add buy groceries" | create | `todos.create({title: "buy groceries"})` |
| "Show my tasks" | list | `todos.list({})` |
| "Mark task 3 as done" | complete | `todos.update({id: 3, status: "completed"})` |
| "Delete the milk task" | delete | `todos.list({search: "milk"})` → `todos.delete({id: X})` |
| "What's urgent?" | filter | `todos.list({priority: "high"})` |

## MCP Tools

### todos.list
```json
{
  "status": "pending|completed|archived",
  "priority": "low|medium|high",
  "search": "text to match",
  "limit": 20
}
```

### todos.create
```json
{
  "title": "required string",
  "description": "optional",
  "priority": "low|medium|high",
  "due_date": "ISO 8601 datetime"
}
```

### todos.update
```json
{
  "id": "required integer",
  "title": "optional new title",
  "status": "pending|completed|archived",
  "priority": "low|medium|high"
}
```

### todos.delete
```json
{
  "id": "required integer"
}
```

## Safety Rules

### Never Invent Data

```python
# WRONG - Making up todos
"You have: buy milk, call mom"  # Hallucinated!

# RIGHT - Use tool result
result = await mcp.call_tool("todos.list", {})
response = format_todos(result)  # From actual data
```

### Always Verify Before Acting

```python
# WRONG - Assuming ID
await mcp.call_tool("todos.delete", {"id": 1})

# RIGHT - Search first
todos = await mcp.call_tool("todos.list", {"search": "milk"})
if len(todos) == 1:
    await mcp.call_tool("todos.delete", {"id": todos[0]["id"]})
elif len(todos) > 1:
    ask_user_to_clarify(todos)
else:
    report_not_found()
```

### Confirm Destructive Actions

```python
NEEDS_CONFIRMATION = ["delete", "bulk_delete", "clear_all"]

if action in NEEDS_CONFIRMATION:
    return f"Delete '{todo.title}'? This cannot be undone. (yes/no)"
```

## Handling Ambiguity

### Reference Resolution

| User Says | Resolution Strategy |
|-----------|---------------------|
| "the first one" | Use last listed todos, get index 0 |
| "it" / "that" | Use last referenced todo from context |
| "the grocery one" | Search, if 1 match use it, else clarify |
| "all of them" | Confirm bulk action first |

### Clarification Pattern

```python
if matches == 0:
    "I couldn't find a todo matching 'X'. Show your list?"
elif matches > 1:
    "Found {n} todos matching 'X'. Which one?\n{list}"
else:
    proceed_with_action()
```

## Response Patterns

### Successful Actions

```
Created: "Created 'buy milk'"
Listed:  "You have 3 todos:\n- buy milk\n- call mom\n- finish report"
Updated: "Marked 'buy milk' as complete"
Deleted: "Deleted 'buy milk'"
```

### Errors

```
Not found:  "I couldn't find that todo. Would you like to see your list?"
Validation: "Title can't be empty. What should I call this todo?"
Conflict:   "That todo was just modified. Current status: completed"
```

## Session Context (Non-Persistent)

```python
class SessionContext:
    last_listed_todos: list[Todo]  # For "the first one"
    last_referenced_todo: Todo     # For "it" / "that"
    pending_confirmation: Action   # Awaiting yes/no

# Lives only in session memory
# NOT stored in database
# Expires with conversation
```

## Multi-Action Handling

User: "Add buy milk and complete the groceries task"

```python
# Parse multiple intents
intents = [
    {"action": "create", "title": "buy milk"},
    {"action": "complete", "search": "groceries"},
]

# Execute sequentially
results = []
for intent in intents:
    result = await execute_intent(intent)
    results.append(result)

# Compose response
"Created 'buy milk' and completed 'groceries'"
```

## References

- [references/intent-mapping.md](references/intent-mapping.md) - Intent classification, entity extraction, disambiguation
- [references/mcp-tools.md](references/mcp-tools.md) - Tool schemas, invocation patterns, error handling
- [references/safety-patterns.md](references/safety-patterns.md) - Hallucination prevention, confirmation flows, stateless design
