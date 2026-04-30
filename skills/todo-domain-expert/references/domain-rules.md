# Todo Domain Rules - Extended Reference

## Table of Contents
1. [Security Considerations](#security-considerations)
2. [Data Integrity Rules](#data-integrity-rules)
3. [Business Logic Patterns](#business-logic-patterns)
4. [Error Handling](#error-handling)
5. [Query Patterns](#query-patterns)
6. [Testing Scenarios](#testing-scenarios)

---

## Security Considerations

### Authentication & Authorization
- Every API endpoint MUST verify the authenticated user
- `user_id` on todos MUST match the authenticated user's ID for all operations
- Never expose todos belonging to other users, even in error messages
- Admin endpoints require separate role verification

### Input Sanitization
- Sanitize all string inputs to prevent XSS
- Use parameterized queries to prevent SQL injection
- Validate UUIDs format before database queries
- Rate limit create/update operations per user

### Data Exposure
- Never return `user_id` in public API responses (only in admin contexts)
- Strip internal fields from responses (database IDs, audit fields if sensitive)
- Log access patterns for security auditing

---

## Data Integrity Rules

### Immutable Fields
These fields MUST NOT be modifiable after creation:
- `id` - Primary identifier
- `created_at` - Creation timestamp
- `user_id` - Owner reference

### Server-Managed Fields
These fields MUST be set by the server, never accepted from client:
- `id` - Generate UUID v4 server-side
- `created_at` - Set to `NOW()` on insert
- `updated_at` - Set to `NOW()` on every update
- `completed_at` - Set/cleared based on status transitions

### Cascade Rules
When deleting a user:
- Option A: Cascade delete all user's todos
- Option B: Orphan todos (set `user_id` to null) - requires schema change
- Option C: Block user deletion if todos exist

---

## Business Logic Patterns

### Status Transition Matrix

| From \ To   | pending | completed | archived |
|-------------|---------|-----------|----------|
| pending     | -       | YES       | YES      |
| completed   | YES     | -         | YES      |
| archived    | YES     | NO        | -        |

### Transition Side Effects

```
on_transition(from, to):
  if to == 'completed':
    set completed_at = NOW()
  elif from == 'completed':
    set completed_at = NULL

  always:
    set updated_at = NOW()
```

### Priority Ordering
When sorting by priority:
1. `high` (value: 3)
2. `medium` (value: 2)
3. `low` (value: 1)
4. `null` (no priority - sort last or first based on preference)

### Due Date Logic
- Overdue: `due_date < NOW() AND status = 'pending'`
- Due today: `due_date` is within current day (timezone-aware)
- Upcoming: `due_date` is within next 7 days

---

## Error Handling

### HTTP Status Codes
- `200` - Success (GET, PUT/PATCH with body)
- `201` - Created (POST)
- `204` - No Content (DELETE, PUT without body)
- `400` - Bad Request (validation errors)
- `401` - Unauthorized (not authenticated)
- `403` - Forbidden (authenticated but not authorized)
- `404` - Not Found (todo doesn't exist or belongs to another user)
- `409` - Conflict (optimistic locking failure)
- `422` - Unprocessable Entity (semantic errors)
- `429` - Too Many Requests (rate limited)

### Error Response Format
```json
{
  "error": "error_code",
  "message": "Human readable message",
  "details": [
    {
      "field": "field_name",
      "code": "specific_error_code",
      "message": "Field-specific message"
    }
  ],
  "request_id": "uuid-for-tracing"
}
```

### Validation Error Codes
- `required` - Field is required but missing
- `invalid_format` - Value doesn't match expected format
- `too_long` - Exceeds maximum length
- `too_short` - Below minimum length
- `invalid_enum` - Value not in allowed set
- `invalid_date` - Date/time parsing failed
- `immutable` - Attempted to modify immutable field

---

## Query Patterns

### List Todos with Filters
```sql
SELECT * FROM todos
WHERE user_id = :user_id
  AND (:status IS NULL OR status = :status)
  AND (:priority IS NULL OR priority = :priority)
  AND (:due_before IS NULL OR due_date <= :due_before)
  AND (:due_after IS NULL OR due_date >= :due_after)
ORDER BY created_at DESC
LIMIT :limit OFFSET :offset
```

### Count for Pagination
```sql
SELECT COUNT(*) FROM todos
WHERE user_id = :user_id
  AND (:status IS NULL OR status = :status)
  -- same filters as above
```

### Optimistic Locking Update
```sql
UPDATE todos
SET title = :title,
    description = :description,
    status = :status,
    priority = :priority,
    due_date = :due_date,
    updated_at = NOW(),
    completed_at = CASE
      WHEN :status = 'completed' THEN NOW()
      ELSE NULL
    END
WHERE id = :id
  AND user_id = :user_id
  AND updated_at = :expected_updated_at
RETURNING *
```

If `RETURNING` returns 0 rows, either:
- Todo doesn't exist → 404
- User doesn't own it → 404 (don't leak existence)
- `updated_at` mismatch → 409 Conflict

---

## Testing Scenarios

### Unit Test Cases

**Create:**
- Valid todo with all fields
- Valid todo with minimal fields (only title)
- Missing required title → 400
- Title too long (>255 chars) → 400
- Title only whitespace → 400
- Invalid status enum → 400
- Invalid priority enum → 400
- Invalid due_date format → 400

**Read:**
- Get own todo by ID → 200
- Get another user's todo → 404
- Get non-existent todo → 404
- List with no filters → 200 + pagination
- List with status filter → filtered results
- List with multiple filters → combined filters

**Update:**
- Valid update → 200
- Update non-existent → 404
- Update another user's todo → 404
- Update immutable field (id) → 400
- Optimistic lock conflict → 409
- Invalid status transition (archived→completed) → 400

**Delete:**
- Delete own todo → 204
- Delete another user's todo → 404
- Delete non-existent → 404

### Integration Test Scenarios

1. **Full lifecycle:** Create → Read → Update → Complete → Archive → Delete
2. **Concurrent edit:** Two clients update same todo, one gets 409
3. **Pagination:** Create 50 todos, verify pagination works correctly
4. **Filter combinations:** Test all filter combinations return correct results
5. **User isolation:** Verify user A cannot see/modify user B's todos

### Edge Case Tests

- Empty title after trim: `"   "` → 400
- Maximum length title (255 chars) → 200
- Maximum length description (2000 chars) → 200
- Due date in far past → 200 (allowed)
- Due date in far future → 200 (allowed)
- Null vs missing optional fields
- Unicode in title/description
- SQL injection attempts in filters
- XSS attempts in title/description
