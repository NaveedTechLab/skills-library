#!/usr/bin/env python3
"""
Slack MCP Server - Model Context Protocol server for Slack workspace integration

This FastMCP server enables Claude Code to send messages, read channels,
manage threads, search workspaces, upload files, and add reactions via the
Slack Web API.  Sensitive operations are gated by Human-in-the-Loop (HITL)
approval through the approval_workflow module.

Usage:
    python slack_mcp_server.py [--config slack_config.json]
"""

import json
import logging
import os
import sys
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional

# ---------------------------------------------------------------------------
# Optional dependency imports with graceful degradation
# ---------------------------------------------------------------------------

try:
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError
    SLACK_AVAILABLE = True
except ImportError:
    SLACK_AVAILABLE = False

try:
    from fastmcp import FastMCP
    FASTMCP_AVAILABLE = True
except ImportError:
    FASTMCP_AVAILABLE = False

# Local imports (sibling modules)
_SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPT_DIR))

from config_manager import SlackConfig, load_config, ensure_directories
from approval_workflow import ApprovalWorkflow

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("slack_mcp_server")

# ---------------------------------------------------------------------------
# Audit logger (separate file-based logger for compliance)
# ---------------------------------------------------------------------------

_audit_logger: Optional[logging.Logger] = None


def _get_audit_logger(config: SlackConfig) -> logging.Logger:
    """Return (and lazily create) the audit file logger."""
    global _audit_logger
    if _audit_logger is not None:
        return _audit_logger

    _audit_logger = logging.getLogger("slack_audit")
    _audit_logger.setLevel(logging.INFO)

    log_path = Path(config.audit_log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    handler = logging.FileHandler(str(log_path))
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    )
    _audit_logger.addHandler(handler)
    return _audit_logger


def _audit(config: SlackConfig, operation: str, details: Dict[str, Any]) -> None:
    """Write an audit log entry."""
    al = _get_audit_logger(config)
    al.info(
        "op=%s | details=%s",
        operation,
        json.dumps(details, default=str),
    )

# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------

class RateLimiter:
    """Simple token-bucket style rate limiter."""

    def __init__(self, per_second: int = 1, per_minute: int = 50):
        self.per_second = per_second
        self.per_minute = per_minute
        self._second_window: Deque[float] = deque()
        self._minute_window: Deque[float] = deque()

    def acquire(self) -> bool:
        """Try to acquire a token.  Returns True if allowed, False if rate-limited."""
        now = time.time()

        # Prune old entries
        while self._second_window and self._second_window[0] < now - 1.0:
            self._second_window.popleft()
        while self._minute_window and self._minute_window[0] < now - 60.0:
            self._minute_window.popleft()

        if len(self._second_window) >= self.per_second:
            return False
        if len(self._minute_window) >= self.per_minute:
            return False

        self._second_window.append(now)
        self._minute_window.append(now)
        return True

    def wait_and_acquire(self, max_wait: float = 5.0) -> bool:
        """Block up to *max_wait* seconds until a token is available."""
        deadline = time.time() + max_wait
        while time.time() < deadline:
            if self.acquire():
                return True
            time.sleep(0.1)
        return False


# ---------------------------------------------------------------------------
# Slack client wrapper
# ---------------------------------------------------------------------------

class SlackClientWrapper:
    """Thin wrapper around slack_sdk.WebClient with rate limiting and audit."""

    def __init__(self, config: SlackConfig):
        if not SLACK_AVAILABLE:
            raise RuntimeError(
                "slack_sdk is not installed.  "
                "Run: pip install slack-sdk>=3.20.0"
            )
        self.config = config
        self.client = WebClient(token=config.bot_token)
        self.rate_limiter = RateLimiter(
            per_second=config.rate_limit_per_second,
            per_minute=config.rate_limit_per_minute,
        )

    def _rate_limit(self) -> None:
        if not self.rate_limiter.wait_and_acquire(max_wait=10.0):
            raise RuntimeError("Rate limit exceeded. Please try again later.")

    # -- Channel helpers ---------------------------------------------------

    def is_external_channel(self, channel_id: str) -> bool:
        """Heuristic: Slack shared channels start with 'C' but have
        is_ext_shared or is_shared set.  We check via API."""
        try:
            self._rate_limit()
            info = self.client.conversations_info(channel=channel_id)
            ch = info.get("channel", {})
            return bool(
                ch.get("is_ext_shared")
                or ch.get("is_org_shared")
                or ch.get("is_shared")
            )
        except SlackApiError:
            # If we can't determine, treat as internal (fail-open for reads)
            return False

    def is_dm_channel(self, channel_id: str) -> bool:
        """Check if a channel ID refers to a DM."""
        return channel_id.startswith("D")

    def resolve_channel(self, channel: str) -> str:
        """Resolve a #channel-name to a channel ID, or return as-is if already an ID."""
        if channel.startswith("#"):
            name = channel.lstrip("#")
            try:
                self._rate_limit()
                resp = self.client.conversations_list(
                    types="public_channel,private_channel", limit=1000
                )
                for ch in resp.get("channels", []):
                    if ch["name"] == name:
                        return ch["id"]
                raise ValueError(f"Channel '{channel}' not found in workspace.")
            except SlackApiError as exc:
                raise RuntimeError(f"Failed to resolve channel: {exc.response['error']}")
        return channel


