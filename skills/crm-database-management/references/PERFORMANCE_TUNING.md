# Database Performance Tuning Reference

## PostgreSQL Configuration

### Connection Settings
```ini
# postgresql.conf
max_connections = 200                    # Maximum number of concurrent connections
shared_buffers = 25%                     # Amount of memory for shared buffer cache (25% of RAM)
effective_cache_size = 75%               # OS + PostgreSQL disk cache (75% of RAM)
work_mem = 16MB                          # Memory per operation (sorts, hashes)
maintenance_work_mem = 512MB             # Memory for maintenance operations
```

### WAL Settings
```ini
# Write-Ahead Logging settings for better performance
wal_level = replica                      # Minimal WAL level for streaming replication
synchronous_commit = off                 # Balance durability vs performance
wal_sync_method = fsync                  # Method for WAL synchronization
checkpoint_completion_target = 0.9       # Spread checkpoint load
wal_buffers = 16MB                       # WAL buffers in shared memory
```

### Query Planner Settings
```ini
# Query planner settings
random_page_cost = 1.1                   # Cost of random page access (SSD: 1.1, HDD: 4.0)
seq_page_cost = 1.0                      # Cost of sequential page access
effective_io_concurrency = 200           # Concurrent I/O operations (higher for SSDs)
```

## Index Optimization

### Identifying Missing Indexes
```sql
-- Find tables with high sequential scans
SELECT schemaname, tablename, seq_scan, seq_tup_read,
       n_tup_ins + n_tup_upd + n_tup_del AS writes
FROM pg_stat_user_tables
WHERE seq_scan > 0
ORDER BY seq_scan DESC;

-- Find slow queries
SELECT query, mean_time, calls, rows
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
```

### Index Creation Best Practices

#### Single Column Indexes
```sql
-- For frequently queried columns
CREATE INDEX idx_customers_email ON customers(email);
CREATE INDEX idx_messages_customer_id ON messages(customer_id);
CREATE INDEX idx_tickets_status ON tickets(status);
CREATE INDEX idx_tickets_priority ON tickets(priority);
```

#### Composite Indexes
```sql
-- For common query patterns
CREATE INDEX idx_messages_customer_date ON messages(customer_id, timestamp DESC);
CREATE INDEX idx_tickets_customer_status_priority ON tickets(customer_id, status, priority);
CREATE INDEX idx_customer_identity_mapping_lookup ON customer_identity_mapping(channel_id, identifier_type, channel_identifier);
```

#### Partial Indexes
```sql
-- For filtered queries
CREATE INDEX idx_active_tickets ON tickets(customer_id, status)
WHERE status IN ('new', 'in_progress', 'waiting_for_customer');

CREATE INDEX idx_published_kb_articles ON knowledge_base_articles(id, title)
WHERE is_published = TRUE;

CREATE INDEX idx_recent_messages ON messages(customer_id, timestamp)
WHERE timestamp > NOW() - INTERVAL '30 days';
```

#### Expression Indexes
```sql
-- For case-insensitive searches
CREATE INDEX idx_customers_email_lower ON customers(lower(email));

-- For JSONB queries
CREATE INDEX idx_messages_metadata_gin ON messages USING GIN((metadata->'tags'));
CREATE INDEX idx_customers_preferences_gin ON customers USING GIN(preferences);
```

## Query Optimization

### Analyzing Slow Queries

#### Using EXPLAIN ANALYZE
```sql
-- Analyze query execution plan
EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT c.name, t.subject, t.status, t.created_at
FROM customers c
JOIN tickets t ON c.id = t.customer_id
WHERE c.email = 'user@example.com'
ORDER BY t.created_at DESC
LIMIT 10;
```

#### Identifying Bottlenecks
```sql
-- Find queries with high execution time
SELECT query, mean_time, calls, mean_time * calls AS total_time
FROM pg_stat_statements
ORDER BY mean_time * calls DESC
LIMIT 10;

-- Find queries with high I/O
SELECT query, blks_read, blks_hit, (blks_read * 100.0 / NULLIF(blks_hit + blks_read, 0)) AS io_ratio
FROM pg_stat_statements
WHERE blks_read > 0
ORDER BY blks_read DESC
LIMIT 10;
```

### Optimized Query Patterns

#### Efficient Joins
```sql
-- Good: Using proper indexes
SELECT c.name, COUNT(t.id) as ticket_count
FROM customers c
LEFT JOIN tickets t ON c.id = t.customer_id
WHERE c.status = 'active'
GROUP BY c.id, c.name
HAVING COUNT(t.id) > 0;

-- Better: Use EXISTS for existence checks
SELECT c.name, c.email
FROM customers c
WHERE EXISTS (
    SELECT 1
    FROM tickets t
    WHERE t.customer_id = c.id
    AND t.status = 'new'
);
```

