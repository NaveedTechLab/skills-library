# Express.js Debugging Reference

## Table of Contents
1. [Async Error Handling](#1-async-error-handling)
2. [Middleware Ordering](#2-middleware-ordering)
3. [Common 4xx/5xx Patterns](#3-common-4xx5xx-patterns)
4. [SQL Injection — ORM Patterns](#4-sql-injection--orm-patterns)
5. [Request Validation](#5-request-validation)

---

## 1. Async Error Handling

Express 4 does not catch rejected promises automatically. Every async route must either use try/catch or a wrapper.

**Pattern A — try/catch (explicit):**
```js
router.get('/user/:id', async (req, res, next) => {
  try {
    const user = await User.findById(req.params.id);
    if (!user) return res.status(404).json({ error: 'Not found' });
    res.json(user);
  } catch (err) {
    next(err); // passes to error-handling middleware
  }
});
```

**Pattern B — async wrapper (DRY):**
```js
const asyncHandler = fn => (req, res, next) =>
  Promise.resolve(fn(req, res, next)).catch(next);

router.get('/user/:id', asyncHandler(async (req, res) => {
  const user = await User.findById(req.params.id);
  res.json(user);
}));
```

**Error-handling middleware (must be last, with 4 params):**
```js
app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(err.status || 500).json({ error: err.message || 'Internal server error' });
});
```

---

## 2. Middleware Ordering

Order matters. Common mistakes:

```js
// WRONG: body parser after routes
app.get('/data', handler);
app.use(express.json()); // too late — req.body is undefined in handler

// CORRECT
app.use(express.json());
app.use(cors());
app.use('/api', router);
app.use(errorHandler); // error middleware last
```

Correct order:
1. Security middleware (helmet, cors)
2. Body parsers (express.json, express.urlencoded)
3. Auth middleware
4. Routes
5. 404 handler
6. Error handler

---

## 3. Common 4xx/5xx Patterns

**404 — Route not matched:**
- Check method (GET vs POST)
- Check if route is inside an `app.use('/prefix', router)` — path in router is relative
- Check if a catch-all route (`app.use('*', ...)`) appears before this route

**400 — req.body is undefined:**
- `express.json()` or `express.urlencoded()` middleware is missing or after the route

**401/403 — Auth failures:**
- Verify JWT secret matches between signing and verification
- Check token expiry (`exp` claim)
- Confirm `Authorization: Bearer <token>` header format

**500 — Unhandled promise rejection:**
- Add `try/catch` or async wrapper (see Section 1)
- Check DB connection — pool exhaustion causes silent hangs

**Request hangs (no response):**
- Missing `res.send()`, `res.json()`, or `next()` in at least one code path
- Middleware that conditionally calls `next()` but omits it in an else branch

---

## 4. SQL Injection — ORM Patterns

### Raw queries (mysql2 / pg / better-sqlite3)
```js
// VULNERABLE
db.query(`SELECT * FROM orders WHERE user_id = ${userId}`);

// SAFE — positional placeholder
db.query('SELECT * FROM orders WHERE user_id = ?', [userId]);          // mysql2
db.query('SELECT * FROM orders WHERE user_id = $1', [userId]);         // pg
```

### Knex
```js
// VULNERABLE
knex.raw(`SELECT * FROM users WHERE email = '${email}'`);

// SAFE
knex('users').where({ email });
knex.raw('SELECT * FROM users WHERE email = ?', [email]);
```

### Sequelize
```js
// VULNERABLE
User.findAll({ where: sequelize.literal(`name = '${name}'`) });

// SAFE
User.findAll({ where: { name } });
User.findAll({ where: sequelize.literal('name = :name'), replacements: { name } });
```

### TypeORM
```js
// VULNERABLE
repo.query(`SELECT * FROM user WHERE id = ${id}`);

// SAFE
repo.findOne({ where: { id } });
repo.createQueryBuilder('u').where('u.id = :id', { id }).getOne();
```

**Checklist when auditing for SQL injection:**
- [ ] No template literals containing `req.*` values inside SQL strings
- [ ] All `knex.raw()` calls use `?` placeholders
- [ ] All `sequelize.literal()` calls use `:param` replacements
- [ ] All ORM query builders use object conditions, not string conditions

---

## 5. Request Validation

Validate at the boundary before the value reaches any query or business logic.

```js
// Using express-validator
import { param, body, validationResult } from 'express-validator';

router.get('/user/:id',
  param('id').isInt({ min: 1 }).toInt(),
  (req, res, next) => {
    const errors = validationResult(req);
    if (!errors.isEmpty()) return res.status(400).json({ errors: errors.array() });
    next();
  },
  asyncHandler(async (req, res) => {
    const user = await User.findById(req.params.id); // safe — validated integer
    res.json(user);
  })
);
```

Using Zod for schema validation:
```js
import { z } from 'zod';

const CreateUserSchema = z.object({
  email: z.string().email(),
  age: z.number().int().min(0).max(120),
});

router.post('/user', asyncHandler(async (req, res) => {
  const data = CreateUserSchema.parse(req.body); // throws ZodError on invalid input
  const user = await User.create(data);
  res.status(201).json(user);
}));
```
