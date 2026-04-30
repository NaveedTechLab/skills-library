#!/usr/bin/env python3
"""
A2A Messaging CLI

Command-line interface for the Agent-to-Agent messaging system.
Provides send, receive, status, sync, and heartbeat subcommands.

Platinum Phase 2 - Personal AI Employee Project

Usage:
    python cli.py send --type <message_type> --to <agent> --payload <json>
    python cli.py receive [--limit N]
    python cli.py status
    python cli.py sync [--method git|syncthing]
    python cli.py heartbeat
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure the scripts directory is on the path
sys.path.insert(0, str(Path(__file__).parent))

from a2a_messaging import (
    A2ACloudAgent,
    A2ALocalAgent,
    A2AMessage,
    A2AMessageBroker,
    AgentRole,
    MessagePriority,
    MessageType,
    create_agent_from_env,
    create_broker_from_env,
)
from message_router import MessageRouter
from vault_sync import (
    GitVaultSync,
    SecurityFilter,
    SyncMonitor,
    create_vault_sync,
)

logger = logging.getLogger("a2a-cli")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_vault_path() -> Path:
    vault = os.environ.get("A2A_VAULT_PATH")
    if not vault:
        print("Error: A2A_VAULT_PATH environment variable is required")
        sys.exit(1)
    return Path(vault)


def _get_role() -> AgentRole:
    role = os.environ.get("A2A_AGENT_ROLE", "").lower()
    if role not in ("cloud", "local"):
        print("Error: A2A_AGENT_ROLE must be 'cloud' or 'local'")
        sys.exit(1)
    return AgentRole(role)


def _format_message(msg: A2AMessage) -> str:
    lines = [
        f"  ID:          {msg.message_id}",
        f"  From:        {msg.sender.value}",
        f"  To:          {msg.recipient.value}",
        f"  Type:        {msg.message_type.value}",
        f"  Priority:    {msg.priority.value}",
        f"  Status:      {msg.status.value}",
        f"  Time:        {msg.timestamp.isoformat()}",
        f"  Correlation: {msg.correlation_id or 'none'}",
        f"  Approval:    {'yes' if msg.requires_approval else 'no'}",
        f"  Payload:     {json.dumps(msg.payload, indent=4, default=str)}",
    ]
    return "\n".join(lines)


def _print_json(data: dict | list) -> None:
    print(json.dumps(data, indent=2, default=str))


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

async def cmd_send(args: argparse.Namespace) -> int:
    """Send a message to another agent."""
    broker = create_broker_from_env()

    # Parse message type
    try:
        msg_type = MessageType(args.type)
    except ValueError:
        valid = ", ".join(t.value for t in MessageType)
        print(f"Error: Invalid message type '{args.type}'. Valid types: {valid}")
        return 1

    # Parse recipient
    try:
        recipient = AgentRole(args.to)
    except ValueError:
        print(f"Error: Invalid recipient '{args.to}'. Use 'cloud' or 'local'.")
        return 1

    # Parse payload
    try:
        payload = json.loads(args.payload) if args.payload else {}
    except json.JSONDecodeError as exc:
        print(f"Error: Invalid JSON payload: {exc}")
        return 1

    # Parse priority
    try:
        priority = MessagePriority(args.priority) if args.priority else MessagePriority.NORMAL
    except ValueError:
        valid = ", ".join(p.value for p in MessagePriority)
        print(f"Error: Invalid priority '{args.priority}'. Valid: {valid}")
        return 1

    # Create and send message
    msg = broker.create_message(
        recipient=recipient,
        message_type=msg_type,
        payload=payload,
        priority=priority,
        correlation_id=args.correlation_id,
        requires_approval=args.requires_approval,
        ttl_seconds=args.ttl or 3600,
    )

    success = await broker.send(msg)
    await broker.close()

    if success:
        print(f"Message sent successfully:")
        print(_format_message(msg))
        return 0
    else:
        print(f"Failed to send message: {msg.message_id}")
        if msg.metadata.get("rejection_reason") == "secret_detected":
            print("SECURITY: Message payload contains potential secrets!")
            for finding in msg.metadata.get("secret_findings", []):
                print(f"  - {finding}")
        return 1


async def cmd_receive(args: argparse.Namespace) -> int:
    """Receive messages from inbox."""
    broker = create_broker_from_env()
    messages = await broker.receive(limit=args.limit)
    await broker.close()

    if not messages:
        print("No messages in inbox.")
        return 0

    print(f"Received {len(messages)} message(s):\n")
    for i, msg in enumerate(messages, 1):
        print(f"--- Message {i}/{len(messages)} ---")
        print(_format_message(msg))
        print()

    if args.json:
        _print_json([m.to_dict() for m in messages])

    return 0


async def cmd_status(args: argparse.Namespace) -> int:
    """Show broker and agent status."""
    broker = create_broker_from_env()
    status = broker.get_status()
    await broker.close()

    if args.json:
        _print_json(status)
        return 0

    print("A2A Messaging Status")
    print("=" * 40)
    print(f"  Agent Role:      {status['agent_role']}")
    print(f"  Transport:       {status['transport']}")
    print(f"  Dry Run:         {status['dry_run']}")
    print(f"  Vault Path:      {status['vault_path']}")
    print(f"  Messages Seen:   {status['seen_message_count']}")
    print(f"  Dead Letters:    {status['dead_letter_count']}")
    print(f"  Inbox Pending:   {status['inbox_pending']}")
    print()
    print("Agent Health:")
    for agent_name, health in status["agent_health"].items():
        hstatus = health.get("status", "unknown")
        last_hb = health.get("last_heartbeat", "never")
        print(f"  {agent_name}: {hstatus} (last heartbeat: {last_hb})")

    # Show dead letters if requested
    if args.dead_letters:
        dead = broker.get_dead_letters()
        if dead:
            print(f"\nDead Letters ({len(dead)}):")
            for dl in dead:
                print(f"  - {dl['message_id']} ({dl['message_type']}) [{dl.get('metadata', {}).get('dlq_reason', 'unknown')}]")

    return 0


async def cmd_sync(args: argparse.Namespace) -> int:
    """Trigger vault synchronization."""
    vault_path = _get_vault_path()
    method = args.method or os.environ.get("A2A_SYNC_METHOD", "git")

    print(f"Starting vault sync (method: {method})...")

    sync_instance = create_vault_sync(vault_path, method=method)
    monitor = SyncMonitor(vault_path)

    if method == "git":
        if not isinstance(sync_instance, GitVaultSync):
            print("Error: Unexpected sync instance type")
            return 1

        if not sync_instance.is_git_repo():
            if args.init:
                print("Initializing git repository...")
                sync_instance.init_repo()
            else:
                print("Error: Vault is not a git repository. Use --init to initialize.")
                return 1

        status = sync_instance.sync()
    else:
        # Syncthing
        sync_instance.ensure_ignore_file()
        conflicts = sync_instance.resolve_conflicts()
        status = sync_instance.status
        status.conflicts_resolved = conflicts
        status.last_sync = datetime.now(timezone.utc)

    monitor.log_sync_event("sync_completed", status.to_dict())

    if args.json:
        _print_json(status.to_dict())
        return 0

    print("\nSync Results:")
    print(f"  Files Synced:       {status.files_synced}")
    print(f"  Files Blocked:      {status.files_blocked}")
    print(f"  Conflicts Resolved: {status.conflicts_resolved}")
    print(f"  Last Sync:          {status.last_sync.isoformat() if status.last_sync else 'never'}")

    if status.errors:
        print("\nErrors:")
        for err in status.errors:
            print(f"  - {err}")
        return 1

    print("\nSync completed successfully.")
    return 0


async def cmd_heartbeat(args: argparse.Namespace) -> int:
    """Send a heartbeat signal."""
    broker = create_broker_from_env()
    success = await broker.send_heartbeat()
    await broker.close()

    if success:
        print(f"Heartbeat sent from {broker.agent_role.value} agent")
        return 0
    else:
        print("Failed to send heartbeat")
        return 1


async def cmd_approve(args: argparse.Namespace) -> int:
    """Respond to a pending approval request (Local agent only)."""
    broker = create_broker_from_env()

    if broker.agent_role != AgentRole.LOCAL:
        print("Error: Only the Local agent can approve/reject requests")
        await broker.close()
        return 1

    agent = A2ALocalAgent(broker)

    # Process pending messages first
    await broker.process_messages()

    if args.list:
        pending = agent.get_pending_approvals()
        if not pending:
            print("No pending approvals.")
        else:
            print(f"Pending approvals ({len(pending)}):\n")
            for p in pending:
                print(f"  Correlation: {p['correlation_id']}")
                print(f"  Task:        {p['task']}")
                print(f"  Priority:    {p['priority']}")
                print(f"  Time:        {p['timestamp']}")
                print()
        await broker.close()
        return 0

    if not args.correlation_id:
        print("Error: --correlation-id is required")
        await broker.close()
        return 1

    msg = await agent.send_approval_response(
        correlation_id=args.correlation_id,
        approved=args.approved,
        reason=args.reason,
    )

    print(f"Approval response sent:")
    print(f"  Correlation: {args.correlation_id}")
    print(f"  Decision:    {'APPROVED' if args.approved else 'REJECTED'}")
    if args.reason:
        print(f"  Reason:      {args.reason}")

    await broker.close()
    return 0


async def cmd_dlq(args: argparse.Namespace) -> int:
    """Manage the dead letter queue."""
    vault_path = _get_vault_path()

    from message_router import DeadLetterQueue
    dlq = DeadLetterQueue(vault_path)

    if args.action == "list":
        messages = dlq.list_messages(limit=args.limit)
        if not messages:
            print("Dead letter queue is empty.")
            return 0
        print(f"Dead Letter Queue ({len(messages)} messages):\n")
        for m in messages:
            print(f"  ID:     {m['message_id']}")
            print(f"  Type:   {m['message_type']}")
            print(f"  From:   {m['sender']}")
            print(f"  Time:   {m['timestamp']}")
            reason = m.get("metadata", {}).get("dlq_reason", "unknown")
            print(f"  Reason: {reason}")
            print()
        return 0

    elif args.action == "retry":
        if not args.message_id:
            print("Error: --message-id required for retry")
            return 1
        msg = dlq.retry(args.message_id)
        if msg:
            broker = create_broker_from_env()
            success = await broker.send(msg)
            await broker.close()
            print(f"Retry {'succeeded' if success else 'failed'} for {args.message_id}")
            return 0 if success else 1
        else:
            print(f"Message not found in DLQ: {args.message_id}")
            return 1

    elif args.action == "purge":
        count = dlq.purge(older_than_hours=args.older_than)
        print(f"Purged {count} messages from DLQ")
        return 0

    return 0


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="a2a",
        description="A2A (Agent-to-Agent) Messaging CLI for Personal AI Employee",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # -- send ----------------------------------------------------------------
    send_p = subparsers.add_parser("send", help="Send a message to another agent")
    send_p.add_argument("--type", "-t", required=True, help="Message type")
    send_p.add_argument("--to", required=True, help="Recipient agent (cloud|local)")
    send_p.add_argument("--payload", "-p", default="{}", help="JSON payload")
    send_p.add_argument("--priority", default="normal", help="Message priority")
    send_p.add_argument("--correlation-id", help="Correlation ID for request-response pairs")
    send_p.add_argument("--requires-approval", action="store_true", help="Mark as requiring approval")
    send_p.add_argument("--ttl", type=int, default=3600, help="TTL in seconds")

    # -- receive -------------------------------------------------------------
    recv_p = subparsers.add_parser("receive", help="Receive messages from inbox")
    recv_p.add_argument("--limit", "-l", type=int, default=10, help="Max messages to receive")
    recv_p.add_argument("--json", action="store_true", help="Output as JSON")

    # -- status --------------------------------------------------------------
    stat_p = subparsers.add_parser("status", help="Show messaging system status")
    stat_p.add_argument("--json", action="store_true", help="Output as JSON")
    stat_p.add_argument("--dead-letters", action="store_true", help="Include dead letters")

    # -- sync ----------------------------------------------------------------
    sync_p = subparsers.add_parser("sync", help="Trigger vault synchronization")
    sync_p.add_argument("--method", choices=["git", "syncthing"], help="Sync method")
    sync_p.add_argument("--init", action="store_true", help="Initialize git repo if needed")
    sync_p.add_argument("--json", action="store_true", help="Output as JSON")

    # -- heartbeat -----------------------------------------------------------
    subparsers.add_parser("heartbeat", help="Send a heartbeat signal")

    # -- approve -------------------------------------------------------------
    appr_p = subparsers.add_parser("approve", help="Manage approval requests (Local only)")
    appr_p.add_argument("--list", action="store_true", help="List pending approvals")
    appr_p.add_argument("--correlation-id", help="Correlation ID of the request")
    appr_p.add_argument("--approved", action="store_true", default=False, help="Approve the request")
    appr_p.add_argument("--reason", help="Reason for approval/rejection")

    # -- dlq -----------------------------------------------------------------
    dlq_p = subparsers.add_parser("dlq", help="Manage the dead letter queue")
    dlq_p.add_argument("action", choices=["list", "retry", "purge"], help="DLQ action")
    dlq_p.add_argument("--message-id", help="Message ID (for retry)")
    dlq_p.add_argument("--limit", type=int, default=20, help="Max messages to list")
    dlq_p.add_argument("--older-than", type=int, default=72, help="Purge messages older than N hours")

    return parser


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def async_main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    # Configure logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if not args.command:
        parser.print_help()
        return 0

    commands = {
        "send": cmd_send,
        "receive": cmd_receive,
        "status": cmd_status,
        "sync": cmd_sync,
        "heartbeat": cmd_heartbeat,
        "approve": cmd_approve,
        "dlq": cmd_dlq,
    }

    handler = commands.get(args.command)
    if handler is None:
        parser.print_help()
        return 1

    return await handler(args)


def main() -> None:
    try:
        exit_code = asyncio.run(async_main())
    except KeyboardInterrupt:
        print("\nInterrupted.")
        exit_code = 130
    except Exception as exc:
        print(f"Error: {exc}")
        logger.exception("Unhandled exception")
        exit_code = 1
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
