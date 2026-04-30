#!/usr/bin/env python3
"""
Channel Ingestion Service
Implements FastAPI endpoints and webhook handlers for Gmail API, Twilio WhatsApp, and Web Support Form.
Handles message normalization and initial ingestion into the system.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import uuid4

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from pydantic import BaseModel, EmailStr, validator
import html
import re

# Import required libraries
try:
    from twilio.request_validator import RequestValidator
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Channel Ingestion Service")

# Models
class ChannelType:
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    WEB_FORM = "web_form"

class Attachment(BaseModel):
    url: str
    type: str  # MIME type
    filename: str
    size: Optional[int] = None

class NormalizedMessage(BaseModel):
    id: str
    channel: str
    sender_id: str
    sender_name: Optional[str] = None
    content: str
    timestamp: datetime
    metadata: Dict[str, Any] = {}
    attachments: Optional[List[Attachment]] = []
    subject: Optional[str] = None
    priority: Optional[str] = "medium"
    category: Optional[str] = "general"

# Configuration (in production, use environment variables)
TWILIO_AUTH_TOKEN = "YOUR_TWILIO_AUTH_TOKEN"  # Replace with env var
GMAIL_ALLOWED_ADDRESSES = ["user@example.com"]  # Replace with actual addresses
WEBHOOK_SECRET = "YOUR_WEBHOOK_SECRET"  # Replace with env var

# Utility functions
def sanitize_content(content: str) -> str:
    """Sanitize message content to prevent XSS"""
    content = html.escape(content)
    content = re.sub(r'javascript:', '', content, flags=re.IGNORECASE)
    content = re.sub(r'on\w+\s*=', '', content, flags=re.IGNORECASE)
    return content

def detect_priority_from_content(content: str, subject: str = "") -> str:
    """Detect priority based on content keywords"""
    high_priority_keywords = [
        'urgent', 'asap', 'immediately', 'crash', 'down', 'error',
        'critical', 'emergency', 'problem', 'broken', 'stopped'
    ]

    combined_text = (subject + " " + content).lower()

    for keyword in high_priority_keywords:
        if keyword in combined_text:
            return 'high'

    return 'medium'

def log_webhook_received(channel: str, sender_id: str, message_id: str):
    """Log webhook receipt without sensitive content"""
    logger.info(f"Webhook received - Channel: {channel}, "
                f"Sender ID: {sender_id}, Message ID: {message_id}")

# Message processing functions
def process_gmail_message(payload: Dict[str, Any]) -> NormalizedMessage:
    """Process Gmail webhook payload and normalize to common format"""
    # Extract message components from Gmail format
    email_address = payload.get('emailAddress', '')

    # Verify this is an allowed email address
    if email_address not in GMAIL_ALLOWED_ADDRESSES:
        raise HTTPException(status_code=403, detail="Unauthorized Gmail webhook")

    # In a real implementation, you'd fetch the actual message using Gmail API
    # based on the historyId provided in the webhook
    message_data = {
        'id': str(uuid4()),
        'channel': ChannelType.EMAIL,
        'sender_id': email_address,
        'sender_name': email_address,  # Would come from message headers
        'content': 'Gmail message content would be retrieved using the Gmail API',  # Would come from actual message
        'timestamp': datetime.utcnow(),
        'metadata': {
            'original_email_address': email_address,
            'history_id': payload.get('historyId'),
            'gmail_expiration': payload.get('expiration')
        },
        'priority': 'medium',
        'category': 'email'
    }

    return NormalizedMessage(**message_data)

def process_twilio_whatsapp_message(form_data: Dict[str, Any]) -> NormalizedMessage:
    """Process Twilio WhatsApp webhook payload and normalize to common format"""
    if not TWILIO_AVAILABLE:
        raise HTTPException(status_code=500, detail="Twilio library not installed")

    sender_number = form_data.get('From', '').replace('whatsapp:', '')
    content = form_data.get('Body', '')

    # Handle media attachments
    attachments = []
    num_media = int(form_data.get('NumMedia', 0))
    for i in range(num_media):
        media_url_key = f'MediaUrl{i}'
        media_type_key = f'MediaContentType{i}'
        if media_url_key in form_data:
            attachments.append(Attachment(
                url=form_data[media_url_key],
                type=form_data[media_type_key],
                filename=f"{form_data.get('MessageSid', 'unknown')}_{i}"
            ))

    message_data = {
        'id': form_data.get('MessageSid', str(uuid4())),
        'channel': ChannelType.WHATSAPP,
        'sender_id': sender_number,
        'sender_name': form_data.get('From'),
        'content': sanitize_content(content),
        'timestamp': datetime.utcnow(),  # Would use actual timestamp if available
        'metadata': {
            'twilio_message_sid': form_data.get('MessageSid'),
            'twilio_account_sid': form_data.get('AccountSid'),
            'num_media': num_media
        },
        'attachments': attachments,
        'priority': detect_priority_from_content(content),
        'category': 'whatsapp'
    }

    return NormalizedMessage(**message_data)

def process_web_form_message(form_data: Dict[str, Any]) -> NormalizedMessage:
    """Process web form submission and normalize to common format"""
    content = form_data.get('message', '')
    subject = form_data.get('subject', '')

    message_data = {
        'id': str(uuid4()),
        'channel': ChannelType.WEB_FORM,
        'sender_id': form_data.get('customer_email', ''),
        'sender_name': form_data.get('customer_name', ''),
        'content': sanitize_content(content),
        'timestamp': datetime.utcnow(),
        'metadata': {
            'form_source': 'web_support_form',
            'category': form_data.get('category', 'general'),
        },
        'subject': subject,
        'priority': form_data.get('priority', detect_priority_from_content(content, subject)),
        'category': form_data.get('category', 'general')
    }

    return NormalizedMessage(**message_data)

# Background task to process messages asynchronously
async def process_normalized_message_async(normalized_msg: NormalizedMessage):
    """Process the normalized message in the background"""
    # In a real implementation, this would:
    # 1. Store the message in a database
    # 2. Trigger further processing workflows
    # 3. Send notifications if needed
    # 4. Update customer records

    logger.info(f"Processing message {normalized_msg.id} from {normalized_msg.sender_id}")

    # Simulate async processing
    await asyncio.sleep(0.1)

    # Example: Store in database or message queue
    print(f"Stored message: {normalized_msg.dict()}")

# Webhook endpoints
@app.post("/webhook/gmail")
async def gmail_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Handle Gmail API webhook notifications
    """
    # In a real implementation, verify authentication
    payload = await request.json()

    try:
        # Process the Gmail message
        normalized_msg = process_gmail_message(payload)

        # Log the webhook receipt
        log_webhook_received(normalized_msg.channel, normalized_msg.sender_id, normalized_msg.id)

        # Process the message asynchronously
        background_tasks.add_task(process_normalized_message_async, normalized_msg)

        return {"status": "received", "message_id": normalized_msg.id}

    except Exception as e:
        logger.error(f"Gmail webhook error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/webhook/twilio-whatsapp")
