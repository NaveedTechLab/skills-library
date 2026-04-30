# Migration Strategy Reference

## Alembic Setup

### Initial Configuration

Set up Alembic for PostgreSQL migrations:

```bash
# Install alembic
pip install alembic

# Initialize alembic in your project
alembic init alembic
```

Update `alembic.ini`:
```ini
# alembic.ini
sqlalchemy.url = postgresql://username:password@localhost/dbname
```

Configure `alembic/env.py`:
```python
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from app.models import Base  # Import your models

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate support
target_metadata = Base.metadata

def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url, target_metadata=target_metadata, literal_binds=True
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

## Migration Patterns

### Creating a New Migration

```bash
# Auto-generate migration based on model changes
alembic revision --autogenerate -m "Add customer preferences field"

# Create empty migration
alembic revision -m "Manual migration for complex changes"
```

### Basic Migration Operations

```python
"""Add customer preferences field

Revision ID: abc123def456
Revises: xyz789uvw012
Create Date: 2023-10-01 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'abc123def456'
down_revision = 'xyz789uvw012'
branch_labels = None
depends_on = None

def upgrade():
    # Add new column with default value
    op.add_column('customers', sa.Column('preferences', postgresql.JSONB(),
                                        server_default=sa.text("'{}'::jsonb"),
                                        nullable=False))

def downgrade():
    # Remove the column
    op.drop_column('customers', 'preferences')
```

### Adding a New Table

```python
"""Create ticket_status_changes table

