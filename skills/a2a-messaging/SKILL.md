---
name: a2a-messaging
description: Agent-to-Agent (A2A) messaging system for direct communication between Cloud and Local agents. Replaces file-based handoffs with real-time messaging while maintaining vault as audit record. Supports task delegation, status updates, approval requests, and result delivery between distributed AI Employee instances. Use when coordinating multiple Claude Code agents across cloud and local environments.
---

# A2A Messaging System

## Overview

The A2A (Agent-to-Agent) Messaging skill provides a direct communication layer between Cloud and Local Claude Code agents. It replaces file-based handoffs with structured messages while preserving the Obsidian vault as the authoritative audit record. This is the Platinum Phase 2 requirement for the Personal AI Employee project.

## Architecture

### Agents

- **Cloud Agent**: Runs on cloud infrastructure. Owns email triage, social media draft generation, calendar analysis, and research tasks. Produces drafts and recommendations but never performs sensitive actions directly.
- **Local Agent**: Runs on the user's local machine. Owns WhatsApp sessions, payment approvals, bank interactions, final email sends, social media posting, and Dashboard.md updates. Has access to local credentials and sensitive sessions.

### Message Broker

The `A2AMessageBroker` sits between agents and handles:
- Message queue management (per-agent inboxes)
- Transport abstraction (file-based or Redis)
- Message deduplication and TTL enforcement
- Dead letter queue for undeliverable messages
- Vault audit trail writing

### Transport Layers

1. **File-based transport** (default): Messages written as JSON files to shared vault directories under `/Messages/outbox/` and `/Messages/inbox/`. Compatible with git-based vault sync.
2. **Redis transport** (optional): Pub/sub channels for real-time delivery. Requires Redis server. Falls back to file-based if Redis is unavailable.

## Message Types

| Type | Direction | Description |
|------|-----------|-------------|
| `task_delegation` | Cloud -> Local or Local -> Cloud | Delegate a task to the other agent |
| `approval_request` | Cloud -> Local | Request human approval for a sensitive action |
| `approval_response` | Local -> Cloud | Respond to an approval request |
| `status_update` | Either direction | Report progress on an ongoing task |
| `result_delivery` | Either direction | Deliver completed task results |
| `heartbeat` | Either direction | Health check signal |
| `error` | Either direction | Report an error condition |

## Message Priority

- **CRITICAL**: Requires immediate processing (e.g., security alerts)
- **HIGH**: Process within minutes (e.g., approval requests)
- **NORMAL**: Standard processing queue
- **LOW**: Background tasks, can be deferred

## Security Rules

1. **No secrets in messages**: Messages are scanned for API keys, tokens, passwords, and credential patterns before sending. Any message containing detected secrets is rejected.
2. **Vault as audit trail**: Every message is written to the vault as a markdown file under `/Updates/` or `/Signals/` for full auditability.
3. **Claim-by-move**: The first agent to move a file from `/Needs_Action/` to `/In_Progress/<agent>/` owns that task. No concurrent claims.
4. **Single-writer for Dashboard.md**: Only the Local agent may write to `Dashboard.md` to prevent merge conflicts.
5. **Security filter on sync**: `.env` files, token stores, WhatsApp session data, and banking credentials are never synced between agents.

## Vault Audit Trail

Every A2A message generates a vault entry:

```
/Updates/a2a-messages/YYYY-MM-DD/
  {timestamp}-{message_type}-{sender}-{message_id_short}.md
```

The markdown file contains:
- YAML frontmatter with message metadata
- Human-readable summary of the message content
- Correlation chain (links to related messages)

## Configuration

Environment variables:
- `A2A_AGENT_ROLE`: "cloud" or "local" (required)
- `A2A_VAULT_PATH`: Path to the shared Obsidian vault (required)
- `A2A_TRANSPORT`: "file" or "redis" (default: "file")
- `A2A_REDIS_URL`: Redis connection URL (required if transport is "redis")
- `A2A_HEARTBEAT_INTERVAL`: Seconds between heartbeats (default: 60)
- `A2A_MESSAGE_TTL`: Default message TTL in seconds (default: 3600)
- `A2A_DRY_RUN`: If "true", messages are logged but not sent (default: "false")

## CLI Usage

```bash
# Send a task delegation
python cli.py send --type task_delegation --to local --payload '{"task": "approve_payment", "amount": 150.00}'

# Check inbox
python cli.py receive --limit 10

# Check agent status
python cli.py status

# Trigger vault sync
python cli.py sync

# Send heartbeat
python cli.py heartbeat
```

## File Structure

```
.claude/skills/a2a-messaging/
  SKILL.md                    # This file
  scripts/
    a2a_messaging.py          # Core messaging system
    message_router.py          # Message routing and transport
    vault_sync.py              # Vault synchronization
    cli.py                     # Command-line interface
  assets/
    requirements.txt           # Python dependencies
  references/                  # Reference materials
```

## Integration Points

- **Orchestrator Engine**: The orchestrator can use A2A messaging to coordinate cross-agent workflows.
- **Watchdog Process Manager**: Monitors agent health via heartbeat messages.
- **Audit Logging System**: All messages are logged through the audit system.
- **Finance Watcher**: Payment approvals flow through A2A approval_request/response.
- **Gmail Watcher**: Email triage results sent as task_delegation from Cloud to Local.
