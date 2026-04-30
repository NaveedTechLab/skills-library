# Database Schema Design Reference

## Core Entity Relationships

### Customer Table
```sql
CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id VARCHAR(255) UNIQUE, -- External system ID
    email VARCHAR(255) UNIQUE,
    phone VARCHAR(50),
    name VARCHAR(255),
    company VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_interaction_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) DEFAULT 'active',
    preferences JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    -- Identity resolution fields
    primary_channel_id UUID,
    is_merged BOOLEAN DEFAULT FALSE,
    merged_into_customer_id UUID REFERENCES customers(id)
);
```

### Channel Table
```sql
CREATE TABLE channels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL, -- 'email', 'whatsapp', 'web_form', etc.
    provider VARCHAR(100), -- 'gmail', 'twilio', etc.
    config JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Message Table
```sql
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES customers(id),
    channel_id UUID NOT NULL REFERENCES channels(id),
    external_message_id VARCHAR(255), -- ID from external system
    sender_id VARCHAR(255), -- Channel-specific sender ID
    sender_name VARCHAR(255),
    content TEXT NOT NULL,
    message_type VARCHAR(50), -- 'text', 'image', 'document', etc.
    direction VARCHAR(10) CHECK (direction IN ('inbound', 'outbound')),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    metadata JSONB DEFAULT '{}',
    embedding vector(1536), -- For semantic search
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Full-text search
    tsvector_col TSVECTOR GENERATED ALWAYS AS (
        to_tsvector('english', coalesce(content, ''))
    ) STORED
);

-- Indexes for messages
CREATE INDEX idx_messages_customer_id ON messages(customer_id);
CREATE INDEX idx_messages_channel_id ON messages(channel_id);
CREATE INDEX idx_messages_timestamp ON messages(timestamp DESC);
CREATE INDEX idx_messages_tsvector ON messages USING GIN(tsvector_col);
CREATE INDEX idx_messages_embedding ON messages USING ivfflat(embedding vector_cosine_ops) WITH (lists = 100);
```

### Ticket Table
```sql
CREATE TABLE tickets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES customers(id),
    external_id VARCHAR(255), -- External ticket system ID
    subject VARCHAR(500) NOT NULL,
    description TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'new',
    priority VARCHAR(20) DEFAULT 'medium',
    category VARCHAR(100),
    assigned_to UUID REFERENCES users(id),
    created_by UUID REFERENCES users(id),
    resolved_at TIMESTAMP WITH TIME ZONE,
    closed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

-- Indexes for tickets
CREATE INDEX idx_tickets_customer_id ON tickets(customer_id);
CREATE INDEX idx_tickets_status ON tickets(status);
CREATE INDEX idx_tickets_priority ON tickets(priority);
CREATE INDEX idx_tickets_assigned_to ON tickets(assigned_to);
CREATE INDEX idx_tickets_created_at ON tickets(created_at DESC);
```

### Customer Identity Mapping Table
```sql
CREATE TABLE customer_identity_mapping (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    channel_id UUID NOT NULL REFERENCES channels(id),
    channel_identifier VARCHAR(255) NOT NULL, -- Email, phone number, etc.
    confidence_score DECIMAL(3,2) DEFAULT 1.00, -- 0.00 to 1.00
    verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(channel_id, channel_identifier)
);

-- Index for identity mapping
CREATE INDEX idx_customer_identity_mapping_customer_id ON customer_identity_mapping(customer_id);
```

### Ticket Status Change History
```sql
CREATE TABLE ticket_status_changes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id UUID NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    old_status VARCHAR(50),
    new_status VARCHAR(50) NOT NULL,
    changed_by VARCHAR(255), -- User ID or system identifier
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    comment TEXT,
    metadata JSONB DEFAULT '{}'
);

-- Index for status changes
CREATE INDEX idx_ticket_status_changes_ticket_id ON ticket_status_changes(ticket_id);
CREATE INDEX idx_ticket_status_changes_changed_at ON ticket_status_changes(changed_at DESC);
```

## Additional Supporting Tables

### User Table
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'agent',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Knowledge Base Articles
```sql
CREATE TABLE knowledge_base_articles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    category VARCHAR(100),
    tags TEXT[],
    is_published BOOLEAN DEFAULT FALSE,
    embedding vector(1536), -- For semantic search
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Full-text search
    tsvector_col TSVECTOR GENERATED ALWAYS AS (
        to_tsvector('english', coalesce(title || ' ' || content, ''))
    ) STORED
);

-- Indexes for knowledge base
CREATE INDEX idx_kb_articles_category ON knowledge_base_articles(category);
CREATE INDEX idx_kb_articles_published ON knowledge_base_articles(is_published);
CREATE INDEX idx_kb_articles_tsvector ON knowledge_base_articles USING GIN(tsvector_col);
CREATE INDEX idx_kb_articles_embedding ON knowledge_base_articles USING ivfflat(embedding vector_cosine_ops) WITH (lists = 100);
```

## Indexing Strategy

### Primary Indexes
- Primary keys are indexed by default
- Foreign key columns should have indexes for JOIN performance
- Frequently queried columns need indexes

### Composite Indexes
For common query patterns:
```sql
-- For querying messages by customer and date range
CREATE INDEX idx_messages_customer_date ON messages(customer_id, timestamp DESC);

-- For querying tickets by customer, status, and priority
CREATE INDEX idx_tickets_customer_status_priority ON tickets(customer_id, status, priority);

-- For identity resolution
CREATE INDEX idx_customer_identity_lookup ON customer_identity_mapping(channel_id, channel_identifier);
```

### Partial Indexes
For common filtered queries:
```sql
-- Index only for active tickets
CREATE INDEX idx_active_tickets ON tickets(customer_id, status) WHERE status IN ('new', 'in_progress', 'waiting_for_customer');

-- Index only for published knowledge base articles
CREATE INDEX idx_published_kb ON knowledge_base_articles(id, title) WHERE is_published = TRUE;
```

## Constraints and Validation

### Check Constraints
```sql
-- Ensure priority values are valid
ALTER TABLE tickets ADD CONSTRAINT chk_ticket_priority
CHECK (priority IN ('low', 'medium', 'high', 'urgent'));

-- Ensure status values are valid
ALTER TABLE tickets ADD CONSTRAINT chk_ticket_status
CHECK (status IN ('new', 'in_progress', 'waiting_for_customer', 'resolved', 'closed', 'reopened'));

-- Ensure message direction is valid
ALTER TABLE messages ADD CONSTRAINT chk_message_direction
CHECK (direction IN ('inbound', 'outbound'));
```

### Unique Constraints
```sql
-- Ensure external IDs are unique where applicable
ALTER TABLE customers ADD CONSTRAINT uk_customers_external_id UNIQUE (external_id);
ALTER TABLE tickets ADD CONSTRAINT uk_tickets_external_id UNIQUE (external_id, customer_id);
```

## Triggers for Data Integrity

### Update Timestamp Trigger
```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply to all tables that have updated_at column
CREATE TRIGGER update_customers_updated_at
    BEFORE UPDATE ON customers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_messages_updated_at
    BEFORE UPDATE ON messages
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tickets_updated_at
    BEFORE UPDATE ON tickets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

## Partitioning Strategy

For large tables like messages, consider partitioning:
```sql
-- Partition messages by month
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
CREATE TABLE messages_2023_01 PARTITION OF messages_partitioned
    FOR VALUES FROM ('2023-01-01') TO ('2023-02-01');

CREATE TABLE messages_2023_02 PARTITION OF messages_partitioned
    FOR VALUES FROM ('2023-02-01') TO ('2023-03-01');
```