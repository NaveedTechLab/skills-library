"""
Payment approval workflow with mandatory HITL controls.

This module manages the lifecycle of payment approval files:

1. **Create** -- ``create_approval_request`` writes a Markdown file into
   ``Pending_Approval/`` with all payment details.
2. **Check** -- ``check_approval`` looks in ``Approved/`` for the matching
   file, validates that amounts match and the approval has not expired.
3. **Never auto-approve** -- Every payment, regardless of amount or
   recipient familiarity, MUST be approved by a human.

Approval files expire after 24 hours (configurable).
"""

import hashlib
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from config_manager import config


class ApprovalStatus:
    PENDING = "pending"
    APPROVED = "approved"
    EXPIRED = "expired"
    REJECTED = "rejected"
    NOT_FOUND = "not_found"
    INVALID = "invalid"


class ApprovalWorkflow:
    """Manages HITL payment approval files."""

    def __init__(self) -> None:
        config.ensure_directories()
        self._pending_dir = config.pending_approval_dir
        self._approved_dir = config.approved_dir
        self._expiry_hours = config.approval_expiry_hours
        self._known_recipients_file = (
            Path(config.vault_dir) / ".known_recipients.json"
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_approval_request(
        self,
        *,
        recipient: str,
        amount: str,
        currency: str = "USD",
        reference: str = "",
        account: str = "",
        extra_details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create an approval-required file in Pending_Approval/.

        Returns a dict with ``approval_id``, ``file_path``, ``status``,
        ``expires_at``, and ``is_new_payee``.
        """
        now = datetime.now(timezone.utc)
        approval_id = self._generate_id(recipient, amount, now)
        expires_at = now + timedelta(hours=self._expiry_hours)
        is_new_payee = not self._is_known_recipient(recipient)

        filename = f"APPROVAL_REQUIRED_Payment_{approval_id}.md"
        filepath = self._pending_dir / filename

        content = self._render_approval_file(
            approval_id=approval_id,
            recipient=recipient,
            amount=amount,
            currency=currency,
            reference=reference,
            account=account,
            created_at=now,
            expires_at=expires_at,
            is_new_payee=is_new_payee,
            extra_details=extra_details,
        )

        self._pending_dir.mkdir(parents=True, exist_ok=True)
        filepath.write_text(content, encoding="utf-8")

        return {
            "approval_id": approval_id,
            "file_path": str(filepath),
            "status": ApprovalStatus.PENDING,
            "expires_at": expires_at.isoformat(),
            "is_new_payee": is_new_payee,
            "message": (
                f"Approval file created at {filepath}. "
                "A human MUST review and move this file to the "
                f"'{self._approved_dir}' folder to approve the payment."
            ),
        }

    def check_approval(
        self, approval_id: str, expected_amount: Optional[str] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """Check whether an approval has been granted.

        Returns ``(status, details)`` where *status* is one of the
        ``ApprovalStatus`` constants.
        """
        # 1. Look in Approved folder.
        approved_file = self._find_approval_file(self._approved_dir, approval_id)
        if approved_file is not None:
            parsed = self._parse_approval_file(approved_file)
            if parsed is None:
                return ApprovalStatus.INVALID, {
                    "error": "Approved file could not be parsed."
                }

            # Validate expiry.
            if self._is_expired(parsed.get("expires_at", "")):
                return ApprovalStatus.EXPIRED, {
                    "error": "Approval has expired.",
                    "expires_at": parsed.get("expires_at"),
                }

            # Validate amount match.
            if expected_amount and parsed.get("amount") != expected_amount:
                return ApprovalStatus.INVALID, {
                    "error": (
                        f"Amount mismatch: approval says {parsed.get('amount')} "
                        f"but execution requests {expected_amount}."
                    ),
                }

            return ApprovalStatus.APPROVED, {
                "approval_id": approval_id,
                "file_path": str(approved_file),
                "parsed": parsed,
            }

        # 2. Check if still pending.
        pending_file = self._find_approval_file(self._pending_dir, approval_id)
        if pending_file is not None:
            parsed = self._parse_approval_file(pending_file)
            if parsed and self._is_expired(parsed.get("expires_at", "")):
                return ApprovalStatus.EXPIRED, {
                    "error": "Approval request has expired while still pending.",
                    "expires_at": parsed.get("expires_at"),
                }
            return ApprovalStatus.PENDING, {
                "message": (
                    "Payment is still awaiting human approval. "
                    f"The approval file is at: {pending_file}"
                ),
            }

        # 3. Not found at all.
        return ApprovalStatus.NOT_FOUND, {
            "error": f"No approval file found for ID {approval_id}."
        }

    def record_known_recipient(self, recipient: str) -> None:
        """Add a recipient to the known-recipients list after a successful payment."""
        known = self._load_known_recipients()
        normalised = recipient.strip().lower()
        if normalised not in known:
            known.append(normalised)
            self._save_known_recipients(known)

    def cleanup_expired(self) -> int:
        """Remove expired approval files from Pending_Approval/. Returns count removed."""
        removed = 0
        for filepath in self._pending_dir.glob("APPROVAL_REQUIRED_Payment_*.md"):
            parsed = self._parse_approval_file(filepath)
            if parsed and self._is_expired(parsed.get("expires_at", "")):
                try:
                    filepath.unlink()
                    removed += 1
                except OSError:
                    pass
        return removed

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _generate_id(self, recipient: str, amount: str, now: datetime) -> str:
        """Create a short unique approval ID."""
        raw = f"{recipient}|{amount}|{now.isoformat()}|{os.getpid()}"
        return hashlib.sha256(raw.encode()).hexdigest()[:12].upper()

    def _render_approval_file(
        self,
        *,
        approval_id: str,
        recipient: str,
        amount: str,
        currency: str,
        reference: str,
        account: str,
        created_at: datetime,
        expires_at: datetime,
        is_new_payee: bool,
        extra_details: Optional[Dict[str, Any]],
    ) -> str:
        """Render the Markdown approval file."""
        new_payee_warning = ""
        if is_new_payee:
            new_payee_warning = (
                "\n> **WARNING: NEW PAYEE** -- This recipient has never been paid "
                "before. Please verify their details carefully.\n"
            )

        extra_section = ""
        if extra_details:
            extra_section = "\n## Additional Details\n\n```json\n"
            extra_section += json.dumps(extra_details, indent=2, default=str)
            extra_section += "\n```\n"

        return f"""# APPROVAL REQUIRED -- Payment

**This file was auto-generated by the Browser Payment MCP Server.**
**A human MUST review and approve this payment before it can be executed.**

---

## Payment Details

| Field       | Value                          |
|-------------|--------------------------------|
| Approval ID | `{approval_id}`               |
| Recipient   | {recipient}                    |
| Amount      | {amount} {currency}            |
| Reference   | {reference or 'N/A'}          |
| Account     | {account or 'N/A'}            |
| Created     | {created_at.isoformat()}       |
| Expires     | {expires_at.isoformat()}       |
{new_payee_warning}
## How to Approve

1. Review the payment details above.
2. Verify the recipient and amount are correct.
3. **Move this file** from `Pending_Approval/` to `Approved/`.
4. The payment will then be eligible for execution.

## How to Reject

- Delete this file, or leave it in `Pending_Approval/` until it expires.
{extra_section}
---

*Do NOT edit the fields above. The system uses them for validation.*
*Approval ID: {approval_id}*
*Amount: {amount}*
*Expires: {expires_at.isoformat()}*
"""

    def _find_approval_file(self, directory: Path, approval_id: str) -> Optional[Path]:
        """Find an approval file by ID in the given directory."""
        if not directory.exists():
            return None
        pattern = f"APPROVAL_REQUIRED_Payment_{approval_id}.md"
        candidate = directory / pattern
        if candidate.exists():
            return candidate
        # Fallback: scan for files containing the ID.
        for filepath in directory.glob("APPROVAL_REQUIRED_Payment_*.md"):
            if approval_id in filepath.name:
                return filepath
        return None

    def _parse_approval_file(self, filepath: Path) -> Optional[Dict[str, str]]:
        """Extract structured data from an approval Markdown file."""
        try:
            content = filepath.read_text(encoding="utf-8")
        except OSError:
            return None

        result: Dict[str, str] = {}

        # Extract from the footer markers.
        id_match = re.search(r"\*Approval ID:\s*([A-F0-9]+)\*", content)
        if id_match:
            result["approval_id"] = id_match.group(1)

        amount_match = re.search(r"\*Amount:\s*(.+?)\*", content)
        if amount_match:
            result["amount"] = amount_match.group(1).strip()

        expires_match = re.search(r"\*Expires:\s*(.+?)\*", content)
        if expires_match:
            result["expires_at"] = expires_match.group(1).strip()

        # Also pull from the table for richer info.
        recipient_match = re.search(r"\|\s*Recipient\s*\|\s*(.+?)\s*\|", content)
        if recipient_match:
            result["recipient"] = recipient_match.group(1).strip()

        return result if result else None

    def _is_expired(self, expires_at_str: str) -> bool:
        """Check if an ISO timestamp is in the past."""
        if not expires_at_str:
            return True
        try:
            expires_at = datetime.fromisoformat(expires_at_str)
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            return datetime.now(timezone.utc) > expires_at
        except (ValueError, TypeError):
            return True

    def _is_known_recipient(self, recipient: str) -> bool:
        known = self._load_known_recipients()
        return recipient.strip().lower() in known

    def _load_known_recipients(self) -> list:
        if not self._known_recipients_file.exists():
            return []
        try:
            data = json.loads(
                self._known_recipients_file.read_text(encoding="utf-8")
            )
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            return []

    def _save_known_recipients(self, recipients: list) -> None:
        try:
            self._known_recipients_file.parent.mkdir(parents=True, exist_ok=True)
            self._known_recipients_file.write_text(
                json.dumps(sorted(set(recipients)), indent=2), encoding="utf-8"
            )
        except OSError:
            pass


# Module-level singleton.
approval_workflow = ApprovalWorkflow()
