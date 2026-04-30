# Security Implementation Patterns Reference

## Database Security

### Connection Security

#### SSL/TLS Configuration
```python
from sqlalchemy import create_engine
import ssl

# Database connection with SSL enforcement
DATABASE_URL = "postgresql://user:password@hostname:5432/dbname?sslmode=require"

engine = create_engine(
    DATABASE_URL,
    connect_args={
        "sslmode": "require",
        "sslcert": "/path/to/client-cert.pem",
        "sslkey": "/path/to/client-key.pem",
        "sslrootcert": "/path/to/ca-cert.pem"
    }
)

# Alternative: Using environment variables for sensitive data
import os
from urllib.parse import quote_plus

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")

encoded_password = quote_plus(DB_PASSWORD)
DATABASE_URL_SECURE = f"postgresql://{DB_USER}:{encoded_password}@{DB_HOST}:5432/{DB_NAME}?sslmode=require"
```

#### Connection Pool Security
```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool
import os

def create_secure_engine():
    """Create a database engine with security best practices."""
    return create_engine(
        os.getenv("DATABASE_URL"),
        poolclass=QueuePool,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,  # Verify connections before use
        pool_recycle=3600,   # Recycle connections after 1 hour
        connect_args={
            "sslmode": "require",  # Require SSL
        }
    )
```

### Authentication and Authorization

#### Row-Level Security (RLS)
```sql
-- Enable RLS on sensitive tables
ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE tickets ENABLE ROW LEVEL SECURITY;

-- Create policies for customer table
CREATE POLICY customer_isolation_policy ON customers
    FOR ALL TO crm_app_user
    USING (id = current_setting('app.current_customer_id')::uuid);

-- Create policies for messages table
CREATE POLICY message_access_policy ON messages
    FOR ALL TO crm_app_user
    USING (customer_id = current_setting('app.current_customer_id')::uuid);

-- Create policies for tickets table
CREATE POLICY ticket_access_policy ON tickets
    FOR ALL TO crm_app_user
    USING (customer_id = current_setting('app.current_customer_id')::uuid);

-- Create a function to set the current customer context
CREATE OR REPLACE FUNCTION set_customer_context(customer_id UUID)
RETURNS void AS $$
BEGIN
    PERFORM set_config('app.current_customer_id', customer_id::text, true);
END;
$$ LANGUAGE plpgsql;
```

#### Application-Level Authentication
```python
from functools import wraps
from typing import Dict, Any
import jwt
import secrets
from datetime import datetime, timedelta

class DatabaseSecurityManager:
    def __init__(self, secret_key: str):
        self.secret_key = secret_key

    def generate_auth_token(self, user_id: str, permissions: list, customer_id: str = None) -> str:
        """Generate a secure authentication token."""
        payload = {
            "user_id": user_id,
            "permissions": permissions,
            "customer_id": customer_id,
            "exp": datetime.utcnow() + timedelta(hours=24),
            "iat": datetime.utcnow(),
            "jti": secrets.token_urlsafe(16)  # JWT ID for revocation
        }

        return jwt.encode(payload, self.secret_key, algorithm="HS256")

    def verify_auth_token(self, token: str) -> Dict[str, Any]:
        """Verify authentication token and return claims."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])

            # Check if token is expired (handled by jwt library)
            # Additional checks can be added here

            return {
                "user_id": payload["user_id"],
                "permissions": payload["permissions"],
                "customer_id": payload.get("customer_id"),
                "valid": True
            }
        except jwt.ExpiredSignatureError:
            return {"valid": False, "reason": "Token expired"}
        except jwt.InvalidTokenError:
            return {"valid": False, "reason": "Invalid token"}

    def set_row_level_security_context(self, db_connection, customer_id: str):
        """Set the database context for row-level security."""
        db_connection.execute(
            "SELECT set_customer_context(%s)",
            (customer_id,)
        )
```

## Input Validation and Sanitization

