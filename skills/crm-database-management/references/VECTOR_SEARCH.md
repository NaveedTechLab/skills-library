# Vector Search Implementation Reference

## Introduction to pgvector

pgvector is a PostgreSQL extension that enables vector similarity search capabilities. It's perfect for implementing semantic search in CRM systems, allowing for similarity matching of customer interactions, ticket content, and knowledge base articles.

### Installation and Setup

```sql
-- Enable the pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Verify installation
SELECT extname FROM pg_extension WHERE extname = 'vector';
```

## Vector Embeddings Schema

### Core Vector Tables

```sql
-- Table for storing message embeddings
CREATE TABLE message_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES customers(id),
    embedding vector(1536), -- Assuming OpenAI ada-002 embeddings (1536 dimensions)
    content_type VARCHAR(50) DEFAULT 'message', -- 'message', 'ticket', 'kb_article'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Index for faster similarity search
    -- This uses IVFFlat index for approximate nearest neighbor search
    -- Lists parameter controls the number of clusters (adjust based on data size)
    -- For smaller datasets, use fewer lists; for larger datasets, use more
);

-- Table for knowledge base article embeddings
CREATE TABLE kb_article_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    article_id UUID NOT NULL REFERENCES knowledge_base_articles(id) ON DELETE CASCADE,
    embedding vector(1536),
    title VARCHAR(500),
    content_summary TEXT, -- First N characters of content for quick preview
    category VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table for ticket embeddings
CREATE TABLE ticket_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id UUID NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES customers(id),
    embedding vector(1536),
    subject VARCHAR(500),
    description_summary TEXT, -- First N characters of description
    status VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Indexing for Performance

```sql
-- Create indexes for vector similarity search
-- IVFFlat index with cosine distance (good balance of speed and accuracy)
-- Adjust the 'lists' parameter based on your dataset size
-- Rule of thumb: lists = sqrt(number_of_rows)

-- For message embeddings (assuming ~100K messages)
CREATE INDEX idx_message_embeddings_ivfflat
ON message_embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 316); -- sqrt(100000) ≈ 316

-- For knowledge base embeddings (assuming ~10K articles)
CREATE INDEX idx_kb_embeddings_ivfflat
ON kb_article_embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100); -- sqrt(10000) = 100

-- For ticket embeddings (assuming ~50K tickets)
CREATE INDEX idx_ticket_embeddings_ivfflat
ON ticket_embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 224); -- sqrt(50000) ≈ 224

-- Additional indexes for filtering
CREATE INDEX idx_message_embeddings_customer_id ON message_embeddings(customer_id);
CREATE INDEX idx_message_embeddings_created_at ON message_embeddings(created_at DESC);
CREATE INDEX idx_kb_embeddings_category ON kb_article_embeddings(category);
CREATE INDEX idx_ticket_embeddings_status ON ticket_embeddings(status);
CREATE INDEX idx_ticket_embeddings_customer_id ON ticket_embeddings(customer_id);
```

## Vector Operations

### Distance Functions

pgvector provides several distance functions:

```sql
-- Cosine distance (most common for text embeddings)
SELECT * FROM table_name ORDER BY embedding <=> '[0,1,2]' LIMIT 5;

-- Euclidean distance (L2 distance)
SELECT * FROM table_name ORDER BY embedding <-> '[0,1,2]' LIMIT 5;

-- Inner product (for binary vectors or specific use cases)
SELECT * FROM table_name ORDER BY embedding <#> '[0,1,2]' LIMIT 5;
```

## Python Implementation

### Vector Database Service

```python
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any, Optional
import uuid
import logging

logger = logging.getLogger(__name__)

