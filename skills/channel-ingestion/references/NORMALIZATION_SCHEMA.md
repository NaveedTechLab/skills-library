# Message Normalization Schema Reference

## Purpose

The normalization schema ensures all messages from different channels (Gmail, WhatsApp, Web Form) follow a consistent format for downstream processing.

## Base Message Schema

```python
from pydantic import BaseModel
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List

class ChannelType(str, Enum):
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    WEB_FORM = "web_form"

class Attachment(BaseModel):
    url: str
    type: str  # MIME type
    filename: str
    size: Optional[int] = None

class NormalizedMessage(BaseModel):
    # Unique identifier for the message
    id: str

    # Channel where the message originated
    channel: ChannelType

    # Sender identification
    sender_id: str  # Unique identifier (email, phone number, etc.)
    sender_name: Optional[str] = None  # Display name if available

    # Message content
    content: str  # The main message text

    # Timestamps
    timestamp: datetime  # When the message was sent/received

    # Additional metadata specific to the channel
    metadata: Dict[str, Any] = {}

    # Attachments if any
    attachments: Optional[List[Attachment]] = []

    # Optional fields for extended functionality
    subject: Optional[str] = None  # For email messages
    priority: Optional[str] = "medium"  # low, medium, high, urgent
    category: Optional[str] = "general"  # technical, billing, general, etc.
```

## Channel-Specific Metadata

Each channel populates the `metadata` field with additional information:

### Email (Gmail) Metadata
```python
{
    "original_message_id": "...",  # Original Gmail message ID
    "thread_id": "...",           # Gmail thread ID
    "cc": [...],                  # CC recipients
    "bcc": [...],                 # BCC recipients
    "labels": [...]               # Gmail labels applied to message
}
```

### WhatsApp (Twilio) Metadata
```python
{
    "twilio_message_sid": "...",  # Twilio's unique message identifier
    "twilio_account_sid": "...",  # Twilio account identifier
    "status": "...",              # Message status (sent, delivered, read, etc.)
    "num_segments": 1             # Number of message segments
}
```

### Web Form Metadata
```python
{
    "form_source": "...",         # Which form interface submitted the message
    "ip_address": "...",          # IP address of submitter (if available)
    "user_agent": "...",          # Browser/user agent string
    "spam_score": 0.0             # Calculated spam likelihood score
}
```

## Normalization Process

### 1. Channel Detection
First, identify the source channel based on the incoming payload structure and headers.

### 2. Content Extraction
Extract the relevant content from the specific channel format:
- Email: Extract body from multipart MIME structure
- WhatsApp: Extract message text from Twilio format
- Web Form: Extract message from form fields

### 3. Identity Resolution
Convert channel-specific identifiers to a consistent format:
- Email: Use email address as `sender_id`
- WhatsApp: Use phone number in international format as `sender_id`
- Web Form: Use provided email as `sender_id`

### 4. Timestamp Standardization
Convert channel-specific timestamps to ISO 8601 datetime format.

### 5. Attachment Processing
Convert channel-specific attachment formats to the common `Attachment` model.

### 6. Metadata Preservation
Store channel-specific information in the `metadata` dictionary for later reference.

## Validation Rules

All normalized messages must pass these validations:
- `id` must be unique within the system
- `channel` must be one of the allowed enum values
- `sender_id` must be non-empty
- `content` must be non-empty (after sanitization)
- `timestamp` must be a valid datetime
- `attachments` URLs must be properly formatted

## Error Handling

When normalization fails:
- Log the original payload for debugging
- Attempt to extract minimal viable message
- Add error information to metadata
- Route to manual review queue if necessary