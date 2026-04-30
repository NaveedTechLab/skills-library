# Security Implementation Guidelines Reference

## Authentication and Authorization

### Customer Identity Verification

Securely verify and manage customer identities:

```python
import jwt
from typing import Optional, Dict, Any
import hashlib
import secrets

class CustomerIdentityManager:
    def __init__(self, secret_key: str):
        self.secret_key = secret_key

    def generate_auth_token(self, customer_id: str, permissions: list) -> str:
        """Generate a secure authentication token for a customer."""
        payload = {
            "customer_id": customer_id,
            "permissions": permissions,
            "exp": datetime.utcnow() + timedelta(hours=24),
            "iat": datetime.utcnow(),
            "jti": secrets.token_urlsafe(16)  # JWT ID for revocation
        }

        return jwt.encode(payload, self.secret_key, algorithm="HS256")

    def verify_auth_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify an authentication token and return customer info."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])

            # Check if token is expired (jwt library handles this)
            # Additional checks can be added here

            return {
                "customer_id": payload["customer_id"],
                "permissions": payload["permissions"],
                "valid": True
            }
        except jwt.ExpiredSignatureError:
            return {"valid": False, "reason": "Token expired"}
        except jwt.InvalidTokenError:
            return {"valid": False, "reason": "Invalid token"}

    def hash_customer_pii(self, pii_data: str) -> str:
        """Hash personally identifiable information for storage."""
        # Use SHA-256 with salt for PII
        salt = secrets.token_bytes(32)
        hashed = hashlib.pbkdf2_hmac('sha256', pii_data.encode('utf-8'), salt, 100000)
        return f"{salt.hex()}:{hashed.hex()}"
```

### Role-Based Access Control (RBAC)

Implement fine-grained permissions:

```python
from enum import Enum
from typing import Set

class Permission(Enum):
    READ_PROFILE = "read:profile"
    UPDATE_PROFILE = "update:profile"
    CREATE_TICKET = "create:ticket"
    VIEW_TICKETS = "view:tickets"
    UPDATE_TICKETS = "update:tickets"
    ACCESS_SENSITIVE_DATA = "access:sensitive_data"
    ADMIN_ACTIONS = "admin:actions"

class RBACManager:
    def __init__(self):
        self.role_permissions = {
            "customer": {
                Permission.READ_PROFILE,
                Permission.UPDATE_PROFILE,
                Permission.CREATE_TICKET,
                Permission.VIEW_TICKETS
            },
            "premium_customer": {
                Permission.READ_PROFILE,
                Permission.UPDATE_PROFILE,
                Permission.CREATE_TICKET,
                Permission.VIEW_TICKETS,
                Permission.ACCESS_SENSITIVE_DATA
            },
            "support_agent": {
                Permission.VIEW_TICKETS,
                Permission.UPDATE_TICKETS,
                Permission.ACCESS_SENSITIVE_DATA
            },
            "admin": set(Permission)  # All permissions
        }

    def has_permission(self, customer_id: str, role: str, permission: Permission) -> bool:
        """Check if a customer with a role has a specific permission."""
        if role not in self.role_permissions:
            return False

        return permission in self.role_permissions[role]

    def get_customer_permissions(self, customer_id: str, role: str) -> Set[Permission]:
        """Get all permissions for a customer."""
        return self.role_permissions.get(role, set())
```

## Input Validation and Sanitization

### Request Validation

Validate all inputs to prevent injection attacks:

```python
import re
from typing import Any, Dict, List
from pydantic import BaseModel, Field, validator
from typing import Optional

class ToolCallParams(BaseModel):
    """Base model for validating tool call parameters."""

    @validator('*', pre=True)
    def validate_strings(cls, v):
        if isinstance(v, str):
            # Remove potentially dangerous characters
            v = v.strip()
            # Prevent common injection patterns
            dangerous_patterns = [
                r'<script', r'javascript:', r'on\w+\s*=',
                r'eval\s*\(', r'expression\s*\('
            ]

            for pattern in dangerous_patterns:
                if re.search(pattern, v, re.IGNORECASE):
                    raise ValueError(f"Potentially dangerous content detected: {pattern}")

            # Limit string length
            if len(v) > 1000:
                raise ValueError("String too long")

        return v

class SearchKnowledgeBaseParams(ToolCallParams):
    query: str = Field(..., min_length=3, max_length=500)
    category: Optional[str] = Field(None, max_length=100)
    max_results: Optional[int] = Field(5, ge=1, le=50)

class CreateTicketParams(ToolCallParams):
    customer_id: str = Field(..., min_length=1, max_length=100)
    subject: str = Field(..., min_length=5, max_length=200)
    description: str = Field(..., min_length=10, max_length=2000)
    priority: str = Field("medium", regex=r"^(low|medium|high|urgent)$")
    category: Optional[str] = Field(None, max_length=50)

def validate_tool_parameters(tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Validate parameters for a specific tool."""
    validators = {
        "search_knowledge_base": SearchKnowledgeBaseParams,
        "create_ticket": CreateTicketParams,
    }

    validator_class = validators.get(tool_name)
    if not validator_class:
        raise ValueError(f"Unknown tool: {tool_name}")

    # Validate and return cleaned parameters
    validated = validator_class(**params)
    return validated.dict()
```

