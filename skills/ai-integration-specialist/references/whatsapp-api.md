# WhatsApp Business API Integration

## Overview

Comprehensive guide for integrating WhatsApp Business API for remote approval workflows, including message templates, interactive messages, and webhook handling.

## Setup

### Prerequisites

1. WhatsApp Business Account
2. Meta Business Manager access
3. Phone number verification
4. API access token

### Configuration

```python
# .env
WHATSAPP_API_URL=https://graph.facebook.com/v18.0
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
WHATSAPP_ACCESS_TOKEN=your_access_token
WHATSAPP_VERIFY_TOKEN=your_webhook_verify_token
WHATSAPP_BUSINESS_ACCOUNT_ID=your_business_account_id
```

### Client Setup

```python
import os
import httpx
from typing import Dict, Any

class WhatsAppClient:
    def __init__(self):
        self.api_url = os.getenv("WHATSAPP_API_URL")
        self.phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
        self.access_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
        self.base_url = f"{self.api_url}/{self.phone_number_id}"

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    async def send_message(self, to: str, message: Dict[str, Any]) -> Dict:
        """Send WhatsApp message"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/messages",
                headers=self._get_headers(),
                json={
                    "messaging_product": "whatsapp",
                    "to": to,
                    **message
                }
            )
            response.raise_for_status()
            return response.json()
```

## Message Types

### Text Messages

```python
async def send_text_message(client: WhatsAppClient, to: str, text: str):
    """Send simple text message"""
    message = {
        "type": "text",
        "text": {"body": text}
    }
    return await client.send_message(to, message)
```

### Template Messages

```python
async def send_template_message(
    client: WhatsAppClient,
    to: str,
    template_name: str,
    language_code: str = "en",
    components: list = None
):
    """Send template message"""
    message = {
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": language_code},
            "components": components or []
        }
    }
    return await client.send_message(to, message)
```

### Interactive Messages

#### Button Messages

```python
async def send_button_message(
    client: WhatsAppClient,
    to: str,
    body_text: str,
    buttons: list[Dict[str, str]],
    header_text: str = None,
    footer_text: str = None
):
    """Send interactive button message"""
    message = {
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": body_text},
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {
                            "id": btn["id"],
                            "title": btn["title"]
                        }
                    }
                    for btn in buttons
                ]
            }
        }
    }

    if header_text:
        message["interactive"]["header"] = {
            "type": "text",
            "text": header_text
        }

    if footer_text:
        message["interactive"]["footer"] = {"text": footer_text}

    return await client.send_message(to, message)
```

#### List Messages

```python
async def send_list_message(
    client: WhatsAppClient,
    to: str,
    body_text: str,
    button_text: str,
    sections: list[Dict],
    header_text: str = None,
    footer_text: str = None
):
    """Send interactive list message"""
    message = {
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": body_text},
            "action": {
                "button": button_text,
                "sections": sections
            }
        }
    }

    if header_text:
        message["interactive"]["header"] = {
            "type": "text",
            "text": header_text
        }

    if footer_text:
        message["interactive"]["footer"] = {"text": footer_text}

    return await client.send_message(to, message)
```

## Approval Workflow Implementation

### Approval Request

```python
from enum import Enum
from typing import Optional
from datetime import datetime

class ApprovalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"

class ApprovalRequest:
    def __init__(
        self,
        request_id: str,
        content: str,
        platform: str,
        requester_id: str,
        approver_phone: str
    ):
        self.request_id = request_id
        self.content = content
        self.platform = platform
        self.requester_id = requester_id
        self.approver_phone = approver_phone
        self.status = ApprovalStatus.PENDING
        self.created_at = datetime.utcnow()
        self.response_at: Optional[datetime] = None
        self.response_message: Optional[str] = None

async def send_approval_request(
    client: WhatsAppClient,
    approval: ApprovalRequest
) -> Dict:
    """Send approval request via WhatsApp"""
    body_text = f"""
📋 *Content Approval Request*

Platform: {approval.platform}
Request ID: {approval.request_id}

Content:
{approval.content}

Please review and approve or reject this content.
    """.strip()

    buttons = [
        {"id": f"approve_{approval.request_id}", "title": "✅ Approve"},
        {"id": f"reject_{approval.request_id}", "title": "❌ Reject"},
        {"id": f"edit_{approval.request_id}", "title": "✏️ Request Edit"}
    ]

    return await send_button_message(
        client,
        to=approval.approver_phone,
        body_text=body_text,
        buttons=buttons,
        header_text="Approval Required",
        footer_text="Reply within 24 hours"
    )
```

### Response Processing

