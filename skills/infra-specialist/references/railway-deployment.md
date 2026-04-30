# Railway Deployment Guide

## Prerequisites

### Install Railway CLI
```bash
# Install Railway CLI
npm install -g @railway/cli

# Or using curl
curl -fsSL https://railway.app/install.sh | sh

# Login to Railway
railway login
```

## Project Setup

### Initialize New Project
```bash
# Initialize Railway project in current directory
railway init

# Or link to existing project
railway link
```

## Railway Configuration

### railway.json Configuration
```json
{
  "projectId": "your-project-id",
  "environmentId": "your-environment-id"
}
```

### Service Configuration (via UI or railway.json)
```yaml
# .railway/config.yml
services:
  - name: web
    type: web
    env: production
    build:
      cmd: pip install -r requirements.txt && python manage.py migrate
    start:
      cmd: uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
    ports:
      - port: 8000
        protocol: http
        expose: true
    healthcheck:
      cmd: curl -f http://localhost:8000/health || exit 1
    restartPolicy:
      type: always
      maxRetries: 3
    storage:
      sizeGb: 1
```

### Dockerfile for Custom Builds
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### railway.toml Configuration
```toml
# For projects using railway.toml
[build]
builder = "nixpacks"

[build.args]
PYTHON_VERSION = "3.11"

[deploy]
numReplicas = 1
region = "us-west-1"
ephemeralDisk = 512
restartPolicyType = "Always"
restartPolicyMaxRetries = 3

[http]
proxyHeaders = true
minTLSServerVersion = "1.0"
minTLSClientVersion = "1.0"
```

## Environment Variables

### Setting Environment Variables
```bash
# Set variables via CLI
railway variables set SECRET_KEY="your-secret-key"
railway variables set DEBUG="False"

# Set multiple variables
railway variables set DATABASE_URL="postgresql://..." REDIS_URL="redis://..."

# Set variables from file
railway variables set -f .env.production

# View current variables
railway variables list

# Delete variables
railway variables delete SECRET_KEY
```

### Railway Built-in Variables
```
RAILWAY_GIT_COMMIT_SHA=commit_hash
RAILWAY_GIT_BRANCH=branch_name
RAILWAY_ENVIRONMENT=production/staging
PORT=8000  # Railway sets this automatically
```

## Database Integration

### PostgreSQL with Railway
```python
# Railway automatically provisions PostgreSQL
import os
from urllib.parse import urlparse

def get_database_url():
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL not found in environment")

    # Parse the URL for connection details
    result = urlparse(database_url)
    return {
        'host': result.hostname,
        'port': result.port,
        'database': result.path[1:],  # Remove leading '/'
        'username': result.username,
        'password': result.password,
    }
```

### Connecting to External Databases (Neon/Supabase)
```python
# For Neon
NEON_DATABASE_URL = os.environ.get('NEON_DATABASE_URL')

# For Supabase
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY')
```

## Deployment Workflows

### Manual Deployment
```bash
# Deploy current code
railway up

# Deploy with specific environment
railway up --environment production

# Deploy without building (just deploy latest build)
railway up --no-build

# Deploy from specific branch
railway up --git-branch main
```

### Automatic Deployment
Railway automatically deploys when:
- Pushing to connected GitHub/GitLab repositories
- Creating new commits on tracked branches
- Merging pull requests to main branch

### Deployment Configuration
```yaml
# .railway/config.yml
environments:
  - name: production
    autoDeploy: true
    branch: main
  - name: staging
    autoDeploy: true
    branch: develop
```

## Health Checks and Monitoring

### Health Check Endpoint
```python
# FastAPI health check
from fastapi import FastAPI
import asyncio

app = FastAPI()

@app.get("/health")
async def health_check():
    # Add any health checks you need
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "version": "1.0.0"
    }
```

### Railway Monitoring
```yaml
# In your service configuration
services:
  - name: web
    healthcheck:
      path: /health
      port: 8000
      timeout: 10
      interval: 30
      failures: 3
```

## Static Files and Assets

