# Environment Variable Management

## Overview

Proper environment variable management is critical for security, portability, and maintainability. This guide covers best practices for managing configuration across development, staging, and production environments.

## Environment File Structure

### .env File Format

```bash
# Database
DATABASE_URL=postgresql://user:password@host:5432/dbname
POSTGRES_USER=postgres
POSTGRES_PASSWORD=secure_password
POSTGRES_DB=appdb

# Application
SECRET_KEY=your-secret-key-min-32-chars
ALLOWED_ORIGINS=http://localhost:3000,https://yourdomain.com
DEBUG=false
ENVIRONMENT=production

# OAuth2 - Twitter
TWITTER_CLIENT_ID=your_twitter_client_id
TWITTER_CLIENT_SECRET=your_twitter_client_secret
TWITTER_REDIRECT_URI=http://localhost:8000/auth/twitter/callback

# OAuth2 - LinkedIn
LINKEDIN_CLIENT_ID=your_linkedin_client_id
LINKEDIN_CLIENT_SECRET=your_linkedin_client_secret
LINKEDIN_REDIRECT_URI=http://localhost:8000/auth/linkedin/callback

# API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# External Services
REDIS_URL=redis://localhost:6379
SENTRY_DSN=https://...@sentry.io/...
```

### .env.example Template

Always commit a `.env.example` with placeholder values:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
POSTGRES_USER=postgres
POSTGRES_PASSWORD=changeme
POSTGRES_DB=appdb

# Application
SECRET_KEY=generate-a-secure-key-here
ALLOWED_ORIGINS=http://localhost:3000
DEBUG=true
ENVIRONMENT=development

# OAuth2 - Twitter
TWITTER_CLIENT_ID=your_twitter_client_id
TWITTER_CLIENT_SECRET=your_twitter_client_secret
TWITTER_REDIRECT_URI=http://localhost:8000/auth/twitter/callback

# OAuth2 - LinkedIn
LINKEDIN_CLIENT_ID=your_linkedin_client_id
LINKEDIN_CLIENT_SECRET=your_linkedin_client_secret
LINKEDIN_REDIRECT_URI=http://localhost:8000/auth/linkedin/callback
```

## Loading Environment Variables

### Python (FastAPI)

```python
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # Database
    database_url: str

    # Application
    secret_key: str
    allowed_origins: List[str] = ["http://localhost:3000"]
    debug: bool = False
    environment: str = "development"

    # OAuth2
    twitter_client_id: str | None = None
    twitter_client_secret: str | None = None
    twitter_redirect_uri: str | None = None

    linkedin_client_id: str | None = None
    linkedin_client_secret: str | None = None
    linkedin_redirect_uri: str | None = None

    # API Keys
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None

    class Config:
        env_file = ".env"
        case_sensitive = False

# Create global settings instance
settings = Settings()

# Usage
print(settings.database_url)
print(settings.secret_key)
```

### TypeScript (Next.js)

```typescript
// lib/env.ts
import { z } from 'zod';

const envSchema = z.object({
  // Public variables (NEXT_PUBLIC_ prefix)
  NEXT_PUBLIC_API_URL: z.string().url(),
  NEXT_PUBLIC_APP_URL: z.string().url(),

  // Server-only variables
  DATABASE_URL: z.string(),
  SECRET_KEY: z.string().min(32),

  // Optional variables
  SENTRY_DSN: z.string().optional(),
});

export const env = envSchema.parse({
  NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
  NEXT_PUBLIC_APP_URL: process.env.NEXT_PUBLIC_APP_URL,
  DATABASE_URL: process.env.DATABASE_URL,
  SECRET_KEY: process.env.SECRET_KEY,
  SENTRY_DSN: process.env.SENTRY_DSN,
});

// Usage
import { env } from '@/lib/env';
console.log(env.NEXT_PUBLIC_API_URL);
```

## Validation

### Python Validation Script

```python
#!/usr/bin/env python3
"""Validate environment variables"""

import os
import sys
from typing import List, Tuple