### Parameterized Queries
```python
from sqlalchemy import text
from typing import Optional
import re

class SecureQueryBuilder:
    @staticmethod
    def build_customer_query(customer_id: str) -> tuple:
        """Build a secure query using parameterization."""
        # Validate UUID format
        if not re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', customer_id):
            raise ValueError("Invalid UUID format")

        query = text("SELECT * FROM customers WHERE id = :customer_id")
        return query, {"customer_id": customer_id}

    @staticmethod
    def build_search_query(search_term: str, limit: int = 10) -> tuple:
        """Build a secure search query with validation."""
        # Validate and sanitize search term
        if not search_term or len(search_term) > 100:
            raise ValueError("Invalid search term length")

        # Escape special characters for LIKE queries
        escaped_term = search_term.replace('%', '\\%').replace('_', '\\_')

        query = text("""
            SELECT * FROM customers
            WHERE name ILIKE :search_term
            OR email ILIKE :search_term
            LIMIT :limit
        """)

        return query, {
            "search_term": f"%{escaped_term}%",
            "limit": min(limit, 100)  # Cap limit to prevent resource exhaustion
        }
```

### Data Sanitization
```python
import html
import bleach
import re
from typing import Dict, Any

class DataSanitizer:
    def __init__(self):
        # Allowed tags and attributes for safe HTML
        self.allowed_tags = [
            'p', 'br', 'strong', 'em', 'u', 'ol', 'ul', 'li',
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote',
            'code', 'pre'
        ]
        self.allowed_attributes = {
            '*': ['style'],  # Allow style attribute on all tags
        }

    def sanitize_customer_input(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize customer input data."""
        sanitized_data = {}

        for key, value in data.items():
            if isinstance(value, str):
                sanitized_data[key] = self._sanitize_string(value)
            elif isinstance(value, dict):
                sanitized_data[key] = self.sanitize_customer_input(value)
            elif isinstance(value, list):
                sanitized_data[key] = [
                    self._sanitize_string(item) if isinstance(item, str)
                    else self.sanitize_customer_input(item) if isinstance(item, dict)
                    else item
                    for item in value
                ]
            else:
                sanitized_data[key] = value

        return sanitized_data

    def _sanitize_string(self, text: str) -> str:
        """Sanitize a single string value."""
        if not isinstance(text, str):
            return text

        # Basic sanitization
        text = text.strip()

        # HTML escape
        text = html.escape(text)

        # Remove potentially dangerous patterns
        dangerous_patterns = [
            r'javascript:',
            r'vbscript:',
            r'expression\s*\(',
            r'eval\s*\(',
            r'on\w+\s*=',
        ]

        for pattern in dangerous_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)

        # Limit length
        if len(text) > 10000:  # Adjust based on your needs
            text = text[:10000]

        return text

    def sanitize_html_content(self, html_content: str) -> str:
        """Sanitize HTML content for rich text fields."""
        # Use bleach to clean HTML
        clean_html = bleach.clean(
            html_content,
            tags=self.allowed_tags,
            attributes=self.allowed_attributes,
            strip=True
        )

        # Additional size check
        if len(clean_html) > 50000:  # 50KB limit
            clean_html = clean_html[:50000]

        return clean_html
```

## Data Encryption

### Field-Level Encryption
```python
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os
from typing import Optional

class FieldEncryption:
    def __init__(self, encryption_key: Optional[bytes] = None):
        if encryption_key is None:
            # In production, get from environment or key management system
            key_env = os.getenv("FIELD_ENCRYPTION_KEY")
            if key_env:
                self.key = base64.urlsafe_b64decode(key_env)
            else:
                # Generate a new key (only for development)
                self.key = Fernet.generate_key()
        else:
            self.key = encryption_key

        self.cipher_suite = Fernet(self.key)

    def encrypt_field(self, field_value: str, context: str = "") -> str:
        """
        Encrypt a field value with optional context for key derivation.

        Args:
            field_value: The value to encrypt
            context: Additional context for key derivation (e.g., customer_id)

        Returns:
            Base64 encoded encrypted value
        """
        if context:
            # Derive key from master key + context
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=context.encode(),
                iterations=100000,
            )
            derived_key = base64.urlsafe_b64encode(kdf.derive(self.key))
            cipher = Fernet(derived_key)
        else:
            cipher = self.cipher_suite

        encrypted_data = cipher.encrypt(field_value.encode('utf-8'))
        return base64.b64encode(encrypted_data).decode('utf-8')

    def decrypt_field(self, encrypted_value: str, context: str = "") -> str:
        """
        Decrypt a field value.

        Args:
            encrypted_value: Base64 encoded encrypted value
            context: Context used during encryption

        Returns:
            Decrypted string value
        """
        encrypted_bytes = base64.b64decode(encrypted_value.encode('utf-8'))

        if context:
            # Derive key from master key + context
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=context.encode(),
                iterations=100000,
            )
            derived_key = base64.urlsafe_b64encode(kdf.derive(self.key))
            cipher = Fernet(derived_key)
        else:
            cipher = self.cipher_suite

        decrypted_data = cipher.decrypt(encrypted_bytes)
        return decrypted_data.decode('utf-8')

# Usage example
encryption = FieldEncryption()

# Encrypt sensitive fields
encrypted_phone = encryption.encrypt_field("+1-555-123-4567", context="customer_123")
encrypted_ssn = encryption.encrypt_field("123-45-6789", context="customer_123")

# Decrypt when needed
decrypted_phone = encryption.decrypt_field(encrypted_phone, context="customer_123")
```

