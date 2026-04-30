# Customer Identity Resolution Reference

## Identity Resolution Strategy

### Core Concepts

Customer identity resolution is the process of linking multiple identifiers (email, phone, social media handles, etc.) to a single customer entity. This is crucial for maintaining a unified customer view across multiple channels.

### Identity Matching Algorithms

#### 1. Exact Matching
For high-confidence matches:
```python
def exact_match_identifiers(identifier1: str, identifier2: str, id_type: str) -> float:
    """
    Calculate confidence score for exact identifier matching.
    Returns 1.0 for exact match, 0.0 for no match.
    """
    if id_type == "email":
        # Normalize email (lowercase, trim whitespace)
        id1_norm = identifier1.lower().strip()
        id2_norm = identifier2.lower().strip()
        return 1.0 if id1_norm == id2_norm else 0.0

    elif id_type == "phone":
        # Normalize phone numbers (remove non-digit characters)
        import re
        id1_norm = re.sub(r'\D', '', identifier1)
        id2_norm = re.sub(r'\D', '', identifier2)

        # Check if numbers match (with or without country code)
        if id1_norm.endswith(id2_norm) or id2_norm.endswith(id1_norm):
            return 1.0
        return 0.0

    else:
        # For other identifiers, do exact match
        return 1.0 if identifier1.strip() == identifier2.strip() else 0.0
```

#### 2. Fuzzy Matching
For potential typos or variations:
```python
from difflib import SequenceMatcher
import re

def fuzzy_match_identifiers(identifier1: str, identifier2: str, threshold: float = 0.85) -> float:
    """
    Calculate confidence score using fuzzy string matching.
    Returns similarity score between 0.0 and 1.0.
    """
    # Normalize strings (remove extra spaces, convert to lowercase)
    id1_norm = re.sub(r'\s+', ' ', identifier1.lower().strip())
    id2_norm = re.sub(r'\s+', ' ', identifier2.lower().strip())

    similarity = SequenceMatcher(None, id1_norm, id2_norm).ratio()
    return similarity if similarity >= threshold else 0.0
```

#### 3. Composite Matching
For matching based on multiple identifiers:
```python
def composite_match_score(identities1: dict, identities2: dict, weights: dict = None) -> float:
    """
    Calculate composite confidence score based on multiple identifiers.

    Args:
        identities1: Dictionary of identifiers for first customer
        identities2: Dictionary of identifiers for second customer
        weights: Weighting for each identifier type

    Returns:
        Composite confidence score between 0.0 and 1.0
    """
    if weights is None:
        weights = {
            'email': 0.4,
            'phone': 0.3,
            'name': 0.2,
            'external_id': 0.1
        }

    total_score = 0.0
    total_weight = 0.0

    for id_type, weight in weights.items():
        id1 = identities1.get(id_type)
        id2 = identities2.get(id_type)

        if id1 and id2:
            score = exact_match_identifiers(id1, id2, id_type)
            if score == 0.0:  # Try fuzzy match if exact match fails
                score = fuzzy_match_identifiers(id1, id2)

            total_score += score * weight
            total_weight += weight
        elif id1 or id2:  # One has the identifier, the other doesn't
            total_weight += weight

    if total_weight == 0:
        return 0.0

    return total_score / total_weight
```

## Database Implementation

### Customer Identity Mapping Table

```sql
-- This table maps channel-specific identifiers to our internal customer IDs
CREATE TABLE customer_identity_mapping (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    channel_id UUID NOT NULL REFERENCES channels(id),
    channel_identifier VARCHAR(255) NOT NULL, -- Email, phone number, etc.
    identifier_type VARCHAR(50) NOT NULL, -- 'email', 'phone', 'external_id', etc.
    confidence_score DECIMAL(3,2) DEFAULT 1.00, -- 0.00 to 1.00
    verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(channel_id, channel_identifier, identifier_type)
);

-- Index for fast lookups
CREATE INDEX idx_customer_identity_mapping_lookup
ON customer_identity_mapping(channel_id, identifier_type, channel_identifier);
CREATE INDEX idx_customer_identity_mapping_customer
ON customer_identity_mapping(customer_id);
```

### Identity Resolution Functions