```python
class ApprovalResponseHandler:
    def __init__(self, db_session, whatsapp_client: WhatsAppClient):
        self.db = db_session
        self.client = whatsapp_client

    async def process_response(self, message: Dict) -> Dict:
        """Process approval response from WhatsApp"""
        # Extract button response
        if message.get("type") == "interactive":
            button_reply = message["interactive"]["button_reply"]
            button_id = button_reply["id"]
            from_phone = message["from"]

            # Parse button ID
            action, request_id = button_id.split("_", 1)

            # Get approval request
            approval = await self.get_approval_request(request_id)

            if not approval:
                await self.send_error_message(from_phone, "Approval request not found")
                return {"status": "error", "message": "Request not found"}

            # Process action
            if action == "approve":
                return await self.approve_content(approval, from_phone)
            elif action == "reject":
                return await self.reject_content(approval, from_phone)
            elif action == "edit":
                return await self.request_edit(approval, from_phone)

    async def approve_content(self, approval: ApprovalRequest, from_phone: str):
        """Approve content and publish"""
        approval.status = ApprovalStatus.APPROVED
        approval.response_at = datetime.utcnow()

        # Update database
        await self.db.commit()

        # Publish content
        await self.publish_content(approval)

        # Send confirmation
        await self.client.send_message(
            to=from_phone,
            message={
                "type": "text",
                "text": {
                    "body": f"✅ Content approved and published!\n\nRequest ID: {approval.request_id}"
                }
            }
        )

        return {"status": "approved", "request_id": approval.request_id}

    async def reject_content(self, approval: ApprovalRequest, from_phone: str):
        """Reject content"""
        approval.status = ApprovalStatus.REJECTED
        approval.response_at = datetime.utcnow()

        await self.db.commit()

        # Send confirmation
        await self.client.send_message(
            to=from_phone,
            message={
                "type": "text",
                "text": {
                    "body": f"❌ Content rejected.\n\nRequest ID: {approval.request_id}\n\nPlease reply with feedback for the content creator."
                }
            }
        )

        return {"status": "rejected", "request_id": approval.request_id}

    async def request_edit(self, approval: ApprovalRequest, from_phone: str):
        """Request content edit"""
        await self.client.send_message(
            to=from_phone,
            message={
                "type": "text",
                "text": {
                    "body": f"✏️ Edit requested.\n\nRequest ID: {approval.request_id}\n\nPlease reply with your edit suggestions."
                }
            }
        )

        return {"status": "edit_requested", "request_id": approval.request_id}
```

## Message Templates

### Creating Templates

Templates must be pre-approved by Meta. Create via Business Manager or API:

```python
async def create_message_template(
    business_account_id: str,
    access_token: str,
    template_data: Dict
):
    """Create WhatsApp message template"""
    url = f"https://graph.facebook.com/v18.0/{business_account_id}/message_templates"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            headers={"Authorization": f"Bearer {access_token}"},
            json=template_data
        )
        return response.json()
```

### Template Examples

#### Approval Request Template

```json
{
  "name": "approval_request",
  "language": "en",
  "category": "UTILITY",
  "components": [
    {
      "type": "HEADER",
      "format": "TEXT",
      "text": "Approval Required"
    },
    {
      "type": "BODY",
      "text": "Platform: {{1}}\nRequest ID: {{2}}\n\nContent:\n{{3}}\n\nPlease review and respond."
    },
    {
      "type": "FOOTER",
      "text": "Reply within 24 hours"
    },
    {
      "type": "BUTTONS",
      "buttons": [
        {
          "type": "QUICK_REPLY",
          "text": "Approve"
        },
        {
          "type": "QUICK_REPLY",
          "text": "Reject"
        }
      ]
    }
  ]
}
```

#### Status Update Template

```json
{
  "name": "status_update",
  "language": "en",
  "category": "UTILITY",
  "components": [
    {
      "type": "BODY",
      "text": "Status Update: {{1}}\n\nYour content has been {{2}}.\n\nRequest ID: {{3}}"
    }
  ]
}
```

## Webhook Integration

### Webhook Setup

```python
from fastapi import APIRouter, Request, HTTPException, status

router = APIRouter()

@router.get("/webhooks/whatsapp")
async def verify_webhook(request: Request):
    """Verify WhatsApp webhook"""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN")

    if mode == "subscribe" and token == verify_token:
        return int(challenge)

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

@router.post("/webhooks/whatsapp")
async def receive_webhook(request: Request):
    """Receive WhatsApp webhook events"""
    body = await request.json()

    # Process webhook
    if body.get("object") == "whatsapp_business_account":
        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                if change.get("field") == "messages":
                    await process_message(change["value"])

    return {"status": "ok"}
```

### Message Processing

```python
async def process_message(value: Dict):
    """Process incoming WhatsApp message"""
    messages = value.get("messages", [])

    for message in messages:
        message_type = message.get("type")
        from_phone = message.get("from")
        message_id = message.get("id")

        # Check for duplicate
        if await is_duplicate_message(message_id):
            continue

        # Process based on type
        if message_type == "text":
            await process_text_message(message, from_phone)
        elif message_type == "interactive":
            await process_interactive_response(message, from_phone)
        elif message_type == "button":
            await process_button_response(message, from_phone)

        # Mark as processed
        await mark_message_processed(message_id)
```

## Error Handling

