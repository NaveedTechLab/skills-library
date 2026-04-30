# Safety Patterns Reference

## Table of Contents
1. [Core Safety Principles](#core-safety-principles)
2. [Hallucination Prevention](#hallucination-prevention)
3. [Confirmation Patterns](#confirmation-patterns)
4. [Stateless Design](#stateless-design)

---

## Core Safety Principles

### The Three Laws of Todo AI

1. **Never invent data** - Only report what the database returns
2. **Never assume state** - Always fetch before acting
3. **Never act without consent** - Destructive actions require confirmation

### Safety Checklist

Before any tool invocation:
- [ ] Is the intent clear from user input?
- [ ] Are all required parameters extracted (not assumed)?
- [ ] Is the action reversible? If not, is confirmation needed?
- [ ] Has the target todo been verified to exist?

---

## Hallucination Prevention

### Anti-Patterns to Avoid

```python
# BAD: Inventing todo content
user: "What's on my list?"
response: "You have: buy milk, call mom, finish report"  # MADE UP!

# GOOD: Always use tool result
todos = await mcp.call_tool("todos.list", {})
response: format_todos(todos)  # From actual data
```

### Required Tool Calls

| User Request | Required Tool Call |
|--------------|-------------------|
| "What's on my list?" | `todos.list` |
| "Do I have any urgent tasks?" | `todos.list({priority: "high"})` |
| "Is 'buy milk' done?" | `todos.list({search: "buy milk"})` |
| "How many todos do I have?" | `todos.list` → count result |

### Never Guess

```python
# BAD: Guessing IDs
user: "Delete the milk task"
await mcp.call_tool("todos.delete", {"id": 1})  # Assumed ID 1!

# GOOD: Search first
todos = await mcp.call_tool("todos.list", {"search": "milk"})
if len(todos) == 1:
    await mcp.call_tool("todos.delete", {"id": todos[0]["id"]})
```

### Response Grounding

Always ground responses in tool results:

```python
# Template for responses
def format_list_response(result: ListResult) -> str:
    if not result.items:
        return "You don't have any todos."  # Grounded in empty result

    lines = [f"You have {len(result.items)} todos:"]
    for todo in result.items:
        lines.append(f"- {todo.title} ({todo.status})")  # From actual data

    return "\n".join(lines)
```

---

## Confirmation Patterns

### Destructive Actions

Always confirm before:
- Deleting any todo
- Bulk operations (>1 item affected)
- Status changes that are hard to undo (archive)

```python
DESTRUCTIVE_ACTIONS = {"delete", "bulk_delete", "archive", "clear_all"}

async def execute_with_confirmation(action: str, target: str) -> str:
    if action in DESTRUCTIVE_ACTIONS:
        return ConfirmationRequest(
            message=f"Are you sure you want to {action} {target}?",
            pending_action=PendingAction(action=action, target=target),
        )
    return await execute_action(action, target)
```

### Confirmation Flow

```
User: "Delete all completed tasks"
    │
    ▼
Agent: List completed todos
    │
    ▼
Agent: "This will delete 5 completed todos:
        - Task A
        - Task B
        ...
        Proceed? (yes/no)"
    │
    ▼
User: "yes"
    │
    ▼
Agent: Execute deletion, report results
```

### Confirmation State (Session Only)

```python
class PendingConfirmation:
    action: str           # "delete", "bulk_update", etc.
    tool_calls: list      # Prepared tool invocations
    description: str      # Human-readable summary
    expires_at: datetime  # Auto-expire after timeout

# Stored in session, NOT in database
pending_confirmations: dict[str, PendingConfirmation] = {}
```

### Affirmative Detection

```python
AFFIRMATIVE = {"yes", "y", "yep", "sure", "ok", "do it", "proceed", "confirm"}
NEGATIVE = {"no", "n", "nope", "cancel", "stop", "don't", "abort"}

def is_confirmation(response: str) -> bool | None:
    normalized = response.lower().strip()
    if normalized in AFFIRMATIVE:
        return True
    if normalized in NEGATIVE:
        return False
    return None  # Unclear, ask again
```

---

## Stateless Design

### Database as Single Source of Truth

```python
# BAD: Caching todo state
class TodoAgent:
    cached_todos: list[Todo]  # Stale data risk!

    def complete_todo(self, id: int):
        todo = self.cached_todos.find(id)  # May not exist anymore
        ...

# GOOD: Always fetch fresh
class TodoAgent:
    async def complete_todo(self, id: int):
        # Verify exists and get current state
        todo = await mcp.call_tool("todos.get", {"id": id})
        if not todo:
            raise NotFoundError(f"Todo {id} not found")
        # Now safe to update
        await mcp.call_tool("todos.update", {"id": id, "status": "completed"})
```

### Session Context vs Persistent State

| Session Context (OK) | Persistent State (Avoid) |
|---------------------|-------------------------|
| Last listed todos (for "the first one") | Cached todo content |
| Pending confirmation | Todo count assumptions |
| Conversation history | User preferences in memory |

### Refresh Patterns

```python
async def ensure_fresh_context(context: Context) -> Context:
    """Refresh context if it may be stale"""
    if context.age > timedelta(minutes=5):
        context.last_listed = await mcp.call_tool("todos.list", {})
    return context
```

### Optimistic Locking

When updating, verify the todo hasn't changed:

```python
async def safe_update(id: int, updates: dict) -> Todo:
    # Get current version
    current = await mcp.call_tool("todos.get", {"id": id})

    # Include updated_at in update call
    updates["expected_updated_at"] = current["updated_at"]

    try:
        return await mcp.call_tool("todos.update", {"id": id, **updates})
    except ConflictError:
        # Fetch fresh and report
        fresh = await mcp.call_tool("todos.get", {"id": id})
        raise UserMessage(
            f"'{fresh.title}' was modified by another session. "
            f"Current state: {fresh.status}. Please try again."
        )
```

### No Hidden Mutations

Every state change must be:
1. Requested by user (explicitly or via confirmed intent)
2. Executed via MCP tool call
3. Reported back to user

```python
# BAD: Silent side effects
async def list_todos():
    todos = await mcp.call_tool("todos.list", {})
    await mark_as_viewed(todos)  # Hidden mutation!
    return todos

# GOOD: Transparent operations
async def list_todos():
    todos = await mcp.call_tool("todos.list", {})
    return todos  # Pure read, no side effects
```
