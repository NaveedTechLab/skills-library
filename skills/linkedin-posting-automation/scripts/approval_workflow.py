#!/usr/bin/env python3
"""
Approval Workflow System for LinkedIn Posting Automation

Implements approval-gated posting workflow with multi-level approval processes
"""

import asyncio
import datetime
import enum
import json
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

import structlog

from linkedin_api_integration import LinkedInPost, PostStatus

logger = structlog.get_logger()


class ApprovalStatus(Enum):
    """Status of an approval request"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class ApprovalLevel(Enum):
    """Levels of approval required"""
    EDITORIAL = "editorial"
    COMPLIANCE = "compliance"
    LEGAL = "legal"
    EXECUTIVE = "executive"


class UserRole(Enum):
    """Roles in the approval system"""
    CONTENT_CREATOR = "content_creator"
    CONTENT_EDITOR = "content_editor"
    COMPLIANCE_OFFICER = "compliance_officer"
    LEGAL_REVIEWER = "legal_reviewer"
    EXECUTIVE_APPROVER = "executive_approver"
    ADMIN = "admin"


@dataclass
class ApprovalStep:
    """A single step in the approval workflow"""
    id: str
    level: ApprovalLevel
    required: bool
    approvers: List[str]  # User IDs who can approve this step
    completed: bool = False
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    feedback: Optional[str] = None


@dataclass
class ApprovalRequest:
    """An approval request for a LinkedIn post"""
    id: str
    post_id: str
    requested_by: str
    requested_at: datetime
    required_levels: List[ApprovalLevel]
    steps: List[ApprovalStep]
    status: ApprovalStatus = ApprovalStatus.PENDING
    approved_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    expiration_date: Optional[datetime] = None


@dataclass
class ApprovalHistoryEntry:
    """History entry for approval actions"""
    id: str
    approval_request_id: str
    action: str  # approve, reject, cancel, etc.
    actor: str  # User who performed the action
    timestamp: datetime
    feedback: Optional[str] = None


class ApprovalStorageInterface:
    """Interface for approval storage"""

    def save_approval_request(self, request: ApprovalRequest) -> bool:
        """Save an approval request"""
        raise NotImplementedError

    def get_approval_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """Get an approval request by ID"""
        raise NotImplementedError

    def get_approval_requests_by_post(self, post_id: str) -> List[ApprovalRequest]:
        """Get all approval requests for a post"""
        raise NotImplementedError

    def get_pending_approvals(self, user_id: str, role: UserRole) -> List[ApprovalRequest]:
        """Get pending approvals for a user"""
        raise NotImplementedError

    def save_approval_history(self, entry: ApprovalHistoryEntry) -> bool:
        """Save an approval history entry"""
        raise NotImplementedError

    def get_approval_history(self, request_id: str) -> List[ApprovalHistoryEntry]:
        """Get approval history for a request"""
        raise NotImplementedError


class SQLiteApprovalStorage(ApprovalStorageInterface):
    """SQLite-based approval storage implementation"""

    def __init__(self, db_path: str = "./linkedin_approval.db"):
        self.db_path = Path(db_path)
        self.lock = threading.Lock()
        self.init_db()

    def init_db(self):
        """Initialize the database tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Approval requests table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS approval_requests (
                    id TEXT PRIMARY KEY,
                    post_id TEXT NOT NULL,
                    requested_by TEXT NOT NULL,
                    requested_at TIMESTAMP NOT NULL,
                    required_levels_json TEXT NOT NULL,
                    steps_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    approved_at TIMESTAMP,
                    rejected_at TIMESTAMP,
                    rejection_reason TEXT,
                    expiration_date TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Approval history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS approval_history (
                    id TEXT PRIMARY KEY,
                    approval_request_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    feedback TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (approval_request_id) REFERENCES approval_requests (id)
                )
            """)

            conn.commit()

    def save_approval_request(self, request: ApprovalRequest) -> bool:
        """Save an approval request to the database"""
        try:
            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT OR REPLACE INTO approval_requests
                    (id, post_id, requested_by, requested_at, required_levels_json,
                     steps_json, status, approved_at, rejected_at, rejection_reason, expiration_date, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    request.id, request.post_id, request.requested_by,
                    request.requested_at.isoformat() if isinstance(request.requested_at, datetime) else request.requested_at,
                    json.dumps([level.value for level in request.required_levels]),
                    json.dumps([{
                        'id': step.id,
                        'level': step.level.value,
                        'required': step.required,
                        'approvers': step.approvers,
                        'completed': step.completed,
                        'approved_by': step.approved_by,
                        'approved_at': step.approved_at.isoformat() if step.approved_at else None,
                        'feedback': step.feedback
                    } for step in request.steps]),
                    request.status.value,
                    request.approved_at.isoformat() if request.approved_at else None,
                    request.rejected_at.isoformat() if request.rejected_at else None,
                    request.rejection_reason,
                    request.expiration_date.isoformat() if request.expiration_date else None
                ))

                conn.commit()
                return True
        except Exception as e:
            logger.error("Failed to save approval request", request_id=request.id, error=str(e))
            return False

    def get_approval_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """Get an approval request by ID"""
        try:
            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, post_id, requested_by, requested_at, required_levels_json,
                           steps_json, status, approved_at, rejected_at, rejection_reason, expiration_date
                    FROM approval_requests WHERE id = ?
                """, (request_id,))

                row = cursor.fetchone()
                if not row:
                    return None

                (id, post_id, requested_by, requested_at_str, required_levels_json,
                 steps_json, status_str, approved_at_str, rejected_at_str, rejection_reason, expiration_date_str) = row

                # Parse datetime strings
                requested_at = datetime.fromisoformat(requested_at_str) if requested_at_str else None
                approved_at = datetime.fromisoformat(approved_at_str) if approved_at_str else None
                rejected_at = datetime.fromisoformat(rejected_at_str) if rejected_at_str else None
                expiration_date = datetime.fromisoformat(expiration_date_str) if expiration_date_str else None

                # Parse required levels
                required_levels = [ApprovalLevel(level) for level in json.loads(required_levels_json)]

                # Parse steps
                steps_data = json.loads(steps_json)
                steps = []
                for step_data in steps_data:
                    step = ApprovalStep(
                        id=step_data['id'],
                        level=ApprovalLevel(step_data['level']),
                        required=step_data['required'],
                        approvers=step_data['approvers'],
                        completed=step_data['completed'],
                        approved_by=step_data.get('approved_by'),
                        approved_at=datetime.fromisoformat(step_data['approved_at']) if step_data.get('approved_at') else None,
                        feedback=step_data.get('feedback')
                    )
                    steps.append(step)

                return ApprovalRequest(
                    id=id,
                    post_id=post_id,
                    requested_by=requested_by,
                    requested_at=requested_at,
                    required_levels=required_levels,
                    steps=steps,
                    status=ApprovalStatus(status_str),
                    approved_at=approved_at,
                    rejected_at=rejected_at,
                    rejection_reason=rejection_reason,
                    expiration_date=expiration_date
                )
        except Exception as e:
            logger.error("Failed to get approval request", request_id=request_id, error=str(e))
            return None

    def get_approval_requests_by_post(self, post_id: str) -> List[ApprovalRequest]:
        """Get all approval requests for a post"""
        try:
            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, post_id, requested_by, requested_at, required_levels_json,
                           steps_json, status, approved_at, rejected_at, rejection_reason, expiration_date
                    FROM approval_requests WHERE post_id = ?
                    ORDER BY requested_at DESC
                """, (post_id,))

                requests = []
                for row in cursor.fetchall():
                    (id, post_id, requested_by, requested_at_str, required_levels_json,
                     steps_json, status_str, approved_at_str, rejected_at_str, rejection_reason, expiration_date_str) = row

                    # Parse datetime strings
                    requested_at = datetime.fromisoformat(requested_at_str) if requested_at_str else None
                    approved_at = datetime.fromisoformat(approved_at_str) if approved_at_str else None
                    rejected_at = datetime.fromisoformat(rejected_at_str) if rejected_at_str else None
                    expiration_date = datetime.fromisoformat(expiration_date_str) if expiration_date_str else None

                    # Parse required levels
                    required_levels = [ApprovalLevel(level) for level in json.loads(required_levels_json)]

                    # Parse steps
                    steps_data = json.loads(steps_json)
                    steps = []
                    for step_data in steps_data:
                        step = ApprovalStep(
                            id=step_data['id'],
                            level=ApprovalLevel(step_data['level']),
                            required=step_data['required'],
                            approvers=step_data['approvers'],
                            completed=step_data['completed'],
                            approved_by=step_data.get('approved_by'),
                            approved_at=datetime.fromisoformat(step_data['approved_at']) if step_data.get('approved_at') else None,
                            feedback=step_data.get('feedback')
                        )
                        steps.append(step)

                    request = ApprovalRequest(
                        id=id,
                        post_id=post_id,
                        requested_by=requested_by,
                        requested_at=requested_at,
                        required_levels=required_levels,
                        steps=steps,
                        status=ApprovalStatus(status_str),
                        approved_at=approved_at,
                        rejected_at=rejected_at,
                        rejection_reason=rejection_reason,
                        expiration_date=expiration_date
                    )
                    requests.append(request)

                return requests
        except Exception as e:
            logger.error("Failed to get approval requests by post", post_id=post_id, error=str(e))
            return []

    def get_pending_approvals(self, user_id: str, role: UserRole) -> List[ApprovalRequest]:
        """Get pending approvals for a user"""
        try:
            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, post_id, requested_by, requested_at, required_levels_json,
                           steps_json, status, approved_at, rejected_at, rejection_reason, expiration_date
                    FROM approval_requests
                    WHERE status = 'pending'
                    ORDER BY requested_at ASC
                """)

                requests = []
                for row in cursor.fetchall():
                    (id, post_id, requested_by, requested_at_str, required_levels_json,
                     steps_json, status_str, approved_at_str, rejected_at_str, rejection_reason, expiration_date_str) = row

                    # Parse datetime strings
                    requested_at = datetime.fromisoformat(requested_at_str) if requested_at_str else None
                    approved_at = datetime.fromisoformat(approved_at_str) if approved_at_str else None
                    rejected_at = datetime.fromisoformat(rejected_at_str) if rejected_at_str else None
                    expiration_date = datetime.fromisoformat(expiration_date_str) if expiration_date_str else None

                    # Parse required levels
                    required_levels = [ApprovalLevel(level) for level in json.loads(required_levels_json)]

                    # Parse steps
                    steps_data = json.loads(steps_json)
                    steps = []
                    for step_data in steps_data:
                        step = ApprovalStep(
                            id=step_data['id'],
                            level=ApprovalLevel(step_data['level']),
                            required=step_data['required'],
                            approvers=step_data['approvers'],
                            completed=step_data['completed'],
                            approved_by=step_data.get('approved_by'),
                            approved_at=datetime.fromisoformat(step_data['approved_at']) if step_data.get('approved_at') else None,
                            feedback=step_data.get('feedback')
                        )
                        steps.append(step)

                    # Check if this user is eligible to approve any of the steps
                    eligible = False
                    for step in steps:
                        if not step.completed and user_id in step.approvers:
                            eligible = True
                            break

                    if eligible:
                        request = ApprovalRequest(
                            id=id,
                            post_id=post_id,
                            requested_by=requested_by,
                            requested_at=requested_at,
                            required_levels=required_levels,
                            steps=steps,
                            status=ApprovalStatus(status_str),
                            approved_at=approved_at,
                            rejected_at=rejected_at,
                            rejection_reason=rejection_reason,
                            expiration_date=expiration_date
                        )
                        requests.append(request)

                return requests
        except Exception as e:
            logger.error("Failed to get pending approvals", user_id=user_id, error=str(e))
            return []

    def save_approval_history(self, entry: ApprovalHistoryEntry) -> bool:
        """Save an approval history entry to the database"""
        try:
            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT INTO approval_history
                    (id, approval_request_id, action, actor, timestamp, feedback)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    entry.id, entry.approval_request_id, entry.action, entry.actor,
                    entry.timestamp.isoformat() if isinstance(entry.timestamp, datetime) else entry.timestamp,
                    entry.feedback
                ))

                conn.commit()
                return True
        except Exception as e:
            logger.error("Failed to save approval history", entry_id=entry.id, error=str(e))
            return False

    def get_approval_history(self, request_id: str) -> List[ApprovalHistoryEntry]:
        """Get approval history for a request"""
        try:
            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, approval_request_id, action, actor, timestamp, feedback
                    FROM approval_history
                    WHERE approval_request_id = ?
                    ORDER BY timestamp ASC
                """, (request_id,))

                entries = []
                for row in cursor.fetchall():
                    (id, approval_request_id, action, actor, timestamp_str, feedback) = row
                    timestamp = datetime.fromisoformat(timestamp_str) if timestamp_str else None

                    entry = ApprovalHistoryEntry(
                        id=id,
                        approval_request_id=approval_request_id,
                        action=action,
                        actor=actor,
                        timestamp=timestamp,
                        feedback=feedback
                    )
                    entries.append(entry)

                return entries
        except Exception as e:
            logger.error("Failed to get approval history", request_id=request_id, error=str(e))
            return []


class ApprovalWorkflowEngine:
    """Main approval workflow engine"""

    def __init__(self, storage: ApprovalStorageInterface = None):
        self.storage = storage or SQLiteApprovalStorage()
        self.logger = logger.bind(component="ApprovalWorkflowEngine")

    def create_approval_request(self,
                             post_id: str,
                             requested_by: str,
                             required_levels: List[ApprovalLevel],
                             approvers_by_level: Dict[ApprovalLevel, List[str]],
                             expiration_days: int = 7) -> Optional[ApprovalRequest]:
        """Create a new approval request"""
        request_id = f"approval_{uuid4().hex[:8]}"
        requested_at = datetime.now()
        expiration_date = requested_at + timedelta(days=expiration_days)

        # Create approval steps based on required levels
        steps = []
        for level in required_levels:
            approvers = approvers_by_level.get(level, [])
            step = ApprovalStep(
                id=f"step_{uuid4().hex[:6]}",
                level=level,
                required=True,  # For now, all required
                approvers=approvers
            )
            steps.append(step)

        approval_request = ApprovalRequest(
            id=request_id,
            post_id=post_id,
            requested_by=requested_by,
            requested_at=requested_at,
            required_levels=required_levels,
            steps=steps,
            status=ApprovalStatus.PENDING,
            expiration_date=expiration_date
        )

        # Save to storage
        if self.storage.save_approval_request(approval_request):
            # Log to history
            history_entry = ApprovalHistoryEntry(
                id=f"hist_{uuid4().hex[:8]}",
                approval_request_id=request_id,
                action="requested",
                actor=requested_by,
                timestamp=requested_at
            )
            self.storage.save_approval_history(history_entry)

            self.logger.info("Approval request created", request_id=request_id, post_id=post_id)
            return approval_request
        else:
            self.logger.error("Failed to create approval request", post_id=post_id)
            return None

    def submit_approval_step(self,
                           request_id: str,
                           user_id: str,
                           step_id: str,
                           action: str,  # 'approve' or 'reject'
                           feedback: str = "") -> bool:
        """Submit an approval for a specific step"""
        request = self.storage.get_approval_request(request_id)
        if not request:
            self.logger.error("Approval request not found", request_id=request_id)
            return False

        if request.status != ApprovalStatus.PENDING:
            self.logger.error("Cannot approve completed request", request_id=request_id, status=request.status.value)
            return False

        # Find the step
        step = None
        for s in request.steps:
            if s.id == step_id:
                step = s
                break

        if not step:
            self.logger.error("Approval step not found", request_id=request_id, step_id=step_id)
            return False

        if step.completed:
            self.logger.error("Step already completed", request_id=request_id, step_id=step_id)
            return False

        # Check if user is authorized to approve this step
        if user_id not in step.approvers:
            self.logger.error("User not authorized to approve step", request_id=request_id, step_id=step_id, user_id=user_id)
            return False

        # Update step
        step.completed = True
        step.approved_by = user_id
        step.approved_at = datetime.now()
        step.feedback = feedback

        # Update request status based on step outcome
        if action.lower() == 'reject':
            request.status = ApprovalStatus.REJECTED
            request.rejected_at = datetime.now()
            request.rejection_reason = feedback or f"Rejected by {user_id}"
        elif action.lower() == 'approve':
            # Check if all required steps are completed
            all_required_completed = True
            for s in request.steps:
                if s.required and not s.completed:
                    all_required_completed = False
                    break

            if all_required_completed:
                request.status = ApprovalStatus.APPROVED
                request.approved_at = datetime.now()
        else:
            self.logger.error("Invalid approval action", action=action)
            return False

        # Save updated request
        if not self.storage.save_approval_request(request):
            self.logger.error("Failed to update approval request", request_id=request_id)
            return False

        # Log to history
        history_entry = ApprovalHistoryEntry(
            id=f"hist_{uuid4().hex[:8]}",
            approval_request_id=request_id,
            action=action.lower(),
            actor=user_id,
            timestamp=datetime.now(),
            feedback=feedback
        )
        self.storage.save_approval_history(history_entry)

        self.logger.info(f"Approval step {action.lower()}d", request_id=request_id, step_id=step_id, user_id=user_id)
        return True

    def approve_post_submission(self, request_id: str, approver_id: str, feedback: str = "") -> bool:
        """Approve a post submission (all levels)"""
        return self.submit_approval_step(request_id, approver_id, "", "approve", feedback)

    def reject_post_submission(self, request_id: str, approver_id: str, reason: str = "") -> bool:
        """Reject a post submission (any level)"""
        # Reject the first incomplete step
        request = self.storage.get_approval_request(request_id)
        if not request:
            return False

        for step in request.steps:
            if not step.completed:
                return self.submit_approval_step(request_id, approver_id, step.id, "reject", reason)

        # If all steps are completed but we still want to reject, mark the whole request as rejected
        request.status = ApprovalStatus.REJECTED
        request.rejected_at = datetime.now()
        request.rejection_reason = reason or f"Rejected by {approver_id}"

        if not self.storage.save_approval_request(request):
            return False

        # Log to history
        history_entry = ApprovalHistoryEntry(
            id=f"hist_{uuid4().hex[:8]}",
            approval_request_id=request_id,
            action="rejected",
            actor=approver_id,
            timestamp=datetime.now(),
            feedback=reason
        )
        self.storage.save_approval_history(history_entry)

        return True

    def get_pending_approvals_for_user(self, user_id: str, role: UserRole) -> List[ApprovalRequest]:
        """Get pending approvals for a specific user"""
        return self.storage.get_pending_approvals(user_id, role)

    def get_approval_history(self, request_id: str) -> List[ApprovalHistoryEntry]:
        """Get approval history for a request"""
        return self.storage.get_approval_history(request_id)

    def cancel_approval_request(self, request_id: str, canceller_id: str) -> bool:
        """Cancel an approval request"""
        request = self.storage.get_approval_request(request_id)
        if not request:
            return False

        if request.status != ApprovalStatus.PENDING:
            self.logger.error("Cannot cancel non-pending request", request_id=request_id, status=request.status.value)
            return False

        # Only the original requester or an admin can cancel
        if request.requested_by != canceller_id and not self._is_admin(canceller_id):
            self.logger.error("Insufficient permissions to cancel request", request_id=request_id, user_id=canceller_id)
            return False

        request.status = ApprovalStatus.CANCELLED

        if not self.storage.save_approval_request(request):
            return False

        # Log to history
        history_entry = ApprovalHistoryEntry(
            id=f"hist_{uuid4().hex[:8]}",
            approval_request_id=request_id,
            action="cancelled",
            actor=canceller_id,
            timestamp=datetime.now()
        )
        self.storage.save_approval_history(history_entry)

        self.logger.info("Approval request cancelled", request_id=request_id, user_id=canceller_id)
        return True

    def _is_admin(self, user_id: str) -> bool:
        """Check if user has admin privileges (simplified implementation)"""
        # In a real implementation, this would check user roles from a user management system
        admin_users = {"admin", "system"}  # Example admin users
        return user_id in admin_users


class ApprovalGate:
    """Approval gate that checks if a post can be published"""

    def __init__(self, workflow_engine: ApprovalWorkflowEngine):
        self.workflow_engine = workflow_engine
        self.logger = logger.bind(component="ApprovalGate")

    def can_publish(self, post: LinkedInPost) -> tuple[bool, str]:
        """Check if a post can be published based on approval status"""
        # Get the most recent approval request for this post
        approval_requests = self.workflow_engine.storage.get_approval_requests_by_post(post.id)

        if not approval_requests:
            return False, "No approval request found for this post"

        # Get the latest request
        latest_request = approval_requests[0]  # Assuming they are sorted by date descending

        if latest_request.status == ApprovalStatus.APPROVED:
            return True, "Post is approved for publishing"
        elif latest_request.status == ApprovalStatus.PENDING:
            return False, "Post is awaiting approval"
        elif latest_request.status == ApprovalStatus.REJECTED:
            return False, f"Post was rejected: {latest_request.rejection_reason}"
        elif latest_request.status == ApprovalStatus.CANCELLED:
            return False, "Post approval was cancelled"
        else:
            return False, f"Post has unexpected approval status: {latest_request.status.value}"

    def request_approval(self, post: LinkedInPost, requested_by: str,
                        required_levels: List[ApprovalLevel],
                        approvers_by_level: Dict[ApprovalLevel, List[str]]) -> Optional[str]:
        """Request approval for a post"""
        if post.status != PostStatus.DRAFT:
            self.logger.error("Only draft posts can be submitted for approval", post_id=post.id, status=post.status.value)
            return None

        # Create approval request
        approval_request = self.workflow_engine.create_approval_request(
            post.id, requested_by, required_levels, approvers_by_level
        )

        if approval_request:
            # Update post status to pending approval
            post.status = PostStatus.PENDING_APPROVAL
            return approval_request.id

        return None


# Convenience functions
def create_approval_workflow_engine(storage_path: str = "./linkedin_approval.db") -> ApprovalWorkflowEngine:
    """Create and return a configured approval workflow engine"""
    storage = SQLiteApprovalStorage(storage_path)
    return ApprovalWorkflowEngine(storage)


def demo_approval_workflow():
    """Demo function to show approval workflow usage"""
    print("Approval Workflow Demo")
    print("=" * 40)

    # Create workflow engine
    workflow = create_approval_workflow_engine()

    print("Approval workflow engine created successfully")

    # Example usage:
    print("\nExample usage:")
    print("# Define required approval levels")
    print("required_levels = [ApprovalLevel.EDITORIAL, ApprovalLevel.COMPLIANCE]")

    print("\n# Define approvers for each level")
    print("approvers = {")
    print("    ApprovalLevel.EDITORIAL: ['editor1', 'editor2'],")
    print("    ApprovalLevel.COMPLIANCE: ['compliance_officer']")
    print("}")

    print("\n# Create approval request")
    print("request_id = workflow.create_approval_request(")
    print("    post_id='post_123',")
    print("    requested_by='author_1',")
    print("    required_levels=required_levels,")
    print("    approvers_by_level=approvers")
    print(")")

    print("\n# Get pending approvals for a user")
    print("pending = workflow.get_pending_approvals_for_user('editor1', UserRole.CONTENT_EDITOR)")
    print(f"Found {len(pending)} pending approvals")

    print("\n# Submit approval for a step")
    print("success = workflow.submit_approval_step(")
    print("    request_id='request_id',")
    print("    user_id='editor1',")
    print("    step_id='step_id',")
    print("    action='approve',")
    print("    feedback='Content looks good'")
    print(")")
    print(f"Approval submitted: {success}")


if __name__ == "__main__":
    demo_approval_workflow()