#### Window Functions
```sql
-- Efficient ranking and pagination
SELECT
    customer_id,
    subject,
    created_at,
    ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY created_at DESC) as ticket_rank
FROM tickets
WHERE status != 'closed'
QUALIFY ticket_rank <= 5;  -- Top 5 tickets per customer
```

## Connection Pooling

### Using PgBouncer
```ini
# pgbouncer.ini
[databases]
crm_db = host=localhost port=5432 dbname=crm

[pgbouncer]
listen_port = 6432
listen_addr = localhost
auth_type = md5
auth_file = /etc/pgbouncer/userlist.txt
logfile = /var/log/pgbouncer/pgbouncer.log
pidfile = /var/run/pgbouncer/pgbouncer.pid

# Connection settings
pool_mode = transaction      # Transaction-level pooling
max_client_conn = 100       # Maximum client connections
default_pool_size = 25      # Default pool size
reserve_pool_size = 5       # Extra connections for emergencies
```

### SQLAlchemy Connection Pooling
```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    "postgresql://user:pass@localhost/dbname",
    poolclass=QueuePool,
    pool_size=20,                    # Number of connections to maintain
    max_overflow=30,                 # Additional connections beyond pool_size
    pool_pre_ping=True,              # Verify connections before use
    pool_recycle=3600,               # Recycle connections after 1 hour
    pool_timeout=30,                 # Timeout for getting connection from pool
    echo=False                       # Set to True for SQL logging
)
```

## Partitioning Strategies

### Range Partitioning for Messages
```sql
-- Create partitioned table
CREATE TABLE messages_partitioned (
    id UUID DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL,
    channel_id UUID NOT NULL,
    external_message_id VARCHAR(255),
    sender_id VARCHAR(255),
    sender_name VARCHAR(255),
    content TEXT NOT NULL,
    message_type VARCHAR(50),
    direction VARCHAR(10),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    metadata JSONB DEFAULT '{}',
    embedding vector(1536),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    PRIMARY KEY (id, timestamp)
) PARTITION BY RANGE (timestamp);

-- Create monthly partitions
DO $$
DECLARE
    create_month DATE := '2023-01-01';
    end_month DATE := '2025-01-01';
BEGIN
    WHILE create_month < end_month LOOP
        EXECUTE format('CREATE TABLE messages_%s PARTITION OF messages_partitioned
                       FOR VALUES FROM (%L) TO (%L)',
                       to_char(create_month, 'YYYY_MM'),
                       create_month,
                       create_month + INTERVAL '1 month');
        create_month := create_month + INTERVAL '1 month';
    END LOOP;
END $$;
```

### Hash Partitioning for Even Distribution
```sql
-- For tables where range partitioning isn't suitable
CREATE TABLE customer_identity_mapping_partitioned (
    id UUID DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL,
    channel_id UUID NOT NULL,
    channel_identifier VARCHAR(255) NOT NULL,
    identifier_type VARCHAR(50) NOT NULL,
    confidence_score DECIMAL(3,2) DEFAULT 1.00,
    verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    PRIMARY KEY (id, abs(hashtext(channel_identifier::text)) % 10)  -- 10 partitions
) PARTITION BY HASH (hashtext(channel_identifier::text) % 10);

-- Create hash partitions
DO $$
DECLARE
    i INT;
BEGIN
    FOR i IN 0..9 LOOP
        EXECUTE format('CREATE TABLE customer_identity_mapping_%s PARTITION OF customer_identity_mapping_partitioned
                       FOR VALUES WITH (MODULUS 10, REMAINDER %s)', i, i);
    END LOOP;
END $$;
```

## Monitoring and Maintenance

### Performance Monitoring Queries

