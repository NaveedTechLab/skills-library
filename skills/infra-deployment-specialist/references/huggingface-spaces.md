# Hugging Face Spaces Deployment Guide

## Overview

Hugging Face Spaces provides free hosting for ML applications with Docker support. This guide covers deploying full-stack applications to Spaces.

## Prerequisites

1. Hugging Face account
2. Git installed locally
3. Docker (for local testing)

## Space Configuration

### Creating a Space

1. Go to https://huggingface.co/spaces
2. Click "Create new Space"
3. Choose:
   - **SDK**: Docker
   - **Hardware**: CPU Basic (free) or upgrade as needed
   - **Visibility**: Public or Private

### Space Settings

Configure in Space settings:

- **Secrets**: Environment variables (encrypted)
- **Hardware**: CPU/GPU selection
- **Persistent Storage**: Optional volume mounting
- **Sleep Time**: Auto-sleep after inactivity

## Dockerfile Requirements

### Port Configuration

Hugging Face Spaces expects your app on port **7860**:

```dockerfile
EXPOSE 7860

# Start your app on port 7860
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
```

### Multi-Service Setup

For full-stack apps (frontend + backend):

```dockerfile
# Option 1: Backend only on 7860, frontend served by backend
EXPOSE 7860
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]

# Option 2: Reverse proxy (nginx) on 7860
EXPOSE 7860
CMD ["nginx", "-g", "daemon off;"]
```

### Health Checks

Add health check endpoint:

```python
@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

## README.md Configuration

The README.md file configures your Space with YAML frontmatter:

```yaml
---
title: Your App Name
emoji: 🤖
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
license: mit
---
```

### Available Options

- **title**: Display name
- **emoji**: Icon (any emoji)
- **colorFrom/colorTo**: Gradient colors
- **sdk**: `docker`, `gradio`, `streamlit`, or `static`
- **pinned**: Pin to your profile
- **license**: License type
- **python_version**: For non-Docker SDKs
- **app_port**: Custom port (default: 7860)

## Environment Variables & Secrets

### Setting Secrets

In Space settings → Repository secrets:

```
DATABASE_URL=postgresql://...
SECRET_KEY=your-secret-key
TWITTER_CLIENT_ID=...
TWITTER_CLIENT_SECRET=...
```

### Accessing in Code

```python
import os

DATABASE_URL = os.getenv("DATABASE_URL")
SECRET_KEY = os.getenv("SECRET_KEY")
```

### .env Files

For local development, use `.env` files (never commit these):

```bash
# .env.example (commit this)
DATABASE_URL=postgresql://user:pass@host/db
SECRET_KEY=change-me

# .env (gitignored)
DATABASE_URL=postgresql://real:credentials@host/db
SECRET_KEY=actual-secret-key
```

## Deployment Process

### Method 1: Git Push

```bash
# Clone your Space
git clone https://huggingface.co/spaces/username/space-name
cd space-name