def validate_env() -> Tuple[bool, List[str]]:
    """Validate required environment variables"""

    required_vars = [
        "DATABASE_URL",
        "SECRET_KEY",
    ]

    optional_vars = [
        "TWITTER_CLIENT_ID",
        "TWITTER_CLIENT_SECRET",
        "LINKEDIN_CLIENT_ID",
        "LINKEDIN_CLIENT_SECRET",
    ]

    errors = []
    warnings = []

    # Check required variables
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            errors.append(f"Missing required variable: {var}")
        elif var == "SECRET_KEY" and len(value) < 32:
            errors.append(f"{var} must be at least 32 characters")

    # Check optional variables
    for var in optional_vars:
        if not os.getenv(var):
            warnings.append(f"Optional variable not set: {var}")

    # Validate DATABASE_URL format
    db_url = os.getenv("DATABASE_URL", "")
    if db_url and not db_url.startswith(("postgresql://", "postgres://")):
        errors.append("DATABASE_URL must start with postgresql:// or postgres://")

    # Print results
    if errors:
        print("❌ Validation failed:")
        for error in errors:
            print(f"  - {error}")

    if warnings:
        print("\n⚠️  Warnings:")
        for warning in warnings:
            print(f"  - {warning}")

    if not errors and not warnings:
        print("✓ All environment variables validated successfully")

    return len(errors) == 0, errors

if __name__ == "__main__":
    success, _ = validate_env()
    sys.exit(0 if success else 1)
```

### Bash Validation Script

```bash
#!/bin/bash
# validate-env.sh

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ERRORS=0
WARNINGS=0

check_required() {
    local var_name=$1
    if [ -z "${!var_name}" ]; then
        echo -e "${RED}✗ Missing required variable: ${var_name}${NC}"
        ((ERRORS++))
    else
        echo -e "${GREEN}✓ ${var_name} is set${NC}"
    fi
}

check_optional() {
    local var_name=$1
    if [ -z "${!var_name}" ]; then
        echo -e "${YELLOW}⚠ Optional variable not set: ${var_name}${NC}"
        ((WARNINGS++))
    else
        echo -e "${GREEN}✓ ${var_name} is set${NC}"
    fi
}

echo "Validating environment variables..."

# Required variables
check_required "DATABASE_URL"
check_required "SECRET_KEY"

# Optional variables
check_optional "TWITTER_CLIENT_ID"
check_optional "TWITTER_CLIENT_SECRET"
check_optional "LINKEDIN_CLIENT_ID"
check_optional "LINKEDIN_CLIENT_SECRET"

# Summary
echo ""
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✓ Validation passed${NC}"
    if [ $WARNINGS -gt 0 ]; then
        echo -e "${YELLOW}  ($WARNINGS warnings)${NC}"
    fi
    exit 0
else
    echo -e "${RED}✗ Validation failed with $ERRORS error(s)${NC}"
    exit 1
fi
```

## Docker Integration

### docker-compose.yml

```yaml
services:
  backend:
    build: ./backend
    env_file:
      - .env
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - SECRET_KEY=${SECRET_KEY}
```

### Dockerfile

```dockerfile
# Don't copy .env files into images
# Use build args for build-time variables
ARG NODE_ENV=production
ENV NODE_ENV=${NODE_ENV}

# Runtime variables come from docker-compose or deployment platform
```

## Platform-Specific Configuration

### Hugging Face Spaces

Set secrets in Space settings (not in code):

```python
import os

# Automatically loads from Space secrets
DATABASE_URL = os.getenv("DATABASE_URL")
SECRET_KEY = os.getenv("SECRET_KEY")
```

### Vercel (Next.js)

Add environment variables in project settings:

```bash
# Production
NEXT_PUBLIC_API_URL=https://api.production.com
DATABASE_URL=postgresql://...

