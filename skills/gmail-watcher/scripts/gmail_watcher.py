#!/usr/bin/env python3
"""
GmailWatcher - Monitor Gmail for unread/important emails.

Extends BaseWatcher to poll Gmail API and emit events for emails
matching configured filters (unread, important, specific labels).
"""

import base64
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from pathlib import Path
import sys

# Add base-watcher-framework to path
BASE_WATCHER_PATH = Path(__file__).parent.parent.parent / "base-watcher-framework" / "scripts"
if BASE_WATCHER_PATH.exists():
    sys.path.insert(0, str(BASE_WATCHER_PATH))

from base_watcher import BaseWatcher, WatcherConfig, WatcherEvent, EventType

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    GMAIL_AVAILABLE = True
except ImportError:
    GMAIL_AVAILABLE = False


# Gmail API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


@dataclass
class EmailData:
    """Parsed email data structure."""
    message_id: str
    thread_id: str
    subject: str
    sender: str
    sender_email: str
    recipient: str
    date: datetime
    snippet: str
    body_preview: str
    labels: list
    is_unread: bool
    is_important: bool
    has_attachments: bool
    attachment_names: list


@dataclass
class GmailWatcherConfig(WatcherConfig):
    """
    Configuration for GmailWatcher.
    
    Attributes:
        credentials_path: Path to Google OAuth credentials.json
        token_path: Path to store/load OAuth token
        filter_unread: Include unread emails
        filter_important: Include important emails
        filter_labels: Include emails with these labels
        exclude_labels: Exclude emails with these labels
        max_results: Maximum emails to fetch per poll
        include_body: Include email body preview
        body_max_length: Maximum body preview length
        mark_as_processed: Add label to processed emails (optional)
    """
    credentials_path: str = "credentials.json"
    token_path: str = "token.json"
    filter_unread: bool = True
    filter_important: bool = False
    filter_labels: list = field(default_factory=list)
    exclude_labels: list = field(default_factory=lambda: ["TRASH", "SPAM"])
    max_results: int = 20
    include_body: bool = True
    body_max_length: int = 500
    mark_as_processed: Optional[str] = None  # Label name to add after processing


