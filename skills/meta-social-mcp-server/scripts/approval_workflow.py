#!/usr/bin/env python3
"""
Approval Workflow for Meta Social MCP Server

HITL approval workflow for Facebook/Instagram content posting.
"""

import json
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

import structlog

from .models import ApprovalRequest, ApprovalStatus, MetaConfig

logger = structlog.get_logger()


class MetaSocialApprovalWorkflow:
    """
    Manages HITL approval workflow for Meta social media operations.

    All posting operations require approval:
    - Facebook posts
    - Facebook scheduled posts
    - Instagram posts
    - Instagram Reels
    """

    def __init__(self, config: MetaConfig = None, db_path: str = "./meta_social.db"):
        self.config = config or MetaConfig()
        self.db_path = Path(db_path)
        self.lock = threading.Lock()
        self.logger = logger.bind(component="MetaSocialApprovalWorkflow")

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

            # Content table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS meta_content (
                    id TEXT PRIMARY KEY,
                    platform TEXT NOT NULL,
                    content_type TEXT NOT NULL,
                    account_id TEXT,
                    data_json TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'draft',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Approvals table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS meta_approvals (
                    id TEXT PRIMARY KEY,
                    platform TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    content_type TEXT NOT NULL,
                    data_json TEXT NOT NULL,
                    preview_url TEXT,
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
                CREATE INDEX IF NOT EXISTS idx_meta_approval_status ON meta_approvals(status)
            """)

            conn.commit()

        self.logger.info("Meta Social database initialized")

    def requires_approval(self, operation: str) -> bool:
        """Check if operation requires approval (always true for posting)"""
        posting_operations = [
            "create_post", "schedule_post", "create_reel",
            "facebook_create_post", "facebook_schedule_post",
            "instagram_create_post", "instagram_create_reel"
        ]
        return operation in posting_operations

    def create_approval_request(
        self,
        platform: str,
        operation: str,
        content_type: str = "post",
        data: Dict[str, Any] = None,
        preview_url: str = None,
        requested_by: str = "claude",
        context: Dict[str, Any] = None
    ) -> ApprovalRequest:
        """
        Create a new approval request.

        Args:
            platform: "facebook" or "instagram"
            operation: Operation type
            content_type: post, reel, story
            data: Content data
            preview_url: Preview URL
            requested_by: Requester
            context: Additional context

        Returns:
            ApprovalRequest
        """
        request_id = f"meta_approval_{uuid4().hex[:12]}"
        now = datetime.now()
        expires_at = now + timedelta(hours=self.config.approval_timeout_hours)

        request = ApprovalRequest(
            id=request_id,
            platform=platform,
            operation=operation,
            content_type=content_type,
            data=data or {},
            preview_url=preview_url,
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
            platform=platform,
            operation=operation
        )

        return request

    def _save_request(self, request: ApprovalRequest) -> bool:
        """Save request to database"""
        try:
            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO meta_approvals
                    (id, platform, operation, content_type, data_json, preview_url,
                     status, requested_by, requested_at, approved_by, approved_at,
                     rejection_reason, expires_at, context_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    request.id,
                    request.platform,
                    request.operation,
                    request.content_type,
                    json.dumps(request.data),
                    request.preview_url,
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
                    SELECT id, platform, operation, content_type, data_json, preview_url,
                           status, requested_by, requested_at, approved_by, approved_at,
                           rejection_reason, expires_at, context_json
                    FROM meta_approvals WHERE id = ?
                """, (request_id,))

                row = cursor.fetchone()
                if not row:
                    return None

                return self._row_to_request(row)
        except Exception as e:
            self.logger.error("Failed to get request", request_id=request_id, error=str(e))
            return None

    def _row_to_request(self, row: tuple) -> ApprovalRequest:
        """Convert row to ApprovalRequest"""
        (request_id, platform, operation, content_type, data_json, preview_url,
         status, requested_by, requested_at, approved_by, approved_at,
         rejection_reason, expires_at, context_json) = row

        return ApprovalRequest(
            id=request_id,
            platform=platform,
            operation=operation,
            content_type=content_type,
            data=json.loads(data_json) if data_json else {},
            preview_url=preview_url,
            status=ApprovalStatus(status),
            requested_by=requested_by,
            requested_at=datetime.fromisoformat(requested_at) if requested_at else None,
            approved_by=approved_by,
            approved_at=datetime.fromisoformat(approved_at) if approved_at else None,
            rejection_reason=rejection_reason,
            expires_at=datetime.fromisoformat(expires_at) if expires_at else None,
            context=json.loads(context_json) if context_json else {}
        )

    def get_pending_requests(self, platform: str = None) -> List[ApprovalRequest]:
        """Get pending requests"""
        try:
            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                query = """
                    SELECT id, platform, operation, content_type, data_json, preview_url,
                           status, requested_by, requested_at, approved_by, approved_at,
                           rejection_reason, expires_at, context_json
                    FROM meta_approvals
                    WHERE status = 'pending'
                """
                params = []

                if platform:
                    query += " AND platform = ?"
                    params.append(platform)

                query += " ORDER BY requested_at ASC"

                cursor.execute(query, params)

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
        vault_folder = Path(f"./vault/Pending_Approval/meta/{request.platform}")
        vault_folder.mkdir(parents=True, exist_ok=True)

        filepath = vault_folder / f"{request.id}.md"

        # Format content preview
        content_preview = ""
        if request.platform == "facebook":
            content_preview = f"""
**Message:** {request.data.get('message', 'N/A')}
**Link:** {request.data.get('link', 'N/A')}
**Media:** {len(request.data.get('media_urls', []))} attachment(s)
"""
        elif request.platform == "instagram":
            content_preview = f"""
**Caption:** {request.data.get('caption', 'N/A')}
**Media Type:** {request.data.get('media_type', 'N/A')}
**Media URL:** {request.data.get('media_url', 'N/A')}
"""

        content = f"""---
id: {request.id}
platform: {request.platform}
operation: {request.operation}
content_type: {request.content_type}
status: {request.status.value}
requested_by: {request.requested_by}
requested_at: {request.requested_at.isoformat() if request.requested_at else 'N/A'}
expires_at: {request.expires_at.isoformat() if request.expires_at else 'N/A'}
---

# {request.platform.capitalize()} Content Approval: {request.operation}

## Content Preview
{content_preview}

## Full Data
```json
{json.dumps(request.data, indent=2, default=str)}
```

## Approval Instructions

**To approve:**
```
approve_meta_request("{request.id}")
```

**To reject:**
```
reject_meta_request("{request.id}", reason="your reason")
```

**Expires at:** {request.expires_at.isoformat() if request.expires_at else 'N/A'}
"""

        try:
            filepath.write_text(content, encoding="utf-8")
        except Exception as e:
            self.logger.error("Failed to create vault file", error=str(e))

    def _move_vault_file(self, request: ApprovalRequest, destination: str):
        """Move vault file to destination"""
        source = Path(f"./vault/Pending_Approval/meta/{request.platform}/{request.id}.md")
        dest_folder = Path(f"./vault/{destination}/meta/{request.platform}")
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
                    action_type=f"meta_social.{action}",
                    target=request.id,
                    approval_status=request.status.value,
                    approver=request.approved_by,
                    result="success",
                    additional_metadata={
                        "platform": request.platform,
                        "operation": request.operation,
                        "content_type": request.content_type
                    }
                )
            except Exception as e:
                self.logger.warning("Failed to log audit", error=str(e))
