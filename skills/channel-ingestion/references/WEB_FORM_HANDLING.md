# Web Support Form Integration Reference

## Form Endpoint Setup

Web support form endpoints should accept POST requests with customer inquiry data. The endpoint should validate input and normalize the data to match other channels.

## Expected Payload Format

Standard web support form payloads should contain:
- `customer_email`: Customer's email address
- `customer_name`: Customer's name (optional)
- `subject`: Inquiry subject or topic
- `message`: Main inquiry content
- `priority`: Priority level (low, medium, high, urgent)
- `category`: Inquiry category (technical, billing, general, etc.)
- `timestamp`: Submission timestamp

## Input Validation

Validate web form inputs:
- Email format validation
- Content length limits
- Spam detection
- Required field validation
- Content sanitization to prevent XSS

## Customer Identification

Identify customers from web forms:
- Match email addresses to existing customers
- Create new customer records if needed
- Track customer history across channels

## Priority Assignment

Automatically assign priority based on:
- Keywords in subject/content
- Customer tier/SLA
- Time of day/urgency indicators
- Historical interaction patterns

## Spam Protection

Implement anti-spam measures:
- CAPTCHA or similar verification
- Rate limiting by IP address
- Content analysis for spam patterns
- Honeypot fields

## Error Handling

Handle common web form issues:
- Invalid input - return descriptive error messages
- Server errors - log and return generic error
- Rate limit exceeded - implement cool-down periods
- Validation failures - provide specific feedback

## Sample Implementation

```python
from pydantic import BaseModel, EmailStr, validator
from typing import Optional
import re

class WebSupportForm(BaseModel):
    customer_email: EmailStr
    customer_name: Optional[str] = ""
    subject: str
    message: str
    priority: Optional[str] = "medium"
    category: Optional[str] = "general"

    @validator('message')
    def validate_message_length(cls, v):
        if len(v) > 10000:  # 10KB limit
            raise ValueError('Message too long')
        return v

    @validator('subject')
    def validate_subject_length(cls, v):
        if len(v) > 200:  # Reasonable subject limit
            raise ValueError('Subject too long')
        return v

def detect_priority_from_content(content: str, subject: str) -> str:
    """Detect priority based on content keywords"""
    high_priority_keywords = [
        'urgent', 'asap', 'immediately', 'crash', 'down', 'error',
        'critical', 'emergency', 'problem', 'broken', 'stopped'
    ]

    combined_text = (subject + " " + content).lower()

    for keyword in high_priority_keywords:
        if keyword in combined_text:
            return 'high'

    return 'medium'  # default priority

def sanitize_input(text: str) -> str:
    """Sanitize input to prevent XSS"""
    # Remove potentially dangerous HTML tags
    sanitized = re.sub(r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>', '', text, flags=re.IGNORECASE)
    sanitized = re.sub(r'javascript:', '', sanitized, flags=re.IGNORECASE)
    return sanitized
```