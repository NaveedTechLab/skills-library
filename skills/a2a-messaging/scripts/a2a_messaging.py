"""
A2A (Agent-to-Agent) Messaging System

Core messaging system for direct communication between Cloud and Local agents.
Replaces file-based handoffs with structured messages while maintaining the
Obsidian vault as the authoritative audit record.

Platinum Phase 2 - Personal AI Employee Project
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional, Callable
from pathlib import Path
import json
import asyncio
import logging
import uuid
import hashlib
import re
import os
import shutil

logger = logging.getLogger("a2a-messaging")


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class AgentRole(Enum):
    CLOUD = "cloud"
    LOCAL = "local"


class MessageType(Enum):
    TASK_DELEGATION = "task_delegation"
    APPROVAL_REQUEST = "approval_request"
    APPROVAL_RESPONSE = "approval_response"
    STATUS_UPDATE = "status_update"
    RESULT_DELIVERY = "result_delivery"
    HEARTBEAT = "heartbeat"
    ERROR = "error"


class MessagePriority(Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class MessageStatus(Enum):
    PENDING = "pending"
    DELIVERED = "delivered"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"
    DEAD_LETTER = "dead_letter"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class A2AMessage:
    """Represents a single agent-to-agent message."""

    message_id: str
    sender: AgentRole
    recipient: AgentRole
    message_type: MessageType
    priority: MessagePriority
    payload: dict
    timestamp: datetime
    correlation_id: Optional[str] = None
    requires_approval: bool = False
    ttl_seconds: int = 3600
    checksum: str = ""
    status: MessageStatus = MessageStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.checksum:
            self.checksum = self._compute_checksum()

    # -- serialization -------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "message_id": self.message_id,
            "sender": self.sender.value,
            "recipient": self.recipient.value,
            "message_type": self.message_type.value,
            "priority": self.priority.value,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "requires_approval": self.requires_approval,
            "ttl_seconds": self.ttl_seconds,
            "checksum": self.checksum,
            "status": self.status.value,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, default=str)

    @classmethod
    def from_dict(cls, data: dict) -> "A2AMessage":
        return cls(
            message_id=data["message_id"],
            sender=AgentRole(data["sender"]),
            recipient=AgentRole(data["recipient"]),
            message_type=MessageType(data["message_type"]),
            priority=MessagePriority(data["priority"]),
            payload=data["payload"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            correlation_id=data.get("correlation_id"),
            requires_approval=data.get("requires_approval", False),
            ttl_seconds=data.get("ttl_seconds", 3600),
            checksum=data.get("checksum", ""),
            status=MessageStatus(data.get("status", "pending")),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "A2AMessage":
        return cls.from_dict(json.loads(json_str))

    # -- helpers -------------------------------------------------------------

    def _compute_checksum(self) -> str:
        content = json.dumps(
            {
                "message_id": self.message_id,
                "sender": self.sender.value,
                "recipient": self.recipient.value,
                "message_type": self.message_type.value,
                "payload": self.payload,
                "timestamp": self.timestamp.isoformat(),
            },
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def verify_checksum(self) -> bool:
        return self.checksum == self._compute_checksum()

    def is_expired(self) -> bool:
        age = (datetime.now(timezone.utc) - self.timestamp).total_seconds()
        return age > self.ttl_seconds


# ---------------------------------------------------------------------------
# Secret detection
# ---------------------------------------------------------------------------

# Patterns that indicate secrets / credentials
_SECRET_PATTERNS: list[re.Pattern] = [
    re.compile(r"(?i)(api[_-]?key|apikey)\s*[:=]\s*\S+"),
    re.compile(r"(?i)(secret|token|password|passwd|pwd)\s*[:=]\s*\S+"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9\-._~+/]+=*"),
    re.compile(r"(?i)(aws|gcp|azure)[_-]?(access|secret|key)\s*[:=]\s*\S+"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),  # OpenAI-style keys
    re.compile(r"ghp_[A-Za-z0-9]{36,}"),  # GitHub personal access tokens
    re.compile(r"xox[bpsar]-[A-Za-z0-9\-]+"),  # Slack tokens
    re.compile(r"(?i)private[_-]?key"),
    re.compile(r"-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----"),
    re.compile(r"(?i)(db|database|mongo|redis|postgres)[_-]?(url|uri|password)\s*[:=]\s*\S+"),
]


def scan_for_secrets(text: str) -> list[str]:
    """Return list of matched secret pattern descriptions found in *text*."""
    findings: list[str] = []
    for pattern in _SECRET_PATTERNS:
        matches = pattern.findall(text)
        if matches:
            findings.append(f"Pattern '{pattern.pattern}' matched {len(matches)} time(s)")
    return findings


def validate_no_secrets(message: A2AMessage) -> tuple[bool, list[str]]:
    """Validate that a message payload contains no secrets.

    Returns (is_clean, findings).
    """
    payload_text = json.dumps(message.payload, default=str)
    findings = scan_for_secrets(payload_text)
    return (len(findings) == 0, findings)


# ---------------------------------------------------------------------------
# Vault audit writer
# ---------------------------------------------------------------------------

class VaultAuditWriter:
    """Writes A2A messages to the Obsidian vault as audit records."""

    def __init__(self, vault_path: Path) -> None:
        self.vault_path = Path(vault_path)

    def write_audit_record(self, message: A2AMessage) -> Path:
        date_str = message.timestamp.strftime("%Y-%m-%d")
        time_str = message.timestamp.strftime("%H%M%S")
        short_id = message.message_id[:8]

        # Determine vault subdirectory
        if message.message_type in (MessageType.APPROVAL_REQUEST, MessageType.APPROVAL_RESPONSE):
            base = self.vault_path / "Signals" / "a2a-approvals" / date_str
        else:
            base = self.vault_path / "Updates" / "a2a-messages" / date_str

        base.mkdir(parents=True, exist_ok=True)
        filename = f"{time_str}-{message.message_type.value}-{message.sender.value}-{short_id}.md"
        filepath = base / filename

        content = self._render_markdown(message)
        filepath.write_text(content, encoding="utf-8")
        logger.info("Vault audit record written: %s", filepath)
        return filepath

    @staticmethod
    def _render_markdown(msg: A2AMessage) -> str:
        lines = [
            "---",
            f"message_id: {msg.message_id}",
            f"sender: {msg.sender.value}",
            f"recipient: {msg.recipient.value}",
            f"type: {msg.message_type.value}",
            f"priority: {msg.priority.value}",
            f"timestamp: {msg.timestamp.isoformat()}",
            f"correlation_id: {msg.correlation_id or 'null'}",
            f"requires_approval: {str(msg.requires_approval).lower()}",
            f"status: {msg.status.value}",
            f"checksum: {msg.checksum}",
            "---",
            "",
            f"# A2A Message: {msg.message_type.value}",
            "",
            f"**From:** {msg.sender.value} agent  ",
            f"**To:** {msg.recipient.value} agent  ",
            f"**Priority:** {msg.priority.value}  ",
            f"**Time:** {msg.timestamp.isoformat()}  ",
            "",
            "## Payload",
            "",
            "```json",
            json.dumps(msg.payload, indent=2, default=str),
            "```",
            "",
        ]
        if msg.correlation_id:
            lines.extend([
                "## Correlation",
                "",
                f"This message is part of conversation `{msg.correlation_id}`.",
                "",
            ])
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Claim-by-move enforcement
# ---------------------------------------------------------------------------

class ClaimManager:
    """Implements the claim-by-move rule for task ownership."""

    def __init__(self, vault_path: Path) -> None:
        self.vault_path = Path(vault_path)
        self.needs_action = self.vault_path / "Needs_Action"
        self.in_progress = self.vault_path / "In_Progress"

    def claim_task(self, task_filename: str, agent: AgentRole) -> bool:
        """Attempt to claim a task.  Returns True if this agent now owns it."""
        source = self.needs_action / task_filename
        if not source.exists():
            logger.warning("Task file does not exist in Needs_Action: %s", task_filename)
            return False

        agent_dir = self.in_progress / agent.value
        agent_dir.mkdir(parents=True, exist_ok=True)
        dest = agent_dir / task_filename

        if dest.exists():
            logger.warning("Task already claimed by %s: %s", agent.value, task_filename)
            return False

        # Check if any other agent already has it
        for other in AgentRole:
            if other == agent:
                continue
            other_path = self.in_progress / other.value / task_filename
            if other_path.exists():
                logger.warning("Task already claimed by %s: %s", other.value, task_filename)
                return False

        try:
            shutil.move(str(source), str(dest))
            logger.info("Task claimed by %s: %s", agent.value, task_filename)
            return True
        except OSError as exc:
            logger.error("Failed to claim task %s: %s", task_filename, exc)
            return False

    def release_task(self, task_filename: str, agent: AgentRole, to_done: bool = True) -> bool:
        """Release a task, optionally moving to Done."""
        source = self.in_progress / agent.value / task_filename
        if not source.exists():
            logger.warning("Task not found in agent's In_Progress: %s", task_filename)
            return False

        if to_done:
            done_dir = self.vault_path / "Done"
            done_dir.mkdir(parents=True, exist_ok=True)
            dest = done_dir / task_filename
        else:
            dest = self.needs_action / task_filename

        try:
            shutil.move(str(source), str(dest))
            logger.info("Task released by %s: %s -> %s", agent.value, task_filename, dest)
            return True
        except OSError as exc:
            logger.error("Failed to release task %s: %s", task_filename, exc)
            return False

    def list_claimed(self, agent: AgentRole) -> list[str]:
        agent_dir = self.in_progress / agent.value
        if not agent_dir.exists():
            return []
        return [f.name for f in agent_dir.iterdir() if f.is_file()]


# ---------------------------------------------------------------------------
# Dashboard single-writer enforcement
# ---------------------------------------------------------------------------

class DashboardGuard:
    """Enforces single-writer rule: only Local agent may write Dashboard.md."""

    def __init__(self, vault_path: Path) -> None:
        self.dashboard_path = Path(vault_path) / "Dashboard.md"

    def can_write(self, agent: AgentRole) -> bool:
        return agent == AgentRole.LOCAL

    def write_dashboard(self, agent: AgentRole, content: str) -> bool:
        if not self.can_write(agent):
            logger.error("Agent %s is not allowed to write Dashboard.md", agent.value)
            return False
        self.dashboard_path.write_text(content, encoding="utf-8")
        logger.info("Dashboard.md updated by %s agent", agent.value)
        return True

    def append_dashboard(self, agent: AgentRole, section: str) -> bool:
        if not self.can_write(agent):
            logger.error("Agent %s is not allowed to write Dashboard.md", agent.value)
            return False
        with open(self.dashboard_path, "a", encoding="utf-8") as f:
            f.write(f"\n{section}\n")
        logger.info("Dashboard.md appended by %s agent", agent.value)
        return True


# ---------------------------------------------------------------------------
# Message broker
# ---------------------------------------------------------------------------

class A2AMessageBroker:
    """Central message broker managing queues, delivery, and audit."""

    def __init__(
        self,
        vault_path: Path,
        agent_role: AgentRole,
        transport: str = "file",
        redis_url: Optional[str] = None,
        dry_run: bool = False,
    ) -> None:
        self.vault_path = Path(vault_path)
        self.agent_role = agent_role
        self.transport = transport
        self.redis_url = redis_url
        self.dry_run = dry_run

        self.audit_writer = VaultAuditWriter(self.vault_path)
        self.claim_manager = ClaimManager(self.vault_path)
        self.dashboard_guard = DashboardGuard(self.vault_path)

        # In-memory queues per recipient
        self._queues: dict[AgentRole, asyncio.Queue] = {
            AgentRole.CLOUD: asyncio.Queue(),
            AgentRole.LOCAL: asyncio.Queue(),
        }

        # Deduplication set (message_id -> timestamp)
        self._seen_ids: dict[str, datetime] = {}

        # Dead letter queue
        self._dead_letters: list[A2AMessage] = []

        # Message handlers
        self._handlers: dict[MessageType, list[Callable]] = {}

        # Heartbeat tracking
        self._heartbeats: dict[AgentRole, datetime] = {}

        # File transport directories
        self._msg_dir = self.vault_path / "Messages"
        self._setup_directories()

        # Redis client (lazy init)
        self._redis = None
        self._redis_pubsub = None

        logger.info(
            "A2AMessageBroker initialized: role=%s, transport=%s, dry_run=%s",
            agent_role.value, transport, dry_run,
        )

    def _setup_directories(self) -> None:
        for subdir in [
            "inbox/cloud", "inbox/local",
            "outbox/cloud", "outbox/local",
            "processed", "dead_letter",
        ]:
            (self._msg_dir / subdir).mkdir(parents=True, exist_ok=True)

    # -- message creation helpers -------------------------------------------

    def create_message(
        self,
        recipient: AgentRole,
        message_type: MessageType,
        payload: dict,
        priority: MessagePriority = MessagePriority.NORMAL,
        correlation_id: Optional[str] = None,
        requires_approval: bool = False,
        ttl_seconds: int = 3600,
    ) -> A2AMessage:
        return A2AMessage(
            message_id=str(uuid.uuid4()),
            sender=self.agent_role,
            recipient=recipient,
            message_type=message_type,
            priority=priority,
            payload=payload,
            timestamp=datetime.now(timezone.utc),
            correlation_id=correlation_id or str(uuid.uuid4()),
            requires_approval=requires_approval,
            ttl_seconds=ttl_seconds,
        )

    # -- sending -------------------------------------------------------------

    async def send(self, message: A2AMessage) -> bool:
        """Validate and send a message."""
        # Security check
        is_clean, findings = validate_no_secrets(message)
        if not is_clean:
            logger.error(
                "SECURITY: Message %s contains potential secrets: %s",
                message.message_id, findings,
            )
            message.status = MessageStatus.FAILED
            message.metadata["rejection_reason"] = "secret_detected"
            message.metadata["secret_findings"] = findings
            self._dead_letters.append(message)
            return False

        # Checksum verification
        if not message.verify_checksum():
            logger.error("Checksum mismatch for message %s", message.message_id)
            return False

        # Dry-run mode
        if self.dry_run:
            logger.info("[DRY RUN] Would send message: %s", message.message_id)
            self.audit_writer.write_audit_record(message)
            return True

        # Write audit record
        self.audit_writer.write_audit_record(message)

        # Send via transport
        if self.transport == "redis":
            sent = await self._send_redis(message)
        else:
            sent = await self._send_file(message)

        if sent:
            message.status = MessageStatus.DELIVERED
            logger.info("Message sent: %s -> %s (%s)", message.sender.value, message.recipient.value, message.message_id)
        else:
            message.retry_count += 1
            if message.retry_count >= message.max_retries:
                message.status = MessageStatus.DEAD_LETTER
                self._dead_letters.append(message)
                logger.error("Message moved to dead letter queue: %s", message.message_id)
            else:
                message.status = MessageStatus.PENDING
                logger.warning("Message send failed, will retry (%d/%d): %s", message.retry_count, message.max_retries, message.message_id)

        return sent

    async def _send_file(self, message: A2AMessage) -> bool:
        """Send via file-based transport."""
        try:
            outbox = self._msg_dir / "outbox" / self.agent_role.value
            inbox = self._msg_dir / "inbox" / message.recipient.value
            filename = f"{message.message_id}.json"

            # Write to our outbox
            outbox_file = outbox / filename
            outbox_file.write_text(message.to_json(), encoding="utf-8")

            # Copy to recipient inbox
            inbox_file = inbox / filename
            inbox_file.write_text(message.to_json(), encoding="utf-8")

            return True
        except OSError as exc:
            logger.error("File transport error: %s", exc)
            return False

    async def _send_redis(self, message: A2AMessage) -> bool:
        """Send via Redis pub/sub transport."""
        try:
            redis_client = await self._get_redis()
            if redis_client is None:
                logger.warning("Redis unavailable, falling back to file transport")
                return await self._send_file(message)

            channel = f"a2a:{message.recipient.value}:inbox"
            await redis_client.publish(channel, message.to_json())

            # Also write to file for persistence/audit
            await self._send_file(message)
            return True
        except Exception as exc:
            logger.error("Redis transport error: %s", exc)
            logger.info("Falling back to file transport")
            return await self._send_file(message)

    async def _get_redis(self):
        """Lazy-initialize Redis client."""
        if self._redis is not None:
            return self._redis
        if not self.redis_url:
            return None
        try:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(self.redis_url)
            await self._redis.ping()
            logger.info("Redis connection established: %s", self.redis_url)
            return self._redis
        except Exception as exc:
            logger.warning("Redis connection failed: %s", exc)
            self._redis = None
            return None

    # -- receiving -----------------------------------------------------------

    async def receive(self, limit: int = 10) -> list[A2AMessage]:
        """Receive messages from this agent's inbox."""
        messages: list[A2AMessage] = []
        inbox = self._msg_dir / "inbox" / self.agent_role.value

        if not inbox.exists():
            return messages

        files = sorted(inbox.glob("*.json"), key=lambda f: f.stat().st_mtime)
        for msg_file in files[:limit]:
            try:
                data = json.loads(msg_file.read_text(encoding="utf-8"))
                msg = A2AMessage.from_dict(data)

                # Deduplication
                if msg.message_id in self._seen_ids:
                    logger.debug("Skipping duplicate message: %s", msg.message_id)
                    msg_file.unlink()
                    continue

                # TTL check
                if msg.is_expired():
                    logger.warning("Message expired: %s", msg.message_id)
                    msg.status = MessageStatus.EXPIRED
                    self._move_to_processed(msg_file, msg)
                    continue

                # Checksum verification
                if not msg.verify_checksum():
                    logger.error("Checksum verification failed: %s", msg.message_id)
                    self._move_to_dead_letter(msg_file, msg)
                    continue

                self._seen_ids[msg.message_id] = msg.timestamp
                msg.status = MessageStatus.PROCESSING
                messages.append(msg)

                # Move to processed
                self._move_to_processed(msg_file, msg)

            except (json.JSONDecodeError, KeyError, ValueError) as exc:
                logger.error("Failed to parse message file %s: %s", msg_file, exc)
                # Move bad file to dead letter
                dead = self._msg_dir / "dead_letter" / msg_file.name
                shutil.move(str(msg_file), str(dead))

        # Sort by priority (critical first)
        priority_order = {
            MessagePriority.CRITICAL: 0,
            MessagePriority.HIGH: 1,
            MessagePriority.NORMAL: 2,
            MessagePriority.LOW: 3,
        }
        messages.sort(key=lambda m: priority_order.get(m.priority, 99))

        return messages

    def _move_to_processed(self, msg_file: Path, msg: A2AMessage) -> None:
        processed = self._msg_dir / "processed" / f"{msg.message_id}.json"
        try:
            shutil.move(str(msg_file), str(processed))
        except OSError as exc:
            logger.error("Failed to move message to processed: %s", exc)

    def _move_to_dead_letter(self, msg_file: Path, msg: A2AMessage) -> None:
        dead = self._msg_dir / "dead_letter" / f"{msg.message_id}.json"
        try:
            shutil.move(str(msg_file), str(dead))
            self._dead_letters.append(msg)
        except OSError as exc:
            logger.error("Failed to move message to dead letter: %s", exc)

    # -- handler registration ------------------------------------------------

    def register_handler(self, message_type: MessageType, handler: Callable) -> None:
        if message_type not in self._handlers:
            self._handlers[message_type] = []
        self._handlers[message_type].append(handler)

    async def process_messages(self, limit: int = 10) -> int:
        """Receive and process messages using registered handlers."""
        messages = await self.receive(limit=limit)
        processed = 0

        for msg in messages:
            handlers = self._handlers.get(msg.message_type, [])
            if not handlers:
                logger.warning("No handler for message type: %s", msg.message_type.value)
                continue

            for handler in handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(msg)
                    else:
                        handler(msg)
                    processed += 1
                except Exception as exc:
                    logger.error("Handler error for message %s: %s", msg.message_id, exc)
                    msg.status = MessageStatus.FAILED

        return processed

    # -- heartbeat -----------------------------------------------------------

    async def send_heartbeat(self) -> bool:
        msg = self.create_message(
            recipient=AgentRole.LOCAL if self.agent_role == AgentRole.CLOUD else AgentRole.CLOUD,
            message_type=MessageType.HEARTBEAT,
            payload={
                "agent": self.agent_role.value,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "alive",
                "queued_messages": self._queues[self.agent_role].qsize(),
                "dead_letters": len(self._dead_letters),
            },
            priority=MessagePriority.LOW,
            ttl_seconds=120,
        )
        return await self.send(msg)

    def record_heartbeat(self, agent: AgentRole) -> None:
        self._heartbeats[agent] = datetime.now(timezone.utc)

    def get_agent_health(self, agent: AgentRole, timeout_seconds: int = 180) -> dict:
        last_heartbeat = self._heartbeats.get(agent)
        if last_heartbeat is None:
            return {"agent": agent.value, "status": "unknown", "last_heartbeat": None}

        age = (datetime.now(timezone.utc) - last_heartbeat).total_seconds()
        status = "healthy" if age < timeout_seconds else "unhealthy"
        return {
            "agent": agent.value,
            "status": status,
            "last_heartbeat": last_heartbeat.isoformat(),
            "seconds_since_heartbeat": int(age),
        }

    # -- status / diagnostics ------------------------------------------------

    def get_status(self) -> dict:
        return {
            "agent_role": self.agent_role.value,
            "transport": self.transport,
            "dry_run": self.dry_run,
            "vault_path": str(self.vault_path),
            "seen_message_count": len(self._seen_ids),
            "dead_letter_count": len(self._dead_letters),
            "agent_health": {
                role.value: self.get_agent_health(role) for role in AgentRole
            },
            "inbox_pending": self._count_inbox_files(),
        }

    def _count_inbox_files(self) -> int:
        inbox = self._msg_dir / "inbox" / self.agent_role.value
        if not inbox.exists():
            return 0
        return len(list(inbox.glob("*.json")))

    def get_dead_letters(self) -> list[dict]:
        return [msg.to_dict() for msg in self._dead_letters]

    async def close(self) -> None:
        """Clean up resources."""
        if self._redis is not None:
            await self._redis.close()
            self._redis = None
        logger.info("A2AMessageBroker closed")