```python
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, List, Optional, Tuple
import uuid

def resolve_customer_identity(
    db: Session,
    channel_id: uuid.UUID,
    identifier_type: str,
    identifier_value: str,
    min_confidence: float = 0.8
) -> Optional[uuid.UUID]:
    """
    Resolve a customer ID based on a channel identifier.

    Args:
        db: Database session
        channel_id: The channel where the identifier was found
        identifier_type: Type of identifier ('email', 'phone', etc.)
        identifier_value: The actual identifier value
        min_confidence: Minimum confidence score for a match

    Returns:
        Customer ID if found, None otherwise
    """
    result = db.execute(
        text("""
        SELECT customer_id, confidence_score
        FROM customer_identity_mapping
        WHERE channel_id = :channel_id
          AND identifier_type = :identifier_type
          AND channel_identifier = :identifier_value
        ORDER BY confidence_score DESC
        LIMIT 1
        """),
        {
            "channel_id": channel_id,
            "identifier_type": identifier_type,
            "identifier_value": identifier_value
        }
    ).fetchone()

    if result and result.confidence_score >= min_confidence:
        return result.customer_id

    return None

def find_potential_duplicates(
    db: Session,
    new_customer_data: Dict,
    threshold: float = 0.7
) -> List[uuid.UUID]:
    """
    Find potential duplicate customers based on new customer data.

    Args:
        db: Database session
        new_customer_data: Dictionary containing customer identifiers
        threshold: Similarity threshold for potential duplicates

    Returns:
        List of potential matching customer IDs
    """
    # Get all existing customers with their identifiers
    existing_customers = db.execute(
        text("""
        SELECT
            c.id as customer_id,
            c.name,
            c.email,
            c.phone,
            c.company,
            array_agg(cim.channel_identifier) as other_identifiers
        FROM customers c
        LEFT JOIN customer_identity_mapping cim ON c.id = cim.customer_id
        GROUP BY c.id
        """)
    ).fetchall()

    potential_matches = []

    for customer in existing_customers:
        existing_data = {
            'name': customer.name,
            'email': customer.email,
            'phone': customer.phone,
            'company': customer.company
        }

        score = composite_match_score(existing_data, new_customer_data)

        if score >= threshold:
            potential_matches.append(customer.customer_id)

    return potential_matches

def link_customer_identifier(
    db: Session,
    customer_id: uuid.UUID,
    channel_id: uuid.UUID,
    identifier_type: str,
    identifier_value: str,
    confidence_score: float = 1.0,
    verified: bool = False
):
    """
    Link a channel identifier to a customer.

    Args:
        db: Database session
        customer_id: Internal customer ID
        channel_id: Channel ID
        identifier_type: Type of identifier
        identifier_value: The identifier value
        confidence_score: Confidence in the match
        verified: Whether this association has been verified
    """
    # Insert or update the mapping
    db.execute(
        text("""
        INSERT INTO customer_identity_mapping
        (customer_id, channel_id, identifier_type, channel_identifier, confidence_score, verified)
        VALUES (:customer_id, :channel_id, :identifier_type, :identifier_value, :confidence_score, :verified)
        ON CONFLICT (channel_id, identifier_type, channel_identifier)
        DO UPDATE SET
            customer_id = :customer_id,
            confidence_score = :confidence_score,
            verified = :verified,
            updated_at = NOW()
        """),
        {
            "customer_id": customer_id,
            "channel_id": channel_id,
            "identifier_type": identifier_type,
            "identifier_value": identifier_value,
            "confidence_score": confidence_score,
            "verified": verified
        }
    )
    db.commit()
```

## Identity Resolution Workflows

### 1. New Customer Creation

