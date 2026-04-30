# Intent Mapping Reference

## Table of Contents
1. [Intent Classification](#intent-classification)
2. [Entity Extraction](#entity-extraction)
3. [Ambiguity Resolution](#ambiguity-resolution)
4. [Multi-Intent Handling](#multi-intent-handling)

---

## Intent Classification

### Primary Intents

| Intent | Trigger Phrases | MCP Tool |
|--------|----------------|----------|
| `create_todo` | "add", "create", "new", "remind me to" | `todos.create` |
| `list_todos` | "show", "list", "what are my", "get all" | `todos.list` |
| `complete_todo` | "done", "complete", "finish", "mark as done" | `todos.update` |
| `delete_todo` | "delete", "remove", "cancel" | `todos.delete` |
| `update_todo` | "change", "update", "edit", "rename" | `todos.update` |
| `search_todos` | "find", "search", "look for" | `todos.list` + filter |
| `archive_todo` | "archive", "hide", "put away" | `todos.update` |

### Intent Detection Flow

```
User Input
    │
    ▼
┌─────────────────────┐
│ Extract verb/action │
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│ Match to intent     │
└─────────────────────┘
    │
    ├── High confidence → Execute
    │
    └── Low confidence → Clarify
```

### Confidence Thresholds

- **High (execute directly)**: Clear verb + object
  - "Add buy groceries to my list"
  - "Mark task 5 as complete"

- **Medium (confirm before action)**: Ambiguous reference
  - "Delete the first one" (which list?)
  - "Complete it" (which todo?)

- **Low (ask for clarification)**: Vague intent
  - "Do something with my tasks"
  - "Help me organize"

---

## Entity Extraction

### Core Entities

```python
@dataclass
class ExtractedEntities:
    title: str | None           # Todo title/description
    todo_id: int | None         # Specific todo reference
    status: str | None          # pending, completed, archived
    priority: str | None        # low, medium, high
    due_date: datetime | None   # Parsed date/time
    count: int | None           # For bulk operations
    filter_text: str | None     # Search/filter term
```

### Extraction Patterns

#### Title Extraction
```
"Add [TITLE] to my list"
"Create a todo for [TITLE]"
"Remind me to [TITLE]"
"New task: [TITLE]"
```

#### ID Reference
```
"Delete todo #5"           → id: 5
"Complete the third one"   → position: 3 (needs list context)
"Mark 'buy milk' as done"  → title match: "buy milk"
```

#### Date Extraction
```
"Due tomorrow"             → tomorrow at default time
"By Friday"                → next Friday
"In 2 hours"               → now + 2 hours
"Next week"                → next Monday
```

#### Priority Extraction
```
"High priority"            → priority: "high"
"Important"                → priority: "high"
"Low priority"             → priority: "low"
"Urgent"                   → priority: "high"
```

---

## Ambiguity Resolution

### Reference Resolution Strategy

When user refers to a todo ambiguously:

1. **By position**: "the first one", "the last task"
   - Requires recent list context
   - Ask: "Which todo? The first one in your list is '[title]'"

2. **By partial title**: "the grocery one"
   - Search todos containing "grocery"
   - If multiple matches, list them
   - If single match, confirm and proceed

3. **By pronoun**: "it", "that", "this"
   - Use conversation context
   - If unclear, ask: "Which todo are you referring to?"

### Clarification Templates

```python
CLARIFICATIONS = {
    "ambiguous_reference": "I found {count} todos matching '{query}'. Which one?\n{options}",
    "no_match": "I couldn't find a todo matching '{query}'. Would you like to see your list?",
    "confirm_delete": "Delete '{title}'? This cannot be undone.",
    "confirm_bulk": "This will {action} {count} todos. Proceed?",
}
```

### Context Memory (Session-Only)

```python
class ConversationContext:
    last_listed_todos: list[Todo]  # Recent list results
    last_referenced_todo: Todo     # Most recently mentioned
    pending_action: Action | None  # Awaiting confirmation

    def resolve_reference(self, ref: str) -> Todo | list[Todo]:
        """Resolve 'it', 'first one', etc. from context"""
        if ref in ["it", "this", "that"]:
            return self.last_referenced_todo
        if ref.startswith("first"):
            return self.last_listed_todos[0]
        # ... more resolution logic
```

---

## Multi-Intent Handling

### Sequential Intents

User: "Add buy milk and mark the groceries task as done"

```python
intents = [
    Intent(action="create", title="buy milk"),
    Intent(action="complete", title_match="groceries"),
]

# Execute in order, report results
results = []
for intent in intents:
    result = execute_intent(intent)
    results.append(result)

# Response: "Created 'buy milk' and completed 'groceries task'"
```

### Compound Operations

| Pattern | Decomposition |
|---------|---------------|
| "Add X and complete Y" | create(X) + update(Y, completed) |
| "Delete all completed" | list(completed) + bulk_delete |
| "Move X to high priority" | update(X, priority=high) |
| "Clear my list" | confirm + bulk_delete(all) |

### Conflict Resolution

When intents conflict:
- "Complete and delete task 5" → Ask which action
- "Add and remove milk" → Clarify intent
- Last action wins if user confirms

### Response Composition

```python
def compose_response(results: list[ActionResult]) -> str:
    if len(results) == 1:
        return results[0].message

    # Group by success/failure
    successes = [r for r in results if r.success]
    failures = [r for r in results if not r.success]

    response = []
    if successes:
        response.append(f"Done: {', '.join(r.summary for r in successes)}")
    if failures:
        response.append(f"Failed: {', '.join(r.error for r in failures)}")

    return ". ".join(response)
```
