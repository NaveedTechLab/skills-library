#!/usr/bin/env python3
"""
Slack MCP Server - HITL Approval Workflow

Manages Human-in-the-Loop approval for sensitive Slack operations:
- Sending messages to external/shared channels
- Sending DMs to new (previously un-contacted) users
- File uploads to any channel
- Bulk messaging (exceeding threshold within time window)

Approval requests are persisted as JSON files in the Pending_Approval/
directory so that a human operator (or a separate approval UI) can
review, approve, or reject them.
"""

import json
import logging
import os
import time
import uuid
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ApprovalRequest:
    """Represents a pending HITL approval request."""

    id: str
    operation: str
    details: Dict[str, Any]
    reason: str
    requested_by: str
    created_at: str
    expires_at: str
    status: str = "pending"  # pending | approved | rejected | expired
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None
    rejection_reason: Optional[str] = None


@dataclass
class ApprovalDecision:
    """The result of reviewing an approval request."""

    request_id: str
    approved: bool
    reviewed_by: str
    reviewed_at: str
    rejection_reason: Optional[str] = None


# ---------------------------------------------------------------------------
# Approval Workflow Engine
# ---------------------------------------------------------------------------

class ApprovalWorkflow:
    """File-based HITL approval workflow for Slack operations.

    Approval files are written to ``approval_dir`` as JSON. A human or
    external system modifies the file (setting ``status`` to ``approved``
    or ``rejected``) and the workflow engine picks up the decision on the
    next poll.
    """

    def __init__(
        self,
        approval_dir: str = "Pending_Approval",
        timeout_seconds: int = 3600,
        bulk_threshold: int = 3,
        bulk_window_seconds: int = 60,
        known_dm_users_file: str = "data/known_dm_users.json",
    ):
        self.approval_dir = Path(approval_dir)
        self.timeout_seconds = timeout_seconds
        self.bulk_threshold = bulk_threshold
        self.bulk_window_seconds = bulk_window_seconds
        self.known_dm_users_file = Path(known_dm_users_file)

        # In-memory tracking for bulk-message detection
        self._recent_sends: Deque[float] = deque()

        # In-memory cache of known DM users (loaded from file)
        self._known_dm_users: set = set()

        # Ensure directories exist
        self.approval_dir.mkdir(parents=True, exist_ok=True)
        self.known_dm_users_file.parent.mkdir(parents=True, exist_ok=True)

        # Load known DM users
        self._load_known_dm_users()

    # ------------------------------------------------------------------
    # Known DM users persistence
    # ------------------------------------------------------------------

    def _load_known_dm_users(self) -> None:
        """Load the set of previously-contacted DM user IDs from disk."""
        if self.known_dm_users_file.exists():
            try:
                with open(self.known_dm_users_file, "r") as f:
                    data = json.load(f)
                self._known_dm_users = set(data.get("user_ids", []))
                logger.info(
                    "Loaded %d known DM users from %s",
                    len(self._known_dm_users),
                    self.known_dm_users_file,
                )
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Could not load known DM users: %s", exc)
                self._known_dm_users = set()
        else:
            self._known_dm_users = set()

    def _save_known_dm_users(self) -> None:
        """Persist the known DM user set to disk."""
        try:
            with open(self.known_dm_users_file, "w") as f:
                json.dump({"user_ids": sorted(self._known_dm_users)}, f, indent=2)
        except OSError as exc:
            logger.error("Failed to save known DM users: %s", exc)

    def mark_dm_user_known(self, user_id: str) -> None:
        """Record that a DM has been successfully sent to this user."""
        self._known_dm_users.add(user_id)
        self._save_known_dm_users()

    def is_dm_user_known(self, user_id: str) -> bool:
        """Check whether we have previously messaged this user."""
        return user_id in self._known_dm_users

    # ------------------------------------------------------------------
    # Bulk-message tracking
    # ------------------------------------------------------------------

    def _record_send(self) -> None:
        """Record a message-send event for bulk detection."""
        now = time.time()
        self._recent_sends.append(now)
        # Prune events outside the window
        cutoff = now - self.bulk_window_seconds
        while self._recent_sends and self._recent_sends[0] < cutoff:
            self._recent_sends.popleft()

    def _is_bulk_send(self) -> bool:
        """Return True if current send rate exceeds the bulk threshold."""
        now = time.time()
        cutoff = now - self.bulk_window_seconds
        while self._recent_sends and self._recent_sends[0] < cutoff:
            self._recent_sends.popleft()
        # Count including the pending send
        return len(self._recent_sends) >= self.bulk_threshold

    # ------------------------------------------------------------------
    # HITL requirement checks
    # ------------------------------------------------------------------

    def requires_approval(
        self,
        operation: str,
        *,
        channel_id: Optional[str] = None,
        user_id: Optional[str] = None,
        is_external_channel: bool = False,
        is_dm: bool = False,
        hitl_external_channels: bool = True,
        hitl_new_dm_users: bool = True,
        hitl_file_uploads: bool = True,
    ) -> Tuple[bool, str]:
        """Determine whether an operation needs HITL approval.

        Returns:
            Tuple of (needs_approval: bool, reason: str).
        """
        # File uploads always require approval
        if operation == "upload_file" and hitl_file_uploads:
            return True, "File uploads require human approval."

        # External / shared channels
        if operation == "send_message" and is_external_channel and hitl_external_channels:
            return True, (
                f"Channel {channel_id} is an external/shared channel. "
                "Sending messages to external channels requires approval."
            )

        # DMs to new users
        if operation == "send_message" and is_dm and user_id and hitl_new_dm_users:
            if not self.is_dm_user_known(user_id):
                return True, (
                    f"User {user_id} has not been contacted before. "
                    "First-contact DMs require approval."
                )

        # Bulk messaging
        if operation == "send_message":
            self._record_send()
            if self._is_bulk_send():
                return True, (
                    f"Bulk messaging detected: {len(self._recent_sends)} messages "
                    f"in the last {self.bulk_window_seconds} seconds "
                    f"(threshold: {self.bulk_threshold})."
                )

        return False, ""

    # ------------------------------------------------------------------
    # Request creation and file I/O
    # ------------------------------------------------------------------

    def create_request(
        self,
        operation: str,
        details: Dict[str, Any],
        reason: str,
        requested_by: str = "claude",
    ) -> ApprovalRequest:
        """Create a new approval request and write it to the approval directory.

        Args:
            operation: The operation type (e.g. send_message, upload_file).
            details: Operation-specific details for the reviewer.
            reason: Human-readable explanation of why approval is needed.
            requested_by: Identifier for the requester.

        Returns:
            The created ApprovalRequest.
        """
        request_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        expires_at = datetime.fromtimestamp(
            now.timestamp() + self.timeout_seconds, tz=timezone.utc
        )

        request = ApprovalRequest(
            id=request_id,
            operation=operation,
            details=details,
            reason=reason,
            requested_by=requested_by,
            created_at=now.isoformat(),
            expires_at=expires_at.isoformat(),
            status="pending",
        )

        # Write to file
        file_path = self.approval_dir / f"{request_id}.json"
        try:
            with open(file_path, "w") as f:
                json.dump(asdict(request), f, indent=2)
            logger.info(
                "Created approval request %s at %s (reason: %s)",
                request_id,
                file_path,
                reason,
            )
        except OSError as exc:
            logger.error("Failed to write approval request: %s", exc)
            raise

        return request

    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """Load an approval request from disk by its ID.

        Returns:
            The ApprovalRequest if found, or None.
        """
        file_path = self.approval_dir / f"{request_id}.json"
        if not file_path.exists():
            return None

        try:
            with open(file_path, "r") as f:
                data = json.load(f)
            return ApprovalRequest(**data)
        except (json.JSONDecodeError, OSError, TypeError) as exc:
            logger.error("Failed to read approval request %s: %s", request_id, exc)
            return None

    def list_pending(self) -> List[ApprovalRequest]:
        """List all pending approval requests.

        Also expires any requests past their timeout.
        """
        pending = []
        now = datetime.now(timezone.utc)

        for file_path in self.approval_dir.glob("*.json"):
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                request = ApprovalRequest(**data)

                # Auto-expire
                if request.status == "pending":
                    expires = datetime.fromisoformat(request.expires_at)
                    if now > expires:
                        request.status = "expired"
                        self._update_request_file(request)
                        logger.info("Auto-expired request %s", request.id)
                        continue

                if request.status == "pending":
                    pending.append(request)
            except (json.JSONDecodeError, OSError, TypeError) as exc:
                logger.warning("Skipping invalid request file %s: %s", file_path, exc)

        return pending

    def approve(
        self, request_id: str, reviewed_by: str = "human"
    ) -> Optional[ApprovalDecision]:
        """Approve a pending request.

        Returns:
            ApprovalDecision if successful, None if request not found or not pending.
        """
        request = self.get_request(request_id)
        if request is None or request.status != "pending":
            logger.warning(
                "Cannot approve request %s (not found or not pending)", request_id
            )
            return None

        now = datetime.now(timezone.utc).isoformat()
        request.status = "approved"
        request.reviewed_by = reviewed_by
        request.reviewed_at = now
        self._update_request_file(request)

        logger.info("Approved request %s by %s", request_id, reviewed_by)
        return ApprovalDecision(
            request_id=request_id,
            approved=True,
            reviewed_by=reviewed_by,
            reviewed_at=now,
        )

    def reject(
        self,
        request_id: str,
        reviewed_by: str = "human",
        rejection_reason: str = "",
    ) -> Optional[ApprovalDecision]:
        """Reject a pending request.

        Returns:
            ApprovalDecision if successful, None if request not found or not pending.
        """
        request = self.get_request(request_id)
        if request is None or request.status != "pending":
            logger.warning(
                "Cannot reject request %s (not found or not pending)", request_id
            )
            return None

        now = datetime.now(timezone.utc).isoformat()
        request.status = "rejected"
        request.reviewed_by = reviewed_by
        request.reviewed_at = now
        request.rejection_reason = rejection_reason
        self._update_request_file(request)

        logger.info(
            "Rejected request %s by %s (reason: %s)",
            request_id,
            reviewed_by,
            rejection_reason,
        )
        return ApprovalDecision(
            request_id=request_id,
            approved=False,
            reviewed_by=reviewed_by,
            reviewed_at=now,
            rejection_reason=rejection_reason,
        )

    def poll_decision(self, request_id: str) -> Optional[ApprovalRequest]:
        """Poll the approval file for a decision (approve/reject by external actor).

        An external system or human can modify the JSON file directly,
        setting ``status`` to ``approved`` or ``rejected``. This method
        re-reads the file to detect such changes.

        Returns:
            Updated ApprovalRequest if a decision has been made, None otherwise.
        """
        request = self.get_request(request_id)
        if request is None:
            return None
        if request.status in ("approved", "rejected", "expired"):
            return request
        return None

    def cleanup_expired(self) -> int:
        """Remove expired and old completed approval files.

        Returns:
            Number of files cleaned up.
        """
        cleaned = 0
        now = datetime.now(timezone.utc)

        for file_path in self.approval_dir.glob("*.json"):
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)

                status = data.get("status", "pending")
                expires_at = data.get("expires_at", "")

                # Remove expired requests
                if status == "pending" and expires_at:
                    expires = datetime.fromisoformat(expires_at)
                    if now > expires:
                        file_path.unlink()
                        cleaned += 1
                        continue

                # Remove completed requests older than 24 hours
                if status in ("approved", "rejected", "expired"):
                    reviewed_at = data.get("reviewed_at") or data.get("created_at", "")
                    if reviewed_at:
                        reviewed = datetime.fromisoformat(reviewed_at)
                        age_hours = (now - reviewed).total_seconds() / 3600
                        if age_hours > 24:
                            file_path.unlink()
                            cleaned += 1

            except (json.JSONDecodeError, OSError, ValueError) as exc:
                logger.warning("Error processing %s during cleanup: %s", file_path, exc)

        if cleaned:
            logger.info("Cleaned up %d expired/old approval files", cleaned)
        return cleaned

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _update_request_file(self, request: ApprovalRequest) -> None:
        """Write the updated request back to its file."""
        file_path = self.approval_dir / f"{request.id}.json"
        try:
            with open(file_path, "w") as f:
                json.dump(asdict(request), f, indent=2)
        except OSError as exc:
            logger.error("Failed to update approval file %s: %s", file_path, exc)
