# Infrastructure Specialist Skill

This skill provides expertise in configuring Cloudflare R2 for verbatim content storage and media assets, deploying Python applications to Fly.io or Railway, and managing Neon/Supabase database integrations for progress tracking.

## Components

### SKILL.md
Core instructions and patterns for infrastructure configuration with focus on:
- Cloudflare R2 setup and management
- Fly.io and Railway deployment workflows
- Neon and Supabase database integrations
- Security and performance optimization

### References
- `r2-storage.md` - Complete guide for Cloudflare R2 configuration and usage
- `flyio-deployment.md` - Comprehensive Fly.io deployment guide with configuration examples
- `railway-deployment.md` - Detailed Railway deployment procedures and best practices
- `database-integrations.md` - Neon and Supabase database integration guides

### Scripts
- `deploy_to_fly.py` - Automated deployment script for Fly.io with database setup
- `deploy_to_railway.py` - Automated deployment script for Railway with environment configuration
- `r2_manager.py` - Command-line tool for R2 bucket and file management

### Assets
- `infrastructure-template.md` - Complete template with environment variables, Dockerfile, and configuration examples

## Usage

Use this skill when working with:
- Cloudflare R2 configuration for static content and media assets
- Deploying Python applications to Fly.io or Railway platforms
- Setting up and managing Neon or Supabase database integrations
- Optimizing content delivery and storage infrastructure
- Managing application scaling and performance

## Quick Start

### For R2 Management:
```bash
python r2_manager.py --account-id YOUR_ID --access-key-id KEY --secret-access-key SECRET --bucket BUCKET upload local_file.txt
```

### For Fly.io Deployment:
```bash
python deploy_to_fly.py my-app --create-postgres my-app-db --region sea
```

### For Railway Deployment:
```bash
python deploy_to_railway.py init my-app --db-type neon
python deploy_to_railway.py deploy --framework fastapi
```