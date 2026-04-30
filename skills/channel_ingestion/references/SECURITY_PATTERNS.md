# Security Implementation Patterns Reference

## Authentication and Authorization

### Twilio Webhook Verification

Always verify that incoming Twilio webhooks are legitimate:

```python
from twilio.request_validator import RequestValidator
from fastapi import Request, HTTPException

async def verify_twilio_signature(
    request: Request,
    webhook_url: str,
    auth_token: str
):
    validator = RequestValidator(auth_token)
    signature = request.headers.get('X-Twilio-Signature', '')

    # Get the form data from the request
    form_data = await request.form()

    # Validate the signature
    if not validator.validate(webhook_url, dict(form_data), signature):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")
```

### Gmail API Verification

Verify Gmail webhook authenticity by checking the email address and using proper OAuth tokens:

```python
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

def verify_gmail_webhook(email_address: str, allowed_emails: list):
    """Verify that the webhook is for an allowed email address"""
    if email_address not in allowed_emails:
        raise HTTPException(status_code=403, detail="Unauthorized Gmail webhook")
```

## Input Validation and Sanitization

### Content Sanitization

Sanitize all incoming message content to prevent XSS and other injection attacks:

```python
import html
import re

def sanitize_content(content: str) -> str:
    """Sanitize message content to prevent XSS"""
    # HTML encode special characters
    content = html.escape(content)

    # Remove potentially dangerous patterns
    content = re.sub(r'javascript:', '', content, flags=re.IGNORECASE)
    content = re.sub(r'on\w+\s*=', '', content, flags=re.IGNORECASE)

    return content
```

### Rate Limiting

Implement rate limiting per source to prevent abuse:

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from fastapi import FastAPI, Request

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(429, _rate_limit_exceeded_handler)

@app.post("/webhook/twilio-whatsapp")
@limiter.limit("100/minute")  # 100 requests per minute per IP
async def twilio_whatsapp_webhook(request: Request):
    # Handle request
    pass
```

## Secure Configuration

### Environment Variables

Store sensitive information in environment variables:

```python
import os
from dotenv import load_dotenv

load_dotenv()

TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
GMAIL_CLIENT_ID = os.getenv("GMAIL_CLIENT_ID")
GMAIL_CLIENT_SECRET = os.getenv("GMAIL_CLIENT_SECRET")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
```

## Error Handling

### Safe Error Messages

Return generic error messages to clients while logging detailed errors:

```python
import logging

logger = logging.getLogger(__name__)

@app.post("/webhook/gmail")
async def gmail_webhook(request: Request):
    try:
        # Process webhook
        pass
    except Exception as e:
        # Log detailed error for debugging
        logger.error(f"Gmail webhook error: {str(e)}", exc_info=True)

        # Return generic error to client
        raise HTTPException(status_code=500, detail="Internal server error")
```

## Data Protection

### Encryption at Rest

Encrypt sensitive data when storing:

```python
from cryptography.fernet import Fernet

def encrypt_sensitive_data(data: str, key: bytes) -> str:
    """Encrypt sensitive data before storage"""
    fernet = Fernet(key)
    encrypted_data = fernet.encrypt(data.encode())
    return encrypted_data.decode()

def decrypt_sensitive_data(encrypted_data: str, key: bytes) -> str:
    """Decrypt sensitive data when retrieving"""
    fernet = Fernet(key)
    decrypted_data = fernet.decrypt(encrypted_data.encode())
    return decrypted_data.decode()
```

### Secure Logging

Avoid logging sensitive information:

```python
import logging

logger = logging.getLogger(__name__)

def log_webhook_received(channel: str, sender_id: str, message_id: str):
    """Log webhook receipt without sensitive content"""
    logger.info(f"Webhook received - Channel: {channel}, "
                f"Sender ID: {sender_id}, Message ID: {message_id}")
```

## Network Security

### HTTPS Enforcement

Ensure all webhook endpoints use HTTPS:

```python
from fastapi import Request

def require_https(request: Request):
    """Ensure request was made over HTTPS"""
    if request.url.scheme != "https":
        raise HTTPException(status_code=400, detail="HTTPS required")
```

### CORS Configuration

Properly configure CORS for web form endpoints:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Restrict to your domains
    allow_credentials=True,
    allow_methods=["POST"],
    allow_headers=["*"],
)
```

## Monitoring and Alerting

### Security Event Logging

Log security-relevant events:

```python
def log_security_event(event_type: str, details: dict):
    """Log security events for monitoring"""
    logger.warning(f"Security event: {event_type}", extra={"details": details})

# Example usage
log_security_event("INVALID_WEBHOOK_SIGNATURE", {
    "source_ip": request.client.host,
    "channel": "twilio",
    "timestamp": datetime.utcnow().isoformat()
})
```

## Best Practices Summary

1. Always validate webhook signatures/authenticity
2. Sanitize all input data
3. Implement rate limiting
4. Use environment variables for secrets
5. Log security events without exposing sensitive data
6. Encrypt sensitive data at rest
7. Enforce HTTPS
8. Configure proper CORS settings
9. Return generic error messages to clients
10. Regularly rotate secrets and tokens