#### Table Bloat Analysis
```sql
-- Check for table bloat
SELECT
    schemaname,
    tablename,
    ROUND(CASE WHEN otta=0 THEN 0.0 ELSE table_bloat.relsize::FLOAT/otta END, 1) AS tbloat,
    CASE WHEN table_bloat.relsize > (otta::FLOAT * 2.0) THEN 'Yes' ELSE 'No' END AS is_bloated
FROM (
    SELECT
        schemaname, tablename, cc.reltuples, cc.relpages,
        CEILING((cc.reltuples * ((datahdr + ma - (CASE WHEN datahdr % ma = 0 THEN ma ELSE datahdr % ma END)) + nullhdr2 + 4)) / (bs - 20::FLOAT)) AS otta
    FROM (
        SELECT
            ma, bs, schemaname, tablename,
            (datawidth + (hdr + ma - (CASE WHEN hdr % ma = 0 THEN ma ELSE hdr % ma END)))::NUMERIC AS datahdr,
            (maxfracsum * (nullhdr + ma - (CASE WHEN nullhdr % ma = 0 THEN ma ELSE nullhdr % ma END))) AS nullhdr2
        FROM (
            SELECT
                schemaname, tablename, hdr, ma, bs,
                SUM((1 - null_frac) * avg_width) AS datawidth,
                MAX(null_frac) AS maxfracsum,
                hdr + (SELECT 1 + COUNT(*) / 8
                       FROM pg_stats s2
                       WHERE s2.schemaname = s.schemaname
                         AND s2.tablename = s.tablename
                         AND s2.n_distinct > 1) AS nullhdr
            FROM pg_stats s, (
                SELECT
                    (SELECT current_setting('block_size')::NUMERIC) AS bs,
                    CASE WHEN substring(v, 12, 3) IN ('8.0', '8.1', '8.2') THEN 27 ELSE 23 END AS hdr,
                    CASE WHEN x = 0 THEN 20 ELSE 23 + (x + (CASE WHEN x % 4 = 0 THEN 0 ELSE 4 - (x % 4) END)) END AS ma
                FROM (SELECT current_setting('block_size')::INTEGER % 8 AS x) AS foo
            ) AS constants
            GROUP BY 1, 2, 3, 4, 5
        ) AS table_stats
    ) AS table_bloat
    JOIN pg_class cc ON cc.relname = table_bloat.tablename
    JOIN pg_namespace nn ON cc.relnamespace = nn.oid AND nn.nspname = table_bloat.schemaname
    WHERE cc.reltuples > 0;
```

#### Index Usage Analysis
```sql
-- Check index usage
SELECT
    schemaname,
    tablename,
    indexname,
    idx_tup_read,
    idx_tup_fetch,
    idx_scan
FROM pg_stat_user_indexes
WHERE idx_scan < 100  -- Less than 100 scans, might be unused
ORDER BY idx_scan ASC;
```

### Maintenance Scripts

#### Vacuum and Analyze Automation
```bash
#!/bin/bash
# maintenance_script.sh
# Run daily maintenance tasks

# Connect to database
export PGPASSWORD="your_password"

# Update table statistics
echo "Updating statistics..."
psql -h localhost -U postgres -d crm_db -c "ANALYZE;"

# Identify tables needing vacuum
echo "Checking for tables needing vacuum..."
tables_to_vacuum=$(psql -h localhost -U postgres -d crm_db -t -c "
SELECT schemaname||'.'||tablename
FROM pg_stat_user_tables
WHERE n_tup_ins + n_tup_upd + n_tup_del > 0
  AND last_vacuum IS NULL OR last_vacuum < NOW() - INTERVAL '1 day'
  AND schemaname = 'public'
ORDER BY n_tup_upd + n_tup_del DESC
LIMIT 10;
")

# Vacuum identified tables
for table in $tables_to_vacuum; do
    echo "Vacuuming table: $table"
    psql -h localhost -U postgres -d crm_db -c "VACUUM ANALYZE $table;"
done
```

## Caching Strategies

### Application-Level Caching
```python
import redis
import json
from typing import Any, Optional
from datetime import timedelta

class DatabaseCache:
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis = redis.from_url(redis_url)

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        value = self.redis.get(key)
        if value:
            return json.loads(value.decode('utf-8'))
        return None

    def set(self, key: str, value: Any, expire: timedelta = timedelta(minutes=15)):
        """Set value in cache."""
        self.redis.setex(key, expire.seconds, json.dumps(value))

    def delete(self, key: str):
        """Delete key from cache."""
        self.redis.delete(key)

    def make_key(self, prefix: str, *args) -> str:
        """Create a cache key."""
        return f"{prefix}:{':'.join(str(arg) for arg in args)}"

class CustomerServiceWithCache:
    def __init__(self, db_session, cache: DatabaseCache):
        self.db = db_session
        self.cache = cache

    def get_customer_by_email(self, email: str):
        """Get customer by email with caching."""
        cache_key = self.cache.make_key("customer", "email", email)

        # Try cache first
        cached_customer = self.cache.get(cache_key)
        if cached_customer:
            return cached_customer

        # Query database
        customer = self.db.execute(
            text("SELECT * FROM customers WHERE email = :email"),
            {"email": email}
        ).fetchone()

        # Cache result
        if customer:
            self.cache.set(cache_key, dict(customer), expire=timedelta(minutes=30))

        return customer
```