class GmailWatcher(BaseWatcher):
    """
    Watcher that monitors Gmail for new/important emails.
    
    Extends BaseWatcher to integrate with WatcherRegistry and emitters.
    Uses Google Gmail API with OAuth2 authentication.
    
    Example:
        config = GmailWatcherConfig(
            name="gmail-inbox",
            credentials_path="./credentials.json",
            filter_unread=True,
            filter_important=True,
            poll_interval=60.0
        )
        
        watcher = GmailWatcher(config)
        watcher.on_event(lambda e: print(f"New email: {e.data['subject']}"))
        
        await watcher.start()
    """
    
    def __init__(self, config: GmailWatcherConfig):
        if not GMAIL_AVAILABLE:
            raise ImportError(
                "Gmail API libraries required. Install with:\n"
                "pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client"
            )
        
        super().__init__(config)
        self.gmail_config = config
        self._service = None
        self._creds = None
        self._seen_ids: set = set()
        self._user_email: str = ""
    
    async def _setup(self) -> None:
        """Initialize Gmail API connection."""
        self._creds = self._get_credentials()
        self._service = build('gmail', 'v1', credentials=self._creds)
        
        # Get user email
        profile = self._service.users().getProfile(userId='me').execute()
        self._user_email = profile.get('emailAddress', '')
        
        # Build initial seen set (don't emit events for existing emails)
        messages = self._fetch_messages()
        self._seen_ids = {msg['id'] for msg in messages}
    
    async def _teardown(self) -> None:
        """Clean up resources."""
        self._service = None
        self._creds = None
        self._seen_ids.clear()
    
    async def _poll(self) -> list[WatcherEvent]:
        """Poll Gmail for new messages matching filters."""
        events = []
        
        messages = self._fetch_messages()
        
        for msg_meta in messages:
            msg_id = msg_meta['id']
            
            # Skip already seen messages
            if msg_id in self._seen_ids:
                continue
            
            # Fetch full message details
            try:
                email_data = self._get_email_details(msg_id)
                
                if email_data and self._matches_filters(email_data):
                    events.append(self._create_email_event(email_data))
                    self._seen_ids.add(msg_id)
                    
            except Exception as e:
                events.append(self._create_event(
                    EventType.ERROR,
                    data={"error": str(e), "message_id": msg_id},
                    source=f"gmail:{msg_id}"
                ))
        
        return events
    
    def _get_credentials(self) -> Credentials:
        """Get or refresh OAuth credentials."""
        creds = None
        token_path = Path(self.gmail_config.token_path)
        creds_path = Path(self.gmail_config.credentials_path)
        
        # Load existing token
        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        
        # Refresh or get new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not creds_path.exists():
                    raise FileNotFoundError(
                        f"Credentials file not found: {creds_path}\n"
                        "Download from Google Cloud Console."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save token for next run
            token_path.write_text(creds.to_json())
        
        return creds
    
    def _build_query(self) -> str:
        """Build Gmail search query from filters."""
        query_parts = []
        
        if self.gmail_config.filter_unread:
            query_parts.append("is:unread")
        
        if self.gmail_config.filter_important:
            query_parts.append("is:important")
        
        for label in self.gmail_config.filter_labels:
            query_parts.append(f"label:{label}")
        
        for label in self.gmail_config.exclude_labels:
            query_parts.append(f"-label:{label}")
        
        # Join with OR if multiple positive filters, AND for excludes
        if self.gmail_config.filter_unread and self.gmail_config.filter_important:
            # Both unread AND important
            return " ".join(query_parts)
        
        return " ".join(query_parts) if query_parts else "in:inbox"
    
    def _fetch_messages(self) -> list[dict]:
        """Fetch message list from Gmail."""
        query = self._build_query()
        
        results = self._service.users().messages().list(
            userId='me',
            q=query,
            maxResults=self.gmail_config.max_results
        ).execute()
        
        return results.get('messages', [])
    
    def _get_email_details(self, message_id: str) -> Optional[EmailData]:
        """Fetch and parse full email details."""
        msg = self._service.users().messages().get(
            userId='me',
            id=message_id,
            format='full'
        ).execute()
        
        headers = {h['name'].lower(): h['value'] for h in msg['payload'].get('headers', [])}
        labels = msg.get('labelIds', [])
        
        # Parse sender
        sender_raw = headers.get('from', '')
        sender_match = re.match(r'([^<]*)<([^>]+)>', sender_raw)
        if sender_match:
            sender_name = sender_match.group(1).strip().strip('"')
            sender_email = sender_match.group(2)
        else:
            sender_name = sender_raw
            sender_email = sender_raw
        
        # Parse date
        date_str = headers.get('date', '')
        try:
            # Try common date formats
            for fmt in ['%a, %d %b %Y %H:%M:%S %z', '%d %b %Y %H:%M:%S %z']:
                try:
                    email_date = datetime.strptime(date_str.split(' (')[0].strip(), fmt)
                    break
                except ValueError:
                    continue
            else:
                email_date = datetime.now()
        except Exception:
            email_date = datetime.now()
        
        # Get body preview
        body_preview = ""
        if self.gmail_config.include_body:
            body_preview = self._extract_body(msg['payload'])
            if len(body_preview) > self.gmail_config.body_max_length:
                body_preview = body_preview[:self.gmail_config.body_max_length] + "..."
        
        # Check for attachments
        attachments = self._get_attachments(msg['payload'])
        
        return EmailData(
            message_id=message_id,
            thread_id=msg.get('threadId', ''),
            subject=headers.get('subject', '(No Subject)'),
            sender=sender_name,
            sender_email=sender_email,
            recipient=headers.get('to', self._user_email),
            date=email_date,
            snippet=msg.get('snippet', ''),
            body_preview=body_preview,
            labels=labels,
            is_unread='UNREAD' in labels,
            is_important='IMPORTANT' in labels,
            has_attachments=len(attachments) > 0,
            attachment_names=attachments
        )
    
    def _extract_body(self, payload: dict) -> str:
        """Extract plain text body from email payload."""
        if 'body' in payload and payload['body'].get('data'):
            return base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part.get('mimeType') == 'text/plain':
                    if 'body' in part and part['body'].get('data'):
                        return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                elif 'parts' in part:
                    # Nested multipart
                    result = self._extract_body(part)
                    if result:
                        return result
        
        return ""
    
    def _get_attachments(self, payload: dict) -> list[str]:
        """Get list of attachment filenames."""
        attachments = []
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part.get('filename'):
                    attachments.append(part['filename'])
                if 'parts' in part:
                    attachments.extend(self._get_attachments(part))
        
        return attachments
    
    def _matches_filters(self, email: EmailData) -> bool:
        """Check if email matches configured filters."""
        # Apply additional Python-side filtering if needed
        if self.gmail_config.filter_unread and not email.is_unread:
            return False
        
        if self.gmail_config.filter_important and not email.is_important:
            return False
        
        return True
    
    def _create_email_event(self, email: EmailData) -> WatcherEvent:
        """Create event from email data."""
        # Determine priority
        priority = "normal"
        if email.is_important:
            priority = "high"
        if "STARRED" in email.labels:
            priority = "urgent"
        
        return self._create_event(
            EventType.CREATED,
            data={
                "message_id": email.message_id,
                "thread_id": email.thread_id,
                "subject": email.subject,
                "sender": email.sender,
                "sender_email": email.sender_email,
                "recipient": email.recipient,
                "date": email.date.isoformat(),
                "snippet": email.snippet,
                "body_preview": email.body_preview,
                "labels": email.labels,
                "is_unread": email.is_unread,
                "is_important": email.is_important,
                "has_attachments": email.has_attachments,
                "attachment_names": email.attachment_names,
                "priority": priority
            },
            source=f"gmail:{email.message_id}",
            email_type="gmail",
            priority=priority
        )


# Convenience function
def watch_gmail(
    credentials_path: str = "credentials.json",
    filter_unread: bool = True,
    filter_important: bool = False,
    poll_interval: float = 60.0
) -> GmailWatcher:
    """
    Create a GmailWatcher with common defaults.
    
    Args:
        credentials_path: Path to Google OAuth credentials.json
        filter_unread: Watch for unread emails
        filter_important: Watch for important emails
        poll_interval: Seconds between polls
        
    Returns:
        Configured GmailWatcher instance
    """
    config = GmailWatcherConfig(
        name="gmail-watcher",
        credentials_path=credentials_path,
        filter_unread=filter_unread,
        filter_important=filter_important,
        poll_interval=poll_interval
    )
    return GmailWatcher(config)