Revision ID: def456ghi789
Revises: abc123def456
Create Date: 2023-10-02 15:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'def456ghi789'
down_revision = 'abc123def456'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('ticket_status_changes',
        sa.Column('id', postgresql.UUID(as_uuid=True),
                  server_default=sa.text("gen_random_uuid()"),
                  nullable=False),
        sa.Column('ticket_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('old_status', sa.String(length=50), nullable=True),
        sa.Column('new_status', sa.String(length=50), nullable=False),
        sa.Column('changed_by', sa.String(length=255), nullable=True),
        sa.Column('changed_at', sa.DateTime(timezone=True),
                  server_default=sa.text("NOW()"), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(),
                  server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.ForeignKeyConstraint(['ticket_id'], ['tickets.id'],
                               name='fk_ticket_status_changes_ticket_id'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index('idx_ticket_status_changes_ticket_id', 'ticket_status_changes', ['ticket_id'])
    op.create_index('idx_ticket_status_changes_changed_at', 'ticket_status_changes', ['changed_at'])

def downgrade():
    op.drop_index('idx_ticket_status_changes_changed_at')
    op.drop_index('idx_ticket_status_changes_ticket_id')
    op.drop_table('ticket_status_changes')
```

### Modifying Existing Columns

```python
"""Modify customer email to be nullable

Revision ID: ghi789jkl012
Revises: def456ghi789
Create Date: 2023-10-03 09:15:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'ghi789jkl012'
down_revision = 'def456ghi789'
branch_labels = None
depends_on = None

def upgrade():
    # Make email nullable (if it wasn't already)
    op.alter_column('customers', 'email',
                    existing_type=sa.VARCHAR(255),
                    nullable=True)

def downgrade():
    # Make email non-nullable again (be careful with this!)
    op.alter_column('customers', 'email',
                    existing_type=sa.VARCHAR(255),
                    nullable=False)
```

### Adding Indexes

```python
"""Add indexes for performance

Revision ID: jkl012mno345
Revises: ghi789jkl012
Create Date: 2023-10-04 14:20:00.000000

"""
from alembic import op

revision = 'jkl012mno345'
down_revision = 'ghi789jkl012'
branch_labels = None
depends_on = None

def upgrade():
    # Add composite index
    op.create_index('idx_messages_customer_date', 'messages',
                    ['customer_id', 'timestamp'], postgresql_ops={'timestamp': 'DESC'})

    # Add partial index
    op.create_index('idx_active_tickets', 'tickets',
                    ['customer_id', 'status'],
                    postgresql_where=sa.text("status IN ('new', 'in_progress', 'waiting_for_customer')"))

def downgrade():
    op.drop_index('idx_active_tickets')
    op.drop_index('idx_messages_customer_date')
```

### Working with JSONB Columns

```python
"""Add metadata to messages table

Revision ID: mno345pqr678
Revises: jkl012mno345
Create Date: 2023-10-05 11:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'mno345pqr678'
down_revision = 'jkl012mno345'
branch_labels = None
depends_on = None

def upgrade():
    # Add metadata column with default empty JSONB
    op.add_column('messages', sa.Column('metadata', postgresql.JSONB(),
                                        server_default=sa.text("'{}'::jsonb"),
                                        nullable=False))

    # Create GIN index for JSONB queries
    op.create_index('idx_messages_metadata', 'messages', ['metadata'],
                    postgresql_using='GIN')

def downgrade():
    op.drop_index('idx_messages_metadata')
    op.drop_column('messages', 'metadata')
```

### Working with pgvector

```python
"""Add vector search capabilities

Revision ID: pqr678stu901
Revises: mno345pqr678
Create Date: 2023-10-06 16:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'pqr678stu901'
down_revision = 'mno345pqr678'
branch_labels = None
depends_on = None

def upgrade():
    # Create pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Add embedding column to messages
    op.add_column('messages', sa.Column('embedding',
                                        postgresql.Vector(dim=1536),
                                        nullable=True))

    # Add embedding column to knowledge base articles
    op.add_column('knowledge_base_articles', sa.Column('embedding',
                                                       postgresql.Vector(dim=1536),
                                                       nullable=True))

    # Create vector indexes
    op.execute("CREATE INDEX idx_messages_embedding ON messages USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)")
    op.execute("CREATE INDEX idx_kb_articles_embedding ON knowledge_base_articles USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)")

def downgrade():
    # Drop vector indexes
    op.execute("DROP INDEX IF EXISTS idx_messages_embedding")
    op.execute("DROP INDEX IF EXISTS idx_kb_articles_embedding")

    # Drop embedding columns
    op.drop_column('messages', 'embedding')
    op.drop_column('knowledge_base_articles', 'embedding')

    # Drop pgvector extension
    op.execute("DROP EXTENSION IF EXISTS vector")
```

## Migration Best Practices

### 1. Test Migrations Thoroughly

Always test migrations on a copy of production data:

```bash
# Create a backup of production data
pg_dump -h prod-db -U username -d crm_db > production_backup.sql

# Restore to test database
psql -h localhost -U username -d crm_test < production_backup.sql

# Apply migration to test database
alembic upgrade head
```

### 2. Migration Safety Checklist

Before running migrations in production:

- [ ] Back up the database
- [ ] Test migration on staging/development
- [ ] Have a rollback plan
- [ ] Schedule during maintenance window if needed
- [ ] Verify migration worked as expected
- [ ] Test application functionality after migration

### 3. Handling Large Data Migrations

For migrations involving large datasets:

```python
"""Large data migration example

Revision ID: stu901vwx234
Revises: pqr678stu901
Create Date: 2023-10-07 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = 'stu901vwx234'
down_revision = 'pqr678stu901'
branch_labels = None
depends_on = None

def upgrade():
    # Add new column
    op.add_column('customers', sa.Column('computed_score', sa.Float()))

    # Update data in batches to avoid locking the table too long
    conn = op.get_bind()

    # Process in batches of 1000
    batch_size = 1000
    offset = 0

    while True:
        # Update batch
        result = conn.execute(text(f"""
            UPDATE customers
            SET computed_score = (
                SELECT COUNT(*) * 0.1
                FROM messages
                WHERE messages.customer_id = customers.id
            )
            WHERE id IN (
                SELECT id FROM customers
                WHERE computed_score IS NULL
                LIMIT :batch_size OFFSET :offset
            )
        """), {"batch_size": batch_size, "offset": offset})

        if result.rowcount == 0:
            break

        offset += batch_size

        # Commit each batch to avoid long-running transaction
        conn.execute(text("COMMIT"))
        conn.execute(text("BEGIN"))

def downgrade():
    op.drop_column('customers', 'computed_score')
```

### 4. Zero-Downtime Migration Techniques

For zero-downtime deployments:

```python
"""Zero-downtime migration example

Revision ID: vwx234yz567
Revises: stu901vwx234
Create Date: 2023-10-08 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'vwx234yz567'
down_revision = 'stu901vwx234'
branch_labels = None
depends_on = None

def upgrade():
    # Phase 1: Add new column (can be done without downtime)
    op.add_column('tickets', sa.Column('new_status', sa.String(50)))

    # Phase 2: Populate new column gradually (application handles dual writes)
    # This happens over time through application code

    # Phase 3: Flip application logic to use new column

    # Phase 4: Drop old column (after confirming no references)
    # This would be in a separate migration later

def downgrade():
    # In a zero-downtime scenario, this might not be a true downgrade
    # Instead, you might just drop the new column
    op.drop_column('tickets', 'new_status')
```

### 5. Migration Commands

Common Alembic commands:

```bash
# Check current migration status
alembic current

# Show migration history
alembic history

# Show migration history with verbose output
alembic history -v

# Upgrade to latest migration
alembic upgrade head

# Downgrade by one migration
alembic downgrade -1

# Downgrade to specific migration
alembic downgrade abc123def456

# Show what would be applied (dry run)
alembic upgrade head --sql

# Generate migration from model changes
alembic revision --autogenerate -m "Description of changes"

# Create blank migration
alembic revision -m "Manual migration"
```

## Rollback Procedures

### Automated Rollback Testing

Set up automated tests for rollbacks:

```python
import pytest
from alembic.command import upgrade, downgrade
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def test_migration_rollback():
    """Test that migration can be rolled back safely."""
    alembic_cfg = Config("alembic.ini")
    engine = create_engine(alembic_cfg.get_main_option("sqlalchemy.url"))

    # Upgrade to the migration
    upgrade(alembic_cfg, "abc123def456")

    # Perform some operations to verify migration worked

    # Downgrade back
    downgrade(alembic_cfg, "xyz789uvw012")  # Previous migration ID

    # Verify downgrade worked
```

### Emergency Rollback

For emergency situations:

```bash
# If migration fails partway through, try to rollback
alembic downgrade -1

# If that doesn't work, you may need to manually fix the alembic_version table
psql -d your_database -c "UPDATE alembic_version SET version_num = 'previous_version';"

# Then try the downgrade again
alembic downgrade previous_version
```