### Serving Static Files
```python
# For FastAPI with static files
from fastapi.staticfiles import StaticFiles
import os

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Or serve from R2/CDN for better performance
STATIC_HOST = os.environ.get('STATIC_HOST', '')
```

### Build Process for Static Assets
```yaml
# In railway.json or service config
build:
  cmd: |
    pip install -r requirements.txt &&
    python manage.py collectstatic --noinput &&
    npm run build
```

## CI/CD Integration

### GitHub Actions with Railway
```yaml
name: Deploy to Railway
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Railway
        uses: railwayapp/gh-action@v2
        with:
          railway_token: ${{ secrets.RAILWAY_TOKEN }}

      - name: Deploy
        run: railway up
```

### Environment Promotion
```bash
# Promote variables from one environment to another
railway variables promote --from staging --to production
```

## Scaling Configuration

### Resource Allocation
```yaml
# In service configuration
services:
  - name: web
    resources:
      cpu: 1000  # MHz
      memory: 1024  # MB
      ephemeral_disk: 512  # MB
```

### Auto-scaling Settings
```yaml
# Railway scales based on load automatically
# Configure replica settings
services:
  - name: web
    scaling:
      min_replicas: 1
      max_replicas: 5
      cpu_threshold: 70
      memory_threshold: 80
```

## Database Migrations

### Running Migrations on Deploy
```yaml
# In build configuration
build:
  cmd: |
    pip install -r requirements.txt &&
    python manage.py migrate &&
    python manage.py collectstatic --noinput
```

### Pre-deployment Hooks
```yaml
# In service configuration
services:
  - name: web
    build:
      cmd: pip install -r requirements.txt
    deploy:
      cmd: python manage.py migrate
    start:
      cmd: uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

## Troubleshooting

### Common Issues

#### Port Binding
```python
# Always use the PORT environment variable
import os

port = int(os.environ.get('PORT', 8000))
# Don't hardcode port numbers
```

#### Database Connection
```python
# Handle Railway's proxy connections
import os
import urllib.parse

def fix_database_url():
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        # Railway adds ?sslmode=require automatically
        return database_url
    return None
```

#### Memory Issues
```yaml
# Increase memory allocation
services:
  - name: web
    resources:
      memory: 2048  # Increase from default 512MB
```

### Debugging Commands
```bash
# View deployment logs
railway logs

# View build logs
railway logs --service build

# SSH into running container (if available)
railway shell

# Check environment variables
railway variables list
```

## Performance Optimization

### Caching Setup
```python
# Redis caching with Railway
import redis
import os

def get_redis_client():
    redis_url = os.environ.get('REDIS_URL')
    if redis_url:
        return redis.from_url(redis_url)
    return None
```

### CDN Integration
```python
# Integrate with R2 or other CDN providers
CDN_HOST = os.environ.get('CDN_HOST', '')

def get_asset_url(asset_path):
    if CDN_HOST:
        return f"{CDN_HOST}/{asset_path}"
    return f"/static/{asset_path}"
```

### Database Connection Pooling
```python
# Use connection pooling for better performance
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool
import os

def create_db_engine():
    database_url = os.environ.get('DATABASE_URL')
    return create_engine(
        database_url,
        poolclass=QueuePool,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=300
    )
```

## Security Best Practices

### Environment Security
```
# Never hardcode sensitive information
# Use Railway's encrypted environment variables
SECRET_KEY=${{SECRET_KEY}}
DATABASE_URL=${{DATABASE_URL}}

# Use .railwayignore to exclude sensitive files
# Similar to .gitignore but for Railway deployments
```

### HTTPS Configuration
```yaml
# Railway automatically handles HTTPS
# Ensure your app redirects to HTTPS
services:
  - name: web
    http:
      forceHttps: true
```

## Domain Configuration

### Custom Domains
```bash
# Add custom domain via CLI
railway domains add yourdomain.com

# Or configure via UI
# Go to Settings > Domains in Railway dashboard
```

### SSL Certificates
Railway automatically manages SSL certificates for custom domains.