### Transparent Database Encryption
```sql
-- Using PostgreSQL's built-in PGCrypto extension
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Example table with encrypted fields
CREATE TABLE customers_secure (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255), -- Not encrypted - needed for lookups
    phone_encrypted BYTEA, -- Encrypted phone number
    ssn_encrypted BYTEA, -- Encrypted SSN
    credit_card_encrypted BYTEA, -- Encrypted credit card
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Function to encrypt data
CREATE OR REPLACE FUNCTION encrypt_field(input_text TEXT, encryption_key TEXT)
RETURNS BYTEA AS $$
BEGIN
    RETURN pgp_sym_encrypt(input_text, encryption_key);
END;
$$ LANGUAGE plpgsql;

-- Function to decrypt data
CREATE OR REPLACE FUNCTION decrypt_field(encrypted_data BYTEA, encryption_key TEXT)
RETURNS TEXT AS $$
BEGIN
    RETURN pgp_sym_decrypt(encrypted_data, encryption_key);
END;
$$ LANGUAGE plpgsql;

-- Example usage in application
INSERT INTO customers_secure (
    email,
    phone_encrypted,
    ssn_encrypted
) VALUES (
    'user@example.com',
    encrypt_field('+1-555-123-4567', current_setting('app.encryption_key')),
    encrypt_field('123-45-6789', current_setting('app.encryption_key'))
);
```

## Audit Logging

### Database Audit Trail
```sql
-- Audit log table
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    table_name VARCHAR(100) NOT NULL,
    record_id UUID NOT NULL,
    operation VARCHAR(10) NOT NULL, -- 'INSERT', 'UPDATE', 'DELETE'
    user_id VARCHAR(255),
    ip_address INET,
    user_agent TEXT,
    old_values JSONB,
    new_values JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Function to log audit events
CREATE OR REPLACE FUNCTION log_audit_event()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO audit_log (table_name, record_id, operation, user_id, ip_address, user_agent, new_values)
        VALUES (TG_TABLE_NAME, NEW.id, 'INSERT',
                current_setting('app.user_id', true),
                current_setting('app.ip_address', true),
                current_setting('app.user_agent', true),
                to_jsonb(NEW));
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit_log (table_name, record_id, operation, user_id, ip_address, user_agent, old_values, new_values)
        VALUES (TG_TABLE_NAME, NEW.id, 'UPDATE',
                current_setting('app.user_id', true),
                current_setting('app.ip_address', true),
                current_setting('app.user_agent', true),
                to_jsonb(OLD), to_jsonb(NEW));
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO audit_log (table_name, record_id, operation, user_id, ip_address, user_agent, old_values)
        VALUES (TG_TABLE_NAME, OLD.id, 'DELETE',
                current_setting('app.user_id', true),
                current_setting('app.ip_address', true),
                current_setting('app.user_agent', true),
                to_jsonb(OLD));
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Apply audit triggers to sensitive tables
CREATE TRIGGER audit_customers_trigger
    AFTER INSERT OR UPDATE OR DELETE ON customers
    FOR EACH ROW EXECUTE FUNCTION log_audit_event();

CREATE TRIGGER audit_tickets_trigger
    AFTER INSERT OR UPDATE OR DELETE ON tickets
    FOR EACH ROW EXECUTE FUNCTION log_audit_event();
```

