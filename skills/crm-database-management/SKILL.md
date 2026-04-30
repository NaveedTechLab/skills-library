---
name: crm-database-management
description: Manages the PostgreSQL database (the 'Internal CRM'). Responsible for schema migrations, customer identity resolution across channels, ticket lifecycle tracking, and vector search implementation via pgvector. Use when Claude needs to work with PostgreSQL database operations, perform schema migrations, manage customer identity resolution, track ticket lifecycles, or implement vector search functionality.
---

# CRM Database Management Skill

This skill provides guidance for managing the PostgreSQL database that serves as the Internal CRM. It covers schema migrations, customer identity resolution across channels, ticket lifecycle tracking, and vector search implementation via pgvector.

## Overview

The CRM database management system handles:
- PostgreSQL database schema management and migrations
- Customer identity resolution across multiple channels
- Ticket lifecycle tracking and management
- Vector search capabilities using pgvector extension
- Data integrity and relationship management

## Key Components

### 1. Database Schema Management

The database follows a normalized schema design with these core entities:
- `customers` - Central customer identity table
- `channels` - Different communication channels (email, whatsapp, web form)
- `messages` - All messages from all channels
- `tickets` - Support tickets and their lifecycle
- `interactions` - Customer interactions and touchpoints
- `embeddings` - Vector embeddings for semantic search

### 2. Schema Migration Strategy

Use Alembic for database migrations with a version-controlled approach:
- Keep migration scripts in version control
- Test migrations on staging before production
- Always provide downgrade paths
- Backup database before migrations

### 3. Customer Identity Resolution

Implement a robust customer identity resolution system:
- Unify customer profiles across channels
- Handle duplicate detection and merging
- Manage customer identity conflicts
- Maintain audit trail of identity changes

### 4. Ticket Lifecycle Tracking

Track tickets through their complete lifecycle:
- Creation and initial categorization
- Assignment and progress tracking
- Resolution and closure
- Post-closure monitoring

### 5. Vector Search Implementation

Implement semantic search using pgvector:
- Store embeddings for customer interactions
- Enable similarity search for knowledge base
- Support semantic search across tickets and messages
- Optimize vector indexes for performance

## Implementation Guidelines

### Database Connection Management

Use connection pooling and proper error handling:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/crm")

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=3600    # Recycle connections after 1 hour
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        return db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
```

### Customer Identity Resolution

Implement a flexible identity resolution system:

```python
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

def resolve_customer_identity(
    db: Session,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    external_id: Optional[str] = None
) -> Optional[Dict]:
    """
    Resolve customer identity across multiple identifiers.
    Returns existing customer or creates new one if not found.
    """
    # Search by email first
    if email:
        customer = db.query(Customer).filter(Customer.email == email).first()
        if customer:
            return customer

    # Search by phone
    if phone:
        customer = db.query(Customer).filter(Customer.phone == phone).first()
        if customer:
            return customer

    # Search by external ID
    if external_id:
        customer = db.query(Customer).filter(Customer.external_id == external_id).first()
        if customer:
            return customer

    # If no match found, create new customer
    return None
```

### Ticket Lifecycle Management

Track tickets through their complete lifecycle:

```python
from enum import Enum
from datetime import datetime

class TicketStatus(Enum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    WAITING_FOR_CUSTOMER = "waiting_for_customer"
    RESOLVED = "resolved"
    CLOSED = "closed"
    REOPENED = "reopened"

class TicketPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

def update_ticket_status(
    db: Session,
    ticket_id: int,
    new_status: TicketStatus,
    updated_by: str,
    comment: Optional[str] = None
):
    """
    Update ticket status with audit trail.
    """
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()

    # Create status change record
    status_change = TicketStatusChange(
        ticket_id=ticket_id,
        old_status=ticket.status,
        new_status=new_status,
        changed_by=updated_by,
        changed_at=datetime.utcnow(),
        comment=comment
    )

    db.add(status_change)
    ticket.status = new_status
    ticket.updated_at = datetime.utcnow()

    db.commit()
    return ticket
```

## Best Practices

### Performance Optimization

- Index frequently queried columns
- Use connection pooling
- Implement read replicas for heavy read operations
- Optimize queries with proper JOINs and filters
- Use pagination for large result sets

### Security Considerations

- Use parameterized queries to prevent SQL injection
- Implement proper access controls
- Encrypt sensitive data at rest
- Audit database access
- Regular security updates

### Data Integrity

- Implement foreign key constraints
- Use transactions for data consistency
- Validate data before insertion
- Implement soft deletes for audit trails
- Regular data integrity checks

## Reference Files

For detailed implementation patterns, see:
- [SCHEMA_DESIGN.md](references/SCHEMA_DESIGN.md) - Database schema design patterns
- [MIGRATION_STRATEGY.md](references/MIGRATION_STRATEGY.md) - Alembic migration patterns
- [CUSTOMER_IDENTITY.md](references/CUSTOMER_IDENTITY.md) - Identity resolution implementation
- [TICKET_LIFECYCLE.md](references/TICKET_LIFECYCLE.md) - Ticket management patterns
- [VECTOR_SEARCH.md](references/VECTOR_SEARCH.md) - pgvector implementation
- [PERFORMANCE_TUNING.md](references/PERFORMANCE_TUNING.md) - Database optimization
- [SECURITY_PATTERNS.md](references/SECURITY_PATTERNS.md) - Security implementation
## When NOT to Use This Skill

- **Off-the-shelf CRM platforms** (Salesforce, HubSpot) — if your organization uses a managed CRM, use its native APIs instead of building a custom PostgreSQL CRM
- **Non-relational customer data** — if customer relationships are highly graph-like (social networks, hierarchies), consider a graph database over PostgreSQL
- **Greenfield projects without data** — don't over-engineer a CRM schema before you have real data; start simple and migrate as requirements become clearer

## Common Mistakes

- Not implementing customer identity resolution from the start — merging duplicate customer records retroactively is painful; build deduplication logic at ingestion time
- Using `text` columns for all customer attributes — typed columns (email, phone, UUID) enable proper validation and indexing; use appropriate types
- Not indexing on `customer_id` and `email` — CRM queries are almost always customer-centric; missing indexes cause full table scans at scale

## Related Skills

- [`channel-ingestion`](../channel-ingestion/SKILL.md) — Ingest customer messages that populate this CRM
- [`database-postgresql-design`](../database-postgresql-design/SKILL.md) — Design the PostgreSQL schema for this CRM
- [`agent-workflow`](../agent-workflow/SKILL.md) — The Customer Success Agent that reads and writes this CRM data
