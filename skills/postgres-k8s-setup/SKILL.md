---
name: postgres-k8s-setup
description: Deploy PostgreSQL on Kubernetes, run migrations, and verify schemas. Use when Claude needs to set up PostgreSQL infrastructure on Kubernetes with proper migration execution and schema verification. Helm-based deployment with migration execution via scripts. Verification must return minimal output only.
---

# PostgreSQL Kubernetes Setup

This skill deploys PostgreSQL on Kubernetes and runs initial schema migrations.

## Usage
Run this skill when you need to set up PostgreSQL infrastructure on Kubernetes. The skill will:
1. Deploy PostgreSQL using Helm
2. Execute initial schema migrations
3. Verify the database schema
4. Return minimal success/failure logs

## Process
The deployment and migration are handled by the supporting scripts which:
- Deploy PostgreSQL using Helm in a dedicated namespace
- Execute initial schema migrations
- Verify the database schema
- Return only success/failure status to minimize context window usage