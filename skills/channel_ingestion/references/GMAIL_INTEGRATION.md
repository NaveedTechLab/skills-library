# Gmail API Integration Reference

## Webhook Setup

Gmail push notifications require setting up watch requests to receive updates about a user's mailbox. The webhook endpoint should handle these push notifications.

## Payload Format

Gmail webhook payloads contain:
- `emailAddress`: The email address associated with the watch request
- `historyId`: The history ID up to which messages have been delivered
- `expiration`: The expiration date of the push notification

## Message Retrieval

Upon receiving a webhook notification, retrieve the actual messages using the Gmail API with the history ID:
- Use the `users.history.list` endpoint to get changes
- Retrieve new messages using `users.messages.get`
- Parse message content from the payload

## Authentication Verification

Verify that the request comes from Google:
- Check that the request includes proper authentication headers
- Validate that the email address matches expected accounts
- Implement proper OAuth 2.0 token validation

## Error Handling

Handle common Gmail webhook issues:
- Invalid access tokens - refresh tokens as needed
- Rate limits - implement exponential backoff
- Malformed payloads - validate structure before processing

## Sample Implementation

```python
import base64
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

def parse_gmail_message(message_data):
    """Parse raw Gmail message data into normalized format"""
    headers = {header['name'].lower(): header['value'] for header in message_data['payload']['headers']}

    # Extract message parts
    if 'parts' in message_data['payload']:
        # Multi-part message
        for part in message_data['payload']['parts']:
            if part['mimeType'] == 'text/plain':
                body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                break
    else:
        # Single-part message
        body = base64.urlsafe_b64decode(message_data['payload']['body']['data']).decode('utf-8')

    return {
        'sender': headers.get('from'),
        'subject': headers.get('subject'),
        'body': body,
        'timestamp': int(message_data['internalDate']) / 1000
    }
```