# Preview
NEXT_PUBLIC_API_URL=https://api.staging.com
DATABASE_URL=postgresql://...
```

### Railway

Set variables in project settings or use railway.json:

```json
{
  "build": {
    "builder": "DOCKERFILE"
  },
  "deploy": {
    "restartPolicyType": "ON_FAILURE"
  }
}
```

## Security Best Practices

### Never Commit Secrets

```bash
# .gitignore
.env
.env.local
.env.*.local
*.pem
*.key
secrets/
```

### Rotate Credentials Regularly

```python
# Check credential age
from datetime import datetime, timedelta

CREDENTIAL_MAX_AGE = timedelta(days=90)

def check_credential_age(created_at: datetime) -> bool:
    age = datetime.now() - created_at
    if age > CREDENTIAL_MAX_AGE:
        print("⚠️  Credentials are older than 90 days. Consider rotating.")
        return False
    return True
```

### Use Different Keys Per Environment

```bash
# Development
SECRET_KEY=dev-key-not-for-production

# Staging
SECRET_KEY=staging-key-different-from-prod

# Production
SECRET_KEY=prod-key-highly-secure-32-chars-min
```

### Encrypt Sensitive Values

```python
from cryptography.fernet import Fernet

def encrypt_secret(secret: str, key: bytes) -> str:
    f = Fernet(key)
    return f.encrypt(secret.encode()).decode()

def decrypt_secret(encrypted: str, key: bytes) -> str:
    f = Fernet(key)
    return f.decrypt(encrypted.encode()).decode()
```

## Environment-Specific Configuration

### Development

```bash
# .env.development
DEBUG=true
LOG_LEVEL=debug
DATABASE_URL=postgresql://localhost:5432/dev_db
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001
```

### Staging

```bash
# .env.staging
DEBUG=false
LOG_LEVEL=info
DATABASE_URL=postgresql://staging-db.example.com:5432/staging_db
ALLOWED_ORIGINS=https://staging.example.com
```

### Production

```bash
# .env.production
DEBUG=false
LOG_LEVEL=warning
DATABASE_URL=postgresql://prod-db.example.com:5432/prod_db
ALLOWED_ORIGINS=https://example.com
SENTRY_DSN=https://...
```

## Loading Strategy

### Python with python-dotenv

```python
from dotenv import load_dotenv
import os

# Load environment-specific file
env = os.getenv("ENVIRONMENT", "development")
load_dotenv(f".env.{env}")

# Override with local file if exists
load_dotenv(".env.local", override=True)
```

### Next.js Automatic Loading

Next.js automatically loads in this order:
1. `.env.local` (all environments, gitignored)
2. `.env.development` or `.env.production` (environment-specific)
3. `.env` (all environments)

## Troubleshooting

### Variable Not Loading

```python
# Debug: Print all environment variables
import os
print("Environment variables:")
for key, value in os.environ.items():
    if not key.startswith("_"):  # Skip system variables
        # Mask sensitive values
        if any(secret in key.lower() for secret in ["key", "secret", "password"]):
            print(f"{key}=***MASKED***")
        else:
            print(f"{key}={value}")
```

### Type Conversion Issues

```python
# Convert string to appropriate type
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
PORT = int(os.getenv("PORT", "8000"))
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "").split(",")
```

### Missing Variables in Docker

```bash
# Check if variable is available in container
docker exec container_name env | grep DATABASE_URL

# Pass variable explicitly
docker run -e DATABASE_URL=$DATABASE_URL image_name
```

## Testing

### Mock Environment Variables

```python
import pytest
from unittest.mock import patch

@patch.dict(os.environ, {
    "DATABASE_URL": "postgresql://test:test@localhost/test",
    "SECRET_KEY": "test-secret-key-32-characters-long"
})
def test_with_env():
    from app.config import settings
    assert settings.database_url == "postgresql://test:test@localhost/test"
```

### Test Different Environments

```python
@pytest.mark.parametrize("env,expected_debug", [
    ("development", True),
    ("production", False),
])
def test_environment_config(env, expected_debug):
    with patch.dict(os.environ, {"ENVIRONMENT": env}):
        settings = Settings()
        assert settings.debug == expected_debug
```
