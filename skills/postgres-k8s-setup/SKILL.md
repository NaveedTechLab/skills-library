---
name: postgres-k8s-setup
description: Deploy PostgreSQL on Kubernetes, run migrations, and verify schemas. Use when Claude needs to set up PostgreSQL infrastructure on Kubernetes with proper migration execution and schema verification. Helm-based deployment with migration execution via scripts. Verification must return minimal output only.
---

# PostgreSQL Kubernetes Setup

This skill deploys PostgreSQL on Kubernetes using the Bitnami Helm chart, executes initial schema migrations, and verifies the database schema. It handles the full database bootstrap sequence — cluster deploy, migration run, schema check — and returns a compact pass/fail status to keep context usage low.

Use this skill at infrastructure setup time, or after a schema change that requires migration execution against a Kubernetes-hosted Postgres instance.

## Quick Start

```bash
# Deploy Postgres and run migrations from migrations/ directory
/postgres-k8s-setup namespace=app-db migrations_dir=./migrations

# Expected output:
# PostgreSQL deployed in namespace app-db
# Migrations: 3 applied successfully
# Schema verified: Done
```

## Key Features

- Deploys PostgreSQL via the Bitnami Helm chart in a dedicated namespace
- Executes SQL migration files in order from a specified directory
- Verifies the resulting schema matches expected tables/columns
- Returns only success/failure status — no verbose query output — to minimize context window usage
- Supports custom `values.yaml` overrides for storage class, resource limits, and credentials

## Process

1. Deploy PostgreSQL using Helm in a dedicated namespace
2. Execute initial schema migrations via `kubectl exec` or a migration job
3. Verify the database schema
4. Return only success/failure status

## When NOT to Use This Skill

- **Managed Postgres** (AWS RDS, Cloud SQL, Supabase) — use their native provisioning tools; this skill targets self-hosted Kubernetes only
- **Schema migrations in production without review** — always review migration files before running this skill against a production database
- **Large datasets or complex migrations** — for multi-hour migrations, use a dedicated migration tool (Flyway, Alembic) with rollback support rather than this skill

## Common Mistakes

- Not setting `persistence.enabled=true` in Helm values — default ephemeral storage causes complete data loss when the pod restarts
- Running migrations without a backup — always snapshot the PVC or use `pg_dump` before applying schema changes
- Using the default Bitnami credentials (`postgres`/`postgres`) in production — always override `auth.password` and `auth.postgresPassword` via a Kubernetes secret

## Related Skills

- [`database-postgresql-design`](../database-postgresql-design/SKILL.md) — Design the schema before deploying it
- [`k8s-foundation`](../k8s-foundation/SKILL.md) — Kubernetes cluster prerequisites
- [`crm-database-management`](../crm-database-management/SKILL.md) — Manage an existing PostgreSQL CRM database
