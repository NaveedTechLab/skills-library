"""
Audit trail for all payment operations.

Every significant action (navigation, form fill, payment draft, execution,
balance check) is recorded as a JSON event and, where applicable, accompanied
by a browser screenshot.  Logs are stored under the configured audit directory
(default: demo_vault/Logs/payments/) and retained for 90 days.
"""

import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from config_manager import config


class PaymentAuditLogger:
    """Append-only JSON-lines audit logger with screenshot management."""

    def __init__(self) -> None:
        config.ensure_directories()
        self._log_dir = config.audit_log_path
        self._screenshot_dir = config.screenshot_path
        self._retention_days = config.audit_retention_days
        self._log_file = self._log_dir / "payment_audit.jsonl"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def log_event(
        self,
        action: str,
        *,
        amount: Optional[str] = None,
        recipient: Optional[str] = None,
        approval_id: Optional[str] = None,
        approval_status: Optional[str] = None,
        url: Optional[str] = None,
        selector: Optional[str] = None,
        screenshot_path: Optional[str] = None,
        dry_run: bool = False,
        success: bool = True,
        error: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Record a single audit event.

        Returns the event dict that was persisted.
        """
        now = datetime.now(timezone.utc)
        event: Dict[str, Any] = {
            "timestamp": now.isoformat(),
            "epoch": time.time(),
            "action": action,
            "success": success,
            "dry_run": dry_run,
        }

        # Optional fields -- only include if provided.
        if amount is not None:
            event["amount"] = amount
        if recipient is not None:
            event["recipient"] = recipient
        if approval_id is not None:
            event["approval_id"] = approval_id
        if approval_status is not None:
            event["approval_status"] = approval_status
        if url is not None:
            event["url"] = url
        if selector is not None:
            event["selector"] = selector
        if screenshot_path is not None:
            event["screenshot"] = screenshot_path
        if error is not None:
            event["error"] = error
        if extra:
            event["extra"] = extra

        self._append(event)
        return event

    async def take_screenshot(
        self, page: Any, name: str
    ) -> Optional[str]:
        """Capture a browser screenshot and return the file path.

        Parameters
        ----------
        page : playwright.async_api.Page or None
            The Playwright page object.  If ``None`` or DRY_RUN mode,
            a placeholder path is returned.
        name : str
            A human-readable name (e.g. ``"pre_submit"``).  The actual
            filename will be timestamped.
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
        filename = f"{timestamp}_{safe_name}.png"
        filepath = self._screenshot_dir / filename

        if config.dry_run or page is None:
            # Log the intent but don't actually capture.
            self.log_event(
                "screenshot_skipped",
                screenshot_path=str(filepath),
                dry_run=True,
            )
            return str(filepath)

        try:
            await page.screenshot(path=str(filepath), full_page=True)
            self.log_event(
                "screenshot_captured",
                screenshot_path=str(filepath),
            )
            return str(filepath)
        except Exception as exc:
            self.log_event(
                "screenshot_failed",
                screenshot_path=str(filepath),
                success=False,
                error=str(exc),
            )
            return None

    def cleanup_old_logs(self) -> int:
        """Delete audit logs and screenshots older than the retention period.

        Returns the number of files removed.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=self._retention_days)
        cutoff_epoch = cutoff.timestamp()
        removed = 0

        for directory in [self._log_dir, self._screenshot_dir]:
            if not directory.exists():
                continue
            for filepath in directory.iterdir():
                if filepath.is_file():
                    try:
                        mtime = filepath.stat().st_mtime
                        if mtime < cutoff_epoch:
                            filepath.unlink()
                            removed += 1
                    except OSError:
                        pass

        if removed > 0:
            self.log_event(
                "audit_cleanup",
                extra={"files_removed": removed, "retention_days": self._retention_days},
            )
        return removed

    def get_recent_events(self, limit: int = 50) -> list:
        """Read the last *limit* events from the audit log."""
        if not self._log_file.exists():
            return []

        events = []
        try:
            with open(self._log_file, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        try:
                            events.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass
        except OSError:
            return []

        return events[-limit:]

    def get_payment_events(self, approval_id: Optional[str] = None) -> list:
        """Return all events related to payments, optionally filtered by approval_id."""
        payment_actions = {
            "draft_payment",
            "execute_payment",
            "payment_approved",
            "payment_rejected",
            "payment_expired",
        }
        events = self.get_recent_events(limit=10000)
        filtered = [e for e in events if e.get("action") in payment_actions]
        if approval_id:
            filtered = [e for e in filtered if e.get("approval_id") == approval_id]
        return filtered

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _append(self, event: Dict[str, Any]) -> None:
        """Append a JSON event to the audit log file."""
        try:
            self._log_dir.mkdir(parents=True, exist_ok=True)
            with open(self._log_file, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(event, default=str) + "\n")
        except OSError:
            # If we cannot write audit logs, fail silently to avoid
            # breaking the payment flow.  In production this should
            # trigger an alert.
            pass


# Module-level singleton.
audit_logger = PaymentAuditLogger()
