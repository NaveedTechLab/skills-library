# Infrastructure Configuration Template

This template provides a comprehensive setup for deploying a Python application with Cloudflare R2 storage and database integration on either Fly.io or Railway.

## Environment Variables Template (.env)

```env
# Cloudflare R2 Configuration
CLOUDFLARE_ACCOUNT_ID=your_account_id_here
CLOUDFLARE_R2_ACCESS_KEY_ID=your_access_key_id
CLOUDFLARE_R2_SECRET_ACCESS_KEY=your_secret_access_key
CLOUDFLARE_R2_BUCKET_NAME=your_bucket_name
CLOUDFLARE_R2_PUBLIC_DOMAIN=https://your_subdomain.r2.cloudflarestorage.com

# Database Configuration (Choose one)
# For Neon PostgreSQL
NEON_DATABASE_URL=postgresql://username:password@ep-xxx.region.neon.tech/dbname?sslmode=require

# For Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

# For general database access
DATABASE_URL=your_database_url_here

# Application Configuration
SECRET_KEY=your_secret_key_here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Redis Cache (if using)
REDIS_URL=redis://your-redis-url:6379

# Application Settings
PORT=8000
STATIC_HOST=https://your-cdn-domain.com
MEDIA_HOST=https://your-r2-bucket.r2.cloudflarestorage.com
```

## Dockerfile Template

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install additional Python packages if needed
RUN pip install psycopg2-binary boto3

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "app:app"]
```

## fly.toml Template for Fly.io

```toml
app = "your-app-name"
primary_region = "ams"

[build]
  builder = "paketobuildpacks/builder:base"
  buildpacks = ["gcr.io/paketo-buildpacks/python"]

[http_service]
  internal_port = 8000
  force_https = true
  auto_stop_machines = true
  auto_start_machines = true
  min_machines_running = 0
  processes = ["app"]

[[vm]]
  cpu_kind = "shared"
  cpus = 2
  memory_mb = 2048

[env]
  PORT = "8000"
  PYTHONPATH = "/app"

# Static files mounting
[[statics]]
  guest_path = "/app/static"
  url_prefix = "/static/"

# Metrics endpoint
[[metrics]]
  port = 8000
  path = "/metrics"
```

## Railway Configuration Template

```yaml
# .railway/config.yml
services:
  - name: web
    type: web
    env: production
    build:
      cmd: pip install -r requirements.txt
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
    resources:
      cpu: 1000
      memory: 1024
      ephemeral_disk: 512
```

## Application Configuration Example (Python)

```python
# config.py
import os
from urllib.parse import urlparse
import boto3
from botocore.config import Config
from sqlalchemy import create_engine

class Config:
    # Database
    DATABASE_URL = os.environ.get('DATABASE_URL')

    # Cloudflare R2
    CLOUDFLARE_ACCOUNT_ID = os.environ.get('CLOUDFLARE_ACCOUNT_ID')
    CLOUDFLARE_R2_ACCESS_KEY_ID = os.environ.get('CLOUDFLARE_R2_ACCESS_KEY_ID')
    CLOUDFLARE_R2_SECRET_ACCESS_KEY = os.environ.get('CLOUDFLARE_R2_SECRET_ACCESS_KEY')
    CLOUDFLARE_R2_BUCKET_NAME = os.environ.get('CLOUDFLARE_R2_BUCKET_NAME')

    # Application
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'

    @staticmethod
    def init_r2_client():
        config = Config(
            signature_version='s3v4',
            region_name='auto',
            s3={
                'addressing_style': 'virtual'
            }
        )

        return boto3.client(
            's3',
            endpoint_url=f'https://{Config.CLOUDFLARE_ACCOUNT_ID}.r2.cloudflarestorage.com',
            aws_access_key_id=Config.CLOUDFLARE_R2_ACCESS_KEY_ID,
            aws_secret_access_key=Config.CLOUDFLARE_R2_SECRET_ACCESS_KEY,
            config=config
        )

    @staticmethod
    def init_db_engine():
        return create_engine(
            Config.DATABASE_URL,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=300
        )

config = Config()
```

## Deployment Checklist

- [ ] Environment variables configured
- [ ] Database connection tested
- [ ] R2 bucket created and configured
- [ ] CORS policy set for R2
- [ ] Domain configured and SSL certificates applied
- [ ] Health check endpoint implemented
- [ ] Monitoring and logging configured
- [ ] Backup strategy in place
- [ ] Security measures implemented (secrets, RLS, etc.)

## Common Commands

### For Fly.io Deployment:
```bash
# Initialize and deploy
fly launch
fly deploy

# Set secrets
fly secrets set SECRET_KEY="your-key" DATABASE_URL="your-db-url"

# View logs
fly logs
```

### For Railway Deployment:
```bash
# Initialize and deploy
railway init
railway up

# Set variables
railway variables set SECRET_KEY="your-key"

# View logs
railway logs
```

### For R2 Operations:
```bash
# Upload file
python r2_manager.py --account-id YOUR_ID --access-key-id KEY --secret-access-key SECRET --bucket BUCKET upload local_file.txt

# Generate presigned URL
python r2_manager.py --account-id YOUR_ID --access-key-id KEY --secret-access-key SECRET --bucket BUCKET presigned-url object_key
```