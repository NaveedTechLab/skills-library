# Twilio WhatsApp Integration Reference

## Webhook Setup

Twilio sends POST requests to your webhook URL when WhatsApp messages arrive. The endpoint should handle Twilio's specific format for WhatsApp messages.

## Payload Format

Twilio webhook payloads for WhatsApp contain:
- `From`: The sender's WhatsApp number (format: whatsapp:+1234567890)
- `To`: Your WhatsApp number receiving the message
- `Body`: The message content
- `MessageSid`: Unique identifier for the message
- `AccountSid`: Your Twilio account identifier
- `NumMedia`: Number of media files attached (0 if none)

## Message Parsing

Parse Twilio's WhatsApp format:
- Extract phone numbers from `whatsapp:+1234567890` format
- Handle media attachments using `NumMedia` and `MediaUrl*` fields
- Process message body with potential Unicode characters

## Signature Verification

Verify that the request comes from Twilio:
- Use Twilio's helper libraries for signature validation
- Construct the expected URL and compare signatures
- Reject requests with invalid signatures

## Media Handling

Handle media attachments in WhatsApp messages:
- Download media from Twilio's secure URLs
- Validate media types and sizes
- Store temporarily for processing

## Error Handling

Handle common Twilio issues:
- Invalid signatures - reject unauthorized requests
- Rate limits - implement queuing mechanism
- Media download failures - log and continue processing

## Sample Implementation

```python
from twilio.request_validator import RequestValidator
from urllib.parse import parse_qs
import requests

def validate_twilio_request(request, webhook_url, auth_token):
    """Validate that the request came from Twilio"""
    validator = RequestValidator(auth_token)
    signature = request.headers.get('X-Twilio-Signature', '')
    return validator.validate(webhook_url, request.form, signature)

def parse_twilio_whatsapp_message(form_data):
    """Parse Twilio WhatsApp message into normalized format"""
    sender_number = form_data.get('From', '').replace('whatsapp:', '')

    # Handle media attachments
    media_urls = []
    num_media = int(form_data.get('NumMedia', 0))
    for i in range(num_media):
        media_url_key = f'MediaUrl{i}'
        media_type_key = f'MediaContentType{i}'
        if media_url_key in form_data:
            media_urls.append({
                'url': form_data[media_url_key],
                'type': form_data[media_type_key],
                'filename': f"{form_data.get('MessageSid')}_{i}"
            })

    return {
        'sender_id': sender_number,
        'sender_name': form_data.get('From'),  # May be available in some contexts
        'content': form_data.get('Body', ''),
        'timestamp': form_data.get('Timestamp', ''),
        'message_sid': form_data.get('MessageSid'),
        'attachments': media_urls
    }
```