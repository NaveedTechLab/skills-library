# Docker Reference

## Table of Contents
1. [Multi-Stage Dockerfile](#1-multi-stage-dockerfile)
2. [docker-compose Setup](#2-docker-compose-setup)
3. [Healthcheck Patterns](#3-healthcheck-patterns)
4. [Secrets and Environment Variables](#4-secrets-and-environment-variables)
5. [Build and Run Commands](#5-build-and-run-commands)
6. [Production Hardening](#6-production-hardening)

---

## 1. Multi-Stage Dockerfile

```dockerfile
# ---- Stage 1: Build ----
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci --include=dev

COPY tsconfig.json ./
COPY src/ ./src/
RUN npm run build   # outputs to dist/

# ---- Stage 2: Production ----
FROM node:20-alpine AS production

# Principle of least privilege — run as non-root user
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

WORKDIR /app

COPY package*.json ./
RUN npm ci --omit=dev --ignore-scripts && npm cache clean --force

COPY --from=builder /app/dist ./dist

USER appuser

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -qO- http://localhost:3000/health || exit 1

CMD ["node", "dist/index.js"]
```

Key decisions:
- `node:20-alpine` — minimal image (~50MB vs ~900MB for full node)
- `npm ci --omit=dev` in production — no devDependencies shipped
- Non-root user — required for security compliance
- `--ignore-scripts` in production — prevents malicious postinstall scripts

---

## 2. docker-compose Setup

```yaml
# docker-compose.yml
version: '3.9'

services:
  ai-service:
    build:
      context: .
      target: production
    ports:
      - "3000:3000"
    environment:
      # Secrets: value comes from shell env or .env file — NO default values
      - LLM_API_KEY
      # Non-sensitive config: defaults are fine
      - LLM_BASE_URL=https://api.openai.com/v1
      - LLM_MODEL=gpt-4o-mini
      - NODE_ENV=production
      - LOG_LEVEL=info
      - PORT=3000
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost:3000/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 15s
    restart: unless-stopped
    # Memory limit — prevents runaway processes
    deploy:
      resources:
        limits:
          memory: 512M

  # Optional: nginx reverse proxy for production
  # nginx:
  #   image: nginx:alpine
  #   ports: ["80:80", "443:443"]
  #   volumes: ["./nginx.conf:/etc/nginx/nginx.conf:ro"]
  #   depends_on: [ai-service]
```

**Never commit `.env` files** — only commit `.env.example`.

```gitignore
# .gitignore additions
.env
.env.local
.env.*.local
```

---

## 3. Healthcheck Patterns

Every service must have a `/health` endpoint — checked by Docker, load balancers, and Kubernetes probes.

```ts
// Liveness: is the process alive?
app.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// Readiness: can the service handle traffic? (check dependencies)
app.get('/ready', async (req, res) => {
  try {
    // Verify LLM API key is present (don't call the API — too slow/expensive)
    if (!env.LLM_API_KEY) throw new Error('LLM_API_KEY not set');
    res.json({ status: 'ready' });
  } catch (err: any) {
    res.status(503).json({ status: 'not_ready', reason: err.message });
  }
});
```

---

## 4. Secrets and Environment Variables

**Hierarchy (most to least preferred):**

1. **Docker secrets** (Swarm/Kubernetes) — secret mounted as file, read at runtime
2. **Environment variable from shell** — passed via `docker run -e KEY=$KEY`
3. **`.env` file** — only for local development, never committed
4. **Hardcoded default in compose** — only for non-sensitive config

Reading a Docker secret from file (if using Swarm):
```ts
// src/config/env.ts — read from file if env var not set
import fs from 'fs';

function readSecret(envKey: string, secretPath: string): string {
  if (process.env[envKey]) return process.env[envKey]!;
  try { return fs.readFileSync(secretPath, 'utf8').trim(); } catch { return ''; }
}

const LLM_API_KEY = readSecret('LLM_API_KEY', '/run/secrets/llm_api_key');
```

**Audit check — before any commit:**
```bash
# Scan for hardcoded secrets patterns
grep -rn 'sk-\|Bearer \|password\s*=' src/ --include='*.ts'
```

---

## 5. Build and Run Commands

```bash
# Local development (hot reload)
npm run dev

# Build image
docker build --target production -t ai-service:latest .

# Run with env from shell
LLM_API_KEY=sk-... docker run -p 3000:3000 --env LLM_API_KEY ai-service:latest

# Run with .env file (local dev only)
docker run -p 3000:3000 --env-file .env ai-service:latest

# docker-compose (reads .env automatically)
docker compose up --build

# Check healthcheck status
docker inspect --format='{{json .State.Health}}' <container_id>
```

---

## 6. Production Hardening

```dockerfile
# Additional security hardening in Dockerfile

# Pin exact base image digest for reproducibility
FROM node:20.11.0-alpine3.19@sha256:<digest> AS builder

# Set NODE_ENV at build time
ENV NODE_ENV=production

# Read-only filesystem (except tmp)
# In docker-compose:
# read_only: true
# tmpfs: [/tmp]
```

```yaml
# docker-compose production additions
services:
  ai-service:
    read_only: true
    tmpfs:
      - /tmp
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
```

**Logging to stdout** (not to files) — Docker captures stdout/stderr automatically:
```ts
// pino writes to stdout by default — correct for containers
const logger = pino({ level: env.LOG_LEVEL });
// Never use winston file transports or write to /app/logs inside container
```
