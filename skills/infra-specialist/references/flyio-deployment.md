# Fly.io Deployment Guide

## Prerequisites

### Install Fly CLI
```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Or on macOS with Homebrew
brew install flyctl

# Login to Fly.io
fly auth login
```

## Application Setup

### Initialize New Application
```bash
# Initialize a new Fly.io app
fly launch

# This will:
# - Create a fly.toml configuration file
# - Build and deploy your application
# - Set up a PostgreSQL database if needed
```

### fly.toml Configuration Examples

#### Basic Python Application
```toml
app = "your-app-name"
primary_region = "ams"  # Choose closest region

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
  cpus = 1
  memory_mb = 1024

[env]
  PORT = "8000"
  DATABASE_URL = "your-database-url"
  SECRET_KEY = "your-secret-key"
```

#### FastAPI Application
```toml
app = "fastapi-course-companion"
primary_region = "iad"

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
  cpus = 1
  memory_mb = 1024

[[statics]]
  guest_path = "/app/static"
  url_prefix = "/static/"

[env]
  PORT = "8000"
  PYTHONPATH = "/app"
```

#### With PostgreSQL Database
```toml
app = "your-app-with-db"
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
  cpus = 1
  memory_mb = 1024

[env]
  PORT = "8000"
  # Database URL will be available after database creation

[[metrics]]
  port = 8000
  path = "/metrics"
```

## Database Setup

### Create PostgreSQL Database
```bash
# Create a PostgreSQL database
fly postgres create --name your-app-db --region ams

# Attach database to your app
fly postgres attach --postgres-app your-app-db

# The DATABASE_URL will be automatically set in your app's environment
```

### Alternative: Connect to External Database
```bash
# Set environment variable for external database
fly secrets set DATABASE_URL="postgresql://username:password@host:port/database"
```

## Deployment Commands

### Initial Deployment
```bash
# Deploy your application
fly deploy

# Deploy with specific image
fly deploy --image your-image:tag

# Deploy without building
fly deploy --remote-only
```

### Managing Deployments
```bash
# View deployment status
fly status

# View logs
fly logs

# View recent deployments
fly deployments

# Rollback to previous version
fly deploy --image $(fly history -j | jq -r '.[1].ImageRef')
```

## Scaling Configuration

### Scale VM Resources
```bash
# Scale VM to different size
fly scale vm shared-cpu-1x

# Scale to specific CPU/Memory
fly scale vm --cpus 2 --memory 2048

# Scale number of machines
fly scale count 3
```

### Auto-scaling Configuration
```toml
[[vm]]
  cpu_kind = "shared"
  cpus = 1
  memory_mb = 1024

[http_service]
  internal_port = 8000
  force_https = true
  auto_stop_machines = true
  auto_start_machines = true
  min_machines_running = 1  # Keep at least 1 machine running
  processes = ["app"]
```

## Environment Variables and Secrets

### Setting Environment Variables
```bash
# Set environment variables
fly secrets set SECRET_KEY="your-secret-key" DEBUG="False"

# Set multiple variables
fly secrets set VAR1=value1 VAR2=value2

# Unset variables
fly secrets unset SECRET_KEY

# View secrets (values are hidden)
fly secrets list
```

### Managing Configuration Files
```bash
# Set configuration from file
fly secrets set -f .env.production

# Create config map from file
fly config save -o fly-config.json
```

## Health Checks and Monitoring

### Health Check Configuration
```toml
[http_service]
  internal_port = 8000
  force_https = true
  auto_stop_machines = true
  auto_start_machines = true
  min_machines_running = 0
  processes = ["app"]

[[http_service.checks]]
  grace_period = "10s"
  interval = "30s"
  timeout = "5s"
  method = "GET"
  path = "/health"
```

### Application Health Endpoint
```python
# FastAPI health check endpoint
from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}
```

## Domain Configuration

### Purchase and Configure Domain
```bash
# Purchase domain through Fly.io
fly domains create yourdomain.com

# Add existing domain
fly domains add yourdomain.com

# Show DNS configuration
fly ips show
```

### SSL Certificate Management
```bash
# Fly.io automatically manages SSL certificates
# Just configure your domain and it will handle SSL
fly certs create yourdomain.com
```

## Monitoring and Debugging

### View Logs
```bash
# Stream logs in real-time
fly logs

# View recent logs
fly logs --recent

# Filter logs by level
fly logs --level info

# View logs from specific machine
fly logs --machine MACHINE_ID
```

### SSH Access to Machines
```bash
# List machines
fly machines list

# SSH into a machine
fly ssh console

# Execute command on machine
fly ssh exec "ls -la /app"
```

## CI/CD Integration

### GitHub Actions Example
```yaml
name: Deploy to Fly.io
on:
  push:
    branches: [main]

jobs:
  deploy:
    name: Deploy app
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - uses: superfly/flyctl-actions/setup-flyctl@master

      - run: flyctl deploy --remote-only
        env:
          FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}
```

### Environment-Specific Deployments
```bash
# Deploy to specific app
fly deploy -a your-staging-app

# Deploy with different configuration
fly deploy -c fly.staging.toml
```

## Troubleshooting Common Issues

### Application Won't Start
```bash
# Check logs for errors
fly logs

# SSH into machine and inspect
fly ssh console
ps aux | grep python
```

### Resource Limits
```bash
# Check current resource usage
fly status
fly platform vm-resources

# Scale up resources if needed
fly scale vm shared-cpu-2x
```

### Database Connection Issues
```bash
# Check if database is attached
fly status

# Test database connection
fly ssh console
python -c "import psycopg2; conn = psycopg2.connect('${DATABASE_URL}')"
```

## Performance Optimization

### Caching Configuration
```toml
# Add Redis cache
[[mounts]]
  source = "cache_data"
  destination = "/cache"

[env]
  REDIS_URL = "redis://your-redis-instance:6379"
```

### Static Files Optimization
```toml
[[statics]]
  guest_path = "/app/static"
  url_prefix = "/static/"

# Serve static files with proper caching headers
[http_service]
  [http_service.concurrency]
    type = "requests"
    soft_limit = 100
    hard_limit = 150
```