# Add your files
cp -r /path/to/your/app/* .

# Commit and push
git add .
git commit -m "Initial deployment"
git push
```

### Method 2: Web Interface

1. Go to your Space
2. Click "Files" tab
3. Upload files directly
4. Commit changes

### Method 3: Hugging Face CLI

```bash
# Install CLI
pip install huggingface_hub

# Login
huggingface-cli login

# Upload files
huggingface-cli upload username/space-name ./local-folder --repo-type=space
```

## Project Structure for Spaces

```
space-name/
├── README.md              # Space configuration
├── Dockerfile             # Container definition
├── requirements.txt       # Python dependencies (if needed)
├── .gitignore            # Ignore .env, __pycache__, etc.
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   └── app/
└── frontend/
    ├── package.json
    └── app/
```

## Database Integration

### Using Neon PostgreSQL

1. Create Neon database
2. Get connection string
3. Add to Space secrets as `DATABASE_URL`
4. Use in application:

```python
import os
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = os.getenv("DATABASE_URL", "").replace(
    "postgresql://", "postgresql+asyncpg://"
)

engine = create_async_engine(DATABASE_URL)
```

### Connection Pooling

Use Neon's pooled endpoint for Spaces:

```
postgresql://user:pass@ep-xxx.pooler.neon.tech/db
```

## Static Files & Assets

### Serving Static Files

```python
from fastapi.staticfiles import StaticFiles

app.mount("/static", StaticFiles(directory="static"), name="static")
```

### Frontend Build

For Next.js or React apps:

```dockerfile
# Build frontend
COPY frontend/ ./frontend/
RUN cd frontend && npm ci && npm run build

# Serve with backend
COPY --from=builder /app/frontend/.next ./frontend/.next
```

## Monitoring & Logs

### Viewing Logs

In Space interface:
1. Click "Logs" tab
2. View real-time logs
3. Filter by severity

### Application Logging

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {"message": "Hello"}
```

## Performance Optimization

### Docker Image Size

Minimize image size:

```dockerfile
# Use slim base images
FROM python:3.11-slim

# Multi-stage builds
FROM node:20-alpine AS builder
# ... build steps
FROM python:3.11-slim
COPY --from=builder /app/build ./build

# Clean up
RUN apt-get clean && rm -rf /var/lib/apt/lists/*
```

### Caching

Leverage Docker layer caching:

```dockerfile
# Copy requirements first (changes less frequently)
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy code last (changes frequently)
COPY . .
```

### Cold Start Optimization

Spaces sleep after inactivity. Optimize cold starts:

1. Keep Docker image small
2. Use lazy loading for heavy dependencies
3. Implement health check endpoint
4. Consider upgrading to persistent hardware

## CORS Configuration

For frontend-backend communication:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Troubleshooting

### Build Failures

**Issue**: Docker build fails
- Check Dockerfile syntax
- Verify all files are committed
- Review build logs in Space

**Issue**: Port binding errors
- Ensure app runs on port 7860
- Check EXPOSE directive in Dockerfile

### Runtime Errors

**Issue**: Database connection fails
- Verify DATABASE_URL secret is set
- Check Neon database is accessible
- Ensure SSL mode is configured

**Issue**: Static files not found
- Verify file paths in Dockerfile
- Check COPY commands
- Ensure files are in git repo

### Performance Issues

**Issue**: Slow cold starts
- Reduce Docker image size
- Use multi-stage builds
- Consider persistent hardware

**Issue**: Out of memory
- Upgrade Space hardware
- Optimize memory usage
- Add memory limits in code

## Security Best Practices

### Secrets Management

- Never commit secrets to git
- Use Space secrets for sensitive data
- Rotate credentials regularly
- Use environment-specific secrets

### API Security

```python
from fastapi import Security, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

@app.get("/protected")
async def protected_route(credentials = Security(security)):
    # Verify token
    if not verify_token(credentials.credentials):
        raise HTTPException(status_code=401)
    return {"message": "Authorized"}
```

### Rate Limiting

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.get("/api/endpoint")
@limiter.limit("10/minute")
async def limited_endpoint():
    return {"message": "Rate limited"}
```

## Continuous Deployment

### Automated Deployments

Push to main branch triggers automatic rebuild:

```bash
git add .
git commit -m "Update feature"
git push origin main
# Space automatically rebuilds
```

### GitHub Integration

Link GitHub repo to Space for automatic syncing:

1. Space settings → Repository
2. Connect GitHub account
3. Select repository
4. Enable auto-sync

## Cost Optimization

### Free Tier Limits

- CPU Basic: Free, sleeps after inactivity
- Storage: Limited persistent storage
- Bandwidth: Fair use policy

### Upgrading Hardware

When to upgrade:
- High traffic (no sleep needed)
- GPU requirements
- Large memory needs
- Persistent storage

### Resource Monitoring

Monitor usage in Space settings:
- CPU/Memory usage
- Request counts
- Storage usage
- Build times

## Example Deployment Checklist

- [ ] Dockerfile configured for port 7860
- [ ] README.md with proper frontmatter
- [ ] All secrets added to Space settings
- [ ] Database connection tested
- [ ] Health check endpoint implemented
- [ ] CORS configured correctly
- [ ] Static files properly served
- [ ] Logging configured
- [ ] .gitignore includes sensitive files
- [ ] Local testing completed
- [ ] Documentation updated