### Content Sanitization

Sanitize content before processing or storage:

```python
import html
import bleach
from typing import Union

class ContentSanitizer:
    def __init__(self):
        # Allowed tags and attributes for safe HTML
        self.allowed_tags = [
            'p', 'br', 'strong', 'em', 'u', 'ol', 'ul', 'li',
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote'
        ]
        self.allowed_attributes = {
            '*': ['style'],  # Allow style attribute on all tags
        }

    def sanitize_text(self, text: str) -> str:
        """Sanitize plain text content."""
        if not isinstance(text, str):
            return str(text)

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
        ]

        for pattern in dangerous_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)

        return text

    def sanitize_html(self, html_content: str) -> str:
        """Sanitize HTML content."""
        # Use bleach to clean HTML
        clean_html = bleach.clean(
            html_content,
            tags=self.allowed_tags,
            attributes=self.allowed_attributes,
            strip=True
        )

        # Additional checks
        if len(clean_html) > 10000:  # Limit content size
            clean_html = clean_html[:10000]

        return clean_html

    def sanitize_customer_input(self, user_input: str) -> str:
        """Sanitize customer input for conversation."""
        # First sanitize as text
        sanitized = self.sanitize_text(user_input)

        # Then as HTML (in case it contains HTML)
        sanitized = self.sanitize_html(sanitized)

        return sanitized
```

## Data Protection

### Encryption at Rest

Encrypt sensitive data when storing:

```python
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os

class DataEncryptionManager:
    def __init__(self, encryption_key: bytes = None):
        if encryption_key is None:
            # Generate a key - in production, store this securely
            self.key = Fernet.generate_key()
        else:
            self.key = encryption_key

        self.cipher_suite = Fernet(self.key)

    def encrypt_data(self, data: Union[str, bytes]) -> str:
        """Encrypt data and return as base64 string."""
        if isinstance(data, str):
            data = data.encode('utf-8')

        encrypted_data = self.cipher_suite.encrypt(data)
        return base64.b64encode(encrypted_data).decode('utf-8')

    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt data from base64 string."""
        encrypted_bytes = base64.b64decode(encrypted_data.encode('utf-8'))
        decrypted_data = self.cipher_suite.decrypt(encrypted_bytes)
        return decrypted_data.decode('utf-8')

    def encrypt_customer_field(self, field_value: str, customer_id: str) -> str:
        """Encrypt specific customer fields."""
        # Add customer ID to the data to make it unique
        data_to_encrypt = f"{customer_id}:{field_value}"
        return self.encrypt_data(data_to_encrypt)

    def decrypt_customer_field(self, encrypted_field: str, customer_id: str) -> str:
        """Decrypt specific customer fields."""
        decrypted = self.decrypt_data(encrypted_field)
        # Verify it's for the correct customer
        if not decrypted.startswith(f"{customer_id}:"):
            raise ValueError("Decryption failed: customer ID mismatch")

        return decrypted[len(customer_id)+1:]  # Remove customer_id prefix
```

### Secure Logging

Log security events without exposing sensitive data:

