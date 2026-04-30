---
name: backend-rest-api
description: "Build secure RESTful APIs with authentication, validation, and PostgreSQL integration. Use when the user needs to: (1) design CRUD endpoints with consistent response envelopes, (2) implement JWT authentication with protected routes, (3) validate and sanitize request input with Zod, (4) design PostgreSQL schemas with soft delete (deleted_at), (5) add cursor or offset-based pagination with filtering and sorting, or (6) apply rate limiting (100 req/min/IP). Triggers on keywords like: REST API, CRUD, JWT, auth, pagination, rate limit, soft delete, Express router, validation, filtering, sorting."
---

# Backend REST API

Build secure, consistent, and observable REST APIs.

## Build Workflow

```
1. Define the resource schema (PostgreSQL) with soft-delete columns
2. Write the Zod validation schemas (body, query, params)
3. Implement auth middleware (JWT verify + attach user)
4. Build CRUD route handlers — use soft delete on DELETE
5. Add pagination/filtering/sorting to list endpoints
6. Apply rate limiter middleware globally
7. Wire error handler last (4-param middleware)
```

**Constraints — enforce always:**
- DELETE routes set `deleted_at = NOW()`, never `DELETE FROM`
- All queries filter `WHERE deleted_at IS NULL` by default
- Rate limit: 100 requests/minute/IP (global); stricter on auth routes (10/min)

---

## Boilerplate Template

A complete starter scaffold is in `assets/api-template/`. Files included:

```
api-template/
├── src/
│   ├── index.ts              App wiring + server
│   ├── db.ts                 pg Pool singleton
│   ├── config/env.ts         Env validation (Zod)
│   ├── middleware/
│   │   ├── auth.ts           JWT verify middleware
│   │   ├── rateLimiter.ts    express-rate-limit (100/min global, 10/min auth)
│   │   ├── validate.ts       Zod request validator factory
│   │   └── errorHandler.ts   Centralized error handler
│   └── routes/
│       └── resource.ts       CRUD template with soft delete + pagination
└── migrations/
    └── 001_base_schema.sql   Base table with audit + soft-delete columns
```

---

## 1. Soft Delete — Non-Negotiable Pattern

```sql
-- Every resource table must include these columns
deleted_at  TIMESTAMPTZ,        -- NULL = active; NOT NULL = deleted
created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
```

```ts
// DELETE handler — always soft delete
router.delete('/:id', authenticate, async (req, res, next) => {
  await db.query(
    'UPDATE resources SET deleted_at = NOW(), updated_at = NOW() WHERE id = $1 AND deleted_at IS NULL',
    [req.params.id]
  );
  res.status(204).send();
});

// Every SELECT must exclude deleted rows
const BASE_FILTER = 'WHERE r.deleted_at IS NULL';
```

---

## 2. Response Envelope

Use consistent structure across all endpoints:

```ts
// Success
res.json({ data: resource, meta: { requestId: req.id } });

// List
res.json({ data: items, meta: { total, page, limit, requestId: req.id } });

// Error (from error handler)
res.status(status).json({ error: CODE, message: '...', requestId: req.id });
```

---

## 3. Rate Limiting Setup

```ts
import rateLimit from 'express-rate-limit';

// Global: 100 req/min/IP
export const globalLimiter = rateLimit({
  windowMs: 60_000,
  max: 100,
  standardHeaders: true,
  legacyHeaders: false,
  message: { error: 'RATE_LIMIT_EXCEEDED', message: 'Too many requests' },
});

// Auth routes: 10 req/min/IP (brute-force protection)
export const authLimiter = rateLimit({ windowMs: 60_000, max: 10, ...});

app.use(globalLimiter);          // apply before all routes
app.use('/auth', authLimiter);   // stricter limit on auth endpoints
```

---

## Resources

- [references/auth.md](references/auth.md) — JWT signing/verification, protected route middleware, refresh tokens, password hashing
- [references/crud-patterns.md](references/crud-patterns.md) — Full CRUD templates, pagination (offset + cursor), filtering, sorting, error codes
- `assets/api-template/` — Complete boilerplate to copy and adapt
