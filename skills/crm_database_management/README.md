# CRM Database Management Skill

This skill provides guidance and tools for managing the PostgreSQL database that serves as the Internal CRM. It covers schema migrations, customer identity resolution across channels, ticket lifecycle tracking, and vector search implementation via pgvector.

## Overview

The CRM database management system handles:
- PostgreSQL database schema management and migrations
- Customer identity resolution across multiple channels
- Ticket lifecycle tracking and management
- Vector search capabilities using pgvector extension
- Data integrity and relationship management

## Components

### SKILL.md
Main skill file containing overview, key components, and implementation guidelines.

### Reference Files
- `SCHEMA_DESIGN.md` - Database schema design patterns
- `MIGRATION_STRATEGY.md` - Alembic migration patterns
- `CUSTOMER_IDENTITY.md` - Identity resolution implementation
- `TICKET_LIFECYCLE.md` - Ticket management patterns
- `VECTOR_SEARCH.md` - pgvector implementation
- `PERFORMANCE_TUNING.md` - Database optimization
- `SECURITY_PATTERNS.md` - Security implementation

### Scripts
- `crm_database_manager.py` - Complete CRM database management implementation

### Dependencies
- `requirements.txt` - Required Python packages

## Usage

When implementing CRM database management functionality:

1. Review the main `SKILL.md` for architectural guidance
2. Consult the relevant reference files for specific implementation details:
   - For schema design: `SCHEMA_DESIGN.md`
   - For migrations: `MIGRATION_STRATEGY.md`
   - For identity resolution: `CUSTOMER_IDENTITY.md`
   - For ticket management: `TICKET_LIFECYCLE.md`
   - For vector search: `VECTOR_SEARCH.md`
   - For performance: `PERFORMANCE_TUNING.md`
   - For security: `SECURITY_PATTERNS.md`
3. Use the example manager in `scripts/crm_database_manager.py` as a starting point

## Implementation Steps

1. Set up PostgreSQL database with pgvector extension
2. Initialize the CRM database schema using the provided DDL
3. Implement customer identity resolution system
4. Set up ticket lifecycle management
5. Configure vector search for semantic capabilities
6. Implement security measures and audit logging

## Prerequisites

- PostgreSQL 12+ with pgvector extension
- Redis server (for caching)
- Python 3.8+

## Running the CRM Database Manager

1. Install dependencies: `pip install -r requirements.txt`
2. Set up your environment variables (see `.env` template)
3. Run the manager: `python scripts/crm_database_manager.py`

The example demonstrates core CRM database operations including customer creation, identity resolution, ticket management, and knowledge base search.