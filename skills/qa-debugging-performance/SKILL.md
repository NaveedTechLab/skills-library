---
name: qa-debugging-performance
description: "Debug APIs, fix vulnerabilities, and optimize frontend performance. Use when the user needs to: (1) debug Express.js API routes or middleware errors, (2) identify and fix SQL injection vulnerabilities, (3) optimize React component re-renders, (4) create or improve custom React hooks like useDebounce, or (5) improve overall code quality in a full-stack JS/TS application. Triggers on keywords like: debug, fix bug, SQL injection, re-render, performance, useDebounce, hook, slow, vulnerable."
---

# QA Debugging & Performance

Diagnose first, fix second. Never patch a symptom without identifying the root cause.

## Workflow

```
1. Identify the problem class (bug | vulnerability | performance | code quality)
2. Locate the root cause (read code, trace call stack, inspect data flow)
3. Confirm the hypothesis (reproduce or reason through the failure path)
4. Apply the minimal fix
5. Verify the fix did not introduce regressions
```

**Constraint:** Do not propose a fix until root cause is stated explicitly.

---

## 1. Express.js Debugging

See [references/express-debugging.md](references/express-debugging.md) for:
- Common error patterns and how to trace them
- Middleware ordering issues
- Async error handling
- SQL injection prevention patterns

**Quick triage:**

| Symptom | Likely root cause |
|---|---|
| 404 on valid route | Route defined after catch-all, or wrong HTTP verb |
| 500 with no message | Unhandled promise rejection in async handler |
| Request hangs | Missing `next()` or `res.send()` in middleware |
| CORS error | `cors()` middleware positioned after route definitions |
| SQL returns unexpected data | Unsanitized user input interpolated into query string |

---

## 2. SQL Injection Prevention

**Root cause check:** Is user-supplied data concatenated directly into a SQL string?

```js
// VULNERABLE - always flag this pattern
const q = `SELECT * FROM users WHERE id = ${req.params.id}`;

// SAFE - parameterized query
const q = 'SELECT * FROM users WHERE id = ?';
db.query(q, [req.params.id]);

// SAFE - named parameters (pg, knex, TypeORM)
const q = 'SELECT * FROM users WHERE id = :id';
db.query(q, { id: req.params.id });
```

When fixing SQL injection:
1. Identify every place user input touches a query
2. Replace string interpolation/concatenation with parameterized queries
3. Ensure ORM query builders are used with bound parameters, not raw string injection

See [references/express-debugging.md](references/express-debugging.md) for ORM-specific patterns.

---

## 3. React Performance Optimization

See [references/react-performance.md](references/react-performance.md) for detailed patterns.

**Root cause check for re-renders:**

1. Open React DevTools Profiler and record the interaction
2. Identify which component re-rendered and why (prop change, context change, parent re-render)
3. Determine if the re-render is necessary or wasteful

**Decision tree:**

```
Re-render detected
  -> Is the component's output different? (necessary re-render) -> no action needed
  -> Same output? (wasteful re-render)
       -> Caused by new object/array/function reference each render?
            -> Wrap value in useMemo / useCallback
       -> Caused by parent re-render with irrelevant state?
            -> Wrap component in React.memo
       -> Caused by expensive computation?
            -> Memoize with useMemo
       -> Caused by high-frequency event (input, scroll, resize)?
            -> Apply useDebounce or useThrottle
```

---

## 4. Custom Hooks

**useDebounce** — canonical implementation:

```ts
import { useState, useEffect } from 'react';

function useDebounce<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState<T>(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);

  return debounced;
}
```

Usage: `const debouncedQuery = useDebounce(searchInput, 300);`

When creating other custom hooks:
- Single responsibility: one hook = one concern
- Return a stable API (avoid returning new object references unless values changed)
- Include cleanup in `useEffect` return when subscribing to external sources

---

## 5. Code Quality

Before suggesting refactors, confirm the change is requested or clearly necessary for the fix.

| Issue | Fix |
|---|---|
| Deep prop drilling | Extract context or lift state |
| Repeated fetch logic | Custom hook (`useResource`, `useFetch`) |
| Magic numbers/strings | Named constants |
| Inconsistent error handling | Centralized error boundary + Express error middleware |
| Large component | Extract sub-components; apply single-responsibility |

---

## Resources

- [references/express-debugging.md](references/express-debugging.md) — Express error patterns, async handling, ORM query safety
- [references/react-performance.md](references/react-performance.md) — Re-render diagnosis, memo patterns, hook recipes

## When NOT to Use This Skill

- **Premature optimization** — profile before optimizing; don't use this skill until you've measured and identified an actual bottleneck
- **Non-performance bugs** (logic errors, data corruption) — this skill focuses on performance debugging; functional bugs need a different debugging approach
- **Infrastructure-level bottlenecks** — if the slowness is in the database, network, or disk I/O, address infrastructure first; application-level optimization won't help much

## Common Mistakes

- Optimizing the wrong code path — always profile first; developers frequently optimize code that isn't the actual bottleneck
- Measuring performance in development mode — Next.js, React, and most frameworks run significantly slower in development mode; always benchmark in production builds
- Not establishing a performance baseline before optimizing — without a before-measurement, you can't tell if changes improved anything

## Related Skills

- [`qa-auditor`](../qa-auditor/SKILL.md) — Audit-level quality review that surfaces performance issues
- [`qa-testing-specialist`](../qa-testing-specialist/SKILL.md) — Build the test suite including performance regression tests
- [`webapp-testing`](../webapp-testing/SKILL.md) — End-to-end testing including performance scenario coverage
