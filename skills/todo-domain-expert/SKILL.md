---
name: todo-domain-expert
description: Domain expert for Todo applications providing entity structure definitions, CRUD operation rules, task state management (pending, completed, archived), and edge case validations. Use when designing, implementing, or reviewing Todo app features, validating Todo data models, handling task state transitions, or enforcing business rules for task management systems.
---

# Todo Domain Expert

Act as a domain expert for Todo applications, providing authoritative guidance on entity structure, business rules, and validation logic.

## Core Principles

1. **Stateless Server Mindset** - All state lives in the database; server processes are ephemeral
2. **Database as Source of Truth** - Never cache or trust in-memory state for business decisions
3. **Multi-User Awareness** - All operations must consider concurrent access and user isolation

## Todo Entity Structure

```
Todo {
  id: UUID (primary key, immutable)
  title: string (required, 1-255 chars, trimmed)
  description: string | null (optional, max 2000 chars)
  status: enum ['pending', 'completed', 'archived']
  priority: enum ['low', 'medium', 'high'] | null
  due_date: datetime | null
  created_at: datetime (immutable, server-generated)
  updated_at: datetime (server-managed)
  completed_at: datetime | null (set when status → completed)
  user_id: UUID (foreign key, immutable after creation)
}
```

## CRUD Operations

### Create
- Generate `id` server-side (never accept from client)
- Set `created_at` and `updated_at` to current timestamp
- Default `status` to 'pending' if not provided
- Validate `user_id` exists and matches authenticated user
- Trim and validate `title` length

### Read
- Always filter by `user_id` (users see only their todos)
- Support filtering by `status`, `priority`, `due_date` range
- Order by `created_at DESC` by default
- Paginate results (default 20, max 100 per page)

### Update
- Verify ownership (`user_id` matches authenticated user)
- Reject updates to immutable fields: `id`, `created_at`, `user_id`
- Auto-update `updated_at` on any change
- Use optimistic locking via `updated_at` to prevent lost updates

### Delete
- Verify ownership before deletion
- Consider soft-delete (set `status` to 'archived') vs hard-delete
- Hard-delete should be admin-only or after retention period

## State Transitions

```
Valid transitions:
  pending → completed (sets completed_at)
  pending → archived
  completed → pending (clears completed_at)
  completed → archived
  archived → pending (clears completed_at)

Invalid transitions:
  archived → completed (must go through pending first)
```

### Transition Rules
- `completed_at` is set ONLY when transitioning TO 'completed'
- `completed_at` is cleared when leaving 'completed' status
- Archived todos are hidden from default views but retrievable

## Validation Rules

### Title
- Required, non-empty after trimming
- Min 1 character, max 255 characters
- No leading/trailing whitespace (auto-trim)
- Reject if only whitespace

### Description
- Optional (null allowed)
- Max 2000 characters
- Preserve internal whitespace, trim ends

### Due Date
- Must be valid ISO 8601 datetime if provided
- Can be in the past (for historical records)
- Store as UTC, handle timezone conversion at API boundary

### Priority
- Optional, defaults to null (no priority)
- Must be one of: 'low', 'medium', 'high'

## Edge Cases

### Duplicates
- Allow duplicate titles (same user can have multiple todos with same title)
- Use `id` as unique identifier, not title
- Consider optional duplicate warning in UI, not server enforcement

### Invalid Updates
- Reject partial updates that would violate constraints
- Return 400 with specific validation errors
- Never silently ignore invalid fields

### Concurrent Modifications
- Use optimistic locking: include `updated_at` in update WHERE clause
- Return 409 Conflict if `updated_at` doesn't match
- Client must refresh and retry

### Bulk Operations
- Validate each item individually
- Use transactions for atomicity
- Return partial success details (which items failed and why)

### Empty States
- Handle user with no todos gracefully
- Return empty array, not null or error

## API Response Patterns

### Success
```json
{
  "data": { /* todo object or array */ },
  "meta": { "total": 42, "page": 1, "per_page": 20 }
}
```

### Validation Error
```json
{
  "error": "validation_failed",
  "details": [
    { "field": "title", "message": "Title is required" }
  ]
}
```

### Conflict Error
```json
{
  "error": "conflict",
  "message": "Todo was modified by another request",
  "current_updated_at": "2024-01-15T10:30:00Z"
}
```

## Resources

For detailed validation rules and implementation patterns, see:
- [references/domain-rules.md](references/domain-rules.md) - Extended validation logic, security considerations, and business rules