### Rate Limiting

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def send_with_retry(client: WhatsAppClient, to: str, message: Dict):
    """Send message with retry logic"""
    try:
        return await client.send_message(to, message)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            # Rate limited, will retry
            raise
        elif e.response.status_code >= 500:
            # Server error, will retry
            raise
        else:
            # Client error, don't retry
            raise Exception(f"Failed to send message: {e}")
```

### Message Delivery Status

```python
async def process_status_update(value: Dict):
    """Process message status updates"""
    statuses = value.get("statuses", [])

    for status_update in statuses:
        message_id = status_update.get("id")
        status = status_update.get("status")
        timestamp = status_update.get("timestamp")

        # Update message status in database
        await update_message_status(message_id, status, timestamp)

        # Handle failures
        if status == "failed":
            error = status_update.get("errors", [{}])[0]
            await handle_message_failure(message_id, error)
```

## Best Practices

### Message Formatting

```python
def format_approval_message(content: str, platform: str, request_id: str) -> str:
    """Format approval message with proper structure"""
    # Truncate long content
    max_length = 1000
    if len(content) > max_length:
        content = content[:max_length] + "..."

    # Format with emojis for better UX
    return f"""
📋 *Content Approval Request*

🌐 Platform: {platform}
🆔 Request ID: {request_id}

📝 Content:
{content}

⏰ Please respond within 24 hours
    """.strip()
```

### Session Management

```python
class ApprovalSession:
    """Manage approval workflow sessions"""
    def __init__(self, redis_client):
        self.redis = redis_client

    async def create_session(self, request_id: str, data: Dict, ttl: int = 86400):
        """Create approval session with TTL"""
        key = f"approval:{request_id}"
        await self.redis.setex(key, ttl, json.dumps(data))

    async def get_session(self, request_id: str) -> Optional[Dict]:
        """Get approval session"""
        key = f"approval:{request_id}"
        data = await self.redis.get(key)
        return json.loads(data) if data else None

    async def delete_session(self, request_id: str):
        """Delete approval session"""
        key = f"approval:{request_id}"
        await self.redis.delete(key)
```

### Notification Preferences

```python
class NotificationManager:
    """Manage user notification preferences"""

    async def should_notify(self, user_id: str, notification_type: str) -> bool:
        """Check if user should receive notification"""
        preferences = await self.get_preferences(user_id)

        # Check quiet hours
        if self.is_quiet_hours(preferences):
            return False

        # Check notification type enabled
        if not preferences.get(notification_type, True):
            return False

        return True

    def is_quiet_hours(self, preferences: Dict) -> bool:
        """Check if current time is in quiet hours"""
        quiet_start = preferences.get("quiet_hours_start", "22:00")
        quiet_end = preferences.get("quiet_hours_end", "08:00")

        # Implementation depends on timezone handling
        return False
```

## Security

### Message Validation

```python
import hmac
import hashlib

def validate_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Validate WhatsApp webhook signature"""
    expected_signature = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature, f"sha256={expected_signature}")
```

### Phone Number Validation

```python
import phonenumbers

def validate_phone_number(phone: str) -> bool:
    """Validate phone number format"""
    try:
        parsed = phonenumbers.parse(phone, None)
        return phonenumbers.is_valid_number(parsed)
    except phonenumbers.NumberParseException:
        return False
```

## Monitoring

### Metrics Tracking

```python
class WhatsAppMetrics:
    """Track WhatsApp API metrics"""

    async def track_message_sent(self, message_type: str, to: str):
        """Track sent message"""
        await self.increment_counter(f"whatsapp.messages.sent.{message_type}")

    async def track_message_delivered(self, message_id: str):
        """Track delivered message"""
        await self.increment_counter("whatsapp.messages.delivered")

    async def track_message_read(self, message_id: str):
        """Track read message"""
        await self.increment_counter("whatsapp.messages.read")

    async def track_approval_response(self, action: str):
        """Track approval response"""
        await self.increment_counter(f"whatsapp.approvals.{action}")
```

## Testing

### Mock WhatsApp Client

```python
class MockWhatsAppClient:
    """Mock WhatsApp client for testing"""

    def __init__(self):
        self.sent_messages = []

    async def send_message(self, to: str, message: Dict) -> Dict:
        """Mock send message"""
        message_data = {
            "to": to,
            "message": message,
            "id": f"mock_msg_{len(self.sent_messages)}"
        }
        self.sent_messages.append(message_data)
        return {"messages": [{"id": message_data["id"]}]}

    def get_sent_messages(self) -> list:
        """Get all sent messages"""
        return self.sent_messages
```

## Complete Example

```python
# Complete approval workflow example
async def approval_workflow_example():
    # Initialize
    client = WhatsAppClient()
    handler = ApprovalResponseHandler(db_session, client)

    # Create approval request
    approval = ApprovalRequest(
        request_id="req_123",
        content="Check out our new AI-powered marketing tool!",
        platform="linkedin",
        requester_id="user_456",
        approver_phone="+1234567890"
    )

    # Send approval request
    await send_approval_request(client, approval)

    # Wait for response (handled by webhook)
    # When response received, process it
    response = await handler.process_response(webhook_message)

    return response
```
