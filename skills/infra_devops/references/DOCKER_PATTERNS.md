# Docker Containerization Patterns

## Overview

This document provides comprehensive guidance on Docker containerization patterns for the CRM platform. It covers best practices for Dockerfile creation, multi-stage builds, security considerations, and optimization techniques.

## Dockerfile Best Practices

### Multi-Stage Builds

#### Basic Multi-Stage Build
```dockerfile
# Build stage
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /wheels -r requirements.txt

# Production stage
FROM python:3.11-slim

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && mkdir -p /app \
    && chown -R app:app /app

WORKDIR /app

# Copy Python wheels from builder stage
COPY --from=builder /wheels /wheels
RUN pip install --no-cache /wheels/* \
    && rm -rf /wheels

# Copy application code
COPY --chown=app:app . .

# Switch to non-root user
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "app.py"]
```

#### Advanced Multi-Stage Build with Different Environments
```dockerfile
# Base stage
FROM python:3.11-slim as base

# Install common dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app

# Development stage
FROM base as development

# Install development dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    git \
    && rm -rf /var/lib/apt/lists/*

USER app

# Copy requirements and install all dependencies
COPY requirements-dev.txt requirements.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt

# Copy application code
COPY --chown=app:app . .

EXPOSE 8000
CMD ["python", "app.py", "--debug"]

# Builder stage for production
FROM base as builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /wheels -r requirements.txt

# Production stage
FROM base as production

# Copy and install wheels
COPY --from=builder /wheels /wheels
RUN pip install --no-cache /wheels/* \
    && rm -rf /wheels

# Copy application code
COPY --chown=app:app . .

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "app.py"]
```

### Security Best Practices

#### Minimal Base Images
```dockerfile
# Use minimal base images
FROM python:3.11-alpine

# Or use distroless images for production
# FROM gcr.io/distroless/python3-debian11

# Install only necessary packages
RUN apk add --no-cache \
    curl \
    dumb-init

WORKDIR /app

# Create non-root user with specific UID
RUN addgroup -g 1001 -S appgroup && \
    adduser -S appuser -u 1001 -G appgroup

# Copy application
COPY --chown=appuser:appgroup . .

USER appuser

EXPOSE 8000

# Use dumb-init to handle signals properly
ENTRYPOINT ["dumb-init", "--"]
CMD ["python", "app.py"]
```

#### Secure Layer Ordering
```dockerfile
FROM python:3.11-slim

# Install system dependencies first (they change less frequently)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create user early
RUN useradd --create-home --shell /bin/bash app

WORKDIR /app

# Copy requirements and install dependencies (changes less frequently than app code)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code last (changes most frequently)
COPY --chown=app:app . .

USER app

EXPOSE 8000
CMD ["python", "app.py"]
```

### Optimization Techniques

#### Layer Caching Optimization
```dockerfile
FROM python:3.11-slim

# Create user
RUN useradd --create-home --shell /bin/bash app

WORKDIR /app

# Copy and install requirements first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && rm -rf ~/.cache/pip

# Copy application code separately
COPY --chown=app:app . .

# Precompile Python bytecode
RUN python -m compileall .

USER app

EXPOSE 8000
CMD ["python", "app.py"]
```

#### Multi-architecture Builds
```dockerfile
# Use buildx for multi-platform builds
# docker buildx build --platform linux/amd64,linux/arm64 -t myapp:latest .

FROM --platform=$TARGETPLATFORM python:3.11-slim

RUN useradd --create-home --shell /bin/bash app

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=app:app . .

USER app

EXPOSE 8000
CMD ["python", "app.py"]
```

## Docker Compose for Development

### Multi-Service Development Environment
```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    build:
      context: .
      target: development
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=development
      - DATABASE_URL=postgresql://user:password@db:5432/mydb
      - REDIS_URL=redis://redis:6379
      - DEBUG=true
    depends_on:
      - db
      - redis
    volumes:
      - .:/app  # Live reload for development
      - /app/__pycache__  # Exclude Python cache
    restart: unless-stopped
    networks:
      - app-network

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: mydb
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    ports:
      - "5432:5432"  # For local debugging
    restart: unless-stopped
    networks:
      - app-network

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"  # For local debugging
    restart: unless-stopped
    networks:
      - app-network

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.dev.conf:/etc/nginx/nginx.conf
    depends_on:
      - app
    restart: unless-stopped
    networks:
      - app-network

  kafka:
    image: confluentinc/cp-kafka:latest
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
    depends_on:
      - zookeeper
    restart: unless-stopped
    networks:
      - app-network

  zookeeper:
    image: confluentinc/cp-zookeeper:latest
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000
    restart: unless-stopped
    networks:
      - app-network

volumes:
  postgres_data:

networks:
  app-network:
    driver: bridge
```