# ---------------------------------------------------------------------------
# FastMCP server factory
# ---------------------------------------------------------------------------

def create_slack_mcp_server(
    config: Optional[SlackConfig] = None,
    config_file: Optional[str] = None,
) -> "FastMCP":
    """Create and return the FastMCP server with all Slack tools registered.

    Args:
        config: Pre-built SlackConfig. If None, loaded from env / config_file.
        config_file: Path to JSON config file (used only if config is None).

    Returns:
        A FastMCP server instance ready to .run().
    """
    if not FASTMCP_AVAILABLE:
        raise RuntimeError(
            "fastmcp is not installed.  Run: pip install fastmcp>=0.1.0"
        )

    if config is None:
        config = load_config(config_file=config_file)
    ensure_directories(config)

    # Validate critical config
    issues = config.validate()
    critical = [i for i in issues if "bot_token" in i.lower()]
    if critical:
        raise ValueError("Configuration error: " + "; ".join(critical))

    slack = SlackClientWrapper(config)
    approval = ApprovalWorkflow(
        approval_dir=config.approval_dir,
        timeout_seconds=config.approval_timeout_seconds,
        bulk_threshold=config.hitl_bulk_threshold,
        bulk_window_seconds=config.hitl_bulk_window_seconds,
        known_dm_users_file=config.known_dm_users_file,
    )

    mcp = FastMCP(
        "Slack MCP Server",
        description=(
            "MCP server for Slack workspace integration. "
            "Send messages, read channels, search, upload files, "
            "manage threads, and add reactions with HITL controls."
        ),
    )

    # -----------------------------------------------------------------------
    # Tool: send_message
    # -----------------------------------------------------------------------

    @mcp.tool()
    def send_message(
        channel: str,
        text: str,
        thread_ts: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a message to a Slack channel or thread.

        HITL approval is required for:
        - External/shared channels
        - DMs to users not previously contacted
        - Bulk messaging (exceeding rate threshold)

        Args:
            channel: Channel name (e.g. '#general') or channel ID.
            text: The message text to send (supports Slack mrkdwn formatting).
            thread_ts: Optional thread timestamp to reply in a thread.

        Returns:
            Dict with 'ok', 'channel', 'ts', and 'message' on success,
            or 'approval_required' with request details if HITL is triggered.
        """
        channel_id = slack.resolve_channel(channel)
        is_external = slack.is_external_channel(channel_id)
        is_dm = slack.is_dm_channel(channel_id)

        # Determine DM target user (for new-user HITL check)
        dm_user_id = channel_id if is_dm else None

        needs_approval, reason = approval.requires_approval(
            operation="send_message",
            channel_id=channel_id,
            user_id=dm_user_id,
            is_external_channel=is_external,
            is_dm=is_dm,
            hitl_external_channels=config.hitl_external_channels,
            hitl_new_dm_users=config.hitl_new_dm_users,
        )

        if needs_approval and config.hitl_enabled:
            req = approval.create_request(
                operation="send_message",
                details={
                    "channel": channel,
                    "channel_id": channel_id,
                    "text": text[:500],
                    "thread_ts": thread_ts,
                    "is_external": is_external,
                    "is_dm": is_dm,
                },
                reason=reason,
            )
            _audit(config, "send_message_approval_requested", {
                "channel": channel_id,
                "request_id": req.id,
                "reason": reason,
            })
            return {
                "ok": False,
                "approval_required": True,
                "request_id": req.id,
                "reason": reason,
                "message": (
                    f"Approval required: {reason}  "
                    f"Request ID: {req.id}.  "
                    "A human must approve this before it is sent."
                ),
            }

        # Execute the send
        try:
            slack._rate_limit()
            kwargs: Dict[str, Any] = {"channel": channel_id, "text": text}
            if thread_ts:
                kwargs["thread_ts"] = thread_ts

            response = slack.client.chat_postMessage(**kwargs)

            # Mark DM user as known after successful send
            if is_dm and dm_user_id:
                approval.mark_dm_user_known(dm_user_id)

            _audit(config, "send_message", {
                "channel": channel_id,
                "ts": response.get("ts"),
                "thread_ts": thread_ts,
                "text_length": len(text),
            })

            return {
                "ok": True,
                "channel": response.get("channel"),
                "ts": response.get("ts"),
                "message": response.get("message", {}),
            }
        except SlackApiError as exc:
            _audit(config, "send_message_error", {
                "channel": channel_id,
                "error": exc.response.get("error", str(exc)),
            })
            return {
                "ok": False,
                "error": exc.response.get("error", str(exc)),
            }

    # -----------------------------------------------------------------------
    # Tool: read_channel
    # -----------------------------------------------------------------------

    @mcp.tool()
    def read_channel(
        channel: str,
        limit: int = 20,
        oldest: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Read recent messages from a Slack channel.

        Args:
            channel: Channel name (e.g. '#general') or channel ID.
            limit: Maximum number of messages to return (1-100, default 20).
            oldest: Only messages after this Unix timestamp (e.g. '1234567890.123456').

        Returns:
            Dict with 'ok', 'messages' (list), and 'has_more' flag.
        """
        channel_id = slack.resolve_channel(channel)
        limit = max(1, min(100, limit))

        try:
            slack._rate_limit()
            kwargs: Dict[str, Any] = {"channel": channel_id, "limit": limit}
            if oldest:
                kwargs["oldest"] = oldest

            response = slack.client.conversations_history(**kwargs)

            messages = []
            for msg in response.get("messages", []):
                messages.append({
                    "user": msg.get("user", ""),
                    "text": msg.get("text", ""),
                    "ts": msg.get("ts", ""),
                    "thread_ts": msg.get("thread_ts"),
                    "reply_count": msg.get("reply_count", 0),
                    "reactions": msg.get("reactions", []),
                    "type": msg.get("type", "message"),
                    "subtype": msg.get("subtype"),
                })

            _audit(config, "read_channel", {
                "channel": channel_id,
                "message_count": len(messages),
            })

            return {
                "ok": True,
                "messages": messages,
                "has_more": response.get("has_more", False),
            }
        except SlackApiError as exc:
            return {
                "ok": False,
                "error": exc.response.get("error", str(exc)),
            }

    # -----------------------------------------------------------------------
    # Tool: search_messages
    # -----------------------------------------------------------------------

    @mcp.tool()
    def search_messages(
        query: str,
        count: int = 10,
    ) -> Dict[str, Any]:
        """Search messages across the Slack workspace.

        Requires the 'search:read' OAuth scope. Uses the Slack search API
        which supports standard Slack search operators (from:, in:, has:, etc.).

        Args:
            query: Search query string (supports Slack search syntax).
            count: Number of results to return (1-100, default 10).

        Returns:
            Dict with 'ok', 'matches' (list of messages), and 'total' count.
        """
        count = max(1, min(100, count))

        try:
            slack._rate_limit()
            response = slack.client.search_messages(query=query, count=count)

            matches = []
            msgs = response.get("messages", {})
            for match in msgs.get("matches", []):
                matches.append({
                    "text": match.get("text", ""),
                    "user": match.get("user", ""),
                    "username": match.get("username", ""),
                    "ts": match.get("ts", ""),
                    "channel": match.get("channel", {}).get("name", ""),
                    "channel_id": match.get("channel", {}).get("id", ""),
                    "permalink": match.get("permalink", ""),
                })

            total = msgs.get("total", 0)

            _audit(config, "search_messages", {
                "query": query,
                "results": len(matches),
                "total": total,
            })

            return {
                "ok": True,
                "matches": matches,
                "total": total,
            }
        except SlackApiError as exc:
            return {
                "ok": False,
                "error": exc.response.get("error", str(exc)),
            }

    # -----------------------------------------------------------------------
    # Tool: list_channels
    # -----------------------------------------------------------------------

    @mcp.tool()
    def list_channels(
        types: str = "public_channel",
        limit: int = 100,
    ) -> Dict[str, Any]:
        """List channels in the Slack workspace.

        Args:
            types: Comma-separated channel types.
                   Options: public_channel, private_channel, mpim, im.
                   Default: 'public_channel'.
            limit: Max channels to return (1-1000, default 100).

        Returns:
            Dict with 'ok' and 'channels' list containing id, name, topic,
            purpose, num_members, and is_archived for each channel.
        """
        limit = max(1, min(1000, limit))

        try:
            slack._rate_limit()
            response = slack.client.conversations_list(types=types, limit=limit)

            channels = []
            for ch in response.get("channels", []):
                channels.append({
                    "id": ch.get("id", ""),
                    "name": ch.get("name", ""),
                    "topic": ch.get("topic", {}).get("value", ""),
                    "purpose": ch.get("purpose", {}).get("value", ""),
                    "num_members": ch.get("num_members", 0),
                    "is_archived": ch.get("is_archived", False),
                    "is_private": ch.get("is_private", False),
                    "is_ext_shared": ch.get("is_ext_shared", False),
                })

            _audit(config, "list_channels", {
                "types": types,
                "count": len(channels),
            })

            return {"ok": True, "channels": channels}
        except SlackApiError as exc:
            return {
                "ok": False,
                "error": exc.response.get("error", str(exc)),
            }

    # -----------------------------------------------------------------------
    # Tool: get_channel_info
    # -----------------------------------------------------------------------

    @mcp.tool()
    def get_channel_info(channel: str) -> Dict[str, Any]:
        """Get detailed information about a Slack channel.

        Args:
            channel: Channel name (e.g. '#general') or channel ID.

        Returns:
            Dict with 'ok' and detailed channel metadata including
            name, topic, purpose, member count, creation date, etc.
        """
        channel_id = slack.resolve_channel(channel)

        try:
            slack._rate_limit()
            response = slack.client.conversations_info(channel=channel_id)
            ch = response.get("channel", {})

            info = {
                "id": ch.get("id", ""),
                "name": ch.get("name", ""),
                "name_normalized": ch.get("name_normalized", ""),
                "topic": ch.get("topic", {}).get("value", ""),
                "purpose": ch.get("purpose", {}).get("value", ""),
                "num_members": ch.get("num_members", 0),
                "is_archived": ch.get("is_archived", False),
                "is_private": ch.get("is_private", False),
                "is_ext_shared": ch.get("is_ext_shared", False),
                "is_org_shared": ch.get("is_org_shared", False),
                "is_shared": ch.get("is_shared", False),
                "created": ch.get("created", 0),
                "creator": ch.get("creator", ""),
            }

            _audit(config, "get_channel_info", {"channel": channel_id})

            return {"ok": True, "channel": info}
        except SlackApiError as exc:
            return {
                "ok": False,
                "error": exc.response.get("error", str(exc)),
            }

    # -----------------------------------------------------------------------
    # Tool: upload_file
    # -----------------------------------------------------------------------

    @mcp.tool()
    def upload_file(
        channel: str,
        content: str,
        filename: str = "file.txt",
        title: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upload a file to a Slack channel.

        HITL approval is ALWAYS required for file uploads regardless of
        channel type. The file content is provided as a string.

        Args:
            channel: Channel name (e.g. '#general') or channel ID.
            content: The file content as a string.
            filename: Name for the uploaded file (default: 'file.txt').
            title: Optional display title for the file in Slack.

        Returns:
            Dict with 'ok' and file metadata on success,
            or 'approval_required' with request details if HITL is triggered.
        """
        channel_id = slack.resolve_channel(channel)

        needs_approval, reason = approval.requires_approval(
            operation="upload_file",
            channel_id=channel_id,
            hitl_file_uploads=config.hitl_file_uploads,
        )

        if needs_approval and config.hitl_enabled:
            req = approval.create_request(
                operation="upload_file",
                details={
                    "channel": channel,
                    "channel_id": channel_id,
                    "filename": filename,
                    "title": title,
                    "content_length": len(content),
                    "content_preview": content[:200],
                },
                reason=reason,
            )
            _audit(config, "upload_file_approval_requested", {
                "channel": channel_id,
                "filename": filename,
                "request_id": req.id,
            })
            return {
                "ok": False,
                "approval_required": True,
                "request_id": req.id,
                "reason": reason,
                "message": (
                    f"Approval required: {reason}  "
                    f"Request ID: {req.id}.  "
                    "A human must approve this file upload."
                ),
            }

        try:
            slack._rate_limit()
            response = slack.client.files_upload_v2(
                channel=channel_id,
                content=content,
                filename=filename,
                title=title or filename,
            )

            file_info = response.get("file", {})
            _audit(config, "upload_file", {
                "channel": channel_id,
                "filename": filename,
                "file_id": file_info.get("id"),
                "size": file_info.get("size"),
            })

            return {
                "ok": True,
                "file": {
                    "id": file_info.get("id", ""),
                    "name": file_info.get("name", ""),
                    "title": file_info.get("title", ""),
                    "size": file_info.get("size", 0),
                    "filetype": file_info.get("filetype", ""),
                    "permalink": file_info.get("permalink", ""),
                },
            }
        except SlackApiError as exc:
            _audit(config, "upload_file_error", {
                "channel": channel_id,
                "filename": filename,
                "error": exc.response.get("error", str(exc)),
            })
            return {
                "ok": False,
                "error": exc.response.get("error", str(exc)),
            }

    # -----------------------------------------------------------------------
    # Tool: add_reaction
    # -----------------------------------------------------------------------

    @mcp.tool()
    def add_reaction(
        channel: str,
        timestamp: str,
        emoji: str,
    ) -> Dict[str, Any]:
        """Add an emoji reaction to a message.

        Args:
            channel: Channel name (e.g. '#general') or channel ID.
            timestamp: The 'ts' timestamp of the message to react to.
            emoji: Emoji name without colons (e.g. 'thumbsup', 'white_check_mark').

        Returns:
            Dict with 'ok' on success.
        """
        channel_id = slack.resolve_channel(channel)
        # Strip colons if user included them
        emoji = emoji.strip(":")

        try:
            slack._rate_limit()
            slack.client.reactions_add(
                channel=channel_id,
                timestamp=timestamp,
                name=emoji,
            )

            _audit(config, "add_reaction", {
                "channel": channel_id,
                "timestamp": timestamp,
                "emoji": emoji,
            })

            return {"ok": True, "channel": channel_id, "timestamp": timestamp, "emoji": emoji}
        except SlackApiError as exc:
            error_msg = exc.response.get("error", str(exc))
            # 'already_reacted' is not a real error
            if error_msg == "already_reacted":
                return {"ok": True, "already_reacted": True}
            return {"ok": False, "error": error_msg}

    # -----------------------------------------------------------------------
    # Tool: get_thread
    # -----------------------------------------------------------------------

    @mcp.tool()
    def get_thread(
        channel: str,
        thread_ts: str,
    ) -> Dict[str, Any]:
        """Get all replies in a Slack thread.

        Args:
            channel: Channel name (e.g. '#general') or channel ID.
            thread_ts: The parent message's 'ts' timestamp.

        Returns:
            Dict with 'ok' and 'messages' list containing all thread replies.
        """
        channel_id = slack.resolve_channel(channel)

        try:
            slack._rate_limit()
            response = slack.client.conversations_replies(
                channel=channel_id,
                ts=thread_ts,
                limit=200,
            )

            messages = []
            for msg in response.get("messages", []):
                messages.append({
                    "user": msg.get("user", ""),
                    "text": msg.get("text", ""),
                    "ts": msg.get("ts", ""),
                    "thread_ts": msg.get("thread_ts"),
                    "reply_count": msg.get("reply_count", 0),
                    "reactions": msg.get("reactions", []),
                    "type": msg.get("type", "message"),
                    "subtype": msg.get("subtype"),
                })

            _audit(config, "get_thread", {
                "channel": channel_id,
                "thread_ts": thread_ts,
                "reply_count": len(messages),
            })

            return {
                "ok": True,
                "messages": messages,
                "has_more": response.get("has_more", False),
            }
        except SlackApiError as exc:
            return {
                "ok": False,
                "error": exc.response.get("error", str(exc)),
            }

    return mcp


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Run the Slack MCP Server."""
    import argparse

    parser = argparse.ArgumentParser(description="Slack MCP Server")
    parser.add_argument(
        "--config",
        default=None,
        help="Path to JSON configuration file",
    )
    args = parser.parse_args()

    if not FASTMCP_AVAILABLE:
        logger.error("fastmcp is not installed. Run: pip install fastmcp>=0.1.0")
        sys.exit(1)

    if not SLACK_AVAILABLE:
        logger.error("slack_sdk is not installed. Run: pip install slack-sdk>=3.20.0")
        sys.exit(1)

    server = create_slack_mcp_server(config_file=args.config)
    logger.info("Starting Slack MCP Server...")
    server.run()


if __name__ == "__main__":
    main()