class VectorSearchService:
    def __init__(self, db: Session):
        self.db = db

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text using your preferred model.
        This is a placeholder - implement with your actual embedding provider.
        """
        # Placeholder implementation
        # In real implementation, use OpenAI, SentenceTransformers, etc.
        import random
        # Return a random 1536-dimensional vector as placeholder
        return [random.random() for _ in range(1536)]

    def store_message_embedding(self, message_id: uuid.UUID, customer_id: uuid.UUID, content: str):
        """
        Store embedding for a message.
        """
        embedding = self.generate_embedding(content)

        self.db.execute(
            text("""
            INSERT INTO message_embeddings (message_id, customer_id, embedding)
            VALUES (:message_id, :customer_id, :embedding)
            """),
            {
                "message_id": message_id,
                "customer_id": customer_id,
                "embedding": "[" + ",".join(map(str, embedding)) + "]"
            }
        )
        self.db.commit()

    def store_kb_article_embedding(self, article_id: uuid.UUID, title: str, content: str, category: str):
        """
        Store embedding for a knowledge base article.
        """
        # Use title + content for better semantic representation
        text_to_embed = f"{title} {content[:500]}"  # Limit content to avoid huge embeddings
        embedding = self.generate_embedding(text_to_embed)

        self.db.execute(
            text("""
            INSERT INTO kb_article_embeddings
            (article_id, embedding, title, content_summary, category)
            VALUES (:article_id, :embedding, :title, :content_summary, :category)
            """),
            {
                "article_id": article_id,
                "embedding": "[" + ",".join(map(str, embedding)) + "]",
                "title": title,
                "content_summary": content[:200],  # Store summary for quick preview
                "category": category
            }
        )
        self.db.commit()

    def store_ticket_embedding(self, ticket_id: uuid.UUID, customer_id: uuid.UUID, subject: str, description: str, status: str):
        """
        Store embedding for a ticket.
        """
        text_to_embed = f"{subject} {description[:500]}"
        embedding = self.generate_embedding(text_to_embed)

        self.db.execute(
            text("""
            INSERT INTO ticket_embeddings
            (ticket_id, customer_id, embedding, subject, description_summary, status)
            VALUES (:ticket_id, :customer_id, :embedding, :subject, :description_summary, :status)
            """),
            {
                "ticket_id": ticket_id,
                "customer_id": customer_id,
                "embedding": "[" + ",".join(map(str, embedding)) + "]",
                "subject": subject,
                "description_summary": description[:200],
                "status": status
            }
        )
        self.db.commit()

    def semantic_search_messages(self, query: str, customer_id: Optional[uuid.UUID] = None, limit: int = 5) -> List[Dict]:
        """
        Semantic search in message embeddings.
        """
        query_embedding = self.generate_embedding(query)

        where_clause = "WHERE m.customer_id = :customer_id" if customer_id else ""
        params = {"query_embedding": "[" + ",".join(map(str, query_embedding)) + "]", "customer_id": customer_id}

        sql = f"""
        SELECT
            m.message_id,
            m.customer_id,
            msg.content,
            msg.timestamp,
            (1 - (m.embedding <=> :query_embedding)) as similarity_score
        FROM message_embeddings m
        JOIN messages msg ON m.message_id = msg.id
        {where_clause}
        ORDER BY m.embedding <=> :query_embedding
        LIMIT :limit
        """

        params["limit"] = limit

        results = self.db.execute(text(sql), params).fetchall()

        return [
            {
                "message_id": result.message_id,
                "customer_id": result.customer_id,
                "content": result.content,
                "timestamp": result.timestamp,
                "similarity_score": result.similarity_score
            }
            for result in results
        ]

    def semantic_search_kb_articles(self, query: str, category: Optional[str] = None, limit: int = 5) -> List[Dict]:
        """
        Semantic search in knowledge base articles.
        """
        query_embedding = self.generate_embedding(query)

        where_clause = "WHERE category = :category" if category else ""
        params = {"query_embedding": "[" + ",".join(map(str, query_embedding)) + "]", "category": category}

        sql = f"""
        SELECT
            k.article_id,
            k.title,
            k.content_summary,
            k.category,
            (1 - (k.embedding <=> :query_embedding)) as similarity_score
        FROM kb_article_embeddings k
        {where_clause}
        ORDER BY k.embedding <=> :query_embedding
        LIMIT :limit
        """

        params["limit"] = limit

        results = self.db.execute(text(sql), params).fetchall()

        return [
            {
                "article_id": result.article_id,
                "title": result.title,
                "content_summary": result.content_summary,
                "category": result.category,
                "similarity_score": result.similarity_score
            }
            for result in results
        ]

    def semantic_search_tickets(self, query: str, customer_id: Optional[uuid.UUID] = None, status: Optional[str] = None, limit: int = 5) -> List[Dict]:
        """
        Semantic search in ticket embeddings.
        """
        query_embedding = self.generate_embedding(query)

        conditions = []
        params = {"query_embedding": "[" + ",".join(map(str, query_embedding)) + "]"}

        if customer_id:
            conditions.append("t.customer_id = :customer_id")
            params["customer_id"] = customer_id

        if status:
            conditions.append("t.status = :status")
            params["status"] = status

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        params["limit"] = limit

        sql = f"""
        SELECT
            t.ticket_id,
            t.customer_id,
            t.subject,
            t.description_summary,
            t.status,
            (1 - (t.embedding <=> :query_embedding)) as similarity_score
        FROM ticket_embeddings t
        {where_clause}
        ORDER BY t.embedding <=> :query_embedding
        LIMIT :limit
        """

        results = self.db.execute(text(sql), params).fetchall()

        return [
            {
                "ticket_id": result.ticket_id,
                "customer_id": result.customer_id,
                "subject": result.subject,
                "description_summary": result.description_summary,
                "status": result.status,
                "similarity_score": result.similarity_score
            }
            for result in results
        ]

    def find_similar_tickets(self, ticket_id: uuid.UUID, limit: int = 5) -> List[Dict]:
        """
        Find tickets similar to a given ticket.
        """
        # Get the embedding of the reference ticket
        reference_embedding = self.db.execute(
            text("SELECT embedding FROM ticket_embeddings WHERE ticket_id = :ticket_id"),
            {"ticket_id": ticket_id}
        ).fetchone()

        if not reference_embedding:
            return []

        sql = """
        SELECT
            t.ticket_id,
            t.customer_id,
            t.subject,
            t.description_summary,
            t.status,
            (1 - (t.embedding <=> :reference_embedding)) as similarity_score
        FROM ticket_embeddings t
        WHERE t.ticket_id != :ticket_id
        ORDER BY t.embedding <=> :reference_embedding
        LIMIT :limit
        """

        results = self.db.execute(
            text(sql),
            {
                "reference_embedding": str(reference_embedding.embedding),
                "ticket_id": ticket_id,
                "limit": limit
            }
        ).fetchall()

        return [
            {
                "ticket_id": result.ticket_id,
                "customer_id": result.customer_id,
                "subject": result.subject,
                "description_summary": result.description_summary,
                "status": result.status,
                "similarity_score": result.similarity_score
            }
            for result in results
        ]
```

## Integration with OpenAI Embeddings

### Real Implementation with OpenAI

```python
import openai
from typing import List
import os

class OpenAIEmbeddingService(VectorSearchService):
    def __init__(self, db: Session, api_key: str = None):
        super().__init__(db)

        # Initialize OpenAI
        openai.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not openai.api_key:
            raise ValueError("OpenAI API key is required")

    def generate_embedding(self, text: str, model: str = "text-embedding-ada-002") -> List[float]:
        """
        Generate embedding using OpenAI's text-embedding-ada-002 model.
        """
        try:
            # Truncate text if too long (OpenAI has 8192 token limit)
            if len(text) > 8000:  # Conservative limit
                text = text[:8000]

            response = openai.Embedding.create(
                input=text,
                model=model
            )

            return response['data'][0]['embedding']
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            # Return zeros as fallback
            return [0.0] * 1536

    def batch_generate_embeddings(self, texts: List[str], model: str = "text-embedding-ada-002") -> List[List[float]]:
        """
        Generate embeddings for multiple texts in a batch.
        """
        try:
            # Split into batches of 2000 (OpenAI's max batch size)
            all_embeddings = []
            batch_size = 2000

            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]

                # Truncate long texts
                truncated_batch = [text[:8000] if len(text) > 8000 else text for text in batch]

                response = openai.Embedding.create(
                    input=truncated_batch,
                    model=model
                )

                batch_embeddings = [item['embedding'] for item in response['data']]
                all_embeddings.extend(batch_embeddings)

            return all_embeddings
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            # Return zeros as fallback
            return [[0.0] * 1536 for _ in texts]
```

## Performance Optimization

### Index Maintenance

```python
class VectorIndexOptimizer:
    def __init__(self, db: Session):
        self.db = db

    def optimize_indexes(self):
        """
        Optimize vector indexes based on data size.
        """
        # Get current row counts
        message_count = self.db.execute(text("SELECT COUNT(*) FROM message_embeddings")).fetchone()[0]
        kb_count = self.db.execute(text("SELECT COUNT(*) FROM kb_article_embeddings")).fetchone()[0]
        ticket_count = self.db.execute(text("SELECT COUNT(*) FROM ticket_embeddings")).fetchone()[0]

        # Calculate optimal number of lists for IVFFlat index
        optimal_lists = {
            'message_embeddings': max(100, int(message_count ** 0.5)),  # At least 100 lists
            'kb_article_embeddings': max(50, int(kb_count ** 0.5)),      # At least 50 lists
            'ticket_embeddings': max(75, int(ticket_count ** 0.5))      # At least 75 lists
        }

        # Recreate indexes with optimal parameters
        for table_name, lists in optimal_lists.items():
            # Drop existing index
            self.db.execute(text(f"DROP INDEX IF EXISTS idx_{table_name}_ivfflat"))

            # Create new index
            self.db.execute(text(f"""
                CREATE INDEX idx_{table_name}_ivfflat
                ON {table_name}
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = {lists})
            """))

        self.db.commit()
        logger.info(f"Optimized vector indexes: {optimal_lists}")

    def update_statistics(self):
        """
        Update table statistics for query planner.
        """
        self.db.execute(text("ANALYZE message_embeddings"))
        self.db.execute(text("ANALYZE kb_article_embeddings"))
        self.db.execute(text("ANALYZE ticket_embeddings"))
        self.db.commit()
        logger.info("Updated table statistics")
```

## Semantic Search Applications

### Customer Support Use Cases

```python
class SemanticSearchApplications:
    def __init__(self, vector_service: VectorSearchService):
        self.vector_service = vector_service

    def find_related_tickets(self, current_ticket_description: str, customer_id: uuid.UUID) -> List[Dict]:
        """
        Find previously resolved tickets related to the current issue.
        """
        similar_tickets = self.vector_service.semantic_search_tickets(
            query=current_ticket_description,
            customer_id=customer_id,
            limit=5
        )

        # Filter to only show resolved/closed tickets
        resolved_tickets = [
            ticket for ticket in similar_tickets
            if ticket['status'] in ['resolved', 'closed']
        ]

        return resolved_tickets

    def suggest_kb_articles(self, customer_query: str, category: str = None) -> List[Dict]:
        """
        Suggest relevant knowledge base articles for customer query.
        """
        articles = self.vector_service.semantic_search_kb_articles(
            query=customer_query,
            category=category,
            limit=3
        )

        return articles

    def find_conversation_context(self, customer_id: uuid.UUID, current_query: str) -> List[Dict]:
        """
        Find relevant past messages in customer's conversation history.
        """
        past_messages = self.vector_service.semantic_search_messages(
            query=current_query,
            customer_id=customer_id,
            limit=10
        )

        # Sort by timestamp to show chronological context
        past_messages.sort(key=lambda x: x['timestamp'], reverse=True)

        return past_messages

    def detect_duplicate_tickets(self, new_ticket_subject: str, new_ticket_description: str) -> List[Dict]:
        """
        Detect potential duplicate tickets based on semantic similarity.
        """
        query_text = f"{new_ticket_subject} {new_ticket_description}"

        # Search among recent open tickets
        potential_duplicates = self.vector_service.semantic_search_tickets(
            query=query_text,
            status='new',  # Only check new/in-progress tickets
            limit=5
        )

        # Filter for high similarity (threshold can be adjusted)
        high_similarity_tickets = [
            ticket for ticket in potential_duplicates
            if ticket['similarity_score'] > 0.8  # 80% similarity threshold
        ]

        return high_similarity_tickets
```

## Monitoring and Maintenance

### Performance Monitoring

```sql
-- Query to monitor vector search performance
EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM kb_article_embeddings
ORDER BY embedding <=> '[0.1,0.2,0.3,...]'
LIMIT 5;

-- Check index usage
SELECT schemaname, tablename, attname, indexname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
WHERE tablename LIKE '%embeddings%';
```

### Cleanup and Maintenance

```python
class VectorDataMaintenance:
    def __init__(self, db: Session):
        self.db = db

    def cleanup_stale_embeddings(self):
        """
        Remove embeddings for deleted messages/tickets/articles.
        """
        # Clean up message embeddings without corresponding messages
        self.db.execute(text("""
            DELETE FROM message_embeddings
            WHERE message_id NOT IN (SELECT id FROM messages)
        """))

        # Clean up KB article embeddings without corresponding articles
        self.db.execute(text("""
            DELETE FROM kb_article_embeddings
            WHERE article_id NOT IN (SELECT id FROM knowledge_base_articles)
        """))

        # Clean up ticket embeddings without corresponding tickets
        self.db.execute(text("""
            DELETE FROM ticket_embeddings
            WHERE ticket_id NOT IN (SELECT id FROM tickets)
        """))

        self.db.commit()
        logger.info("Cleaned up stale embeddings")

    def refresh_embeddings(self, content_type: str = "kb_articles"):
        """
        Regenerate embeddings for all content of a specific type.
        Useful when changing embedding models.
        """
        if content_type == "kb_articles":
            # Get all KB articles
            articles = self.db.execute(text("""
                SELECT id, title, content, category
                FROM knowledge_base_articles
                WHERE is_published = TRUE
            """)).fetchall()

            # Delete old embeddings
            self.db.execute(text("DELETE FROM kb_article_embeddings"))

            # Regenerate embeddings
            for article in articles:
                self.vector_service.store_kb_article_embedding(
                    article_id=article.id,
                    title=article.title,
                    content=article.content,
                    category=article.category
                )

        elif content_type == "messages":
            # Similar logic for messages
            pass

        elif content_type == "tickets":
            # Similar logic for tickets
            pass

        self.db.commit()
```

This comprehensive vector search implementation provides semantic search capabilities across messages, tickets, and knowledge base articles, enabling intelligent customer support features like related ticket suggestions, knowledge base article recommendations, and duplicate detection.