```python
def create_or_resolve_customer(
    db: Session,
    channel_id: uuid.UUID,
    message_data: Dict
) -> uuid.UUID:
    """
    Create a new customer or resolve to existing customer based on identifiers.
    """
    # Extract identifiers from message data
    identifiers = extract_identifiers_from_message(message_data)

    # Try to resolve existing customer
    for id_type, id_value in identifiers.items():
        customer_id = resolve_customer_identity(
            db, channel_id, id_type, id_value
        )
        if customer_id:
            # Update customer info if needed
            update_customer_from_message(db, customer_id, message_data)
            return customer_id

    # Check for potential duplicates
    potential_duplicates = find_potential_duplicates(db, identifiers)

    if potential_duplicates:
        # Handle duplicate situation - maybe merge or ask for verification
        if len(potential_duplicates) == 1:
            # High confidence match, link to existing customer
            customer_id = potential_duplicates[0]
            for id_type, id_value in identifiers.items():
                link_customer_identifier(
                    db, customer_id, channel_id, id_type, id_value,
                    confidence_score=0.8  # Lower confidence for fuzzy matches
                )
            return customer_id
        else:
            # Multiple potential matches - need manual resolution
            raise DuplicateCustomerException(
                f"Multiple potential matches found: {potential_duplicates}"
            )

    # Create new customer
    customer_id = create_new_customer(db, message_data)

    # Link all identifiers to the new customer
    for id_type, id_value in identifiers.items():
        link_customer_identifier(
            db, customer_id, channel_id, id_type, id_value
        )

    return customer_id

def extract_identifiers_from_message(message_data: Dict) -> Dict[str, str]:
    """
    Extract various identifiers from a message payload.
    """
    identifiers = {}

    # Extract from common fields
    if message_data.get('sender_id'):
        # This might be email, phone, or other identifier depending on channel
        if '@' in message_data['sender_id']:  # Likely email
            identifiers['email'] = message_data['sender_id']
        elif message_data['sender_id'].startswith('whatsapp:') or message_data['sender_id'].replace('-', '').replace(' ', '').isdigit():
            identifiers['phone'] = message_data['sender_id']

    # Extract from metadata
    if message_data.get('customer_email'):
        identifiers['email'] = message_data['customer_email']

    if message_data.get('customer_phone'):
        identifiers['phone'] = message_data['customer_phone']

    if message_data.get('external_customer_id'):
        identifiers['external_id'] = message_data['external_customer_id']

    # Extract from content (advanced - would use NLP in real implementation)
    # content = message_data.get('content', '')
    # emails_found = extract_emails(content)
    # phones_found = extract_phone_numbers(content)

    return identifiers
```

### 2. Customer Profile Unification

```python
def unify_customer_profile(db: Session, customer_ids: List[uuid.UUID]) -> uuid.UUID:
    """
    Unify multiple customer profiles into one.

    Args:
        db: Database session
        customer_ids: List of customer IDs to unify

    Returns:
        ID of the unified customer profile
    """
    if len(customer_ids) <= 1:
        return customer_ids[0] if customer_ids else None

    # Choose primary customer (maybe the one with the most interactions)
    primary_customer = choose_primary_customer(db, customer_ids)

    # Collect all data from secondary customers
    all_data = collect_customer_data(db, customer_ids)

    # Update primary customer with unified data
    update_customer_with_unified_data(db, primary_customer.id, all_data)

    # Link all identifiers to primary customer
    for customer_id in customer_ids:
        if customer_id != primary_customer.id:
            # Move all identifiers to primary customer
            move_customer_identifiers(db, customer_id, primary_customer.id)

            # Update all related records to point to primary customer
            update_related_records(db, customer_id, primary_customer.id)

            # Mark secondary customer as merged
            mark_customer_as_merged(db, customer_id, primary_customer.id)

    return primary_customer.id

def choose_primary_customer(db: Session, customer_ids: List[uuid.UUID]) -> Dict:
    """
    Choose which customer profile should be the primary one.
    """
    # Criteria could include:
    # - Most recent interaction
    # - Most interactions overall
    # - Most complete profile
    # - Earliest creation date

    customer_stats = []

    for cust_id in customer_ids:
        stats = db.execute(
            text("""
            SELECT
                c.id,
                c.created_at,
                c.last_interaction_at,
                COUNT(m.id) as message_count,
                COUNT(t.id) as ticket_count
            FROM customers c
            LEFT JOIN messages m ON c.id = m.customer_id
            LEFT JOIN tickets t ON c.id = t.customer_id
            WHERE c.id = :customer_id
            GROUP BY c.id, c.created_at, c.last_interaction_at
            """),
            {"customer_id": cust_id}
        ).fetchone()

        customer_stats.append(stats)

    # Choose primary based on most interactions
    primary = max(customer_stats, key=lambda x: x.message_count + x.ticket_count)
    return primary

def move_customer_identifiers(db: Session, from_customer_id: uuid.UUID, to_customer_id: uuid.UUID):
    """
    Move all identifiers from one customer to another.
    """
    db.execute(
        text("""
        UPDATE customer_identity_mapping
        SET customer_id = :to_customer_id
        WHERE customer_id = :from_customer_id
        """),
        {
            "to_customer_id": to_customer_id,
            "from_customer_id": from_customer_id
        }
    )
    db.commit()
```

## Conflict Resolution

### Handling Identity Conflicts

