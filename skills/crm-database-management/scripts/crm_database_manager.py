#!/usr/bin/env python3
"""
CRM Database Manager
Manages the PostgreSQL database for the Internal CRM system.
Responsible for schema migrations, customer identity resolution,
ticket lifecycle tracking, and vector search implementation via pgvector.
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import uuid
import json

# Import required libraries
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import QueuePool
    import redis
    from cryptography.fernet import Fernet
    import jwt
    import numpy as np
except ImportError as e:
    print(f"Missing required package: {e}")
    print("Please install required packages: pip install -r requirements.txt")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TicketStatus(Enum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    WAITING_FOR_CUSTOMER = "waiting_for_customer"
    AWAITING_APPROVAL = "awaiting_approval"
    RESOLVED = "resolved"
    CLOSED = "closed"
    REOPENED = "reopened"

class TicketPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

# Database Manager Class
class CRMDatabaseManager:
    def __init__(self, database_url: str, redis_url: str = None, encryption_key: bytes = None):
        self.database_url = database_url
        self.redis_client = None

        # Initialize Redis if URL provided
        if redis_url:
            try:
                self.redis_client = redis.from_url(redis_url)
                logger.info("Connected to Redis successfully")
            except Exception as e:
                logger.warning(f"Could not connect to Redis: {e}")

        # Initialize database connection
        self.engine = create_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=3600
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        # Initialize encryption
        if encryption_key:
            self.cipher_suite = Fernet(encryption_key)
        else:
            # Generate a key for demonstration (use proper key management in production)
            key = Fernet.generate_key()
            self.cipher_suite = Fernet(key)
            logger.warning("Generated temporary encryption key. Use proper key management in production.")

        # Validate database connection
        self._validate_connection()

    def _validate_connection(self):
        """Validate database connection and extensions."""
        try:
            with self.engine.connect() as conn:
                # Check if pgvector extension is available
                result = conn.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector';"))
                if not result.fetchone():
                    logger.warning("pgvector extension not found. Vector search features will be limited.")

                # Check basic connectivity
                conn.execute(text("SELECT 1"))
                logger.info("Database connection validated successfully")
        except Exception as e:
            logger.error(f"Database connection validation failed: {e}")
            raise

    def initialize_schema(self):
        """Initialize the CRM database schema."""
        logger.info("Initializing CRM database schema...")

        schema_sql = """
        -- Enable pgvector extension if available
        CREATE EXTENSION IF NOT EXISTS vector;

        -- Customers table
        CREATE TABLE IF NOT EXISTS customers (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            external_id VARCHAR(255) UNIQUE,
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
            primary_channel_id UUID,
            is_merged BOOLEAN DEFAULT FALSE,
            merged_into_customer_id UUID REFERENCES customers(id)
        );

        -- Channels table
        CREATE TABLE IF NOT EXISTS channels (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(100) NOT NULL,
            provider VARCHAR(100),
            config JSONB DEFAULT '{}',
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );

        -- Messages table
        CREATE TABLE IF NOT EXISTS messages (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            customer_id UUID NOT NULL REFERENCES customers(id),
            channel_id UUID NOT NULL REFERENCES channels(id),
            external_message_id VARCHAR(255),
            sender_id VARCHAR(255),
            sender_name VARCHAR(255),
            content TEXT NOT NULL,
            message_type VARCHAR(50),
            direction VARCHAR(10) CHECK (direction IN ('inbound', 'outbound')),
            timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
            metadata JSONB DEFAULT '{}',
            embedding vector(1536),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

            -- Full-text search
            tsvector_col TSVECTOR GENERATED ALWAYS AS (
                to_tsvector('english', coalesce(content, ''))
            ) STORED
        );

        -- Tickets table
        CREATE TABLE IF NOT EXISTS tickets (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            customer_id UUID NOT NULL REFERENCES customers(id),
            external_id VARCHAR(255),
            subject VARCHAR(500) NOT NULL,
            description TEXT,
            status VARCHAR(50) NOT NULL DEFAULT 'new',
            priority VARCHAR(20) DEFAULT 'medium',
            category VARCHAR(100),
            subcategory VARCHAR(100),
            assigned_to UUID,
            created_by UUID,
            resolved_at TIMESTAMP WITH TIME ZONE,
            closed_at TIMESTAMP WITH TIME ZONE,
            reopened_count INTEGER DEFAULT 0,
            first_resolved_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            metadata JSONB DEFAULT '{}',
            sla_deadline TIMESTAMP WITH TIME ZONE,
            resolution_time_minutes INTEGER,
            response_time_minutes INTEGER,

            -- Full-text search
            tsvector_col TSVECTOR GENERATED ALWAYS AS (
                to_tsvector('english', coalesce(subject || ' ' || description, ''))
            ) STORED
        );

        -- Customer Identity Mapping Table
        CREATE TABLE IF NOT EXISTS customer_identity_mapping (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
            channel_id UUID NOT NULL REFERENCES channels(id),
            channel_identifier VARCHAR(255) NOT NULL,
            identifier_type VARCHAR(50) NOT NULL,
            confidence_score DECIMAL(3,2) DEFAULT 1.00,
            verified BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

            UNIQUE(channel_id, channel_identifier, identifier_type)
        );

        -- Ticket Status Change History
        CREATE TABLE IF NOT EXISTS ticket_status_changes (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            ticket_id UUID NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
            old_status VARCHAR(50),
            new_status VARCHAR(50) NOT NULL,
            changed_by VARCHAR(255),
            changed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            reason VARCHAR(255),
            comment TEXT,
            metadata JSONB DEFAULT '{}'
        );

        -- Knowledge Base Articles
        CREATE TABLE IF NOT EXISTS knowledge_base_articles (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            title VARCHAR(500) NOT NULL,
            content TEXT NOT NULL,
            category VARCHAR(100),
            tags TEXT[],
            is_published BOOLEAN DEFAULT FALSE,
            embedding vector(1536),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

            -- Full-text search
            tsvector_col TSVECTOR GENERATED ALWAYS AS (
                to_tsvector('english', coalesce(title || ' ' || content, ''))
            ) STORED
        );

        -- Create indexes
        CREATE INDEX IF NOT EXISTS idx_messages_customer_id ON messages(customer_id);
        CREATE INDEX IF NOT EXISTS idx_messages_channel_id ON messages(channel_id);
        CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp DESC);
        CREATE INDEX IF NOT EXISTS idx_messages_tsvector ON messages USING GIN(tsvector_col);
        CREATE INDEX IF NOT EXISTS idx_messages_embedding ON messages USING ivfflat(embedding vector_cosine_ops) WITH (lists = 100);

        CREATE INDEX IF NOT EXISTS idx_tickets_customer_id ON tickets(customer_id);
        CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
        CREATE INDEX IF NOT EXISTS idx_tickets_priority ON tickets(priority);
        CREATE INDEX IF NOT EXISTS idx_tickets_created_at ON tickets(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_tickets_sla_deadline ON tickets(sla_deadline);
        CREATE INDEX IF NOT EXISTS idx_tickets_tsvector ON tickets USING GIN(tsvector_col);

        CREATE INDEX IF NOT EXISTS idx_customer_identity_mapping_lookup ON customer_identity_mapping(channel_id, identifier_type, channel_identifier);
        CREATE INDEX IF NOT EXISTS idx_customer_identity_mapping_customer ON customer_identity_mapping(customer_id);

        CREATE INDEX IF NOT EXISTS idx_ticket_status_changes_ticket_id ON ticket_status_changes(ticket_id);
        CREATE INDEX IF NOT EXISTS idx_ticket_status_changes_changed_at ON ticket_status_changes(changed_at DESC);

        CREATE INDEX IF NOT EXISTS idx_kb_articles_category ON knowledge_base_articles(category);
        CREATE INDEX IF NOT EXISTS idx_kb_articles_published ON knowledge_base_articles(is_published);
        CREATE INDEX IF NOT EXISTS idx_kb_articles_tsvector ON knowledge_base_articles USING GIN(tsvector_col);
        CREATE INDEX IF NOT EXISTS idx_kb_articles_embedding ON knowledge_base_articles USING ivfflat(embedding vector_cosine_ops) WITH (lists = 100);

        -- Insert default channels
        INSERT INTO channels (name, provider) VALUES
        ('email', 'gmail'),
        ('whatsapp', 'twilio'),
        ('web_form', 'web')
        ON CONFLICT (name) DO NOTHING;
        """

        try:
            with self.engine.connect() as conn:
                conn.execute(text(schema_sql))
                conn.commit()
                logger.info("CRM database schema initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing schema: {e}")
            raise

    def create_customer(self, email: str, name: str = None, phone: str = None, company: str = None) -> uuid.UUID:
        """Create a new customer record."""
        customer_id = uuid.uuid4()

        with self.engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO customers (id, email, name, phone, company)
                VALUES (:id, :email, :name, :phone, :company)
            """), {
                "id": customer_id,
                "email": email,
                "name": name,
                "phone": phone,
                "company": company
            })
            conn.commit()

        logger.info(f"Created customer {customer_id} with email {email}")
        return customer_id

    def resolve_customer_identity(self, channel_id: uuid.UUID, identifier_type: str, identifier_value: str) -> Optional[uuid.UUID]:
        """Resolve customer identity based on channel identifier."""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT customer_id
                FROM customer_identity_mapping
                WHERE channel_id = :channel_id
                  AND identifier_type = :identifier_type
                  AND channel_identifier = :identifier_value
                LIMIT 1
            """), {
                "channel_id": channel_id,
                "identifier_type": identifier_type,
                "identifier_value": identifier_value
            }).fetchone()

            return result.customer_id if result else None

    def link_customer_identifier(self, customer_id: uuid.UUID, channel_id: uuid.UUID,
                              identifier_type: str, identifier_value: str, confidence_score: float = 1.0):
        """Link a channel identifier to a customer."""
        with self.engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO customer_identity_mapping
                (customer_id, channel_id, identifier_type, channel_identifier, confidence_score)
                VALUES (:customer_id, :channel_id, :identifier_type, :identifier_value, :confidence_score)
                ON CONFLICT (channel_id, identifier_type, channel_identifier)
                DO UPDATE SET
                    customer_id = :customer_id,
                    confidence_score = :confidence_score,
                    updated_at = NOW()
            """), {
                "customer_id": customer_id,
                "channel_id": channel_id,
                "identifier_type": identifier_type,
                "identifier_value": identifier_value,
                "confidence_score": confidence_score
            })
            conn.commit()

        logger.info(f"Linked identifier {identifier_value} to customer {customer_id}")

    def create_ticket(self, customer_id: uuid.UUID, subject: str, description: str,
                     priority: TicketPriority = TicketPriority.MEDIUM, category: str = None) -> uuid.UUID:
        """Create a new support ticket."""
        ticket_id = uuid.uuid4()

        # Calculate SLA deadline based on priority
        sla_deadline = datetime.utcnow()
        if priority == TicketPriority.URGENT:
            sla_deadline += timedelta(hours=4)
        elif priority == TicketPriority.HIGH:
            sla_deadline += timedelta(hours=24)
        elif priority == TicketPriority.MEDIUM:
            sla_deadline += timedelta(days=3)
        else:  # LOW
            sla_deadline += timedelta(days=7)

        with self.engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO tickets
                (id, customer_id, subject, description, priority, category, sla_deadline)
                VALUES (:id, :customer_id, :subject, :description, :priority, :category, :sla_deadline)
            """), {
                "id": ticket_id,
                "customer_id": customer_id,
                "subject": subject,
                "description": description,
                "priority": priority.value,
                "category": category,
                "sla_deadline": sla_deadline
            })

            # Log status change
            conn.execute(text("""
                INSERT INTO ticket_status_changes (ticket_id, new_status, changed_by, reason)
                VALUES (:ticket_id, 'new', 'system', 'Ticket created')
            """), {"ticket_id": ticket_id})

            conn.commit()

        logger.info(f"Created ticket {ticket_id} for customer {customer_id}")
        return ticket_id

    def update_ticket_status(self, ticket_id: uuid.UUID, new_status: TicketStatus,
                           changed_by: str, reason: str = None, comment: str = None):
        """Update ticket status with audit trail."""
        with self.engine.connect() as conn:
            # Get current status
            current_status = conn.execute(text("""
                SELECT status FROM tickets WHERE id = :ticket_id
            """), {"ticket_id": ticket_id}).fetchone()

            if not current_status:
                raise ValueError(f"Ticket {ticket_id} not found")

            old_status = current_status.status

            # Update ticket
            update_fields = ["updated_at = NOW()"]
            params = {"ticket_id": ticket_id, "new_status": new_status.value}

            if new_status == TicketStatus.RESOLVED and old_status != 'resolved':
                update_fields.append("resolved_at = NOW()")
                if not conn.execute(text("""
                    SELECT first_resolved_at FROM tickets WHERE id = :ticket_id
                """), {"ticket_id": ticket_id}).fetchone().first_resolved_at:
                    update_fields.append("first_resolved_at = NOW()")
            elif new_status == TicketStatus.CLOSED and old_status != 'closed':
                update_fields.append("closed_at = NOW()")
            elif new_status == TicketStatus.REOPENED:
                update_fields.append("reopened_count = COALESCE(reopened_count, 0) + 1")
                update_fields.append("resolved_at = NULL")
                update_fields.append("closed_at = NULL")

            update_fields.append("status = :new_status")

            conn.execute(text(f"""
                UPDATE tickets SET {', '.join(update_fields)} WHERE id = :ticket_id
            """), params)

            # Log status change
            conn.execute(text("""
                INSERT INTO ticket_status_changes
                (ticket_id, old_status, new_status, changed_by, reason, comment)
                VALUES (:ticket_id, :old_status, :new_status, :changed_by, :reason, :comment)
            """), {
                "ticket_id": ticket_id,
                "old_status": old_status,
                "new_status": new_status.value,
                "changed_by": changed_by,
                "reason": reason,
                "comment": comment
            })

            conn.commit()

        logger.info(f"Updated ticket {ticket_id} status to {new_status.value}")

    def semantic_search_kb_articles(self, query: str, category: str = None, limit: int = 5) -> List[Dict]:
        """Perform semantic search on knowledge base articles."""
        # This is a simplified implementation
        # In a real system, you would generate embeddings and use vector similarity

        with self.engine.connect() as conn:
            where_clause = "WHERE is_published = TRUE"
            params = {"limit": limit}

            if category:
                where_clause += " AND category = :category"
                params["category"] = category

            # For demo purposes, use full-text search instead of vector search
            # In production, this would use actual vector similarity
            result = conn.execute(text(f"""
                SELECT id, title, content, category,
                       ts_rank(tsvector_col, plainto_tsquery('english', :query)) as rank_score
                FROM knowledge_base_articles
                {where_clause}
                AND tsvector_col @@ plainto_tsquery('english', :query)
                ORDER BY rank_score DESC
                LIMIT :limit
            """), {**params, "query": query}).fetchall()

            return [
                {
                    "article_id": row.id,
                    "title": row.title,
                    "content": row.content[:200] + "..." if len(row.content) > 200 else row.content,
                    "category": row.category,
                    "relevance_score": float(row.rank_score)
                }
                for row in result
            ]

    def get_customer_tickets(self, customer_id: uuid.UUID, status_filter: str = None) -> List[Dict]:
        """Get all tickets for a customer."""
        with self.engine.connect() as conn:
            where_clause = "WHERE customer_id = :customer_id"
            params = {"customer_id": customer_id}

            if status_filter:
                where_clause += " AND status = :status"
                params["status"] = status_filter

            result = conn.execute(text(f"""
                SELECT id, subject, description, status, priority, category, created_at, updated_at
                FROM tickets
                {where_clause}
                ORDER BY created_at DESC
            """), params).fetchall()

            return [
                {
                    "ticket_id": str(row.id),
                    "subject": row.subject,
                    "description": row.description,
                    "status": row.status,
                    "priority": row.priority,
                    "category": row.category,
                    "created_at": row.created_at,
                    "updated_at": row.updated_at
                }
                for row in result
            ]

    def get_ticket_timeline(self, ticket_id: uuid.UUID) -> List[Dict]:
        """Get complete timeline of ticket activities."""
        with self.engine.connect() as conn:
            # Get status changes
            status_changes = conn.execute(text("""
                SELECT changed_at, old_status, new_status, changed_by, reason, comment
                FROM ticket_status_changes
                WHERE ticket_id = :ticket_id
                ORDER BY changed_at ASC
            """), {"ticket_id": ticket_id}).fetchall()

            timeline = []
            for change in status_changes:
                timeline.append({
                    "timestamp": change.changed_at,
                    "type": "status_change",
                    "old_status": change.old_status,
                    "new_status": change.new_status,
                    "changed_by": change.changed_by,
                    "reason": change.reason,
                    "comment": change.comment
                })

            return sorted(timeline, key=lambda x: x["timestamp"], reverse=True)

def main():
    """Main function demonstrating CRM database manager usage."""
    print("CRM Database Manager")
    print("=" * 50)

    # Get database URL from environment or use default
    database_url = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/crm_db")
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

    try:
        # Initialize the CRM database manager
        crm_db = CRMDatabaseManager(database_url, redis_url)

        # Initialize schema (this would typically be done separately)
        print("\n1. Initializing database schema...")
        crm_db.initialize_schema()

        # Create a sample customer
        print("\n2. Creating sample customer...")
        customer_id = crm_db.create_customer(
            email="john.doe@example.com",
            name="John Doe",
            phone="+1-555-123-4567",
            company="Example Corp"
        )
        print(f"   Created customer: {customer_id}")

        # Link customer identifier
        print("\n3. Linking customer identifier...")
        # First get the email channel ID
        with crm_db.engine.connect() as conn:
            channel_id = conn.execute(text("SELECT id FROM channels WHERE name = 'email'")).fetchone().id

        crm_db.link_customer_identifier(
            customer_id=customer_id,
            channel_id=channel_id,
            identifier_type="email",
            identifier_value="john.doe@example.com"
        )

        # Create a sample ticket
        print("\n4. Creating sample ticket...")
        ticket_id = crm_db.create_ticket(
            customer_id=customer_id,
            subject="Login Issues",
            description="Customer is experiencing problems logging into their account.",
            priority=TicketPriority.HIGH,
            category="technical"
        )
        print(f"   Created ticket: {ticket_id}")

        # Update ticket status
        print("\n5. Updating ticket status...")
        crm_db.update_ticket_status(
            ticket_id=ticket_id,
            new_status=TicketStatus.IN_PROGRESS,
            changed_by="support_agent_1",
            reason="Starting investigation"
        )

        # Search knowledge base
        print("\n6. Searching knowledge base...")
        kb_results = crm_db.semantic_search_kb_articles("login issues")
        print(f"   Found {len(kb_results)} relevant articles")
        for i, article in enumerate(kb_results[:2]):  # Show first 2
            print(f"   {i+1}. {article['title'][:50]}... (Score: {article['relevance_score']:.2f})")

        # Get customer tickets
        print("\n7. Getting customer tickets...")
        customer_tickets = crm_db.get_customer_tickets(customer_id)
        print(f"   Customer has {len(customer_tickets)} tickets")
        for ticket in customer_tickets:
            print(f"   - {ticket['subject']} [{ticket['status']}]")

        # Get ticket timeline
        print("\n8. Getting ticket timeline...")
        timeline = crm_db.get_ticket_timeline(ticket_id)
        print(f"   Ticket has {len(timeline)} timeline events")
        for event in timeline[:3]:  # Show first 3 events
            print(f"   - {event['timestamp']}: Status changed from {event['old_status']} to {event['new_status']} by {event['changed_by']}")

        print("\nCRM Database Manager demonstration completed successfully!")

    except Exception as e:
        logger.error(f"Error running CRM Database Manager: {e}")
        print(f"\nError: {e}")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())