#!/usr/bin/env python3
"""
Approval Workflow for Calendar MCP Server.

Implements file-based HITL (Human-in-the-Loop) approval for calendar operations
that modify shared calendars, invite external attendees, or delete events.

Approval requests are written as Markdown files to a Pending_Approval/calendar/
directory. The human operator reviews the file and changes the YAML front-matter
status from 'pending' to 'approved' or 'rejected'. The server then reads the
file to determine the outcome.
"""

import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

logger = logging.getLogger("calendar-approval")


class ApprovalStatus(Enum):
    """Status values for an approval request."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class CalendarApprovalManager:
    """
    Manages file-based HITL approval workflow for calendar operations.

    Approval files are written to ``<approval_dir>/calendar/`` as Markdown
    with YAML front-matter. The human operator edits the ``status`` field
    to approve or reject.
    """

    def __init__(
        self,
        approval_dir: str = "./Pending_Approval",
        timeout_seconds: int = 3600,
    ):
        self.approval_dir = Path(approval_dir) / "calendar"
        self.timeout_seconds = timeout_seconds
        self._ensure_dir()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def request_approval(
        self,
        operation: str,
        details: Dict[str, Any],
    ) -> str:
        """
        Create an approval request file and return a unique request ID.

        Args:
            operation: The calendar operation type (create_event, update_event,
                       delete_event).
            details: A dict of operation-specific parameters.

        Returns:
            A unique request ID that can be used to check approval status.
        """
        request_id = f"cal_{uuid4().hex[:10]}"
        now = datetime.now(timezone.utc)
        expires = now + timedelta(seconds=self.timeout_seconds)

        # Build a human-readable slug for the filename
        summary_slug = self._slugify(details.get("summary", details.get("event_id", "event")))
        timestamp_str = now.strftime("%Y-%m-%d_%H%M")
        filename = f"{timestamp_str}_{operation}_{summary_slug}.md"
        filepath = self.approval_dir / filename

        # Build Markdown content
        content = self._render_approval_file(
            request_id=request_id,
            operation=operation,
            details=details,
            created=now,
            expires=expires,
        )

        filepath.write_text(content, encoding="utf-8")
        logger.info(
            "Approval request created: %s -> %s", request_id, filepath
        )

        # Also write a machine-readable sidecar JSON for easy parsing
        sidecar_path = filepath.with_suffix(".json")
        sidecar_data = {
            "request_id": request_id,
            "operation": operation,
            "details": details,
            "status": ApprovalStatus.PENDING.value,
            "created": now.isoformat(),
            "expires": expires.isoformat(),
            "approval_file": str(filepath),
        }
        sidecar_path.write_text(
            json.dumps(sidecar_data, indent=2, default=str), encoding="utf-8"
        )

        return request_id

    def check_approval(self, request_id: str) -> Tuple[ApprovalStatus, Dict[str, Any]]:
        """
        Check the current status of an approval request.

        Reads the sidecar JSON and the Markdown file to determine whether
        the human has approved, rejected, or if the request has expired.

        Returns:
            A tuple of (ApprovalStatus, details_dict).
        """
        sidecar = self._find_sidecar(request_id)
        if sidecar is None:
            logger.warning("Approval request not found: %s", request_id)
            return ApprovalStatus.EXPIRED, {}

        data = json.loads(sidecar.read_text(encoding="utf-8"))

        # Check expiration
        expires = datetime.fromisoformat(data["expires"])
        if datetime.now(timezone.utc) > expires:
            self._update_sidecar_status(sidecar, ApprovalStatus.EXPIRED)
            return ApprovalStatus.EXPIRED, data

        # Check the Markdown file for status changes
        md_path = Path(data.get("approval_file", ""))
        if md_path.exists():
            md_status = self._parse_md_status(md_path)
            if md_status in (ApprovalStatus.APPROVED, ApprovalStatus.REJECTED):
                self._update_sidecar_status(sidecar, md_status)
                return md_status, data

        # Check sidecar status (may have been updated externally)
        current_status = ApprovalStatus(data.get("status", "pending"))
        return current_status, data

    def list_pending(self) -> List[Dict[str, Any]]:
        """List all pending approval requests."""
        pending = []
        for sidecar in self.approval_dir.glob("*.json"):
            try:
                data = json.loads(sidecar.read_text(encoding="utf-8"))
                if data.get("status") == ApprovalStatus.PENDING.value:
                    # Check expiration
                    expires = datetime.fromisoformat(data["expires"])
                    if datetime.now(timezone.utc) > expires:
                        self._update_sidecar_status(sidecar, ApprovalStatus.EXPIRED)
                        continue
                    pending.append(data)
            except (json.JSONDecodeError, KeyError):
                continue
        return pending

    def approve(self, request_id: str) -> bool:
        """Programmatically approve a request (updates both sidecar and MD)."""
        return self._set_status(request_id, ApprovalStatus.APPROVED)

    def reject(self, request_id: str) -> bool:
        """Programmatically reject a request (updates both sidecar and MD)."""
        return self._set_status(request_id, ApprovalStatus.REJECTED)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_dir(self) -> None:
        """Create the approval directory if it does not exist."""
        self.approval_dir.mkdir(parents=True, exist_ok=True)

    def _slugify(self, text: str) -> str:
        """Create a filesystem-safe slug from text."""
        slug = re.sub(r"[^\w\s-]", "", text.strip())
        slug = re.sub(r"[\s_]+", "_", slug)
        return slug[:50] or "unnamed"

    def _find_sidecar(self, request_id: str) -> Optional[Path]:
        """Find the sidecar JSON file for a given request ID."""
        for sidecar in self.approval_dir.glob("*.json"):
            try:
                data = json.loads(sidecar.read_text(encoding="utf-8"))
                if data.get("request_id") == request_id:
                    return sidecar
            except (json.JSONDecodeError, KeyError):
                continue
        return None

    def _update_sidecar_status(self, sidecar: Path, status: ApprovalStatus) -> None:
        """Update the status field in a sidecar JSON file."""
        try:
            data = json.loads(sidecar.read_text(encoding="utf-8"))
            data["status"] = status.value
            sidecar.write_text(
                json.dumps(data, indent=2, default=str), encoding="utf-8"
            )
        except Exception as exc:
            logger.error("Failed to update sidecar %s: %s", sidecar, exc)

    def _parse_md_status(self, md_path: Path) -> ApprovalStatus:
        """Parse the YAML front-matter of a Markdown approval file for status."""
        try:
            content = md_path.read_text(encoding="utf-8")
            # Simple YAML front-matter parser (no pyyaml dependency required)
            match = re.search(r"^status:\s*(\w+)", content, re.MULTILINE)
            if match:
                status_str = match.group(1).strip().lower()
                try:
                    return ApprovalStatus(status_str)
                except ValueError:
                    pass
        except Exception as exc:
            logger.error("Failed to parse MD status from %s: %s", md_path, exc)
        return ApprovalStatus.PENDING

    def _set_status(self, request_id: str, status: ApprovalStatus) -> bool:
        """Set the status of a request in both sidecar and Markdown files."""
        sidecar = self._find_sidecar(request_id)
        if sidecar is None:
            return False

        data = json.loads(sidecar.read_text(encoding="utf-8"))

        # Update sidecar
        self._update_sidecar_status(sidecar, status)

        # Update Markdown file
        md_path = Path(data.get("approval_file", ""))
        if md_path.exists():
            content = md_path.read_text(encoding="utf-8")
            content = re.sub(
                r"^status:\s*\w+",
                f"status: {status.value}",
                content,
                count=1,
                flags=re.MULTILINE,
            )
            md_path.write_text(content, encoding="utf-8")

        logger.info("Request %s status set to %s", request_id, status.value)
        return True

    def _render_approval_file(
        self,
        request_id: str,
        operation: str,
        details: Dict[str, Any],
        created: datetime,
        expires: datetime,
    ) -> str:
        """Render the Markdown approval file content."""
        created_str = created.strftime("%Y-%m-%d %H:%M")
        expires_str = expires.strftime("%Y-%m-%d %H:%M")
        calendar_id = details.get("calendar_id", "primary")

        # Build the details table rows
        detail_rows = []
        field_labels = {
            "calendar_id": "Calendar",
            "summary": "Summary",
            "start": "Start",
            "end": "End",
            "description": "Description",
            "attendees": "Attendees",
            "location": "Location",
            "event_id": "Event ID",
        }

        for key, label in field_labels.items():
            value = details.get(key)
            if value is not None and value != "" and value != []:
                if isinstance(value, list):
                    value = ", ".join(str(v) for v in value)
                detail_rows.append(f"| **{label}** | {value} |")

        details_table = "\n".join(detail_rows) if detail_rows else "| *No details* | - |"

        operation_display = operation.replace("_", " ").title()

        return f"""---
type: calendar-approval
status: pending
operation: {operation}
request_id: {request_id}
created: {created_str}
expires: {expires_str}
calendar_id: {calendar_id}
---

# Calendar Operation: {operation_display}

## Request ID
`{request_id}`

## Event Details

| Field | Value |
|-------|-------|
{details_table}

## Actions

- [ ] Approve this operation
- [ ] Reject this operation

> **To approve:** change `status: pending` to `status: approved` in the YAML front-matter above and save this file.
> **To reject:** change `status: pending` to `status: rejected` and save.

## Metadata

- **Created:** {created_str} UTC
- **Expires:** {expires_str} UTC
- **Timeout:** {self.timeout_seconds} seconds
"""