### Production-like Docker Compose
```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  app:
    image: myorg/crm-app:latest
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=postgresql://user:password@db:5432/mydb
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis
    restart: unless-stopped
    networks:
      - app-network
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: mydb
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped
    networks:
      - app-network
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    networks:
      - app-network
    deploy:
      resources:
        limits:
          memory: 256M
        reservations:
          memory: 128M

volumes:
  postgres_data:
    driver: local

networks:
  app-network:
    driver: overlay
```

## Docker Build Optimization

### BuildKit Features
```dockerfile
# Use BuildKit for advanced features
# Build with: DOCKER_BUILDKIT=1 docker build .

# syntax=docker/dockerfile:1
FROM python:3.11-slim

# Use cache mounts for pip cache
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt

# Use SSH mounts for git authentication
RUN --mount=type=ssh \
    git clone git@github.com:org/private-repo.git

# Use secret mounts for sensitive data during build
RUN --mount=type=secret,id=token \
    echo $(cat /run/secrets/token) > /app/token.txt
```

### Build Arguments
```dockerfile
FROM python:3.11-slim

ARG APP_ENV=production
ENV APP_ENV=${APP_ENV}

RUN useradd --create-home --shell /bin/bash app

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=app:app . .

# Conditionally install dev dependencies
RUN if [ "$APP_ENV" = "development" ] ; then \
        pip install --no-cache-dir -r requirements-dev.txt ; \
    fi

USER app

EXPOSE 8000
CMD ["python", "app.py"]
```

## Docker Security

### Docker Bench for Security
```bash
# Run Docker security benchmark
docker run --rm -it \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /etc:/etc:ro \
  -v /usr/bin/docker-containerd:/usr/bin/docker-containerd:ro \
  -v /usr/bin/docker-runc:/usr/bin/docker-runc:ro \
  docker/docker-bench-security
```

### Signed Images
```dockerfile
# Enable content trust to ensure signed images
FROM alpine:latest
LABEL maintainer="team@example.com"
# Only trusted, signed images will be pulled
```

## Docker Image Analysis

### Analyzing Image Layers
```bash
# Install dive to analyze Docker image layers
docker run --rm -it \
  -v /var/run/docker.sock:/var/run/docker.sock \
  wagoodman/dive:latest <IMAGE_NAME>
```

### Reducing Image Size
```dockerfile
FROM python:3.11-alpine as builder

# Install build dependencies
RUN apk add --no-cache gcc musl-dev libffi-dev

WORKDIR /app

COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /wheels -r requirements.txt

FROM python:3.11-alpine

# Install only runtime dependencies
RUN apk add --no-cache curl

RUN addgroup -g 1001 -S appgroup && \
    adduser -S appuser -u 1001 -G appgroup

WORKDIR /app

# Copy wheels from builder stage
COPY --from=builder /wheels /wheels
RUN pip install --no-cache /wheels/* \
    && rm -rf /wheels \
    && pip uninstall -y pip setuptools

COPY --chown=appuser:appuser . .

USER appuser

EXPOSE 8000
CMD ["python", "app.py"]
```

## Docker Health Checks

### Application Health Checks
```dockerfile
FROM python:3.11-slim

RUN useradd --create-home --shell /bin/bash app

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=app:app . .

USER app

EXPOSE 8000

# Health check for application
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python health_check.py || exit 1

CMD ["python", "app.py"]
```

```python
# health_check.py
import requests
import sys
import os

def check_health():
    try:
        response = requests.get('http://localhost:8000/health', timeout=5)
        if response.status_code == 200:
            return True
        return False
    except:
        return False

if __name__ == "__main__":
    if check_health():
        sys.exit(0)
    else:
        sys.exit(1)
```

This comprehensive Docker guide provides all the patterns and best practices needed for containerizing the CRM platform applications.