```python
import logging
import hashlib
from typing import Dict, Any

class SecureLogger:
    def __init__(self, logger_name: str = "secure_agent_logger"):
        self.logger = logging.getLogger(logger_name)
        self.audit_logger = logging.getLogger(f"{logger_name}_audit")

    def log_customer_action(self, customer_id: str, action: str, details: Dict[str, Any] = None):
        """Log customer actions securely."""
        # Hash customer ID for logs
        customer_hash = hashlib.sha256(customer_id.encode()).hexdigest()[:16]

        # Redact sensitive information
        safe_details = self._redact_sensitive_data(details or {})

        self.audit_logger.info(
            f"Customer action: {action}",
            extra={
                "customer_hash": customer_hash,
                "action": action,
                "details": safe_details
            }
        )

    def log_security_event(self, event_type: str, customer_id: str = None,
                          ip_address: str = None, details: Dict[str, Any] = None):
        """Log security events."""
        log_data = {
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if customer_id:
            log_data["customer_hash"] = hashlib.sha256(customer_id.encode()).hexdigest()[:16]

        if ip_address:
            # Hash IP for privacy
            log_data["ip_hash"] = hashlib.sha256(ip_address.encode()).hexdigest()[:16]

        if details:
            log_data["details"] = self._redact_sensitive_data(details)

        self.logger.warning(f"Security event: {event_type}", extra=log_data)

    def _redact_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Redact sensitive information from log data."""
        sensitive_fields = {
            'password', 'token', 'auth', 'key', 'secret',
            'credit_card', 'ssn', 'phone', 'email'
        }

        redacted_data = {}
        for key, value in data.items():
            if key.lower() in sensitive_fields:
                redacted_data[key] = "[REDACTED]"
            elif isinstance(value, dict):
                redacted_data[key] = self._redact_sensitive_data(value)
            elif isinstance(value, list):
                redacted_data[key] = [
                    self._redact_sensitive_data(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                redacted_data[key] = value

        return redacted_data
```

## API Security

### Rate Limiting

Implement rate limiting to prevent abuse:

```python
import time
from collections import defaultdict, deque
from typing import Dict

class RateLimiter:
    def __init__(self):
        self.customer_limits = defaultdict(lambda: deque(maxlen=100))  # 100 requests max
        self.global_limits = deque(maxlen=1000)  # 1000 requests globally
        self.ip_limits = defaultdict(lambda: deque(maxlen=50))  # 50 requests per IP

    def is_allowed(self, customer_id: str, ip_address: str = None,
                   max_per_minute: int = 10, global_max: int = 100) -> bool:
        """Check if a request is allowed based on rate limits."""
        now = time.time()

        # Clean old entries (older than 1 minute)
        self._clean_old_entries(now)

        # Check customer-specific limit
        customer_requests = len(self.customer_limits[customer_id])
        if customer_requests >= max_per_minute:
            return False

        # Check global limit
        if len(self.global_limits) >= global_max:
            return False

        # Check IP-specific limit if IP is provided
        if ip_address:
            ip_requests = len(self.ip_limits[ip_address])
            if ip_requests >= max_per_minute:
                return False

        # Record the request
        self.customer_limits[customer_id].append(now)
        self.global_limits.append(now)
        if ip_address:
            self.ip_limits[ip_address].append(now)

        return True

    def _clean_old_entries(self, now: float):
        """Remove entries older than 1 minute."""
        cutoff = now - 60  # 1 minute ago

        # Clean customer limits
        for customer_id in list(self.customer_limits.keys()):
            while (self.customer_limits[customer_id] and
                   self.customer_limits[customer_id][0] < cutoff):
                self.customer_limits[customer_id].popleft()

        # Clean global limits
        while self.global_limits and self.global_limits[0] < cutoff:
            self.global_limits.popleft()

        # Clean IP limits
        for ip in list(self.ip_limits.keys()):
            while (self.ip_limits[ip] and self.ip_limits[ip][0] < cutoff):
                self.ip_limits[ip].popleft()
```

### Secure Tool Execution

Execute tools securely with proper isolation:

