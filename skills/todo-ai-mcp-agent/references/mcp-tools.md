# MCP Tools Reference

## Table of Contents
1. [Tool Definitions](#tool-definitions)
2. [Tool Invocation Patterns](#tool-invocation-patterns)
3. [Error Handling](#error-handling)
4. [Chaining Tools](#chaining-tools)

---

## Tool Definitions

### todos.list

List todos with optional filtering.

```json
{
  "name": "todos.list",
  "description": "List todos for the current user",
  "inputSchema": {
    "type": "object",
    "properties": {
      "status": {
        "type": "string",
        "enum": ["pending", "completed", "archived"],
        "description": "Filter by status"
      },
      "priority": {
        "type": "string",
        "enum": ["low", "medium", "high"],
        "description": "Filter by priority"
      },
      "search": {
        "type": "string",
        "description": "Search in title and description"
      },
      "limit": {
        "type": "integer",
        "default": 20,
        "description": "Max items to return"
      }
    }
  }
}
```

**Example invocations:**
```
"Show my todos" → todos.list({})
"Show completed tasks" → todos.list({status: "completed"})
"Find grocery todos" → todos.list({search: "grocery"})
```

---

### todos.create

Create a new todo.

```json
{
  "name": "todos.create",
  "description": "Create a new todo",
  "inputSchema": {
    "type": "object",
    "required": ["title"],
    "properties": {
      "title": {
        "type": "string",
        "minLength": 1,
        "maxLength": 255,
        "description": "Todo title"
      },
      "description": {
        "type": "string",
        "maxLength": 2000,
        "description": "Optional description"
      },
      "priority": {
        "type": "string",
        "enum": ["low", "medium", "high"],
        "description": "Priority level"
      },
      "due_date": {
        "type": "string",
        "format": "date-time",
        "description": "Due date in ISO 8601 format"
      }
    }
  }
}
```

**Example invocations:**
```
"Add buy milk" → todos.create({title: "buy milk"})
"Create urgent task: call doctor" → todos.create({title: "call doctor", priority: "high"})
"Remind me tomorrow to submit report" → todos.create({title: "submit report", due_date: "2024-01-16T09:00:00Z"})
```

---

### todos.get

Get a specific todo by ID.

```json
{
  "name": "todos.get",
  "description": "Get a todo by ID",
  "inputSchema": {
    "type": "object",
    "required": ["id"],
    "properties": {
      "id": {
        "type": "integer",
        "description": "Todo ID"
      }
    }
  }
}
```

---

### todos.update

Update an existing todo.

```json
{
  "name": "todos.update",
  "description": "Update a todo",
  "inputSchema": {
    "type": "object",
    "required": ["id"],
    "properties": {
      "id": {
        "type": "integer",
        "description": "Todo ID"
      },
      "title": {
        "type": "string",
        "description": "New title"
      },
      "description": {
        "type": "string",
        "description": "New description"
      },
      "status": {
        "type": "string",
        "enum": ["pending", "completed", "archived"],
        "description": "New status"
      },
      "priority": {
        "type": "string",
        "enum": ["low", "medium", "high"],
        "description": "New priority"
      },
      "due_date": {
        "type": "string",
        "format": "date-time",
        "description": "New due date"
      }
    }
  }
}
```

**Example invocations:**
```
"Mark todo 5 as done" → todos.update({id: 5, status: "completed"})
"Change priority of task 3 to high" → todos.update({id: 3, priority: "high"})
"Archive old tasks" → (requires list + multiple updates)
```

---

### todos.delete

Delete a todo.

```json
{
  "name": "todos.delete",
  "description": "Delete a todo permanently",
  "inputSchema": {
    "type": "object",
    "required": ["id"],
    "properties": {
      "id": {
        "type": "integer",
        "description": "Todo ID"
      }
    }
  }
}
```

---

## Tool Invocation Patterns

### Single Tool Call

```python
# Direct mapping
result = await mcp.call_tool("todos.create", {
    "title": extracted_title,
    "priority": extracted_priority,
})
```

### Sequential Tool Calls

```python
# List then act pattern
todos = await mcp.call_tool("todos.list", {"search": query})
if len(todos) == 1:
    await mcp.call_tool("todos.update", {"id": todos[0]["id"], "status": "completed"})
```

### Bulk Operations

```python
# Complete all matching todos
todos = await mcp.call_tool("todos.list", {"status": "pending"})
results = []
for todo in todos:
    result = await mcp.call_tool("todos.update", {
        "id": todo["id"],
        "status": "completed"
    })
    results.append(result)
```

---

## Error Handling

### Error Types

| Error | Cause | Response |
|-------|-------|----------|
| `not_found` | Todo ID doesn't exist | "I couldn't find that todo. Would you like to see your list?" |
| `validation_error` | Invalid input | "I couldn't create that: {details}" |
| `permission_denied` | Not user's todo | "You don't have access to that todo." |
| `conflict` | Concurrent modification | "That todo was just modified. Here's the current version: ..." |

### Error Response Pattern

```python
async def safe_tool_call(tool: str, params: dict) -> ToolResult:
    try:
        result = await mcp.call_tool(tool, params)
        return ToolResult(success=True, data=result)
    except MCPError as e:
        if e.code == "not_found":
            return ToolResult(success=False, error="Todo not found", recoverable=True)
        elif e.code == "validation_error":
            return ToolResult(success=False, error=e.message, recoverable=True)
        else:
            return ToolResult(success=False, error="Something went wrong", recoverable=False)
```

### Recovery Strategies

1. **Not found** → List todos, ask user to select
2. **Validation error** → Extract specific field error, ask for correction
3. **Conflict** → Fetch fresh data, show current state
4. **Server error** → Apologize, suggest retry

---

## Chaining Tools

### Find-and-Act Pattern

```python
async def complete_by_title(title_query: str):
    # Step 1: Find matching todos
    todos = await mcp.call_tool("todos.list", {"search": title_query})

    if not todos:
        return "No todos found matching '{}'".format(title_query)

    if len(todos) > 1:
        return "Found {} matches. Which one?\n{}".format(
            len(todos),
            format_todo_list(todos)
        )

    # Step 2: Act on single match
    todo = todos[0]
    await mcp.call_tool("todos.update", {"id": todo["id"], "status": "completed"})
    return "Completed '{}'".format(todo["title"])
```

### Transactional Patterns

For operations that should succeed or fail together:

```python
async def swap_priorities(id1: int, id2: int):
    # Get current states
    todo1 = await mcp.call_tool("todos.get", {"id": id1})
    todo2 = await mcp.call_tool("todos.get", {"id": id2})

    # Swap
    try:
        await mcp.call_tool("todos.update", {"id": id1, "priority": todo2["priority"]})
        await mcp.call_tool("todos.update", {"id": id2, "priority": todo1["priority"]})
    except MCPError:
        # Attempt rollback
        await mcp.call_tool("todos.update", {"id": id1, "priority": todo1["priority"]})
        raise
```

### Pagination Handling

```python
async def list_all_todos(status: str = None) -> list:
    all_todos = []
    offset = 0
    limit = 50

    while True:
        batch = await mcp.call_tool("todos.list", {
            "status": status,
            "limit": limit,
            "offset": offset,
        })
        all_todos.extend(batch["items"])

        if len(batch["items"]) < limit:
            break
        offset += limit

    return all_todos
```
