# CRUD Patterns Reference

## Table of Contents
1. [Standard CRUD Route Template](#1-standard-crud-route-template)
2. [Pagination (Offset and Cursor)](#2-pagination-offset-and-cursor)
3. [Filtering and Sorting](#3-filtering-and-sorting)
4. [Zod Validation Schemas](#4-zod-validation-schemas)
5. [Error Codes and Handler](#5-error-codes-and-handler)
6. [PostgreSQL Base Schema](#6-postgresql-base-schema)

---

## 1. Standard CRUD Route Template

```ts
import { Router } from 'express';
import { db } from '../db';
import { authenticate } from '../middleware/auth';
import { validate } from '../middleware/validate';
import { CreateResourceSchema, UpdateResourceSchema, QuerySchema } from '../schemas/resource';

const router = Router();
router.use(authenticate); // protect all resource routes

// GET /resources — list with pagination, filtering, sorting
router.get('/', validate('query', QuerySchema), async (req, res, next) => {
  // See Section 2 and 3 for query building
});

// GET /resources/:id
router.get('/:id', async (req, res, next) => {
  try {
    const { rows: [item] } = await db.query(
      'SELECT * FROM resources WHERE id = $1 AND deleted_at IS NULL',
      [req.params.id]
    );
    if (!item) return res.status(404).json({ error: 'NOT_FOUND' });
    res.json({ data: item });
  } catch (err) { next(err); }
});

// POST /resources
router.post('/', validate('body', CreateResourceSchema), async (req, res, next) => {
  try {
    const { rows: [item] } = await db.query(
      `INSERT INTO resources (name, description, user_id)
       VALUES ($1, $2, $3) RETURNING *`,
      [req.body.name, req.body.description, req.user!.sub]
    );
    res.status(201).json({ data: item });
  } catch (err) { next(err); }
});

// PATCH /resources/:id — partial update
router.patch('/:id', validate('body', UpdateResourceSchema), async (req, res, next) => {
  const allowed = ['name', 'description', 'status'];
  const fields = Object.keys(req.body).filter(k => allowed.includes(k));
  if (fields.length === 0) return res.status(400).json({ error: 'NO_FIELDS' });

  const sets  = fields.map((f, i) => `${f} = $${i + 2}`).join(', ');
  const vals  = fields.map(f => req.body[f]);

  try {
    const { rows: [item] } = await db.query(
      `UPDATE resources SET ${sets}, updated_at = NOW()
       WHERE id = $1 AND deleted_at IS NULL RETURNING *`,
      [req.params.id, ...vals]
    );
    if (!item) return res.status(404).json({ error: 'NOT_FOUND' });
    res.json({ data: item });
  } catch (err) { next(err); }
});

// DELETE /resources/:id — SOFT DELETE (sets deleted_at)
router.delete('/:id', async (req, res, next) => {
  try {
    const { rowCount } = await db.query(
      `UPDATE resources SET deleted_at = NOW(), updated_at = NOW()
       WHERE id = $1 AND deleted_at IS NULL AND user_id = $2`,
      [req.params.id, req.user!.sub]
    );
    if (!rowCount) return res.status(404).json({ error: 'NOT_FOUND' });
    res.status(204).send();
  } catch (err) { next(err); }
});

export { router as resourceRouter };
```

---

## 2. Pagination (Offset and Cursor)

### Offset-based (simple, supports random page access)

```ts
// Query schema: ?page=1&limit=20
const page  = Math.max(1, parseInt(req.query.page as string) || 1);
const limit = Math.min(100, Math.max(1, parseInt(req.query.limit as string) || 20));
const offset = (page - 1) * limit;

const [{ rows: items }, { rows: [{ count }] }] = await Promise.all([
  db.query(
    `SELECT * FROM resources WHERE deleted_at IS NULL
     ORDER BY created_at DESC LIMIT $1 OFFSET $2`,
    [limit, offset]
  ),
  db.query('SELECT COUNT(*) FROM resources WHERE deleted_at IS NULL'),
]);

res.json({
  data: items,
  meta: { total: parseInt(count), page, limit, pages: Math.ceil(count / limit) },
});
```

### Cursor-based (efficient for large datasets, no skipped/duplicate rows)

```ts
// Query: ?cursor=<base64-encoded-id>&limit=20
const cursor = req.query.cursor
  ? Buffer.from(req.query.cursor as string, 'base64').toString()
  : null;

const { rows: items } = await db.query(
  `SELECT * FROM resources
   WHERE deleted_at IS NULL ${cursor ? 'AND id < $2' : ''}
   ORDER BY id DESC LIMIT $1`,
  cursor ? [limit + 1, cursor] : [limit + 1]
);

const hasMore = items.length > limit;
const page    = hasMore ? items.slice(0, limit) : items;
const nextCursor = hasMore
  ? Buffer.from(String(page[page.length - 1].id)).toString('base64')
  : null;

res.json({ data: page, meta: { nextCursor, hasMore } });
```

---

## 3. Filtering and Sorting

**Safe dynamic WHERE clause builder** — never interpolate user values into SQL strings:

```ts
interface QueryParams {
  status?:   string;
  search?:   string;
  sortBy?:   string;
  sortDir?:  'asc' | 'desc';
}

const ALLOWED_SORT_COLUMNS = new Set(['name', 'created_at', 'updated_at', 'status']);

function buildListQuery(params: QueryParams, userId: string) {
  const conditions: string[] = ['deleted_at IS NULL', 'user_id = $1'];
  const values: unknown[]    = [userId];

  if (params.status) {
    values.push(params.status);
    conditions.push(`status = $${values.length}`);
  }

  if (params.search) {
    values.push(`%${params.search.replace(/[%_]/g, '\\$&')}%`); // escape LIKE wildcards
    conditions.push(`(name ILIKE $${values.length} OR description ILIKE $${values.length})`);
  }

  // Validate sort column against allowlist — never trust user input for column names
  const sortCol = ALLOWED_SORT_COLUMNS.has(params.sortBy ?? '') ? params.sortBy : 'created_at';
  const sortDir = params.sortDir === 'asc' ? 'ASC' : 'DESC';

  const where = conditions.join(' AND ');
  return {
    sql: `SELECT * FROM resources WHERE ${where} ORDER BY ${sortCol} ${sortDir}`,
    values,
  };
}
```

**Critical:** Column names and sort direction MUST be validated against an allowlist — they cannot be parameterized in SQL.

---

## 4. Zod Validation Schemas

```ts
// src/schemas/resource.ts
import { z } from 'zod';

export const CreateResourceSchema = z.object({
  name:        z.string().min(1).max(200),
  description: z.string().max(2000).optional(),
  status:      z.enum(['draft', 'active', 'archived']).default('draft'),
});

export const UpdateResourceSchema = CreateResourceSchema.partial();

export const QuerySchema = z.object({
  page:    z.coerce.number().int().min(1).default(1),
  limit:   z.coerce.number().int().min(1).max(100).default(20),
  status:  z.enum(['draft', 'active', 'archived']).optional(),
  search:  z.string().max(200).optional(),
  sortBy:  z.enum(['name', 'created_at', 'updated_at', 'status']).default('created_at'),
  sortDir: z.enum(['asc', 'desc']).default('desc'),
  cursor:  z.string().optional(),
});
```

**Validate middleware factory** (used in routes as `validate('body', Schema)`):

```ts
// src/middleware/validate.ts
import { z } from 'zod';
import { Request, Response, NextFunction } from 'express';

export function validate<T extends z.ZodTypeAny>(
  source: 'body' | 'query' | 'params',
  schema: T
) {
  return (req: Request, res: Response, next: NextFunction) => {
    const result = schema.safeParse(req[source]);
    if (!result.success) {
      return res.status(400).json({
        error: 'VALIDATION_ERROR',
        details: result.error.flatten(),
      });
    }
    req[source] = result.data; // replace with parsed/coerced values
    next();
  };
}
```

---

## 5. Error Codes and Handler

```ts
// src/middleware/errorHandler.ts
export function errorHandler(err: any, req: any, res: any, _next: any) {
  req.log?.error({ err }, 'Unhandled error');

  // PostgreSQL constraint violations
  if (err.code === '23505') { // unique_violation
    return res.status(409).json({ error: 'DUPLICATE_ENTRY', message: err.detail });
  }
  if (err.code === '23503') { // foreign_key_violation
    return res.status(409).json({ error: 'REFERENCE_ERROR', message: err.detail });
  }
  if (err.code === '22P02') { // invalid_text_representation (bad UUID/int)
    return res.status(400).json({ error: 'INVALID_ID', message: 'Invalid ID format' });
  }

  res.status(500).json({
    error: 'INTERNAL_ERROR',
    message: 'Internal server error',
    requestId: req.id,
  });
}
```

**Standard error code taxonomy:**

| HTTP | Code | Cause |
|---|---|---|
| 400 | `VALIDATION_ERROR` | Zod parse failure |
| 400 | `NO_FIELDS` | PATCH with no recognized fields |
| 401 | `AUTH_MISSING` | No Authorization header |
| 401 | `TOKEN_EXPIRED` | JWT expired |
| 401 | `TOKEN_INVALID` | JWT invalid or tampered |
| 401 | `INVALID_CREDENTIALS` | Login with wrong password |
| 403 | `FORBIDDEN` | Valid token, wrong role |
| 404 | `NOT_FOUND` | Row missing or soft-deleted |
| 409 | `DUPLICATE_ENTRY` | Unique constraint violated |
| 409 | `EMAIL_TAKEN` | Register with existing email |
| 429 | `RATE_LIMIT_EXCEEDED` | Too many requests |
| 500 | `INTERNAL_ERROR` | Unhandled exception |

---

## 6. PostgreSQL Base Schema

```sql
-- migrations/001_base_schema.sql

-- Users table
CREATE TABLE users (
  id            BIGSERIAL PRIMARY KEY,
  email         TEXT        NOT NULL UNIQUE,
  password_hash TEXT        NOT NULL,
  name          TEXT        NOT NULL,
  role          TEXT        NOT NULL DEFAULT 'user'
                  CHECK (role IN ('user', 'admin')),
  deleted_at    TIMESTAMPTZ,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users (email) WHERE deleted_at IS NULL;

-- Generic resource table (adapt per domain)
CREATE TABLE resources (
  id          BIGSERIAL PRIMARY KEY,
  user_id     BIGINT      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name        TEXT        NOT NULL CHECK (length(name) > 0),
  description TEXT,
  status      TEXT        NOT NULL DEFAULT 'draft'
                CHECK (status IN ('draft', 'active', 'archived')),
  deleted_at  TIMESTAMPTZ,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_resources_user   ON resources (user_id, created_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX idx_resources_status ON resources (status) WHERE deleted_at IS NULL;

-- Refresh tokens for JWT rotation
CREATE TABLE refresh_tokens (
  id          BIGSERIAL PRIMARY KEY,
  user_id     BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token_hash  TEXT   NOT NULL UNIQUE,
  expires_at  TIMESTAMPTZ NOT NULL,
  revoked_at  TIMESTAMPTZ,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_refresh_tokens_user ON refresh_tokens (user_id) WHERE revoked_at IS NULL;

-- updated_at trigger (apply to every table)
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$;

CREATE TRIGGER trg_users_updated_at     BEFORE UPDATE ON users     FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_resources_updated_at BEFORE UPDATE ON resources FOR EACH ROW EXECUTE FUNCTION set_updated_at();
```
