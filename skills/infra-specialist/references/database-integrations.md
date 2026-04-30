# Database Integrations Guide

## Neon PostgreSQL Integration

### Neon Setup and Configuration

#### Creating a Neon Project
```bash
# Using Neon CLI
npm install -g @neondatabase/serverless
neonctl projects create --name your-project-name

# Or via dashboard
# 1. Go to https://console.neon.tech
# 2. Click "New Project"
# 3. Choose region and settings
# 4. Copy connection string
```

#### Connection String Format
```
postgresql://username:password@ep-xxx.us-east-1.aws.neon.tech/dbname?sslmode=require
```

#### Python Connection with psycopg2
```python
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from urllib.parse import urlparse

def get_neon_connection():
    database_url = os.environ.get('NEON_DATABASE_URL')

    if not database_url:
        raise ValueError("NEON_DATABASE_URL not found in environment")

    # Parse the connection string
    result = urlparse(database_url)

    connection = psycopg2.connect(
        host=result.hostname,
        port=result.port,
        database=result.path[1:],  # Remove leading '/'
        user=result.username,
        password=result.password,
        sslmode='require'  # Required for Neon
    )

    return connection

def execute_query(query, params=None, fetch=False):
    conn = get_neon_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, params)

            if fetch:
                result = cursor.fetchall()
                return result

            conn.commit()
    finally:
        conn.close()
```

#### Python Connection with SQLAlchemy
```python
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool
import os

def create_neon_engine():
    database_url = os.environ.get('NEON_DATABASE_URL')

    if not database_url:
        raise ValueError("NEON_DATABASE_URL not found in environment")

    # Configure for Neon's serverless nature
    engine = create_engine(
        database_url,
        poolclass=QueuePool,
        pool_size=5,  # Smaller pool for serverless
        max_overflow=10,
        pool_pre_ping=True,  # Verify connections before use
        pool_recycle=300,  # Recycle connections every 5 minutes
        echo=False  # Set to True for debugging
    )

    return engine

# Usage example
engine = create_neon_engine()

def execute_query(query, params=None):
    with engine.connect() as conn:
        result = conn.execute(text(query), params or {})
        conn.commit()
        return result
```

#### Neon Branching Features
```python
# Neon's branching allows for development environments
# You can connect to different branches using the same connection string
# Just change the branch name in the connection string:
# postgresql://username:password@ep-xxx.us-east-1.aws.neon.tech/branch-name?sslmode=require

def get_branch_connection(branch_name="main"):
    base_url = os.environ.get('NEON_BASE_URL')
    # Modify to use specific branch
    branch_url = base_url.replace("/main", f"/{branch_name}")

    return create_engine(branch_url, pool_pre_ping=True)
```

## Supabase Integration

### Supabase Setup and Configuration

#### Installing Supabase Client
```bash
pip install supabase
```

#### Python Supabase Client Setup
```python
from supabase import create_client, Client
import os

def get_supabase_client() -> Client:
    url: str = os.environ.get("SUPABASE_URL")
    key: str = os.environ.get("SUPABASE_ANON_KEY")

    if not url or not key:
        raise ValueError("Supabase URL and/or ANON_KEY not found in environment")

    return create_client(url, key)

# Initialize client
supabase = get_supabase_client()
```

#### Data Operations with Supabase
```python
def get_users():
    """Fetch all users"""
    response = supabase.table('users').select('*').execute()
    return response.data

def get_user_by_id(user_id):
    """Fetch user by ID"""
    response = supabase.table('users').select('*').eq('id', user_id).single().execute()
    return response.data

def create_user(user_data):
    """Create a new user"""
    response = supabase.table('users').insert(user_data).execute()
    return response.data

def update_user(user_id, update_data):
    """Update user information"""
    response = supabase.table('users').update(update_data).eq('id', user_id).execute()
    return response.data

def delete_user(user_id):
    """Delete a user"""
    response = supabase.table('users').delete().eq('id', user_id).execute()
    return response.data

def search_users(search_term):
    """Search users by name"""
    response = supabase.table('users').select('*').ilike('name', f'%{search_term}%').execute()
    return response.data
```

#### Supabase Real-time Features
```python
from supabase import SupabaseRealtimeClient

def setup_realtime_listener(table_name, callback):
    """Set up real-time listener for table changes"""
    def on_change(payload):
        callback(payload)

    subscription = supabase.realtime.channel(f"public:{table_name}")
    subscription.on('*', on_change)
    subscription.subscribe()

    return subscription

def listen_for_user_changes():
    """Listen for user table changes"""
    def handle_user_change(payload):
        print(f"User change: {payload['event_type']} - {payload['new']}")

    return setup_realtime_listener('users', handle_user_change)
```

#### Supabase Authentication
```python
from supabase import Client

def authenticate_user(email: str, password: str):
    """Sign in user with email and password"""
    try:
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        return response.session
    except Exception as e:
        print(f"Authentication failed: {e}")
        return None

def sign_out_user():
    """Sign out current user"""
    supabase.auth.sign_out()

def get_current_user():
    """Get current authenticated user"""
    user = supabase.auth.get_user()
    return user.user if user else None

def refresh_session():
    """Refresh current session"""
    session = supabase.auth.refresh_session()
    return session.session
```

## Database Migration Strategies

### Using Alembic with Neon
```python
# alembic.ini configuration for Neon
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import os

# Read Neon database URL
NEON_DATABASE_URL = os.environ.get('NEON_DATABASE_URL')

config = context.config
config.set_main_option('sqlalchemy.url', NEON_DATABASE_URL)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None  # Your models' MetaData

def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
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

### Migration Commands
```bash
# Initialize alembic (first time only)
alembic init alembic