# ---------------------------------------------------------------------------
# Cloud agent
# ---------------------------------------------------------------------------

class A2ACloudAgent:
    """Cloud agent: email triage, social drafts, research tasks.

    The Cloud agent NEVER performs sensitive actions directly. It produces
    drafts and recommendations and delegates final execution to the Local agent.
    """

    def __init__(self, broker: A2AMessageBroker) -> None:
        if broker.agent_role != AgentRole.CLOUD:
            raise ValueError("A2ACloudAgent requires a broker with CLOUD role")
        self.broker = broker
        self._register_handlers()

    def _register_handlers(self) -> None:
        self.broker.register_handler(MessageType.APPROVAL_RESPONSE, self._handle_approval_response)
        self.broker.register_handler(MessageType.STATUS_UPDATE, self._handle_status_update)
        self.broker.register_handler(MessageType.RESULT_DELIVERY, self._handle_result_delivery)
        self.broker.register_handler(MessageType.HEARTBEAT, self._handle_heartbeat)
        self.broker.register_handler(MessageType.ERROR, self._handle_error)

    # -- outbound actions ----------------------------------------------------

    async def delegate_email_triage(
        self,
        email_summary: dict,
        suggested_action: str,
        draft_reply: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> A2AMessage:
        """Send email triage results to Local for approval and final send."""
        msg = self.broker.create_message(
            recipient=AgentRole.LOCAL,
            message_type=MessageType.TASK_DELEGATION,
            payload={
                "task": "email_triage",
                "email_summary": email_summary,
                "suggested_action": suggested_action,
                "draft_reply": draft_reply,
            },
            priority=MessagePriority.NORMAL,
            correlation_id=correlation_id,
        )
        await self.broker.send(msg)
        return msg

    async def request_social_post_approval(
        self,
        platform: str,
        draft_content: str,
        scheduled_time: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> A2AMessage:
        """Request approval for a social media post draft."""
        msg = self.broker.create_message(
            recipient=AgentRole.LOCAL,
            message_type=MessageType.APPROVAL_REQUEST,
            payload={
                "task": "social_post_approval",
                "platform": platform,
                "draft_content": draft_content,
                "scheduled_time": scheduled_time,
            },
            priority=MessagePriority.HIGH,
            requires_approval=True,
            correlation_id=correlation_id,
        )
        await self.broker.send(msg)
        return msg

    async def delegate_research_task(
        self,
        topic: str,
        context: dict,
        deadline: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> A2AMessage:
        """Delegate a research task and send results when done."""
        msg = self.broker.create_message(
            recipient=AgentRole.LOCAL,
            message_type=MessageType.TASK_DELEGATION,
            payload={
                "task": "research",
                "topic": topic,
                "context": context,
                "deadline": deadline,
            },
            priority=MessagePriority.NORMAL,
            correlation_id=correlation_id,
        )
        await self.broker.send(msg)
        return msg

    async def send_result(
        self,
        task_type: str,
        result: dict,
        correlation_id: str,
    ) -> A2AMessage:
        """Deliver a completed task result to Local."""
        msg = self.broker.create_message(
            recipient=AgentRole.LOCAL,
            message_type=MessageType.RESULT_DELIVERY,
            payload={
                "task": task_type,
                "result": result,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            },
            priority=MessagePriority.NORMAL,
            correlation_id=correlation_id,
        )
        await self.broker.send(msg)
        return msg

    # -- inbound handlers ----------------------------------------------------

    async def _handle_approval_response(self, msg: A2AMessage) -> None:
        approved = msg.payload.get("approved", False)
        task = msg.payload.get("task", "unknown")
        logger.info(
            "Approval response for %s: %s (correlation: %s)",
            task, "APPROVED" if approved else "REJECTED", msg.correlation_id,
        )
        if approved and msg.payload.get("execute_immediately"):
            logger.info("Executing approved task: %s", task)

    async def _handle_status_update(self, msg: A2AMessage) -> None:
        logger.info("Status update from Local: %s", msg.payload)

    async def _handle_result_delivery(self, msg: A2AMessage) -> None:
        logger.info("Result received from Local: %s", msg.payload.get("task", "unknown"))

    async def _handle_heartbeat(self, msg: A2AMessage) -> None:
        self.broker.record_heartbeat(AgentRole.LOCAL)

    async def _handle_error(self, msg: A2AMessage) -> None:
        logger.error("Error from Local agent: %s", msg.payload)


# ---------------------------------------------------------------------------
# Local agent
# ---------------------------------------------------------------------------

class A2ALocalAgent:
    """Local agent: approvals, WhatsApp, payments, Dashboard.md.

    The Local agent runs on the user's machine and has access to local
    credentials, browser sessions, and can perform sensitive actions with
    human-in-the-loop approval.
    """

    def __init__(self, broker: A2AMessageBroker) -> None:
        if broker.agent_role != AgentRole.LOCAL:
            raise ValueError("A2ALocalAgent requires a broker with LOCAL role")
        self.broker = broker
        self._pending_approvals: dict[str, A2AMessage] = {}
        self._register_handlers()

    def _register_handlers(self) -> None:
        self.broker.register_handler(MessageType.TASK_DELEGATION, self._handle_task_delegation)
        self.broker.register_handler(MessageType.APPROVAL_REQUEST, self._handle_approval_request)
        self.broker.register_handler(MessageType.RESULT_DELIVERY, self._handle_result_delivery)
        self.broker.register_handler(MessageType.HEARTBEAT, self._handle_heartbeat)
        self.broker.register_handler(MessageType.ERROR, self._handle_error)
        self.broker.register_handler(MessageType.STATUS_UPDATE, self._handle_status_update)

    # -- outbound actions ----------------------------------------------------

    async def send_approval_response(
        self,
        correlation_id: str,
        approved: bool,
        reason: Optional[str] = None,
        modifications: Optional[dict] = None,
        execute_immediately: bool = False,
    ) -> A2AMessage:
        """Respond to an approval request from Cloud."""
        original = self._pending_approvals.pop(correlation_id, None)
        task = original.payload.get("task", "unknown") if original else "unknown"

        msg = self.broker.create_message(
            recipient=AgentRole.CLOUD,
            message_type=MessageType.APPROVAL_RESPONSE,
            payload={
                "task": task,
                "approved": approved,
                "reason": reason,
                "modifications": modifications,
                "execute_immediately": execute_immediately,
            },
            priority=MessagePriority.HIGH,
            correlation_id=correlation_id,
        )
        await self.broker.send(msg)
        return msg

    async def send_payment_result(
        self,
        payment_id: str,
        status: str,
        amount: float,
        correlation_id: Optional[str] = None,
    ) -> A2AMessage:
        """Report payment processing result to Cloud."""
        msg = self.broker.create_message(
            recipient=AgentRole.CLOUD,
            message_type=MessageType.RESULT_DELIVERY,
            payload={
                "task": "payment",
                "payment_id": payment_id,
                "status": status,
                "amount": amount,
                "processed_at": datetime.now(timezone.utc).isoformat(),
            },
            priority=MessagePriority.HIGH,
            correlation_id=correlation_id,
        )
        await self.broker.send(msg)
        return msg

    async def send_whatsapp_update(
        self,
        contact: str,
        message_summary: str,
        action_taken: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> A2AMessage:
        """Report WhatsApp activity to Cloud."""
        msg = self.broker.create_message(
            recipient=AgentRole.CLOUD,
            message_type=MessageType.STATUS_UPDATE,
            payload={
                "task": "whatsapp",
                "contact": contact,
                "message_summary": message_summary,
                "action_taken": action_taken,
            },
            priority=MessagePriority.NORMAL,
            correlation_id=correlation_id,
        )
        await self.broker.send(msg)
        return msg

    async def update_dashboard(self, content: str) -> bool:
        """Update Dashboard.md (Local agent exclusive)."""
        return self.broker.dashboard_guard.write_dashboard(AgentRole.LOCAL, content)

    async def send_status_update(
        self,
        task: str,
        status: str,
        details: Optional[dict] = None,
        correlation_id: Optional[str] = None,
    ) -> A2AMessage:
        """Send a general status update to Cloud."""
        msg = self.broker.create_message(
            recipient=AgentRole.CLOUD,
            message_type=MessageType.STATUS_UPDATE,
            payload={
                "task": task,
                "status": status,
                "details": details or {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            priority=MessagePriority.NORMAL,
            correlation_id=correlation_id,
        )
        await self.broker.send(msg)
        return msg

    async def send_error(
        self,
        task: str,
        error_message: str,
        error_details: Optional[dict] = None,
        correlation_id: Optional[str] = None,
    ) -> A2AMessage:
        """Report an error to Cloud."""
        msg = self.broker.create_message(
            recipient=AgentRole.CLOUD,
            message_type=MessageType.ERROR,
            payload={
                "task": task,
                "error": error_message,
                "details": error_details or {},
            },
            priority=MessagePriority.CRITICAL,
            correlation_id=correlation_id,
        )
        await self.broker.send(msg)
        return msg

    # -- inbound handlers ----------------------------------------------------

    async def _handle_task_delegation(self, msg: A2AMessage) -> None:
        task = msg.payload.get("task", "unknown")
        logger.info("Task delegation received from Cloud: %s (correlation: %s)", task, msg.correlation_id)

        if msg.requires_approval:
            self._pending_approvals[msg.correlation_id] = msg
            logger.info("Task requires approval, queued: %s", msg.correlation_id)

    async def _handle_approval_request(self, msg: A2AMessage) -> None:
        task = msg.payload.get("task", "unknown")
        logger.info(
            "Approval request from Cloud: %s (correlation: %s)",
            task, msg.correlation_id,
        )
        self._pending_approvals[msg.correlation_id] = msg

    async def _handle_result_delivery(self, msg: A2AMessage) -> None:
        logger.info("Result received from Cloud: %s", msg.payload.get("task", "unknown"))

    async def _handle_heartbeat(self, msg: A2AMessage) -> None:
        self.broker.record_heartbeat(AgentRole.CLOUD)

    async def _handle_error(self, msg: A2AMessage) -> None:
        logger.error("Error from Cloud agent: %s", msg.payload)

    async def _handle_status_update(self, msg: A2AMessage) -> None:
        logger.info("Status update from Cloud: %s", msg.payload)

    # -- approval helpers ----------------------------------------------------

    def get_pending_approvals(self) -> list[dict]:
        return [
            {
                "correlation_id": cid,
                "task": msg.payload.get("task", "unknown"),
                "priority": msg.priority.value,
                "timestamp": msg.timestamp.isoformat(),
                "payload": msg.payload,
            }
            for cid, msg in self._pending_approvals.items()
        ]


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_broker_from_env() -> A2AMessageBroker:
    """Create an A2AMessageBroker from environment variables."""
    role_str = os.environ.get("A2A_AGENT_ROLE", "").lower()
    if role_str not in ("cloud", "local"):
        raise ValueError(
            f"A2A_AGENT_ROLE must be 'cloud' or 'local', got '{role_str}'. "
            "Set the A2A_AGENT_ROLE environment variable."
        )

    vault_path = os.environ.get("A2A_VAULT_PATH")
    if not vault_path:
        raise ValueError("A2A_VAULT_PATH environment variable is required")

    transport = os.environ.get("A2A_TRANSPORT", "file").lower()
    redis_url = os.environ.get("A2A_REDIS_URL")
    dry_run = os.environ.get("A2A_DRY_RUN", "false").lower() == "true"

    return A2AMessageBroker(
        vault_path=Path(vault_path),
        agent_role=AgentRole(role_str),
        transport=transport,
        redis_url=redis_url,
        dry_run=dry_run,
    )


def create_agent_from_env() -> tuple[A2AMessageBroker, Any]:
    """Create broker and appropriate agent from environment variables.

    Returns (broker, agent) where agent is A2ACloudAgent or A2ALocalAgent.
    """
    broker = create_broker_from_env()
    if broker.agent_role == AgentRole.CLOUD:
        agent = A2ACloudAgent(broker)
    else:
        agent = A2ALocalAgent(broker)
    return broker, agent
