#!/usr/bin/env python3
"""
Email MCP Server - Model Context Protocol server for Gmail integration

This server enables Claude Code to draft, send, and search emails via Gmail
with HITL (Human-in-the-Loop) enforcement for sensitive operations.
"""

import asyncio
import json
import logging
import os
import re
import tempfile
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import base64
import pickle

import aiohttp
from aiohttp import web
import google.auth.transport.requests
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Gmail API scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.compose'
]


@dataclass
class EmailDraft:
    """Represents an email draft"""
    to: str
    subject: str
    body: str
    cc: Optional[str] = None
    bcc: Optional[str] = None
    attachments: Optional[List[str]] = None
    html_body: Optional[str] = None


@dataclass
class SearchCriteria:
    """Email search criteria"""
    query: str
    max_results: int = 10
    before_date: Optional[str] = None
    after_date: Optional[str] = None
    sender: Optional[str] = None
    recipient: Optional[str] = None


@dataclass
class ApprovalRequest:
    """HITL approval request"""
    id: str
    operation: str
    details: Dict[str, Any]
    requested_by: str
    timestamp: datetime
    expires_at: datetime
    status: str = "pending"  # pending, approved, rejected
    approved_by: Optional[str] = None
    rejection_reason: Optional[str] = None


class HumanInTheLoopManager:
    """Manages HITL approval workflows"""

    def __init__(self):
        self.approval_requests: Dict[str, ApprovalRequest] = {}
        self.approval_timeout = 3600  # 1 hour in seconds

    def create_approval_request(self, operation: str, details: Dict[str, Any], requested_by: str) -> str:
        """Create a new approval request"""
        import uuid
        request_id = str(uuid.uuid4())
        expires_at = datetime.now() + timedelta(seconds=self.approval_timeout)

        request = ApprovalRequest(
            id=request_id,
            operation=operation,
            details=details,
            requested_by=requested_by,
            timestamp=datetime.now(),
            expires_at=expires_at,
            status="pending"
        )

        self.approval_requests[request_id] = request
        logger.info(f"Created approval request {request_id} for operation {operation}")
        return request_id

    def get_approval_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """Get an approval request by ID"""
        return self.approval_requests.get(request_id)

    def approve_request(self, request_id: str, approved_by: str) -> bool:
        """Approve an approval request"""
        if request_id in self.approval_requests:
            request = self.approval_requests[request_id]
            if request.status == "pending":
                request.status = "approved"
                request.approved_by = approved_by
                logger.info(f"Approved request {request_id} by {approved_by}")
                return True
        return False

    def reject_request(self, request_id: str, rejected_by: str, reason: str = "") -> bool:
        """Reject an approval request"""
        if request_id in self.approval_requests:
            request = self.approval_requests[request_id]
            if request.status == "pending":
                request.status = "rejected"
                request.rejection_reason = reason
                logger.info(f"Rejected request {request_id} by {rejected_by}")
                return True
        return False

    def cleanup_expired_requests(self):
        """Remove expired approval requests"""
        now = datetime.now()
        expired_ids = [
            req_id for req_id, req in self.approval_requests.items()
            if req.expires_at < now and req.status == "pending"
        ]
        for req_id in expired_ids:
            del self.approval_requests[req_id]
            logger.info(f"Removed expired approval request {req_id}")


