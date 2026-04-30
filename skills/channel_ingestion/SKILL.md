---
name: channel_ingestion
description: Implements FastAPI endpoints and webhook handlers for Gmail API, Twilio WhatsApp, and the Web Support Form. Handles message normalization and initial ingestion into the system. Use when Claude needs to create or modify webhook endpoints for multi-channel message ingestion, normalize messages from different sources, or integrate with Gmail, Twilio WhatsApp, or web forms.
---

# Channel Ingestion Skill

This skill provides guidance for implementing multi-channel message ingestion with FastAPI endpoints and webhook handlers for Gmail API, Twilio WhatsApp, and Web Support Form integration.

## Overview

The channel ingestion system handles incoming messages from multiple sources:
- Gmail API webhooks for email messages
- Twilio webhooks for WhatsApp messages
- Web Support Form submissions for customer inquiries

All messages are normalized to a common format before being ingested into the system.

## Key Components

### 1. FastAPI Endpoints Structure

When creating webhook endpoints, follow this pattern:

```python
from fastapi import FastAPI, Request, HTTPException
from typing import Dict, Any
import json

app = FastAPI()

@app.post("/webhook/gmail")
async def gmail_webhook(request: Request):
    # Handle Gmail API webhook
    pass

@app.post("/webhook/twilio-whatsapp")
async def twilio_whatsapp_webhook(request: Request):
    # Handle Twilio WhatsApp webhook
    pass

@app.post("/webhook/web-support-form")
async def web_support_form_webhook(request: Request):
    # Handle web form submission
    pass
```

### 2. Message Normalization

All incoming messages should be normalized to a common format:

```python
from pydantic import BaseModel
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any

class ChannelType(str, Enum):
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    WEB_FORM = "web_form"

class NormalizedMessage(BaseModel):
    id: str
    channel: ChannelType
    sender_id: str
    sender_name: Optional[str] = None
    content: str
    timestamp: datetime
    metadata: Dict[str, Any] = {}
    attachments: Optional[list] = []
```

### 3. Gmail API Integration

Gmail webhook endpoints should handle:
- Push notifications from Gmail API
- Message parsing from Gmail format
- Authentication verification
- Error handling for invalid payloads

### 4. Twilio WhatsApp Integration

Twilio webhook endpoints should handle:
- Message validation using Twilio signature verification
- WhatsApp message format parsing
- Media attachment handling
- Status updates (delivered, read, etc.)

### 5. Web Support Form Integration

Web form endpoints should handle:
- Form validation
- Spam protection
- Customer identification
- Priority assignment

## Implementation Guidelines

### Security Best Practices

1. **Authentication & Verification**:
   - Validate webhook signatures for Twilio
   - Verify Gmail API authentication
   - Implement rate limiting
   - Add spam protection for web forms

2. **Input Validation**:
   - Sanitize all incoming message content
   - Validate message formats
   - Check for malicious content

3. **Rate Limiting**:
   - Implement per-source rate limiting
   - Add exponential backoff for retries

### Error Handling

- Log all webhook attempts with payload details
- Implement dead letter queues for failed messages
- Retry mechanisms with exponential backoff
- Alerting for persistent failures

### Message Processing Pipeline

1. Receive webhook request
2. Validate authentication/signature
3. Parse raw message format
4. Normalize to common format
5. Store in message queue/database
6. Trigger downstream processing

## Reference Files

For detailed implementation patterns, see:
- [GMAIL_INTEGRATION.md](references/GMAIL_INTEGRATION.md) - Gmail API webhook specifics
- [TWILIO_WHATSAPP.md](references/TWILIO_WHATSAPP.md) - Twilio WhatsApp integration details
- [WEB_FORM_HANDLING.md](references/WEB_FORM_HANDLING.md) - Web form processing patterns
- [NORMALIZATION_SCHEMA.md](references/NORMALIZATION_SCHEMA.md) - Message normalization schema
- [SECURITY_PATTERNS.md](references/SECURITY_PATTERNS.md) - Security implementation patterns