### Application-Level Security Logging
```python
import logging
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional

class SecurityLogger:
    def __init__(self, logger_name: str = "security"):
        self.logger = logging.getLogger(logger_name)

    def log_database_access(self,
                           user_id: str,
                           operation: str,
                           table_name: str,
                           record_id: Optional[str] = None,
                           success: bool = True,
                           details: Dict[str, Any] = None):
        """Log database access events."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "database_access",
            "user_id": self._hash_pii(user_id),
            "operation": operation,
            "table": table_name,
            "record_id": self._hash_pii(record_id) if record_id else None,
            "success": success,
            "details": details or {}
        }

        if success:
            self.logger.info("Database access", extra=log_data)
        else:
            self.logger.warning("Database access failed", extra=log_data)

    def log_authentication_event(self,
                                user_id: str,
                                event_type: str,
                                success: bool = True,
                                details: Dict[str, Any] = None):
        """Log authentication events."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "user_id": self._hash_pii(user_id),
            "success": success,
            "details": details or {}
        }

        if success:
            self.logger.info("Authentication event", extra=log_data)
        else:
            self.logger.warning("Authentication failed", extra=log_data)

    def log_privilege_escalation(self,
                                 user_id: str,
                                 attempted_operation: str,
                                 granted: bool = False):
        """Log potential privilege escalation attempts."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "privilege_escalation",
            "user_id": self._hash_pii(user_id),
            "operation": attempted_operation,
            "granted": granted
        }

        if granted:
            self.logger.warning("Privilege escalation granted", extra=log_data)
        else:
            self.logger.info("Privilege escalation denied", extra=log_data)

    def _hash_pii(self, data: str) -> str:
        """Hash PII to protect privacy in logs."""
        if not data:
            return None
        return hashlib.sha256(data.encode()).hexdigest()[:16]  # First 16 chars
```

## Rate Limiting and Abuse Prevention

### Database-Level Rate Limiting
```sql
-- Table to track request rates
CREATE TABLE rate_limit_tracker (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    identifier VARCHAR(255) NOT NULL, -- IP address, user ID, etc.
    resource_type VARCHAR(100) NOT NULL, -- 'api_call', 'db_query', etc.
    count INTEGER DEFAULT 1,
    window_start TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for efficient queries
CREATE INDEX idx_rate_limit_tracker ON rate_limit_tracker(identifier, resource_type, window_start);

-- Function to check rate limits
CREATE OR REPLACE FUNCTION check_rate_limit(
    p_identifier VARCHAR,
    p_resource_type VARCHAR,
    p_max_requests INTEGER,
    p_window_seconds INTEGER
) RETURNS BOOLEAN AS $$
DECLARE
    current_count INTEGER;
    window_start_time TIMESTAMP WITH TIME ZONE;
BEGIN
    window_start_time := NOW() - (p_window_seconds || ' seconds')::INTERVAL;

    -- Clean up old entries
    DELETE FROM rate_limit_tracker
    WHERE window_start < window_start_time;

    -- Get current count
    SELECT COALESCE(SUM(count), 0) INTO current_count
    FROM rate_limit_tracker
    WHERE identifier = p_identifier
      AND resource_type = p_resource_type
      AND window_start >= window_start_time;

    -- Increment counter
    INSERT INTO rate_limit_tracker (identifier, resource_type, count, window_start)
    VALUES (p_identifier, p_resource_type, 1, NOW())
    ON CONFLICT (identifier, resource_type, window_start)
    DO UPDATE SET count = rate_limit_tracker.count + 1;

    -- Check if within limit
    RETURN current_count < p_max_requests;
END;
$$ LANGUAGE plpgsql;
```

