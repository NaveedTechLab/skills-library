#!/usr/bin/env python3
"""
Approval Workflow for Odoo MCP Server

HITL (Human-in-the-Loop) approval workflow for financial operations.
"""

import json
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

import structlog

from .models import ApprovalRequest, ApprovalStatus, OdooConfig

logger = structlog.get_logger()


class OdooApprovalWorkflow:
    """
    Manages HITL approval workflow for Odoo financial operations.

    Operations requiring approval:
    - Create invoice (if amount > threshold)
    - Post invoice (always)
    - Create payment (always)
    """

    def __init__(self, config: OdooConfig = None, db_path: str = "./odoo_approvals.db"):
        self.config = config or OdooConfig()
        self.db_path = Path(db_path)
        self.lock = threading.Lock()
        self.logger = logger.bind(component="OdooApprovalWorkflow")

        # Initialize audit logger if available
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
                CREATE TABLE IF NOT EXISTS approval_requests (
                    id TEXT PRIMARY KEY,
                    operation TEXT NOT NULL,
                    model TEXT NOT NULL,
                    record_id INTEGER,
                    data_json TEXT NOT NULL,
                    amount REAL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'pending',
                    requested_by TEXT NOT NULL,
                    requested_at TIMESTAMP NOT NULL,
                    approved_by TEXT,
                    approved_at TIMESTAMP,
                    rejection_reason TEXT,
                    expires_at TIMESTAMP,
                    context_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_approval_status ON approval_requests(status)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_approval_operation ON approval_requests(operation)
            """)

            conn.commit()

        self.logger.info("Approval database initialized", db_path=str(self.db_path))

    def requires_approval(self, operation: str, amount: float = 0) -> bool:
        """
        Check if an operation requires human approval.

        Args:
            operation: Operation type (create_invoice, post_invoice, create_payment)
            amount: Financial amount involved

        Returns:
            True if approval is required
        """
        # Always require approval for these operations
        if operation in self.config.always_require_approval:
            return True

        # Check threshold for invoice creation
        if operation == "create_invoice" and amount > self.config.invoice_threshold:
            return True

        return False

    def create_approval_request(
        self,
        operation: str,
        model: str = "account.move",
        record_id: int = None,
        data: Dict[str, Any] = None,
        amount: float = 0,
        requested_by: str = "claude",
        context: Dict[str, Any] = None
    ) -> ApprovalRequest:
        """
        Create a new approval request.

        Args:
            operation: Operation type
            model: Odoo model
            record_id: Record ID if updating existing record
            data: Operation data
            amount: Financial amount
            requested_by: Requester identifier
            context: Additional context

        Returns:
            Created ApprovalRequest
        """
        request_id = f"odoo_approval_{uuid4().hex[:12]}"
        now = datetime.now()
        expires_at = now + timedelta(hours=self.config.approval_timeout_hours)

        request = ApprovalRequest(
            id=request_id,
            operation=operation,
            model=model,
            record_id=record_id,
            data=data or {},
            amount=amount,
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
            amount=amount
        )

        return request

    def _save_request(self, request: ApprovalRequest) -> bool:
        """Save approval request to database"""
        try:
            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO approval_requests
                    (id, operation, model, record_id, data_json, amount, status,
                     requested_by, requested_at, approved_by, approved_at,
                     rejection_reason, expires_at, context_json, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    request.id,
                    request.operation,
                    request.model,
                    request.record_id,
                    json.dumps(request.data),
                    request.amount,
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
            self.logger.error("Failed to save approval request", error=str(e))
            return False

    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """Get approval request by ID"""
        try:
            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, operation, model, record_id, data_json, amount, status,
                           requested_by, requested_at, approved_by, approved_at,
                           rejection_reason, expires_at, context_json
                    FROM approval_requests WHERE id = ?
                """, (request_id,))

                row = cursor.fetchone()
                if not row:
                    return None

                return self._row_to_request(row)
        except Exception as e:
            self.logger.error("Failed to get approval request", request_id=request_id, error=str(e))
            return None

    def _row_to_request(self, row: tuple) -> ApprovalRequest:
        """Convert database row to ApprovalRequest"""
        (request_id, operation, model, record_id, data_json, amount, status,
         requested_by, requested_at, approved_by, approved_at,
         rejection_reason, expires_at, context_json) = row

        return ApprovalRequest(
            id=request_id,
            operation=operation,
            model=model,
            record_id=record_id,
            data=json.loads(data_json) if data_json else {},
            amount=amount,
            status=ApprovalStatus(status),
            requested_by=requested_by,
            requested_at=datetime.fromisoformat(requested_at) if requested_at else None,
            approved_by=approved_by,
            approved_at=datetime.fromisoformat(approved_at) if approved_at else None,
            rejection_reason=rejection_reason,
            expires_at=datetime.fromisoformat(expires_at) if expires_at else None,
            context=json.loads(context_json) if context_json else {}
        )

    def get_pending_requests(self, operation: str = None) -> List[ApprovalRequest]:
        """Get all pending approval requests"""
        try:
            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                query = """
                    SELECT id, operation, model, record_id, data_json, amount, status,
                           requested_by, requested_at, approved_by, approved_at,
                           rejection_reason, expires_at, context_json
                    FROM approval_requests
                    WHERE status = 'pending'
                """
                params = []

                if operation:
                    query += " AND operation = ?"
                    params.append(operation)

                query += " ORDER BY requested_at ASC"

                cursor.execute(query, params)

                requests = []
                for row in cursor.fetchall():
                    request = self._row_to_request(row)
                    # Check expiration
                    if request.expires_at and datetime.now() > request.expires_at:
                        self._expire_request(request)
                    else:
                        requests.append(request)

                return requests
        except Exception as e:
            self.logger.error("Failed to get pending requests", error=str(e))
            return []

    def approve_request(self, request_id: str, approved_by: str) -> Optional[ApprovalRequest]:
        """
        Approve an approval request.

        Args:
            request_id: Request to approve
            approved_by: Approver identifier

        Returns:
            Updated ApprovalRequest
        """
        request = self.get_request(request_id)
        if not request:
            self.logger.error("Request not found", request_id=request_id)
            return None

        if request.status != ApprovalStatus.PENDING:
            self.logger.error("Request not pending", request_id=request_id, status=request.status.value)
            return None

        # Check expiration
        if request.expires_at and datetime.now() > request.expires_at:
            self._expire_request(request)
            return None

        request.status = ApprovalStatus.APPROVED
        request.approved_by = approved_by
        request.approved_at = datetime.now()

        self._save_request(request)
        self._move_vault_file(request, "Approved")
        self._log_audit("approval_approved", request)

        self.logger.info("Request approved", request_id=request_id, approved_by=approved_by)
        return request

    def reject_request(
        self,
        request_id: str,
        rejected_by: str,
        reason: str = None
    ) -> Optional[ApprovalRequest]:
        """
        Reject an approval request.

        Args:
            request_id: Request to reject
            rejected_by: Rejector identifier
            reason: Rejection reason

        Returns:
            Updated ApprovalRequest
        """
        request = self.get_request(request_id)
        if not request:
            return None

        if request.status != ApprovalStatus.PENDING:
            return None

        request.status = ApprovalStatus.REJECTED
        request.approved_by = rejected_by  # Reusing field for rejector
        request.approved_at = datetime.now()
        request.rejection_reason = reason

        self._save_request(request)
        self._move_vault_file(request, "Rejected")
        self._log_audit("approval_rejected", request)

        self.logger.info("Request rejected", request_id=request_id, rejected_by=rejected_by)
        return request

    def _expire_request(self, request: ApprovalRequest):
        """Mark a request as expired"""
        request.status = ApprovalStatus.EXPIRED
        self._save_request(request)
        self._move_vault_file(request, "Failed")
        self._log_audit("approval_expired", request)
        self.logger.warning("Request expired", request_id=request.id)

    def is_approved(self, request_id: str) -> bool:
        """Check if a request is approved"""
        request = self.get_request(request_id)
        return request is not None and request.status == ApprovalStatus.APPROVED

    def wait_for_approval(
        self,
        request_id: str,
        timeout_seconds: int = 300,
        check_interval: int = 5
    ) -> Optional[ApprovalRequest]:
        """
        Wait for a request to be approved (blocking).

        Args:
            request_id: Request to wait for
            timeout_seconds: Maximum wait time
            check_interval: Check interval in seconds

        Returns:
            Approved request, or None if timeout/rejected
        """
        import time

        start = datetime.now()
        while (datetime.now() - start).seconds < timeout_seconds:
            request = self.get_request(request_id)
            if not request:
                return None

            if request.status == ApprovalStatus.APPROVED:
                return request
            elif request.status in (ApprovalStatus.REJECTED, ApprovalStatus.EXPIRED):
                return None

            time.sleep(check_interval)

        return None

    def _create_vault_file(self, request: ApprovalRequest):
        """Create approval request file in vault"""
        vault_folder = Path("./vault/Pending_Approval/odoo")
        vault_folder.mkdir(parents=True, exist_ok=True)

        filename = f"{request.id}.md"
        filepath = vault_folder / filename

        content = f"""---
id: {request.id}
operation: {request.operation}
model: {request.model}
amount: {request.amount}
status: {request.status.value}
requested_by: {request.requested_by}
requested_at: {request.requested_at.isoformat() if request.requested_at else 'N/A'}
expires_at: {request.expires_at.isoformat() if request.expires_at else 'N/A'}
---

# Odoo Approval Request: {request.operation}

## Operation Details
- **Type:** {request.operation}
- **Model:** {request.model}
- **Amount:** ${request.amount:,.2f}
- **Record ID:** {request.record_id or 'New record'}

## Request Data
```json
{json.dumps(request.data, indent=2, default=str)}
```

## Context
```json
{json.dumps(request.context, indent=2, default=str)}
```

## Approval Instructions
To approve this request:
1. Review the operation details above
2. Verify the amount and data are correct
3. Run: `approve_odoo_request("{request.id}")`

To reject this request:
1. Run: `reject_odoo_request("{request.id}", reason="your reason")`

**This request expires at:** {request.expires_at.isoformat() if request.expires_at else 'N/A'}
"""

        try:
            filepath.write_text(content, encoding="utf-8")
            self.logger.debug("Vault file created", path=str(filepath))
        except Exception as e:
            self.logger.error("Failed to create vault file", error=str(e))

    def _move_vault_file(self, request: ApprovalRequest, destination: str):
        """Move vault file to destination folder"""
        source = Path(f"./vault/Pending_Approval/odoo/{request.id}.md")
        dest_folder = Path(f"./vault/{destination}/odoo")
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
                    action_type=f"odoo.{action}",
                    target=request.id,
                    approval_status=request.status.value,
                    approver=request.approved_by,
                    result="success",
                    additional_metadata={
                        "operation": request.operation,
                        "amount": request.amount,
                        "model": request.model
                    }
                )
            except Exception as e:
                self.logger.warning("Failed to log audit", error=str(e))


# Convenience functions
def create_odoo_approval_workflow(config: OdooConfig = None) -> OdooApprovalWorkflow:
    """Create approval workflow instance"""
    return OdooApprovalWorkflow(config)
