---
name: infra-deployment-specialist
description: "Expert in Docker containerization, Neon PostgreSQL database management, Hugging Face Spaces deployment, and environment variable configuration. Use when: (1) Dockerizing applications with Dockerfile or docker-compose.yml, (2) Setting up Neon PostgreSQL connections, migrations, or schema management, (3) Deploying to Hugging Face Spaces with proper configuration, (4) Managing environment variables, secrets, and .env files across environments, (5) Database initialization, seeding, or migration tasks, (6) Containerizing full-stack applications (Next.js + FastAPI), (7) Configuring production deployment infrastructure. Provides Docker templates, database scripts, deployment configs, and comprehensive reference documentation."
---

# Infra & Deployment Specialist

Expert guidance for Docker containerization, Neon PostgreSQL integration, Hugging Face Spaces deployment, and environment management.

## Quick Start

### Docker Containerization

#### FastAPI Backend Only

```bash
# Copy Dockerfile template
cp assets/docker-templates/Dockerfile.fastapi ./backend/Dockerfile

# Build and run
cd backend
docker build -t backend .
docker run -p 8000:8000 --env-file .env backend
```

#### Next.js Frontend Only

```bash
# Copy Dockerfile template
cp assets/docker-templates/Dockerfile.nextjs ./frontend/Dockerfile

# Update next.config.js for standalone output
# Add: output: 'standalone'

# Build and run
cd frontend
docker build -t frontend .
docker run -p 3000:3000 frontend
```

#### Full-Stack Application

Use docker-compose for multi-service setup:

```bash
# Copy docker-compose template
cp assets/docker-templates/docker-compose.yml ./

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Neon PostgreSQL Setup

For complete Neon integration patterns, connection pooling, and best practices, see [neon-postgresql.md](references/neon-postgresql.md).

#### Quick Connection Setup

```python
# app/core/config.py
from sqlalchemy.ext.asyncio import create_async_engine
import os

DATABASE_URL = os.getenv("DATABASE_URL", "").replace(
    "postgresql://", "postgresql+asyncpg://"
)

engine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    echo=False,
)
```

#### Database Initialization

```bash
# Initialize database tables
python scripts/init_db.py init

# Seed with initial data
python scripts/init_db.py seed

# Reset database (destructive)
python scripts/init_db.py reset
```

#### Database Migrations

```bash
# Make script executable
chmod +x scripts/migrate.sh

# Create new migration
./scripts/migrate.sh create "add users table"

# Apply migrations
./scripts/migrate.sh apply

# Rollback last migration
./scripts/migrate.sh rollback

# View migration history
./scripts/migrate.sh history
```

### Hugging Face Spaces Deployment

For complete deployment guide, configuration options, and troubleshooting, see [huggingface-spaces.md](references/huggingface-spaces.md).

#### Quick Deployment

1. **Copy HF Spaces templates**
```bash
cp assets/hf-spaces-templates/Dockerfile ./
cp assets/hf-spaces-templates/README.md ./
```

2. **Configure README.md frontmatter**
```yaml
---
title: Your App Name
emoji: 🤖
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
---
```

3. **Set secrets in Space settings**
   - `DATABASE_URL`
   - `SECRET_KEY`
   - OAuth credentials

4. **Deploy via Git**
```bash
git clone https://huggingface.co/spaces/username/space-name
cd space-name
# Copy your files
git add .
git commit -m "Initial deployment"
git push
```

#### Important: Port 7860

Hugging Face Spaces requires apps to run on port **7860**:

```python
# main.py
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
```

### Environment Variable Management

For comprehensive environment management patterns, validation, and security practices, see [environment-management.md](references/environment-management.md).

#### Setup Environment Files

```bash
# Create .env from example
cp .env.example .env

# Edit with your values
nano .env
```

#### Environment File Structure

```bash
# .env
DATABASE_URL=postgresql://user:pass@host/db?sslmode=require
SECRET_KEY=your-secret-key-min-32-chars
ALLOWED_ORIGINS=http://localhost:3000

# OAuth2
TWITTER_CLIENT_ID=your_client_id
TWITTER_CLIENT_SECRET=your_client_secret
LINKEDIN_CLIENT_ID=your_client_id
LINKEDIN_CLIENT_SECRET=your_client_secret
```

#### Load in Python (FastAPI)

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    secret_key: str
    allowed_origins: list[str] = ["http://localhost:3000"]

    class Config:
        env_file = ".env"

settings = Settings()
```

#### Load in TypeScript (Next.js)

```typescript
// lib/env.ts
export const env = {
  NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL!,
  DATABASE_URL: process.env.DATABASE_URL!,
};
```

## Docker Best Practices

### Multi-Stage Builds

Reduce image size with multi-stage builds:

```dockerfile
# Build stage
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Production stage
FROM node:20-alpine
WORKDIR /app
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
CMD ["npm", "start"]
```

### Layer Caching

Optimize build times by ordering Dockerfile commands:

```dockerfile
# Copy dependencies first (changes less frequently)
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy code last (changes frequently)
COPY . .
```

### Health Checks

Add health checks to containers:

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s \
  CMD python -c "import requests; requests.get('http://localhost:8000/health')"
```

## Database Workflows

### Initial Setup

1. Set `DATABASE_URL` in `.env`
2. Run `python scripts/init_db.py init`
3. Verify tables created

### Schema Changes

1. Modify models in `app/models/`
2. Create migration: `./scripts/migrate.sh create "description"`
3. Review generated migration in `alembic/versions/`
4. Apply: `./scripts/migrate.sh apply`

### Production Migrations

```bash
# Use direct connection (not pooled) for migrations
export DATABASE_URL="postgresql://user:pass@ep-xxx.neon.tech/db"

