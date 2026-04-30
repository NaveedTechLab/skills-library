"""
A2A Message Router

Routes messages between Cloud and Local agents using file-based or Redis
transport. Handles deduplication, dead letter queues, and TTL enforcement.

Platinum Phase 2 - Personal AI Employee Project
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import asyncio
import json
import hashlib
import logging
import shutil

from a2a_messaging import (
    A2AMessage,
    AgentRole,
    MessagePriority,
    MessageStatus,
    MessageType,
)

logger = logging.getLogger("a2a-router")


# ---------------------------------------------------------------------------
# Transport base
# ---------------------------------------------------------------------------

class TransportBase:
    """Abstract base for message transports."""

    async def send(self, message: A2AMessage) -> bool:
        raise NotImplementedError

    async def receive(self, agent: AgentRole, limit: int = 10) -> list[A2AMessage]:
        raise NotImplementedError

    async def close(self) -> None:
        pass


# ---------------------------------------------------------------------------
# File-based transport
# ---------------------------------------------------------------------------

class FileTransport(TransportBase):
    """File-based message transport using shared vault directories."""

    def __init__(self, vault_path: Path) -> None:
        self.vault_path = Path(vault_path)
        self.msg_dir = self.vault_path / "Messages"
        self._setup()

    def _setup(self) -> None:
        for subdir in [
            "inbox/cloud", "inbox/local",
            "outbox/cloud", "outbox/local",
            "processed", "dead_letter",
        ]:
            (self.msg_dir / subdir).mkdir(parents=True, exist_ok=True)

    async def send(self, message: A2AMessage) -> bool:
        try:
            # Write to sender outbox
            outbox = self.msg_dir / "outbox" / message.sender.value
            outbox_file = outbox / f"{message.message_id}.json"
            outbox_file.write_text(message.to_json(), encoding="utf-8")

            # Write to recipient inbox
            inbox = self.msg_dir / "inbox" / message.recipient.value
            inbox_file = inbox / f"{message.message_id}.json"
            inbox_file.write_text(message.to_json(), encoding="utf-8")

            logger.info(
                "File transport: %s -> %s (%s)",
                message.sender.value, message.recipient.value, message.message_id,
            )
            return True
        except OSError as exc:
            logger.error("File transport send error: %s", exc)
            return False

    async def receive(self, agent: AgentRole, limit: int = 10) -> list[A2AMessage]:
        inbox = self.msg_dir / "inbox" / agent.value
        if not inbox.exists():
            return []

        messages: list[A2AMessage] = []
        files = sorted(inbox.glob("*.json"), key=lambda f: f.stat().st_mtime)

        for msg_file in files[:limit]:
            try:
                data = json.loads(msg_file.read_text(encoding="utf-8"))
                msg = A2AMessage.from_dict(data)
                messages.append(msg)
            except (json.JSONDecodeError, KeyError, ValueError) as exc:
                logger.error("Failed to parse %s: %s", msg_file.name, exc)

        return messages

    def acknowledge(self, message: A2AMessage, agent: AgentRole) -> bool:
        """Move a received message from inbox to processed."""
        inbox_file = self.msg_dir / "inbox" / agent.value / f"{message.message_id}.json"
        if not inbox_file.exists():
            return False
        processed_file = self.msg_dir / "processed" / f"{message.message_id}.json"
        try:
            shutil.move(str(inbox_file), str(processed_file))
            return True
        except OSError as exc:
            logger.error("Failed to acknowledge message %s: %s", message.message_id, exc)
            return False

    def move_to_dead_letter(self, message: A2AMessage, agent: AgentRole) -> bool:
        """Move a message to the dead letter queue."""
        inbox_file = self.msg_dir / "inbox" / agent.value / f"{message.message_id}.json"
        dead_file = self.msg_dir / "dead_letter" / f"{message.message_id}.json"
        try:
            if inbox_file.exists():
                shutil.move(str(inbox_file), str(dead_file))
            else:
                dead_file.write_text(message.to_json(), encoding="utf-8")
            return True
        except OSError as exc:
            logger.error("Failed to move to dead letter: %s", exc)
            return False


# ---------------------------------------------------------------------------
# Redis transport
# ---------------------------------------------------------------------------

class RedisTransport(TransportBase):
    """Redis pub/sub transport for real-time message delivery.

    Falls back to file transport if Redis is unavailable.
    """

    def __init__(
        self,
        vault_path: Path,
        redis_url: str,
        file_fallback: Optional[FileTransport] = None,
    ) -> None:
        self.redis_url = redis_url
        self.file_fallback = file_fallback or FileTransport(vault_path)
        self._redis = None
        self._pubsub = None
        self._connected = False

    async def connect(self) -> bool:
        try:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(self.redis_url)
            await self._redis.ping()
            self._connected = True
            logger.info("Redis transport connected: %s", self.redis_url)
            return True
        except Exception as exc:
            logger.warning("Redis connection failed, using file fallback: %s", exc)
            self._connected = False
            return False

    async def send(self, message: A2AMessage) -> bool:
        # Always persist to file
        file_ok = await self.file_fallback.send(message)

        if not self._connected:
            return file_ok

        try:
            channel = f"a2a:{message.recipient.value}:inbox"
            await self._redis.publish(channel, message.to_json())
            logger.info("Redis publish: %s -> %s", message.sender.value, channel)
            return True
        except Exception as exc:
            logger.error("Redis publish error: %s", exc)
            return file_ok

    async def receive(self, agent: AgentRole, limit: int = 10) -> list[A2AMessage]:
        # Primary: read from file inbox (persistent)
        return await self.file_fallback.receive(agent, limit)

    async def subscribe(self, agent: AgentRole, callback) -> None:
        """Subscribe to real-time messages via Redis pub/sub."""
        if not self._connected:
            logger.warning("Cannot subscribe: Redis not connected")
            return

        try:
            self._pubsub = self._redis.pubsub()
            channel = f"a2a:{agent.value}:inbox"
            await self._pubsub.subscribe(channel)

            async for raw_message in self._pubsub.listen():
                if raw_message["type"] != "message":
                    continue
                try:
                    msg = A2AMessage.from_json(raw_message["data"])
                    await callback(msg)
                except Exception as exc:
                    logger.error("Error processing Redis message: %s", exc)
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.error("Redis subscription error: %s", exc)
        finally:
            if self._pubsub:
                await self._pubsub.unsubscribe()

    async def close(self) -> None:
        if self._pubsub:
            await self._pubsub.unsubscribe()
            await self._pubsub.close()
        if self._redis:
            await self._redis.close()
        self._connected = False


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

class MessageDeduplicator:
    """Tracks seen message IDs to prevent duplicate processing."""

    def __init__(self, max_size: int = 10000, ttl_seconds: int = 7200) -> None:
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._seen: dict[str, datetime] = {}

    def is_duplicate(self, message: A2AMessage) -> bool:
        self._evict_expired()
        return message.message_id in self._seen

    def mark_seen(self, message: A2AMessage) -> None:
        self._evict_expired()
        self._seen[message.message_id] = datetime.now(timezone.utc)

        # Evict oldest if over capacity
        if len(self._seen) > self.max_size:
            oldest_key = min(self._seen, key=self._seen.get)
            del self._seen[oldest_key]

    def _evict_expired(self) -> None:
        now = datetime.now(timezone.utc)
        expired = [
            mid for mid, ts in self._seen.items()
            if (now - ts).total_seconds() > self.ttl_seconds
        ]
        for mid in expired:
            del self._seen[mid]

    @property
    def size(self) -> int:
        return len(self._seen)


# ---------------------------------------------------------------------------
# Dead letter queue
# ---------------------------------------------------------------------------

class DeadLetterQueue:
    """Manages messages that could not be delivered or processed."""

    def __init__(self, vault_path: Path) -> None:
        self.vault_path = Path(vault_path)
        self.dlq_dir = self.vault_path / "Messages" / "dead_letter"
        self.dlq_dir.mkdir(parents=True, exist_ok=True)

    def add(self, message: A2AMessage, reason: str = "unknown") -> Path:
        message.status = MessageStatus.DEAD_LETTER
        message.metadata["dlq_reason"] = reason
        message.metadata["dlq_timestamp"] = datetime.now(timezone.utc).isoformat()

        filepath = self.dlq_dir / f"{message.message_id}.json"
        data = message.to_dict()
        filepath.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        logger.warning("Message added to DLQ: %s (reason: %s)", message.message_id, reason)
        return filepath

    def list_messages(self, limit: int = 50) -> list[dict]:
        results = []
        files = sorted(self.dlq_dir.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
        for f in files[:limit]:
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                results.append(data)
            except (json.JSONDecodeError, OSError) as exc:
                logger.error("Failed to read DLQ file %s: %s", f.name, exc)
        return results

    def retry(self, message_id: str) -> Optional[A2AMessage]:
        """Remove a message from DLQ and return it for retry."""
        filepath = self.dlq_dir / f"{message_id}.json"
        if not filepath.exists():
            return None
        try:
            data = json.loads(filepath.read_text(encoding="utf-8"))
            msg = A2AMessage.from_dict(data)
            msg.status = MessageStatus.PENDING
            msg.retry_count += 1
            filepath.unlink()
            return msg
        except Exception as exc:
            logger.error("Failed to retry DLQ message %s: %s", message_id, exc)
            return None

    def purge(self, older_than_hours: int = 72) -> int:
        """Purge messages older than the given number of hours."""
        now = datetime.now(timezone.utc)
        purged = 0
        for f in self.dlq_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                ts = datetime.fromisoformat(data.get("timestamp", now.isoformat()))
                age_hours = (now - ts).total_seconds() / 3600
                if age_hours > older_than_hours:
                    f.unlink()
                    purged += 1
            except Exception:
                pass
        logger.info("Purged %d messages from DLQ", purged)
        return purged

    @property
    def count(self) -> int:
        return len(list(self.dlq_dir.glob("*.json")))


# ---------------------------------------------------------------------------
# TTL enforcer
# ---------------------------------------------------------------------------

class TTLEnforcer:
    """Enforces message TTL by expiring old messages."""

    def __init__(self, vault_path: Path, dlq: Optional[DeadLetterQueue] = None) -> None:
        self.vault_path = Path(vault_path)
        self.msg_dir = self.vault_path / "Messages"
        self.dlq = dlq or DeadLetterQueue(vault_path)

    def enforce(self) -> int:
        """Scan inboxes and expire messages past their TTL.

        Returns the number of messages expired.
        """
        expired_count = 0
        for agent in AgentRole:
            inbox = self.msg_dir / "inbox" / agent.value
            if not inbox.exists():
                continue
            for msg_file in inbox.glob("*.json"):
                try:
                    data = json.loads(msg_file.read_text(encoding="utf-8"))
                    msg = A2AMessage.from_dict(data)
                    if msg.is_expired():
                        msg.status = MessageStatus.EXPIRED
                        self.dlq.add(msg, reason="ttl_expired")
                        msg_file.unlink()
                        expired_count += 1
                        logger.info("Expired message: %s (TTL: %ds)", msg.message_id, msg.ttl_seconds)
                except Exception as exc:
                    logger.error("TTL enforcement error for %s: %s", msg_file.name, exc)

        return expired_count


# ---------------------------------------------------------------------------
# Message router (orchestrates everything)
# ---------------------------------------------------------------------------

class MessageRouter:
    """High-level router that coordinates transport, dedup, DLQ, and TTL."""

    def __init__(
        self,
        vault_path: Path,
        transport_type: str = "file",
        redis_url: Optional[str] = None,
    ) -> None:
        self.vault_path = Path(vault_path)
        self.transport_type = transport_type

        # Initialize components
        self.file_transport = FileTransport(self.vault_path)
        self.deduplicator = MessageDeduplicator()
        self.dlq = DeadLetterQueue(self.vault_path)
        self.ttl_enforcer = TTLEnforcer(self.vault_path, self.dlq)

        # Select transport
        if transport_type == "redis" and redis_url:
            self.transport: TransportBase = RedisTransport(
                self.vault_path, redis_url, self.file_fallback
            )
        else:
            self.transport = self.file_transport

        logger.info("MessageRouter initialized: transport=%s", transport_type)

    async def route(self, message: A2AMessage) -> bool:
        """Route a message to its recipient."""
        # Deduplication check
        if self.deduplicator.is_duplicate(message):
            logger.warning("Duplicate message dropped: %s", message.message_id)
            return False

        # TTL check before sending
        if message.is_expired():
            logger.warning("Message already expired before routing: %s", message.message_id)
            self.dlq.add(message, reason="expired_before_routing")
            return False

        # Send via transport
        success = await self.transport.send(message)

        if success:
            self.deduplicator.mark_seen(message)
            message.status = MessageStatus.DELIVERED
        else:
            message.retry_count += 1
            if message.retry_count >= message.max_retries:
                self.dlq.add(message, reason="max_retries_exceeded")
                message.status = MessageStatus.DEAD_LETTER
            else:
                message.status = MessageStatus.PENDING

        return success

    async def receive(self, agent: AgentRole, limit: int = 10) -> list[A2AMessage]:
        """Receive messages for an agent, filtering duplicates and expired."""
        # Enforce TTL first
        self.ttl_enforcer.enforce()

        raw_messages = await self.transport.receive(agent, limit=limit * 2)
        valid: list[A2AMessage] = []

        for msg in raw_messages:
            if self.deduplicator.is_duplicate(msg):
                self.file_transport.acknowledge(msg, agent)
                continue

            if msg.is_expired():
                self.dlq.add(msg, reason="ttl_expired")
                self.file_transport.acknowledge(msg, agent)
                continue

            if not msg.verify_checksum():
                self.dlq.add(msg, reason="checksum_mismatch")
                self.file_transport.move_to_dead_letter(msg, agent)
                continue

            self.deduplicator.mark_seen(msg)
            valid.append(msg)

            if len(valid) >= limit:
                break

        # Sort by priority
        priority_order = {
            MessagePriority.CRITICAL: 0,
            MessagePriority.HIGH: 1,
            MessagePriority.NORMAL: 2,
            MessagePriority.LOW: 3,
        }
        valid.sort(key=lambda m: priority_order.get(m.priority, 99))

        return valid

    async def acknowledge(self, message: A2AMessage, agent: AgentRole) -> bool:
        """Acknowledge a processed message."""
        return self.file_transport.acknowledge(message, agent)

    def get_status(self) -> dict:
        return {
            "transport": self.transport_type,
            "dedup_cache_size": self.deduplicator.size,
            "dead_letter_count": self.dlq.count,
        }

    async def close(self) -> None:
        await self.transport.close()