## Performance Testing

### Load Testing Script
```python
import asyncio
import time
import psycopg2
from concurrent.futures import ThreadPoolExecutor
import threading
from typing import List

class DatabaseLoadTester:
    def __init__(self, connection_string: str, num_threads: int = 10):
        self.connection_string = connection_string
        self.num_threads = num_threads
        self.results = []

    def execute_query(self, query: str, params: dict = None):
        """Execute a single query and measure performance."""
        start_time = time.time()

        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor() as cur:
                    cur.execute(query, params)
                    result = cur.fetchall()

            execution_time = time.time() - start_time
            return {
                "success": True,
                "execution_time": execution_time,
                "rows_returned": len(result) if result else 0
            }
        except Exception as e:
            execution_time = time.time() - start_time
            return {
                "success": False,
                "execution_time": execution_time,
                "error": str(e)
            }

    def run_concurrent_queries(self, queries: List[tuple], num_iterations: int = 10):
        """Run queries concurrently to test performance."""
        all_tasks = []

        for _ in range(num_iterations):
            for query, params in queries:
                all_tasks.append((query, params))

        results = []
        with ThreadPoolExecutor(max_workers=self.num_threads) as executor:
            futures = [
                executor.submit(self.execute_query, query, params)
                for query, params in all_tasks
            ]

            for future in futures:
                results.append(future.result())

        # Calculate performance metrics
        successful_queries = [r for r in results if r["success"]]
        failed_queries = [r for r in results if not r["success"]]

        if successful_queries:
            avg_time = sum(q["execution_time"] for q in successful_queries) / len(successful_queries)
            max_time = max(q["execution_time"] for q in successful_queries)
            min_time = min(q["execution_time"] for q in successful_queries)

            print(f"Performance Results:")
            print(f"  Total queries: {len(all_tasks)}")
            print(f"  Successful: {len(successful_queries)}")
            print(f"  Failed: {len(failed_queries)}")
            print(f"  Average execution time: {avg_time:.4f}s")
            print(f"  Min execution time: {min_time:.4f}s")
            print(f"  Max execution time: {max_time:.4f}s")
            print(f"  QPS: {len(successful_queries) / (max_time or 1):.2f}")

        return results

# Example usage
if __name__ == "__main__":
    tester = DatabaseLoadTester("postgresql://user:pass@localhost/crm_db")

    queries = [
        ("SELECT * FROM customers WHERE email = %s", ("test@example.com",)),
        ("SELECT * FROM tickets WHERE customer_id = %s AND status = %s", ("some-uuid", "new")),
        ("SELECT COUNT(*) FROM messages WHERE customer_id = %s", ("some-uuid",))
    ]

    results = tester.run_concurrent_queries(queries, num_iterations=5)
```

## Monitoring Dashboard Queries

### Key Performance Indicators
```sql
-- Overall database performance
SELECT
    now() AS time,
    (SELECT count(*) FROM pg_stat_activity) AS active_connections,
    (SELECT count(*) FROM pg_stat_activity WHERE state = 'active') AS running_queries,
    (SELECT pg_size_pretty(pg_database_size(current_database()))) AS db_size,
    (SELECT count(*) FROM customers) AS total_customers,
    (SELECT count(*) FROM tickets) AS total_tickets,
    (SELECT count(*) FROM messages) AS total_messages;

-- Slow query monitoring
SELECT
    query,
    calls,
    mean_time,
    (mean_time * calls) AS total_time,
    rows,
    (100.0 * shared_blks_hit / NULLIF(shared_blks_hit + shared_blks_read, 0)) AS hit_ratio
FROM pg_stat_statements
WHERE calls > 10
ORDER BY mean_time DESC
LIMIT 10;

-- Table growth monitoring
SELECT
    schemaname,
    tablename,
    n_tup_ins AS inserts,
    n_tup_upd AS updates,
    n_tup_del AS deletes,
    n_tup_hot_upd AS hot_updates,
    n_live_tup AS live_tuples,
    n_dead_tup AS dead_tuples
FROM pg_stat_user_tables
ORDER BY n_tup_ins DESC;
```

This performance tuning guide provides comprehensive strategies for optimizing PostgreSQL performance in a CRM database environment, covering configuration, indexing, query optimization, connection pooling, partitioning, and monitoring.