class GmailService:
    """Wrapper for Gmail API operations"""

    def __init__(self, credentials_path: str, token_path: str = "token.pickle"):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None
        self.hitl_manager = HumanInTheLoopManager()

    def authenticate(self):
        """Authenticate with Gmail API"""
        creds = None

        # Load existing token
        if os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as token:
                creds = pickle.load(token)

        # If there are no valid credentials, request authorization
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    logger.warning(f"Token refresh failed: {e}")
                    creds = None

            if not creds:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save credentials for next run
            with open(self.token_path, 'wb') as token:
                pickle.dump(creds, token)

        self.service = build('gmail', 'v1', credentials=creds)
        logger.info("Gmail API authenticated successfully")

    def _create_message(self, draft: EmailDraft) -> Dict[str, str]:
        """Create a message for sending"""
        if draft.html_body:
            message = MIMEMultipart()
            message.attach(MIMEText(draft.body, 'plain'))
            message.attach(MIMEText(draft.html_body, 'html'))
        else:
            message = MIMEText(draft.body, 'plain')

        message['to'] = draft.to
        message['subject'] = draft.subject

        if draft.cc:
            message['cc'] = draft.cc
        if draft.bcc:
            message['bcc'] = draft.bcc

        # Add attachments
        if draft.attachments:
            for attachment_path in draft.attachments:
                with open(attachment_path, 'rb') as f:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename= {os.path.basename(attachment_path)}'
                    )
                    message.attach(part)

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        return {'raw': raw_message}

    def draft_email(self, draft: EmailDraft) -> str:
        """Draft an email"""
        try:
            message = self._create_message(draft)

            # Create draft in Gmail
            draft_result = self.service.users().drafts().create(
                userId='me',
                body={
                    'message': message
                }
            ).execute()

            logger.info(f"Draft created with ID: {draft_result['id']}")
            return draft_result['id']
        except HttpError as error:
            logger.error(f"An error occurred while drafting email: {error}")
            raise

    def send_email_with_approval(self, draft: EmailDraft, requester: str = "Claude") -> str:
        """Send an email with HITL approval if required"""
        # Check if approval is needed
        needs_approval = self._needs_hitl_approval(draft)

        if needs_approval:
            # Create approval request
            details = {
                'to': draft.to,
                'subject': draft.subject,
                'body_preview': draft.body[:100] + "..." if len(draft.body) > 100 else draft.body,
                'has_attachments': bool(draft.attachments),
                'cc': draft.cc,
                'bcc': draft.bcc
            }

            request_id = self.hitl_manager.create_approval_request(
                operation="send_email",
                details=details,
                requested_by=requester
            )

            logger.info(f"Approval required for email to {draft.to}. Request ID: {request_id}")
            return f"APPROVAL_NEEDED:{request_id}"
        else:
            # Send directly without approval
            return self._send_email_now(draft)

    def _needs_hitl_approval(self, draft: EmailDraft) -> bool:
        """Check if an email needs HITL approval"""
        # Check for external recipients (simple domain check)
        to_emails = [e.strip() for e in draft.to.split(',')]
        for email in to_emails:
            domain = email.split('@')[-1].lower()
            # Add your organization's domain here to identify external recipients
            if domain not in ['yourcompany.com', 'internal.com']:  # Replace with actual domains
                return True

        # Check for large attachments
        if draft.attachments:
            total_size = sum(os.path.getsize(f) for f in draft.attachments if os.path.exists(f))
            if total_size > 10 * 1024 * 1024:  # 10MB
                return True

        # Check for sensitive keywords in subject/body
        sensitive_keywords = ['confidential', 'private', 'urgent', 'sensitive', 'classified']
        content = f"{draft.subject} {draft.body}".lower()
        if any(keyword in content for keyword in sensitive_keywords):
            return True

        return False

    def _send_email_now(self, draft: EmailDraft) -> str:
        """Send an email immediately without approval"""
        try:
            message = self._create_message(draft)

            # Send email
            sent_message = self.service.users().messages().send(
                userId='me',
                body=message
            ).execute()

            logger.info(f"Email sent with ID: {sent_message['id']}")
            return sent_message['id']
        except HttpError as error:
            logger.error(f"An error occurred while sending email: {error}")
            raise

    def search_emails(self, criteria: SearchCriteria) -> List[Dict[str, Any]]:
        """Search emails based on criteria"""
        try:
            # Build query string
            query_parts = [criteria.query] if criteria.query else []

            if criteria.before_date:
                query_parts.append(f"before:{criteria.before_date}")
            if criteria.after_date:
                query_parts.append(f"after:{criteria.after_date}")
            if criteria.sender:
                query_parts.append(f"from:{criteria.sender}")
            if criteria.recipient:
                query_parts.append(f"to:{criteria.recipient}")

            query = ' '.join(query_parts)

            # Search messages
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=criteria.max_results
            ).execute()

            messages = results.get('messages', [])
            email_list = []

            for msg in messages:
                email_data = self.get_email(msg['id'])
                email_list.append(email_data)

            logger.info(f"Found {len(email_list)} emails matching criteria")
            return email_list
        except HttpError as error:
            logger.error(f"An error occurred while searching emails: {error}")
            raise

    def get_email(self, message_id: str) -> Dict[str, Any]:
        """Get email details by message ID"""
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()

            # Extract email details
            headers = {header['name']: header['value'] for header in message['payload']['headers']}

            email_data = {
                'id': message['id'],
                'threadId': message['threadId'],
                'subject': headers.get('Subject', ''),
                'from': headers.get('From', ''),
                'to': headers.get('To', ''),
                'cc': headers.get('Cc', ''),
                'date': headers.get('Date', ''),
                'snippet': message.get('snippet', ''),
                'sizeEstimate': message.get('sizeEstimate', 0)
            }

            # Extract body
            if 'parts' in message['payload']:
                for part in message['payload']['parts']:
                    if part['mimeType'] == 'text/plain':
                        email_data['body_plain'] = base64.urlsafe_b64decode(
                            part['body']['data']
                        ).decode('utf-8')
                    elif part['mimeType'] == 'text/html':
                        email_data['body_html'] = base64.urlsafe_b64decode(
                            part['body']['data']
                        ).decode('utf-8')
            else:
                # Single part message
                if 'body' in message['payload'] and 'data' in message['payload']['body']:
                    body_data = message['payload']['body']['data']
                    email_data['body_plain'] = base64.urlsafe_b64decode(body_data).decode('utf-8')

            return email_data
        except HttpError as error:
            logger.error(f"An error occurred while getting email: {error}")
            raise

    def list_labels(self) -> List[Dict[str, Any]]:
        """List all Gmail labels"""
        try:
            results = self.service.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])

            label_list = []
            for label in labels:
                label_list.append({
                    'id': label['id'],
                    'name': label['name'],
                    'type': label.get('type', 'system'),
                    'messageListVisibility': label.get('messageListVisibility', 'show'),
                    'messagesTotal': label.get('messagesTotal', 0),
                    'messagesUnread': label.get('messagesUnread', 0)
                })

            logger.info(f"Retrieved {len(label_list)} labels")
            return label_list
        except HttpError as error:
            logger.error(f"An error occurred while listing labels: {error}")
            raise

    def create_label(self, name: str) -> Dict[str, Any]:
        """Create a new label"""
        try:
            label_obj = {
                'name': name,
                'messageListVisibility': 'show',
                'labelListVisibility': 'labelShow'
            }

            result = self.service.users().labels().create(
                userId='me',
                body=label_obj
            ).execute()

            logger.info(f"Created label: {name}")
            return {
                'id': result['id'],
                'name': result['name'],
                'type': result.get('type', 'user'),
                'messageListVisibility': result.get('messageListVisibility', 'show')
            }
        except HttpError as error:
            logger.error(f"An error occurred while creating label: {error}")
            raise