### Application-Level Rate Limiting
```python
import time
import threading
from collections import defaultdict, deque
from typing import Dict

class RateLimiter:
    def __init__(self):
        self.limits = defaultdict(lambda: deque(maxlen=1000))
        self.lock = threading.Lock()

    def is_allowed(self,
                   identifier: str,
                   resource_type: str,
                   max_requests: int,
                   window_seconds: int) -> bool:
        """
        Check if a request is allowed based on rate limits.

        Args:
            identifier: The entity making the request (IP, user ID, etc.)
            resource_type: Type of resource being accessed
            max_requests: Maximum requests allowed in the window
            window_seconds: Time window in seconds

        Returns:
            True if request is allowed, False otherwise
        """
        now = time.time()
        window_start = now - window_seconds

        key = f"{identifier}:{resource_type}"

        with self.lock:
            # Clean old entries
            while self.limits[key] and self.limits[key][0] < window_start:
                self.limits[key].popleft()

            # Check if limit exceeded
            if len(self.limits[key]) >= max_requests:
                return False

            # Add current request
            self.limits[key].append(now)
            return True

# Usage in database operations
class SecureDatabaseAccess:
    def __init__(self, db_connection, rate_limiter: RateLimiter):
        self.db = db_connection
        self.rate_limiter = rate_limiter
        self.security_logger = SecurityLogger()

    def execute_query_with_rate_limit(self,
                                     query: str,
                                     params: dict,
                                     user_id: str,
                                     max_queries: int = 100,
                                     window_seconds: int = 3600) -> Any:
        """Execute query with rate limiting."""
        identifier = f"user:{user_id}"

        if not self.rate_limiter.is_allowed(
            identifier,
            "database_query",
            max_queries,
            window_seconds
        ):
            self.security_logger.log_database_access(
                user_id=user_id,
                operation="query",
                table_name="rate_limited",
                success=False,
                details={"query": query[:100]}  # First 100 chars of query
            )
            raise Exception("Rate limit exceeded")

        try:
            result = self.db.execute(query, params)
            self.security_logger.log_database_access(
                user_id=user_id,
                operation="query",
                table_name="unknown",  # Would extract from query in real impl
                success=True
            )
            return result
        except Exception as e:
            self.security_logger.log_database_access(
                user_id=user_id,
                operation="query",
                table_name="unknown",
                success=False,
                details={"error": str(e)}
            )
            raise
```

## Security Monitoring and Alerts

### Security Event Monitoring
```python
from datetime import datetime, timedelta
from typing import List, Dict
import smtplib
from email.mime.text import MIMEText

class SecurityMonitor:
    def __init__(self, db_connection):
        self.db = db_connection
        self.alert_recipients = ["security@company.com"]

    def check_security_anomalies(self) -> List[Dict]:
        """Check for security anomalies in audit logs."""
        anomalies = []

        # Check for unusual access patterns
        unusual_access = self.db.execute("""
            SELECT user_id, COUNT(*) as access_count
            FROM audit_log
            WHERE created_at > NOW() - INTERVAL '1 hour'
            GROUP BY user_id
            HAVING COUNT(*) > 50  -- More than 50 operations in 1 hour
        """).fetchall()

        for record in unusual_access:
            anomalies.append({
                "type": "high_volume_access",
                "user_id": record.user_id,
                "count": record.access_count,
                "timestamp": datetime.utcnow()
            })

        # Check for failed authentication attempts
        failed_auth = self.db.execute("""
            SELECT user_id, COUNT(*) as failure_count
            FROM audit_log
            WHERE operation = 'login_failed'
              AND created_at > NOW() - INTERVAL '15 minutes'
            GROUP BY user_id
            HAVING COUNT(*) > 5  -- More than 5 failures in 15 minutes
        """).fetchall()

        for record in failed_auth:
            anomalies.append({
                "type": "brute_force_attempt",
                "user_id": record.user_id,
                "count": record.failure_count,
                "timestamp": datetime.utcnow()
            })

        # Check for privilege escalation attempts
        escalation_attempts = self.db.execute("""
            SELECT user_id, COUNT(*) as escalation_count
            FROM audit_log
            WHERE table_name = 'privilege_escalation'
              AND created_at > NOW() - INTERVAL '1 hour'
            GROUP BY user_id
            HAVING COUNT(*) > 3
        """).fetchall()

        for record in escalation_attempts:
            anomalies.append({
                "type": "privilege_escalation",
                "user_id": record.user_id,
                "count": record.escalation_count,
                "timestamp": datetime.utcnow()
            })

        return anomalies

    def send_security_alert(self, anomaly: Dict):
        """Send security alert for detected anomaly."""
        subject = f"Security Alert: {anomaly['type']}"
        body = f"""
        Security anomaly detected:

        Type: {anomaly['type']}
        User ID: {anomaly['user_id']}
        Count: {anomaly['count']}
        Timestamp: {anomaly['timestamp']}

        Please investigate immediately.
        """

        # In production, use proper email service
        print(f"ALERT: {subject}\n{body}")
```

This comprehensive security implementation provides multiple layers of protection for the CRM database, including connection security, authentication, data encryption, audit logging, rate limiting, and security monitoring.