async def twilio_whatsapp_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Handle Twilio WhatsApp webhook notifications
    """
    if not TWILIO_AVAILABLE:
        raise HTTPException(status_code=500, detail="Twilio library not installed")

    # Verify Twilio signature (in production, implement this)
    # form_data = await request.form()
    # validator = RequestValidator(TWILIO_AUTH_TOKEN)
    # signature = request.headers.get('X-Twilio-Signature', '')
    #
    # if not validator.validate(str(request.url), dict(form_data), signature):
    #     raise HTTPException(status_code=403, detail="Invalid Twilio signature")

    form_data = await request.form()

    try:
        # Process the Twilio WhatsApp message
        normalized_msg = process_twilio_whatsapp_message(dict(form_data))

        # Log the webhook receipt
        log_webhook_received(normalized_msg.channel, normalized_msg.sender_id, normalized_msg.id)

        # Process the message asynchronously
        background_tasks.add_task(process_normalized_message_async, normalized_msg)

        return {"status": "received", "message_id": normalized_msg.id}

    except Exception as e:
        logger.error(f"Twilio WhatsApp webhook error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/webhook/web-support-form")
async def web_support_form_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Handle web support form submissions
    """
    form_data = await request.form()
    form_dict = dict(form_data)

    # Validate required fields
    required_fields = ['customer_email', 'message']
    for field in required_fields:
        if not form_dict.get(field):
            raise HTTPException(status_code=400, detail=f"Missing required field: {field}")

    try:
        # Process the web form message
        normalized_msg = process_web_form_message(form_dict)

        # Log the webhook receipt
        log_webhook_received(normalized_msg.channel, normalized_msg.sender_id, normalized_msg.id)

        # Process the message asynchronously
        background_tasks.add_task(process_normalized_message_async, normalized_msg)

        return {"status": "received", "message_id": normalized_msg.id}

    except Exception as e:
        logger.error(f"Web support form webhook error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "channels": ["gmail", "twilio-whatsapp", "web-support-form"]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)