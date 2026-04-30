---
name: backend-ai-microservice
description: "Build production-ready AI microservices with Docker and streaming support. Use when the user needs to: (1) create REST endpoints that call an LLM API (OpenAI, Anthropic, or compatible), (2) stream LLM responses to clients via SSE (Server-Sent Events), (3) containerize a Node.js/Express AI service with Dockerfile and docker-compose, (4) manage secrets via environment variables with runtime validation, (5) add structured logging with per-request correlation IDs. Triggers on keywords like: AI microservice, LLM endpoint, streaming, SSE, Dockerfile, docker-compose, request ID, logging, OpenAI API, Anthropic API, containerize, AI service."
---

# Backend AI Microservice

Build containerized, observable, and secrets-safe AI services.

## Build Workflow

```
1. Validate environment variables at startup (fail fast, never silently)
2. Add request ID middleware (first middleware in the chain)
3. Implement LLM client with retry and timeout
4. Build REST endpoint — non-streaming first, then add SSE variant
5. Write Dockerfile (multi-stage) and docker-compose.yml
6. Add .env.example; verify no secrets in committed files
```

**Constraints — enforce always:**
- API keys in environment variables only; never in code or docker-compose.yml defaults
- All containers must have `HEALTHCHECK` instructions
- Request IDs must appear in every log line

---

## Boilerplate Template

A complete starter scaffold is in `assets/microservice-template/`. Copy it as the starting point and adapt. Files included:

```
microservice-template/
├── src/
│   ├── index.ts              Express app + server startup
│   ├── config/env.ts         Env var validation (Zod)
│   ├── middleware/
│   │   ├── requestId.ts      Attach X-Request-ID to every request
│   │   └── logger.ts         Structured JSON logger (pino)
│   └── routes/
│       └── generate.ts       /generate (batch) + /generate/stream (SSE)
├── Dockerfile                Multi-stage Node.js build
├── docker-compose.yml        Service + healthcheck
├── .env.example              All required vars, no values
└── package.json
```

---

## 1. Environment Variable Management

```ts
// src/config/env.ts — validates at startup; throws if missing
import { z } from 'zod';

const EnvSchema = z.object({
  LLM_API_KEY:    z.string().min(1),
  LLM_BASE_URL:   z.string().url().default('https://api.openai.com/v1'),
  LLM_MODEL:      z.string().default('gpt-4o-mini'),
  PORT:           z.coerce.number().default(3000),
  LOG_LEVEL:      z.enum(['trace','debug','info','warn','error']).default('info'),
  NODE_ENV:       z.enum(['development','production','test']).default('development'),
});

export const env = EnvSchema.parse(process.env); // throws ZodError on missing vars
```

**NEVER** pass API keys as docker-compose `environment` defaults. Use `.env` file or a secrets manager:
```yaml
# docker-compose.yml — correct pattern
environment:
  - LLM_API_KEY       # reads from shell env or .env file — no default value
  - LLM_MODEL=gpt-4o-mini  # non-secret defaults are fine
```

---

## 2. Request ID Logging

```ts
// Every log line must include the request ID for traceability
import pino from 'pino';
import { randomUUID } from 'crypto';

export const rootLogger = pino({ level: env.LOG_LEVEL });

// middleware/requestId.ts
export function requestIdMiddleware(req, res, next) {
  req.id = (req.headers['x-request-id'] as string) ?? randomUUID();
  res.setHeader('x-request-id', req.id);
  req.log = rootLogger.child({ requestId: req.id });
  next();
}

// Usage in any handler
req.log.info({ userId, model }, 'LLM generation started');
```

---

## 3. SSE Streaming Pattern

```ts
router.get('/generate/stream', async (req, res) => {
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  res.flushHeaders();

  const stream = await llmClient.stream(req.query.prompt as string);

  for await (const chunk of stream) {
    res.write(`data: ${JSON.stringify({ text: chunk })}\n\n`);
  }

  res.write('data: [DONE]\n\n');
  res.end();
});
```

---

## Resources

- [references/llm-integration.md](references/llm-integration.md) — LLM client setup (OpenAI/Anthropic), streaming, retry logic, error taxonomy
- [references/docker.md](references/docker.md) — Multi-stage Dockerfile, docker-compose patterns, healthchecks, secrets injection
- `assets/microservice-template/` — Complete boilerplate to copy and adapt

## When NOT to Use This Skill

- **Simple CRUD APIs without AI features** — use `backend-rest-api` instead; adding AI infrastructure to a basic CRUD service is unnecessary complexity
- **Real-time streaming AI responses** — the microservice pattern adds latency; use a WebSocket-based skill like `realtime-websocket-system` for streaming
- **Single-page applications calling LLMs directly from the frontend** — always route AI calls through a backend service to protect API keys

## Common Mistakes

- Not implementing rate limiting per user — LLM APIs are expensive; without per-user limits a single abusive caller can exhaust your budget
- Hard-coding the model name in the service — make the model configurable via environment variable so you can switch models without redeployment
- Not caching repeated identical prompts — identical LLM calls with the same inputs are pure waste; add a prompt cache layer for deterministic queries

## Related Skills

- [`backend-rest-api`](../backend-rest-api/SKILL.md) — Build the REST API layer that wraps this AI microservice
- [`fastapi-backend-builder`](../fastapi-backend-builder/SKILL.md) — Full FastAPI application scaffolding including auth and DB
- [`mcp-builder`](../mcp-builder/SKILL.md) — Expose the AI microservice as an MCP server for Claude Code consumption
