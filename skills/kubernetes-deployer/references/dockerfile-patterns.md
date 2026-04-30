# Dockerfile Patterns

## Table of Contents
1. [Multi-Stage Builds](#multi-stage-builds)
2. [Language-Specific Templates](#language-specific-templates)
3. [Security Best Practices](#security-best-practices)
4. [Optimization Tips](#optimization-tips)

---

## Multi-Stage Builds

### Why Multi-Stage?
- Smaller final images (no build tools)
- Faster deployments
- Reduced attack surface

### Pattern

```dockerfile
# Stage 1: Build
FROM <build-image> AS builder
WORKDIR /build
COPY . .
RUN <build-commands>

# Stage 2: Runtime
FROM <runtime-image>
WORKDIR /app
COPY --from=builder /build/<artifacts> .
CMD ["<start-command>"]
```

---

## Language-Specific Templates

### Python (FastAPI/Flask)

```dockerfile
# Build stage
FROM python:3.11-slim AS builder
WORKDIR /build
COPY pyproject.toml ./
RUN pip install --no-cache-dir .

# Runtime stage
FROM python:3.11-slim
WORKDIR /app

# Create non-root user
RUN useradd -m -u 1000 appuser

# Copy installed packages
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application
COPY app ./app

USER appuser
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Node.js (Next.js)

```dockerfile
# Dependencies stage
FROM node:20-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

# Build stage
FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# Runtime stage
FROM node:20-alpine
WORKDIR /app

RUN addgroup -g 1001 -S nodejs && adduser -S nextjs -u 1001

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000

ENV PORT 3000
ENV HOSTNAME "0.0.0.0"

HEALTHCHECK --interval=30s --timeout=3s \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3000/api/health || exit 1

CMD ["node", "server.js"]
```

### Go

```dockerfile
# Build stage
FROM golang:1.21-alpine AS builder
WORKDIR /build
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-w -s" -o server .

# Runtime stage
FROM scratch
WORKDIR /app
COPY --from=builder /build/server .
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/

EXPOSE 8080
ENTRYPOINT ["/app/server"]
```

---

## Security Best Practices

### Non-Root User

```dockerfile
# Create user in build stage or runtime
RUN addgroup -g 1001 -S appgroup && \
    adduser -S appuser -u 1001 -G appgroup

# Switch before CMD
USER appuser
```

### Read-Only Filesystem

```dockerfile
# In Kubernetes, set:
# securityContext:
#   readOnlyRootFilesystem: true

# Ensure app writes to /tmp or mounted volumes only
```

### No Secrets in Image

```dockerfile
# WRONG
ENV DATABASE_PASSWORD=secret123

# RIGHT - pass at runtime
ENV DATABASE_PASSWORD=""
# Set via Kubernetes secrets
```

### Minimal Base Images

| Language | Recommended Base |
|----------|-----------------|
| Python | python:3.11-slim |
| Node.js | node:20-alpine |
| Go | scratch or distroless |
| Java | eclipse-temurin:17-jre-alpine |

---

## Optimization Tips

### Layer Caching

```dockerfile
# Dependencies first (changes less often)
COPY package*.json ./
RUN npm ci

# Source code last (changes most often)
COPY . .
RUN npm run build
```

### .dockerignore

```
node_modules
.git
.env
*.log
__pycache__
.pytest_cache
.next
dist
build
```

### Image Size Reduction

```dockerfile
# Combine RUN commands
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Use --no-cache for pip
RUN pip install --no-cache-dir -r requirements.txt

# Remove build dependencies
RUN apk add --no-cache --virtual .build-deps gcc musl-dev && \
    pip install package && \
    apk del .build-deps
```