class EmailMCPServer:
    """MCP server for email operations"""

    def __init__(self, config_path: str = "email_config.json"):
        self.config = self._load_config(config_path)
        self.gmail_service = GmailService(
            credentials_path=self.config.get('credentials_path', 'credentials.json'),
            token_path=self.config.get('token_path', 'token.pickle')
        )
        self.app = web.Application()
        self._setup_routes()

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load server configuration"""
        default_config = {
            "credentials_path": "credentials.json",
            "token_path": "token.pickle",
            "server": {
                "host": "localhost",
                "port": 8080
            },
            "hitl": {
                "enabled": True,
                "approval_timeout": 3600
            }
        }

        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                file_config = json.load(f)
            default_config.update(file_config)

        return default_config

    def _setup_routes(self):
        """Set up HTTP routes"""
        self.app.router.add_post('/draft_email', self.handle_draft_email)
        self.app.router.add_post('/send_email', self.handle_send_email)
        self.app.router.add_post('/search_emails', self.handle_search_emails)
        self.app.router.add_get('/get_email/{message_id}', self.handle_get_email)
        self.app.router.add_get('/list_labels', self.handle_list_labels)
        self.app.router.add_post('/create_label', self.handle_create_label)
        self.app.router.add_get('/profile', self.handle_get_profile)
        self.app.router.add_get('/approval_requests', self.handle_get_approval_requests)
        self.app.router.add_post('/approve_request', self.handle_approve_request)
        self.app.router.add_post('/reject_request', self.handle_reject_request)

    async def handle_draft_email(self, request):
        """Handle email draft request"""
        try:
            data = await request.json()
            draft = EmailDraft(
                to=data['to'],
                subject=data['subject'],
                body=data['body'],
                cc=data.get('cc'),
                bcc=data.get('bcc'),
                attachments=data.get('attachments'),
                html_body=data.get('html_body')
            )

            draft_id = self.gmail_service.draft_email(draft)
            return web.json_response({
                'success': True,
                'draft_id': draft_id
            })
        except Exception as e:
            logger.error(f"Error drafting email: {e}")
            return web.json_response({
                'success': False,
                'error': str(e)
            }, status=500)

    async def handle_send_email(self, request):
        """Handle email send request"""
        try:
            data = await request.json()
            draft = EmailDraft(
                to=data['to'],
                subject=data['subject'],
                body=data['body'],
                cc=data.get('cc'),
                bcc=data.get('bcc'),
                attachments=data.get('attachments'),
                html_body=data.get('html_body')
            )
            requester = data.get('requester', 'Claude')

            result = self.gmail_service.send_email_with_approval(draft, requester)

            return web.json_response({
                'success': True,
                'result': result
            })
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return web.json_response({
                'success': False,
                'error': str(e)
            }, status=500)

    async def handle_search_emails(self, request):
        """Handle email search request"""
        try:
            data = await request.json()
            criteria = SearchCriteria(
                query=data.get('query', ''),
                max_results=data.get('max_results', 10),
                before_date=data.get('before_date'),
                after_date=data.get('after_date'),
                sender=data.get('sender'),
                recipient=data.get('recipient')
            )

            emails = self.gmail_service.search_emails(criteria)
            return web.json_response({
                'success': True,
                'emails': emails
            })
        except Exception as e:
            logger.error(f"Error searching emails: {e}")
            return web.json_response({
                'success': False,
                'error': str(e)
            }, status=500)

    async def handle_get_email(self, request):
        """Handle get email request"""
        try:
            message_id = request.match_info['message_id']
            email_data = self.gmail_service.get_email(message_id)
            return web.json_response({
                'success': True,
                'email': email_data
            })
        except Exception as e:
            logger.error(f"Error getting email: {e}")
            return web.json_response({
                'success': False,
                'error': str(e)
            }, status=500)

    async def handle_list_labels(self, request):
        """Handle list labels request"""
        try:
            labels = self.gmail_service.list_labels()
            return web.json_response({
                'success': True,
                'labels': labels
            })
        except Exception as e:
            logger.error(f"Error listing labels: {e}")
            return web.json_response({
                'success': False,
                'error': str(e)
            }, status=500)

    async def handle_create_label(self, request):
        """Handle create label request"""
        try:
            data = await request.json()
            label_name = data['name']
            label = self.gmail_service.create_label(label_name)
            return web.json_response({
                'success': True,
                'label': label
            })
        except Exception as e:
            logger.error(f"Error creating label: {e}")
            return web.json_response({
                'success': False,
                'error': str(e)
            }, status=500)

    async def handle_get_profile(self, request):
        """Handle get profile request"""
        try:
            profile = self.gmail_service.service.users().getProfile(userId='me').execute()
            return web.json_response({
                'success': True,
                'profile': profile
            })
        except Exception as e:
            logger.error(f"Error getting profile: {e}")
            return web.json_response({
                'success': False,
                'error': str(e)
            }, status=500)

    async def handle_get_approval_requests(self, request):
        """Handle get approval requests"""
        try:
            # Get all pending requests
            pending_requests = [
                asdict(req) for req in self.gmail_service.hitl_manager.approval_requests.values()
                if req.status == 'pending'
            ]
            return web.json_response({
                'success': True,
                'requests': pending_requests
            })
        except Exception as e:
            logger.error(f"Error getting approval requests: {e}")
            return web.json_response({
                'success': False,
                'error': str(e)
            }, status=500)

    async def handle_approve_request(self, request):
        """Handle approve request"""
        try:
            data = await request.json()
            request_id = data['request_id']
            approved_by = data.get('approved_by', 'System')

            success = self.gmail_service.hitl_manager.approve_request(request_id, approved_by)
            if success:
                # If the request was for sending an email, process it now
                req = self.gmail_service.hitl_manager.get_approval_request(request_id)
                if req and req.operation == 'send_email':
                    # Reconstruct and send the email
                    details = req.details
                    draft = EmailDraft(
                        to=details['to'],
                        subject=details['subject'],
                        body=details['body_preview'],  # This would need to be stored properly
                    )
                    # For now, we'll just record the approval
                    logger.info(f"Approved email sending request {request_id}")

            return web.json_response({
                'success': success
            })
        except Exception as e:
            logger.error(f"Error approving request: {e}")
            return web.json_response({
                'success': False,
                'error': str(e)
            }, status=500)

    async def handle_reject_request(self, request):
        """Handle reject request"""
        try:
            data = await request.json()
            request_id = data['request_id']
            rejected_by = data.get('rejected_by', 'System')
            reason = data.get('reason', '')

            success = self.gmail_service.hitl_manager.reject_request(request_id, rejected_by, reason)
            return web.json_response({
                'success': success
            })
        except Exception as e:
            logger.error(f"Error rejecting request: {e}")
            return web.json_response({
                'success': False,
                'error': str(e)
            }, status=500)

    async def start(self):
        """Start the MCP server"""
        # Authenticate with Gmail
        self.gmail_service.authenticate()

        # Start the web server
        runner = web.AppRunner(self.app)
        await runner.setup()

        site = web.TCPSite(
            runner,
            self.config['server']['host'],
            self.config['server']['port']
        )
        await site.start()

        logger.info(f"Email MCP Server started at http://{self.config['server']['host']}:{self.config['server']['port']}")

        # Keep the server running
        try:
            await asyncio.Future()  # Run forever
        except KeyboardInterrupt:
            logger.info("Shutting down server...")
        finally:
            await runner.cleanup()


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Email MCP Server")
    parser.add_argument("--config", default="email_config.json", help="Configuration file path")
    parser.add_argument("--credentials", default="credentials.json", help="Google credentials file path")

    args = parser.parse_args()

    # Update config with command line args if needed
    server = EmailMCPServer(args.config)

    # If credentials arg was provided, update the config
    if args.credentials != "credentials.json":
        server.gmail_service.credentials_path = args.credentials

    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")


if __name__ == "__main__":
    main()