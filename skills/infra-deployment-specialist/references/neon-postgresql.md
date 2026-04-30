# Neon PostgreSQL Integration Guide

## Overview

Neon is a serverless PostgreSQL platform with automatic scaling, branching, and connection pooling. This guide covers integration patterns for production applications.

## Connection Patterns

### Basic Connection String Format
```
postgresql://[user]:[password]@[endpoint]/[database]?sslmode=require
```

### Environment Variables
```bash
# .env
DATABASE_URL=postgresql://user:password@ep-cool-darkness-123456.us-east-2.aws.neon.tech/neondb?sslmode=require
NEON_PROJECT_ID=cool-darkness-123456
NEON_BRANCH=main
```

## FastAPI Integration

### Using SQLAlchemy with Async Support

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool
import os

# Convert postgres:// to postgresql+asyncpg://
DATABASE_URL = os.getenv("DATABASE_URL", "").replace(
    "postgresql://", "postgresql+asyncpg://"
)

# Create async engine with connection pooling
engine = create_async_engine(
    DATABASE_URL,
    poolclass=NullPool,  # Neon handles pooling
    echo=False,
    future=True,
)

# Create async session factory
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()

# Dependency for FastAPI
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

### Using psycopg3 (Async)

```python
import os
from psycopg_pool import AsyncConnectionPool

DATABASE_URL = os.getenv("DATABASE_URL")

# Create connection pool
pool = AsyncConnectionPool(
    conninfo=DATABASE_URL,
    min_size=1,
    max_size=10,
    timeout=30,
)

async def get_db_connection():
    async with pool.connection() as conn:
        yield conn
```

## Connection Pooling Best Practices

### Neon's Built-in Pooling

Neon provides connection pooling at the platform level. Use pooled connections for better performance:

```python
# Pooled connection (recommended for serverless)
POOLED_URL = "postgresql://user:password@ep-xxx.pooler.neon.tech/db?sslmode=require"

# Direct connection (for migrations and admin tasks)
DIRECT_URL = "postgresql://user:password@ep-xxx.neon.tech/db?sslmode=require"
```

### Application-Level Pooling

For traditional deployments, configure SQLAlchemy pooling:

```python
from sqlalchemy.pool import QueuePool

engine = create_async_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=3600,   # Recycle connections after 1 hour
)
```

## Database Models

### Example Model with SQLAlchemy

```python
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"
```

## Migrations with Alembic

### Setup Alembic

```bash
# Install alembic
pip install alembic

# Initialize alembic
alembic init alembic
```

### Configure alembic.ini

```ini
# alembic.ini
sqlalchemy.url = driver://user:pass@localhost/dbname

# For async drivers
sqlalchemy.url = postgresql+asyncpg://user:pass@host/db
```

### Configure env.py for Async

```python
# alembic/env.py
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context
import asyncio
import os

# Import your models
from app.db.base import Base
from app.models import *  # Import all models

config = context.config

# Override sqlalchemy.url with environment variable
config.set_main_option(
    "sqlalchemy.url",
    os.getenv("DATABASE_URL", "").replace("postgresql://", "postgresql+asyncpg://")
)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

### Create and Run Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "Create users table"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history
```

## Neon-Specific Features

### Database Branching

Neon supports Git-like branching for databases:

```bash
# Create a branch for development
neon branches create --name dev --parent main

# Get branch connection string
neon connection-string dev
```

Use different branches for different environments:
- `main` - Production
- `staging` - Staging environment
- `dev` - Development
- `feature-xyz` - Feature branches

### Autoscaling

Neon automatically scales compute resources. Configure limits:

```python
# No special configuration needed in application
# Neon handles scaling automatically based on load
```

### Point-in-Time Recovery

Neon provides automatic backups with point-in-time recovery:

```bash
# Restore to specific timestamp (via Neon console or API)
# No application code changes needed
```

## Security Best Practices

### SSL/TLS Configuration

Always use SSL for Neon connections:

```python
# SSL is enforced by default with ?sslmode=require
DATABASE_URL = "postgresql://...?sslmode=require"
```

### Secrets Management

Never commit database credentials:

```python
# Use environment variables
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set")
```

### Connection String Validation

```python
from urllib.parse import urlparse

def validate_database_url(url: str) -> bool:
    try:
        result = urlparse(url)
        return all([
            result.scheme in ['postgresql', 'postgres'],
            result.hostname,
            result.username,
            result.password,
            result.path
        ])
    except Exception:
        return False

# Validate on startup
if not validate_database_url(DATABASE_URL):
    raise ValueError("Invalid DATABASE_URL format")
```

## Performance Optimization

### Indexing Strategy

```python
from sqlalchemy import Index

class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, index=True)  # Single column index
    title = Column(String)
    created_at = Column(DateTime, index=True)

    # Composite index
    __table_args__ = (
        Index('idx_user_created', 'user_id', 'created_at'),
    )
```

### Query Optimization

```python
from sqlalchemy import select
from sqlalchemy.orm import selectinload

# Eager loading to avoid N+1 queries
async def get_users_with_posts(db: AsyncSession):
    stmt = select(User).options(selectinload(User.posts))
    result = await db.execute(stmt)
    return result.scalars().all()

# Pagination
async def get_paginated_users(db: AsyncSession, skip: int = 0, limit: int = 100):
    stmt = select(User).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()
```

### Connection Management

```python
# Use connection pooling efficiently
async def health_check():
    try:
        async with AsyncSessionLocal() as session:
            await session.execute("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": str(e)}
```

## Troubleshooting

### Common Issues

**Connection Timeout**
```python
# Increase timeout in connection string
DATABASE_URL = "postgresql://...?connect_timeout=10"
```

**Too Many Connections**
```python
# Use Neon's pooled connection endpoint
POOLED_URL = "postgresql://...@ep-xxx.pooler.neon.tech/..."
```

**SSL Certificate Errors**
```python
# Ensure sslmode is set correctly
DATABASE_URL = "postgresql://...?sslmode=require"
```

**Migration Conflicts**
```bash
# Resolve conflicts by creating a merge migration
alembic merge heads -m "merge migrations"
```

## Testing with Neon

### Test Database Setup

```python
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

@pytest.fixture
async def test_db():
    # Use a separate test database or branch
    TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

    engine = create_async_engine(TEST_DATABASE_URL)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()
```

## Monitoring and Observability

### Query Logging

```python
import logging

# Enable SQLAlchemy query logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# Or use echo parameter
engine = create_async_engine(DATABASE_URL, echo=True)
```

### Performance Metrics

```python
from time import time

async def log_query_time(func):
    async def wrapper(*args, **kwargs):
        start = time()
        result = await func(*args, **kwargs)
        duration = time() - start
        print(f"Query took {duration:.2f}s")
        return result
    return wrapper
```