# Apply migrations
./scripts/migrate.sh apply

# Verify
./scripts/migrate.sh current
```

## Deployment Checklist

### Pre-Deployment

- [ ] Environment variables configured
- [ ] Database migrations applied
- [ ] Docker images build successfully
- [ ] Health check endpoint implemented
- [ ] CORS configured correctly
- [ ] Secrets not committed to git
- [ ] .gitignore includes .env files

### Docker Deployment

- [ ] Dockerfile optimized (multi-stage, layer caching)
- [ ] docker-compose.yml configured
- [ ] Port mappings correct
- [ ] Volume mounts for persistence
- [ ] Network configuration for service communication
- [ ] Environment variables passed correctly

### Neon PostgreSQL

- [ ] Connection string uses SSL (`?sslmode=require`)
- [ ] Using pooled endpoint for application
- [ ] Using direct endpoint for migrations
- [ ] Connection pooling configured
- [ ] Indexes created for performance
- [ ] Backup strategy in place

### Hugging Face Spaces

- [ ] App runs on port 7860
- [ ] README.md with proper frontmatter
- [ ] All secrets set in Space settings
- [ ] Dockerfile builds successfully
- [ ] Health check endpoint working
- [ ] Logs reviewed for errors
- [ ] Cold start time acceptable

## Troubleshooting

### Docker Issues

**Build fails with dependency errors**
```bash
# Clear Docker cache
docker builder prune -a

# Rebuild without cache
docker build --no-cache -t image-name .
```

**Container exits immediately**
```bash
# Check logs
docker logs container-name

# Run interactively
docker run -it image-name /bin/bash
```

**Port already in use**
```bash
# Find process using port
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Use different port
docker run -p 8001:8000 image-name
```

### Database Issues

**Connection refused**
- Verify `DATABASE_URL` is correct
- Check Neon database is active
- Ensure SSL mode is set: `?sslmode=require`
- Test connection: `psql $DATABASE_URL`

**Migration conflicts**
```bash
# View current state
./scripts/migrate.sh current

# Resolve conflicts
alembic merge heads -m "merge migrations"
./scripts/migrate.sh apply
```

**Too many connections**
- Use Neon's pooled endpoint: `ep-xxx.pooler.neon.tech`
- Configure connection pool limits
- Close connections properly in code

### Hugging Face Spaces Issues

**Build timeout**
- Reduce Docker image size
- Use multi-stage builds
- Remove unnecessary dependencies

**App not accessible**
- Verify app runs on port 7860
- Check logs in Space interface
- Ensure health check endpoint exists

**Environment variables not loading**
- Verify secrets are set in Space settings
- Check variable names match code
- Restart Space after adding secrets

## Security Best Practices

### Secrets Management

- Never commit `.env` files
- Use different secrets per environment
- Rotate credentials regularly (every 90 days)
- Use platform-specific secret management (HF Spaces secrets, etc.)

### Database Security

- Always use SSL connections (`?sslmode=require`)
- Use strong passwords (min 16 characters)
- Limit database user permissions
- Enable Neon's IP allowlist if available

### Docker Security

- Run containers as non-root user
- Scan images for vulnerabilities
- Keep base images updated
- Don't include secrets in images

### API Security

- Validate all environment variables on startup
- Use HTTPS in production
- Implement rate limiting
- Add authentication/authorization

## Performance Optimization

### Docker

- Use Alpine-based images when possible
- Minimize layers in Dockerfile
- Use `.dockerignore` to exclude unnecessary files
- Implement multi-stage builds

### Database

- Create indexes on frequently queried columns
- Use connection pooling
- Implement query pagination
- Use Neon's autoscaling features

### Deployment

- Enable caching where appropriate
- Use CDN for static assets
- Implement health checks
- Monitor resource usage

## Reference Documentation

- **[neon-postgresql.md](references/neon-postgresql.md)** - Complete Neon integration guide with connection patterns, migrations, and optimization
- **[huggingface-spaces.md](references/huggingface-spaces.md)** - Comprehensive HF Spaces deployment guide with configuration and troubleshooting
- **[environment-management.md](references/environment-management.md)** - Environment variable best practices, validation, and security

## When NOT to Use This Skill

- **Application feature development** — this skill handles deployment infrastructure, not application code; don't use it for business logic
- **Fully managed PaaS platforms** (Heroku, Railway, Fly.io) — those platforms abstract away the infrastructure this skill manages; use their native deploy commands
- **Simple single-container deployments** — running one Docker container doesn't need the full deployment specialist treatment; use `docker run` or a simple `docker-compose.yml`

## Common Mistakes

- Not implementing health checks before marking deployments complete — a pod that's running but not serving traffic shows as Ready without health check validation
- Deploying to production without testing in a staging environment — infrastructure changes that haven't been smoke-tested in staging frequently cause production incidents
- Not setting resource requests AND limits — missing requests causes pod placement issues; missing limits allows runaway processes to starve other pods

## Related Skills

- [`k8s-foundation`](../k8s-foundation/SKILL.md) — Kubernetes cluster prerequisites for deployment
- [`infra-devops`](../infra-devops/SKILL.md) — Full DevOps pipeline including CI/CD and containerization
- [`prometheus-grafana-setup`](../prometheus-grafana-setup/SKILL.md) — Monitor deployed infrastructure health
