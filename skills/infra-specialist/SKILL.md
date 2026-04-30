---
name: infra-specialist
description: Specialist in configuring Cloudflare R2 for verbatim content storage and media assets. Experienced in deploying Python applications to Fly.io or Railway and managing Neon/Supabase database integrations for progress tracking.
---

# Infrastructure Specialist

Specialist in configuring Cloudflare R2 for verbatim content storage and media assets. Experienced in deploying Python applications to Fly.io or Railway and managing Neon/Supabase database integrations for progress tracking.

## When to Use This Skill

Use this skill when working with:
- Cloudflare R2 configuration for static content and media assets
- Deploying Python applications to Fly.io or Railway platforms
- Setting up and managing Neon or Supabase database integrations
- Optimizing content delivery and storage infrastructure
- Managing application scaling and performance

## Core Capabilities

### Cloudflare R2 Configuration
- Bucket creation and management
- CORS configuration for web applications
- Presigned URL generation for secure uploads
- Static website hosting setup
- CDN configuration for optimal performance

### Platform Deployment (Fly.io & Railway)
- Application deployment workflows
- Environment configuration
- Scaling and performance optimization
- Health checks and monitoring setup
- Domain configuration and SSL certificates

### Database Integration (Neon & Supabase)
- Connection pool management
- Migration strategies
- Backup and recovery procedures
- Performance optimization
- Security configuration

## Cloudflare R2 Setup

### R2 Account Configuration
```bash
# Install wrangler CLI
npm install -g wrangler

# Login to Cloudflare account
wrangler r2 bucket create your-bucket-name

# Configure access
wrangler r2 object put your-bucket-name/path/to/file --file=./local-file
```

### Environment Variables for R2 Access
```
CLOUDFLARE_ACCOUNT_ID=your_account_id
CLOUDFLARE_R2_ACCESS_KEY_ID=your_access_key
CLOUDFLARE_R2_SECRET_ACCESS_KEY=your_secret_key
CLOUDFLARE_R2_BUCKET_NAME=your_bucket_name
CLOUDFLARE_R2_PUBLIC_DOMAIN=https://your_domain.r2.cloudflarestorage.com
```

### Python R2 Integration Example
```python
import boto3
from botocore.config import Config

def get_r2_client():
    config = Config(
        signature_version='s3v4',
        region_name='auto',
        s3={
            'addressing_style': 'virtual'
        }
    )

    s3_client = boto3.client(
        's3',
        endpoint_url='https://your-account-id.r2.cloudflarestorage.com',
        aws_access_key_id='your-access-key',
        aws_secret_access_key='your-secret-key',
        config=config
    )

    return s3_client

def upload_to_r2(client, bucket_name, file_path, object_name):
    client.upload_file(file_path, bucket_name, object_name)
    return f"https://{bucket_name}.your-domain.r2.cloudflarestorage.com/{object_name}"

def generate_presigned_url(client, bucket_name, object_name, expiration=3600):
    return client.generate_presigned_url(
        'get_object',
        Params={'Bucket': bucket_name, 'Key': object_name},
        ExpiresIn=expiration
    )
```

## Fly.io Deployment

### fly.toml Configuration
```toml
app = "your-app-name"
primary_region = "ams"

[build]
  builder = "heroku/buildpacks:20"

[http_service]
  internal_port = 8000
  force_https = true
  auto_stop_machines = true
  auto_start_machines = true
  min_machines_running = 0
  processes = ["app"]

[[vm]]
  cpu_kind = "shared"
  cpus = 1
  memory_mb = 1024

[env]
  PORT = "8000"
  DATABASE_URL = "your-database-url"
```

### Deployment Commands
```bash
# Initialize fly app
fly launch

# Deploy application
fly deploy

# Set secrets
fly secrets set SECRET_KEY=your_secret_key

# Scale application
fly scale count 2

# Monitor logs
fly logs
```

## Railway Deployment

### Railway Configuration
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
```

### Railway Environment Variables
```
RAILWAY_ENVIRONMENT=production
DATABASE_URL=your-database-url
SECRET_KEY=your-secret-key
CLOUDFLARE_R2_ACCESS_KEY_ID=your-r2-key
CLOUDFLARE_R2_SECRET_ACCESS_KEY=your-r2-secret
```

## Database Integration

### Neon Configuration
```python
# Database URL format: postgresql://username:password@ep-xxx.us-east-1.aws.neon.tech/dbname?sslmode=require
DATABASE_URL = "postgresql://username:password@ep-xxx.us-east-1.aws.neon.tech/dbname?sslmode=require"

# Connection pooling with psycopg2
import psycopg2.pool
from urllib.parse import urlparse

def get_db_connection_pool(database_url, minconn=1, maxconn=10):
    result = urlparse(database_url)
    return psycopg2.pool.ThreadedConnectionPool(
        minconn, maxconn,
        host=result.hostname,
        port=result.port,
        database=result.path.lstrip('/'),
        user=result.username,
        password=result.password,
        sslmode='require'
    )
```

### Supabase Configuration
```python
# Using Supabase Python client
from supabase import create_client, Client

def get_supabase_client(url: str, key: str) -> Client:
    return create_client(url, key)

# Example usage
supabase = get_supabase_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# Query data
data = supabase.table('users').select('*').execute()

# Insert data
result = supabase.table('users').insert({'name': 'John', 'email': 'john@example.com'}).execute()
```

## Best Practices

### Security
- Use environment variables for sensitive credentials
- Implement proper CORS policies
- Rotate access keys regularly
- Use least-privilege access patterns

### Performance Optimization
- Implement proper caching strategies
- Optimize database queries
- Use CDN for static assets
- Configure appropriate compression

### Monitoring and Logging
- Set up health checks
- Implement proper error logging
- Monitor resource utilization
- Track performance metrics