```python
class IdentityConflictResolver:
    def __init__(self, db: Session):
        self.db = db

    def resolve_conflict(
        self,
        channel_id: uuid.UUID,
        identifier_type: str,
        identifier_value: str,
        new_customer_id: uuid.UUID
    ) -> Dict:
        """
        Resolve conflict when an identifier is linked to a different customer.

        Returns resolution strategy and result.
        """
        # Find existing mapping
        existing_mapping = self.db.execute(
            text("""
            SELECT customer_id, confidence_score, verified
            FROM customer_identity_mapping
            WHERE channel_id = :channel_id
              AND identifier_type = :identifier_type
              AND channel_identifier = :identifier_value
            """),
            {
                "channel_id": channel_id,
                "identifier_type": identifier_type,
                "identifier_value": identifier_value
            }
        ).fetchone()

        if not existing_mapping:
            # No conflict, link normally
            link_customer_identifier(
                self.db, new_customer_id, channel_id,
                identifier_type, identifier_value
            )
            return {"action": "linked", "customer_id": new_customer_id}

        existing_customer_id = existing_mapping.customer_id

        if existing_customer_id == new_customer_id:
            # Already linked to same customer, nothing to do
            return {"action": "unchanged", "customer_id": existing_customer_id}

        # We have a conflict - same identifier linked to different customers
        if existing_mapping.verified:
            # If the existing mapping is verified, this might be fraud or error
            return {
                "action": "conflict_verified",
                "existing_customer_id": existing_customer_id,
                "new_customer_id": new_customer_id,
                "resolution_needed": True
            }
        else:
            # Existing mapping is not verified, we can potentially update it
            # Check confidence scores
            if existing_mapping.confidence_score < 0.8:
                # Low confidence in existing mapping, update to new customer
                self.db.execute(
                    text("""
                    UPDATE customer_identity_mapping
                    SET customer_id = :new_customer_id,
                        confidence_score = 0.8,
                        updated_at = NOW()
                    WHERE channel_id = :channel_id
                      AND identifier_type = :identifier_type
                      AND channel_identifier = :identifier_value
                    """),
                    {
                        "new_customer_id": new_customer_id,
                        "channel_id": channel_id,
                        "identifier_type": identifier_type,
                        "identifier_value": identifier_value
                    }
                )
                self.db.commit()

                return {"action": "updated", "customer_id": new_customer_id}
            else:
                # High confidence in existing mapping, mark as conflict
                return {
                    "action": "conflict_high_confidence",
                    "existing_customer_id": existing_customer_id,
                    "new_customer_id": new_customer_id,
                    "resolution_needed": True
                }
```

## Performance Optimization

### Caching Strategies

```python
import redis
from typing import Optional
import json

class IdentityCache:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    def get_cached_resolution(
        self,
        channel_id: str,
        identifier_type: str,
        identifier_value: str
    ) -> Optional[str]:
        """Get cached customer ID resolution."""
        key = f"identity:{channel_id}:{identifier_type}:{identifier_value}"
        cached = self.redis.get(key)
        return cached.decode() if cached else None

    def cache_resolution(
        self,
        channel_id: str,
        identifier_type: str,
        identifier_value: str,
        customer_id: str,
        ttl: int = 3600  # 1 hour
    ):
        """Cache customer ID resolution."""
        key = f"identity:{channel_id}:{identifier_type}:{identifier_value}"
        self.redis.setex(key, ttl, customer_id)

    def invalidate_resolution(
        self,
        channel_id: str,
        identifier_type: str,
        identifier_value: str
    ):
        """Invalidate cached resolution."""
        key = f"identity:{channel_id}:{identifier_type}:{identifier_value}"
        self.redis.delete(key)
```

## Monitoring and Auditing

### Identity Resolution Audit Trail

```sql
CREATE TABLE customer_identity_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES customers(id),
    channel_id UUID REFERENCES channels(id),
    identifier_type VARCHAR(50),
    identifier_value TEXT,
    action VARCHAR(50), -- 'link', 'unlink', 'update', 'resolve', 'merge'
    old_value TEXT, -- For updates
    resolver_id UUID, -- Who/what resolved the identity
    resolution_method VARCHAR(100), -- 'exact_match', 'fuzzy_match', 'manual'
    confidence_score DECIMAL(3,2),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for audit queries
CREATE INDEX idx_customer_identity_audit_customer
ON customer_identity_audit(customer_id);
CREATE INDEX idx_customer_identity_audit_created_at
ON customer_identity_audit(created_at DESC);
```

This comprehensive approach to customer identity resolution ensures that customers are properly identified across all channels while maintaining data integrity and providing auditability.