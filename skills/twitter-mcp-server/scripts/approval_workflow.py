#!/usr/bin/env python3
"""
Approval Workflow for Twitter MCP Server

HITL approval workflow for tweet operations.
"""

import json
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

import structlog

from .models import ApprovalRequest, ApprovalStatus, TweetType, TwitterConfig

logger = structlog.get_logger()


class TwitterApprovalWorkflow:
    """
    Manages HITL approval workflow for Twitter operations.

    All tweet operations require approval:
    - Create tweet
    - Create thread
    - Delete tweet
    """

    def __init__(self, config: TwitterConfig = None, db_path: str = "./twitter_approvals.db"):
        self.config = config or TwitterConfig()
        self.db_path = Path(db_path)
        self.lock = threading.Lock()
        self.logger = logger.bind(component="TwitterApprovalWorkflow")

        self._audit_logger = None
        self._init_audit_logger()
        self._init_db()

    def _init_audit_logger(self):
        """Initialize audit logger integration"""
        try:
            from phase_3.audit_logger import get_global_audit_logger
            self._audit_logger = get_global_audit_logger()
        except ImportError:
            self.logger.warning("Audit logger not available")

    def _init_db(self):
        """Initialize database tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS twitter_approvals (
                    id TEXT PRIMARY KEY,
                    operation TEXT NOT NULL,
                    tweet_type TEXT NOT NULL,
                    data_json TEXT NOT NULL,
                    character_count INTEGER DEFAULT 0,
                    media_count INTEGER DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'pending',
                    requested_by TEXT NOT NULL,
                    requested_at TIMESTAMP NOT NULL,
                    approved_by TEXT,
                    approved_at TIMESTAMP,
                    rejection_reason TEXT,
                    expires_at TIMESTAMP,
                    context_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_twitter_approval_status ON twitter_approvals(status)
            """)

            conn.commit()

        self.logger.info("Twitter approval database initialized")

    def requires_approval(self, operation: str) -> bool:
        """Check if operation requires approval"""
        if operation == "create_tweet" and self.config.require_approval_for_tweets:
            return True
        if operation == "create_thread" and self.config.require_approval_for_threads:
            return True
        if operation == "delete_tweet" and self.config.require_approval_for_delete:
            return True
        return False

    def create_approval_request(
        self,
        operation: str,
        tweet_type: TweetType = TweetType.TWEET,
        data: Dict[str, Any] = None,
        character_count: int = 0,
        media_count: int = 0,
        requested_by: str = "claude",
        context: Dict[str, Any] = None
    ) -> ApprovalRequest:
        """Create a new approval request"""
        request_id = f"twitter_approval_{uuid4().hex[:12]}"
        now = datetime.now()
        expires_at = now + timedelta(hours=self.config.approval_timeout_hours)

        request = ApprovalRequest(
            id=request_id,
            operation=operation,
            tweet_type=tweet_type,
            data=data or {},
            character_count=character_count,
            media_count=media_count,
            status=ApprovalStatus.PENDING,
            requested_by=requested_by,
            requested_at=now,
            expires_at=expires_at,
            context=context or {}
        )

        self._save_request(request)
        self._create_vault_file(request)
        self._log_audit("approval_requested", request)

        self.logger.info(
            "Approval request created",
            request_id=request_id,
            operation=operation,
            character_count=character_count
        )

        return request

    def _save_request(self, request: ApprovalRequest) -> bool:
        """Save request to database"""
        try:
            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO twitter_approvals
                    (id, operation, tweet_type, data_json, character_count, media_count,
                     status, requested_by, requested_at, approved_by, approved_at,
                     rejection_reason, expires_at, context_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    request.id,
                    request.operation,
                    request.tweet_type.value,
                    json.dumps(request.data),
                    request.character_count,
                    request.media_count,
                    request.status.value,
                    request.requested_by,
                    request.requested_at.isoformat() if request.requested_at else None,
                    request.approved_by,
                    request.approved_at.isoformat() if request.approved_at else None,
                    request.rejection_reason,
                    request.expires_at.isoformat() if request.expires_at else None,
                    json.dumps(request.context)
                ))
                conn.commit()
                return True
        except Exception as e:
            self.logger.error("Failed to save request", error=str(e))
            return False

    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """Get request by ID"""
        try:
            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, operation, tweet_type, data_json, character_count, media_count,
                           status, requested_by, requested_at, approved_by, approved_at,
                           rejection_reason, expires_at, context_json
                    FROM twitter_approvals WHERE id = ?
                """, (request_id,))

                row = cursor.fetchone()
                if not row:
                    return None

                return self._row_to_request(row)
        except Exception as e:
            self.logger.error("Failed to get request", error=str(e))
            return None

    def _row_to_request(self, row: tuple) -> ApprovalRequest:
        """Convert row to ApprovalRequest"""
        (request_id, operation, tweet_type, data_json, character_count, media_count,
         status, requested_by, requested_at, approved_by, approved_at,
         rejection_reason, expires_at, context_json) = row

        return ApprovalRequest(
            id=request_id,
            operation=operation,
            tweet_type=TweetType(tweet_type),
            data=json.loads(data_json) if data_json else {},
            character_count=character_count,
            media_count=media_count,
            status=ApprovalStatus(status),
            requested_by=requested_by,
            requested_at=datetime.fromisoformat(requested_at) if requested_at else None,
            approved_by=approved_by,
            approved_at=datetime.fromisoformat(approved_at) if approved_at else None,
            rejection_reason=rejection_reason,
            expires_at=datetime.fromisoformat(expires_at) if expires_at else None,
            context=json.loads(context_json) if context_json else {}
        )

    def get_pending_requests(self) -> List[ApprovalRequest]:
        """Get pending requests"""
        try:
            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, operation, tweet_type, data_json, character_count, media_count,
                           status, requested_by, requested_at, approved_by, approved_at,
                           rejection_reason, expires_at, context_json
                    FROM twitter_approvals
                    WHERE status = 'pending'
                    ORDER BY requested_at ASC
                """)

                requests = []
                for row in cursor.fetchall():
                    request = self._row_to_request(row)
                    if request.expires_at and datetime.now() > request.expires_at:
                        self._expire_request(request)
                    else:
                        requests.append(request)

                return requests
        except Exception as e:
            self.logger.error("Failed to get pending requests", error=str(e))
            return []

    def approve_request(self, request_id: str, approved_by: str) -> Optional[ApprovalRequest]:
        """Approve a request"""
        request = self.get_request(request_id)
        if not request or request.status != ApprovalStatus.PENDING:
            return None

        if request.expires_at and datetime.now() > request.expires_at:
            self._expire_request(request)
            return None

        request.status = ApprovalStatus.APPROVED
        request.approved_by = approved_by
        request.approved_at = datetime.now()

        self._save_request(request)
        self._move_vault_file(request, "Approved")
        self._log_audit("approval_approved", request)

        self.logger.info("Request approved", request_id=request_id)
        return request

    def reject_request(
        self,
        request_id: str,
        rejected_by: str,
        reason: str = None
    ) -> Optional[ApprovalRequest]:
        """Reject a request"""
        request = self.get_request(request_id)
        if not request or request.status != ApprovalStatus.PENDING:
            return None

        request.status = ApprovalStatus.REJECTED
        request.approved_by = rejected_by
        request.approved_at = datetime.now()
        request.rejection_reason = reason

        self._save_request(request)
        self._move_vault_file(request, "Rejected")
        self._log_audit("approval_rejected", request)

        self.logger.info("Request rejected", request_id=request_id)
        return request

    def _expire_request(self, request: ApprovalRequest):
        """Mark request as expired"""
        request.status = ApprovalStatus.EXPIRED
        self._save_request(request)
        self._move_vault_file(request, "Failed")
        self._log_audit("approval_expired", request)

    def is_approved(self, request_id: str) -> bool:
        """Check if request is approved"""
        request = self.get_request(request_id)
        return request is not None and request.status == ApprovalStatus.APPROVED

    def _create_vault_file(self, request: ApprovalRequest):
        """Create vault file for approval request"""
        vault_folder = Path("./vault/Pending_Approval/twitter")
        vault_folder.mkdir(parents=True, exist_ok=True)

        filepath = vault_folder / f"{request.id}.md"

        # Format content preview
        if request.operation == "create_tweet":
            content_preview = f"""
**Tweet Text:** {request.data.get('text', 'N/A')}
**Character Count:** {request.character_count}/280
**Media Attachments:** {request.media_count}
**Reply To:** {request.data.get('reply_to', 'N/A')}
"""
        elif request.operation == "create_thread":
            tweets = request.data.get("tweets", [])
            content_preview = f"""
**Thread Length:** {len(tweets)} tweets
**Total Characters:** {request.character_count}

**Tweets:**
"""
            for i, tweet in enumerate(tweets, 1):
                text = tweet.get("text", "")[:100]
                content_preview += f"\n{i}. {text}{'...' if len(tweet.get('text', '')) > 100 else ''}"

        elif request.operation == "delete_tweet":
            content_preview = f"""
**Tweet ID to Delete:** {request.data.get('tweet_id', 'N/A')}
"""
        else:
            content_preview = json.dumps(request.data, indent=2)

        content = f"""---
id: {request.id}
operation: {request.operation}
tweet_type: {request.tweet_type.value}
character_count: {request.character_count}
media_count: {request.media_count}
status: {request.status.value}
requested_at: {request.requested_at.isoformat() if request.requested_at else 'N/A'}
expires_at: {request.expires_at.isoformat() if request.expires_at else 'N/A'}
---

# Twitter Approval: {request.operation}

## Content Preview
{content_preview}

## Full Data
```json
{json.dumps(request.data, indent=2, default=str)}
```

## Approval Instructions

**To approve:**
```
approve_twitter_request("{request.id}")
```

**To reject:**
```
reject_twitter_request("{request.id}", reason="your reason")
```

**Expires at:** {request.expires_at.isoformat() if request.expires_at else 'N/A'}
"""

        try:
            filepath.write_text(content, encoding="utf-8")
        except Exception as e:
            self.logger.error("Failed to create vault file", error=str(e))

    def _move_vault_file(self, request: ApprovalRequest, destination: str):
        """Move vault file to destination"""
        source = Path(f"./vault/Pending_Approval/twitter/{request.id}.md")
        dest_folder = Path(f"./vault/{destination}/twitter")
        dest_folder.mkdir(parents=True, exist_ok=True)

        if source.exists():
            try:
                source.rename(dest_folder / source.name)
            except Exception as e:
                self.logger.warning("Failed to move vault file", error=str(e))

    def _log_audit(self, action: str, request: ApprovalRequest):
        """Log to audit system"""
        if self._audit_logger:
            try:
                self._audit_logger.log_action(
                    action_type=f"twitter.{action}",
                    target=request.id,
                    approval_status=request.status.value,
                    approver=request.approved_by,
                    result="success",
                    additional_metadata={
                        "operation": request.operation,
                        "character_count": request.character_count,
                        "media_count": request.media_count
                    }
                )
            except Exception as e:
                self.logger.warning("Failed to log audit", error=str(e))