```python
import subprocess
import tempfile
import os
from typing import Dict, Any, Optional

class SecureToolExecutor:
    def __init__(self, allowed_tools: set = None):
        self.allowed_tools = allowed_tools or {
            'search_knowledge_base',
            'create_ticket',
            'get_customer_info',
            'send_notification'
        }
        self.timeout = 30  # 30 seconds timeout

    def execute_tool_securely(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool securely with validation and timeout."""
        # Validate tool name
        if tool_name not in self.allowed_tools:
            raise ValueError(f"Tool not allowed: {tool_name}")

        # Validate parameters
        try:
            validated_params = validate_tool_parameters(tool_name, params)
        except Exception as e:
            raise ValueError(f"Invalid parameters: {str(e)}")

        # Execute the tool with timeout and error handling
        try:
            # In a real implementation, you would call the actual tool
            # Here's a simplified example
            if tool_name == "search_knowledge_base":
                result = self._execute_search(validated_params)
            elif tool_name == "create_ticket":
                result = self._execute_create_ticket(validated_params)
            else:
                # Generic execution for other tools
                result = self._execute_generic_tool(tool_name, validated_params)

            return {
                "status": "success",
                "result": result
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "tool_name": tool_name
            }

    def _execute_search(self, params: Dict[str, Any]) -> Any:
        """Execute search tool with security checks."""
        # Sanitize search query
        sanitizer = ContentSanitizer()
        params['query'] = sanitizer.sanitize_text(params['query'])

        # Perform the search (implementation depends on your search system)
        # This is a placeholder
        return {"results": [], "count": 0}

    def _execute_create_ticket(self, params: Dict[str, Any]) -> Any:
        """Execute ticket creation with security checks."""
        # Verify customer permissions
        # Sanitize inputs
        sanitizer = ContentSanitizer()
        params['subject'] = sanitizer.sanitize_text(params['subject'])
        params['description'] = sanitizer.sanitize_text(params['description'])

        # Create ticket (implementation depends on your ticket system)
        # This is a placeholder
        return {"ticket_id": "TKT-12345", "status": "created"}

    def _execute_generic_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """Execute any allowed tool."""
        # This would typically call a registry of allowed tools
        # Implementation depends on your specific tools
        pass
```

## Security Monitoring

### Anomaly Detection

Monitor for unusual activity patterns:

```python
import statistics
from collections import defaultdict
from datetime import datetime, timedelta

class AnomalyDetector:
    def __init__(self):
        self.customer_activity = defaultdict(list)
        self.threshold_multiplier = 2.0  # Flag if activity is 2x normal

    def record_activity(self, customer_id: str, activity_type: str,
                       timestamp: datetime = None):
        """Record customer activity for anomaly detection."""
        if timestamp is None:
            timestamp = datetime.now()

        activity_record = {
            "timestamp": timestamp,
            "type": activity_type
        }

        self.customer_activity[customer_id].append(activity_record)

        # Keep only last 24 hours of data
        cutoff = timestamp - timedelta(hours=24)
        self.customer_activity[customer_id] = [
            record for record in self.customer_activity[customer_id]
            if record["timestamp"] > cutoff
        ]

    def check_anomalies(self, customer_id: str) -> Dict[str, Any]:
        """Check for anomalous activity patterns."""
        activities = self.customer_activity[customer_id]

        if len(activities) < 10:  # Need sufficient data
            return {"anomalous": False, "reason": "Insufficient data"}

        # Calculate average activity per hour
        now = datetime.now()
        hour_counts = defaultdict(int)

        for activity in activities:
            hour_key = activity["timestamp"].strftime("%Y-%m-%d-%H")
            hour_counts[hour_key] += 1

        hourly_values = list(hour_counts.values())
        avg_hourly = statistics.mean(hourly_values) if hourly_values else 0
        std_dev = statistics.stdev(hourly_values) if len(hourly_values) > 1 else 0

        # Check if current hour is significantly higher than normal
        current_hour = now.strftime("%Y-%m-%d-%H")
        current_count = hour_counts.get(current_hour, 0)

        if avg_hourly > 0 and std_dev > 0:
            z_score = (current_count - avg_hourly) / std_dev if std_dev != 0 else 0

            if z_score > self.threshold_multiplier:
                return {
                    "anomalous": True,
                    "reason": f"Spike in activity: {current_count} vs avg {avg_hourly:.1f}",
                    "z_score": z_score
                }

        return {"anomalous": False, "reason": "Normal activity pattern"}
```

## Best Practices Summary

1. **Always validate inputs** - Never trust user input
2. **Sanitize content** - Clean data before processing or storage
3. **Use proper authentication** - Verify customer identity
4. **Implement rate limiting** - Prevent abuse and DoS attacks
5. **Encrypt sensitive data** - Protect PII and confidential information
6. **Log securely** - Don't expose sensitive data in logs
7. **Monitor for anomalies** - Detect suspicious behavior patterns
8. **Principle of least privilege** - Grant minimal necessary permissions
9. **Regular security audits** - Review and update security measures
10. **Stay updated** - Keep dependencies and security patches current