# Generate migration
alembic revision --autogenerate -m "Add users table"

# Apply migrations
alembic upgrade head

# Check current migration status
alembic current

# Downgrade to previous migration
alembic downgrade -1
```

## Connection Pooling Best Practices

### For Production Applications
```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool
from urllib.parse import urlparse
import os

def create_production_engine():
    """
    Create a production-ready database engine with optimized connection pooling
    """
    database_url = os.environ.get('DATABASE_URL')

    # Parse URL to extract connection details
    parsed = urlparse(database_url)

    # Production settings
    engine = create_engine(
        database_url,
        poolclass=QueuePool,
        pool_size=10,           # Number of connections to maintain
        max_overflow=20,        # Additional connections beyond pool_size
        pool_pre_ping=True,     # Verify connections before use
        pool_recycle=3600,      # Recycle connections after 1 hour
        pool_timeout=30,        # Seconds to wait before giving up on getting connection
        echo=False,             # Disable SQL logging in production
        connect_args={
            "connect_timeout": 10,  # Timeout for establishing connection
        }
    )

    return engine
```

### For Serverless Environments (Neon/Fly.io)
```python
def create_serverless_engine():
    """
    Create an engine optimized for serverless environments
    """
    database_url = os.environ.get('DATABASE_URL')

    engine = create_engine(
        database_url,
        poolclass=QueuePool,
        pool_size=2,            # Smaller pool for serverless
        max_overflow=5,         # Limited overflow
        pool_pre_ping=True,     # Essential for serverless
        pool_recycle=300,       # Recycle frequently (5 minutes)
        pool_timeout=10,        # Shorter timeout
        echo=False,
        connect_args={
            "connect_timeout": 5,
            "command_timeout": 10,
        }
    )

    return engine
```

## Performance Optimization

### Indexing Strategies
```sql
-- Example indexes for common queries
-- For user lookups
CREATE INDEX idx_users_email ON users(email);

-- For time-based queries
CREATE INDEX idx_user_created_at ON users(created_at DESC);

-- For compound queries
CREATE INDEX idx_courses_category_status ON courses(category, status);

-- For full-text search
CREATE INDEX idx_courses_search ON courses USING gin(to_tsvector('english', title || ' ' || description));
```

### Query Optimization
```python
# Use specific column selection instead of SELECT *
def get_user_summary(user_id):
    # Good - only select needed columns
    result = supabase.table('users').select('id, name, email, created_at').eq('id', user_id).single().execute()
    return result.data

# Bad - selects all columns
def get_user_bad(user_id):
    result = supabase.table('users').select('*').eq('id', user_id).single().execute()
    return result.data

# Use batch operations when possible
def batch_insert_users(users_list):
    """Insert multiple users in a single operation"""
    response = supabase.table('users').insert(users_list).execute()
    return response.data
```

## Backup and Recovery

### Neon Backup Features
```python
# Neon provides automatic point-in-time recovery
# You can restore to any point within your retention period
# This is handled through the Neon dashboard or CLI

# To restore using CLI:
# neonctl branches create --parent-branchn-name=br-source-branch-name --name=br-restored
```

### Manual Backup Script
```python
import subprocess
import os
from datetime import datetime

def backup_database():
    """Create a database backup"""
    database_url = os.environ.get('DATABASE_URL')
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"backup_{timestamp}.sql"

    # Use pg_dump for PostgreSQL backups
    cmd = [
        'pg_dump',
        '--dbname', database_url,
        '--file', backup_file,
        '--verbose'
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        print(f"Backup created: {backup_file}")
        return backup_file
    else:
        print(f"Backup failed: {result.stderr}")
        return None
```

## Security Best Practices

### Connection Security
```python
# Always use SSL connections
def create_secure_connection():
    database_url = os.environ.get('DATABASE_URL')

    # Ensure SSL is required
    if 'sslmode=require' not in database_url:
        # Add SSL requirement to connection string
        separator = '&' if '?' in database_url else '?'
        database_url = f"{database_url}{separator}sslmode=require"

    return create_engine(database_url, pool_pre_ping=True)
```

### Environment Variables for Credentials
```
# Store credentials securely in environment variables
NEON_DATABASE_URL=postgresql://username:password@ep-xxx.region.neon.tech/dbname?sslmode=require
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

### Row Level Security (RLS) with Supabase
```sql
-- Enable RLS on tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Create policies
CREATE POLICY "Users can view own data" ON users
    FOR SELECT TO authenticated
    USING (auth.uid() = id);

CREATE POLICY "Users can update own data" ON users
    FOR UPDATE TO authenticated
    USING (auth.uid() = id);
```

## Monitoring and Health Checks

### Database Health Check
```python
def check_database_health():
    """Perform database health check"""
    try:
        # Simple query to test connection
        result = supabase.rpc('now').execute()

        if result.data:
            return {"status": "healthy", "timestamp": result.data[0]}
        else:
            return {"status": "unhealthy", "error": "No response from database"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

# For raw SQL connection
def check_neon_health():
    try:
        conn = get_neon_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT NOW();")
            result = cursor.fetchone()
        conn.close()

        return {"status": "healthy", "timestamp": result[0]}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

### Connection Pool Monitoring
```python
def get_pool_stats(engine):
    """Get connection pool statistics"""
    pool = engine.pool

    return {
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "size": pool.size(),
        "connections": len(pool._connections) if hasattr(pool, '_connections') else 0
    }
```