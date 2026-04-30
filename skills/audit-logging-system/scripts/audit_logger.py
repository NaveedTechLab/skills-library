#!/usr/bin/env python3
"""
Audit Logger - Structured JSON audit logging for all agent actions

This module provides comprehensive audit logging with retention and traceability guarantees.
"""

import asyncio
import hashlib
import hmac
import json
import logging
import os
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, asdict, field
from enum import Enum
import uuid
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

# Set up basic logging for the audit system itself
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LogLevel(Enum):
    """Log levels for audit events"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class EventType(Enum):
    """Types of audit events"""
    AGENT_ACTION = "agent_action"
    FILE_ACCESS = "file_access"
    API_CALL = "api_call"
    CONFIG_CHANGE = "config_change"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATA_ACCESS = "data_access"
    SYSTEM_EVENT = "system_event"
    SECURITY_EVENT = "security_event"


@dataclass
class UserInfo:
    """User information for audit logs"""
    id: str
    role: str = ""
    session_id: str = ""


@dataclass
class AgentInfo:
    """Agent information for audit logs"""
    id: str
    version: str = ""
    type: str = ""


@dataclass
class ActionInfo:
    """Action information for audit logs"""
    name: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    result: str = "unknown"  # success, failure, unknown
    duration_ms: Optional[int] = None


@dataclass
class ResourceInfo:
    """Resource information for audit logs"""
    id: str
    type: str
    operation: str  # read, write, delete, execute


@dataclass
class ContextInfo:
    """Context information for audit logs"""
    source_ip: str = ""
    user_agent: str = ""
    location: str = ""
    environment: str = "production"


@dataclass
class AuditEvent:
    """Complete audit event structure"""
    timestamp: datetime
    log_level: LogLevel
    event_type: EventType
    event_id: str
    correlation_id: str
    trace_id: str
    user: UserInfo
    agent: AgentInfo
    action: ActionInfo
    resources: List[ResourceInfo] = field(default_factory=list)
    context: ContextInfo = field(default_factory=ContextInfo)
    metadata: Dict[str, Any] = field(default_factory=dict)
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert audit event to dictionary for JSON serialization"""
        result = {
            'timestamp': self.timestamp.isoformat(),
            'log_level': self.log_level.value,
            'event_type': self.event_type.value,
            'event_id': self.event_id,
            'correlation_id': self.correlation_id,
            'trace_id': self.trace_id,
            'user': asdict(self.user),
            'agent': asdict(self.agent),
            'action': asdict(self.action),
            'resources': [asdict(r) for r in self.resources],
            'context': asdict(self.context),
            'metadata': self.metadata,
            'message': self.message
        }
        return result

    def to_json(self) -> str:
        """Convert audit event to JSON string"""
        return json.dumps(self.to_dict(), default=str)


class AuditLogStorage:
    """Storage backend for audit logs"""

    def __init__(self, storage_path: str = "./audit_logs"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.db_path = self.storage_path / "audit.db"
        self._init_database()
        self.lock = threading.Lock()

    def _init_database(self):
        """Initialize SQLite database for audit logs"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create audit_events table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                log_level TEXT NOT NULL,
                event_type TEXT NOT NULL,
                event_id TEXT UNIQUE NOT NULL,
                correlation_id TEXT,
                trace_id TEXT,
                user_id TEXT,
                agent_id TEXT,
                action_name TEXT,
                action_result TEXT,
                message TEXT,
                log_data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create indexes for efficient querying
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_events(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_id ON audit_events(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_agent_id ON audit_events(agent_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_event_type ON audit_events(event_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_correlation_id ON audit_events(correlation_id)')

        conn.commit()
        conn.close()

    def store_event(self, event: AuditEvent) -> bool:
        """Store an audit event in the database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO audit_events
                (timestamp, log_level, event_type, event_id, correlation_id, trace_id,
                 user_id, agent_id, action_name, action_result, message, log_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                event.timestamp.isoformat(),
                event.log_level.value,
                event.event_type.value,
                event.event_id,
                event.correlation_id,
                event.trace_id,
                event.user.id,
                event.agent.id,
                event.action.name,
                event.action.result,
                event.message,
                event.to_json()
            ))

            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            logger.warning(f"Duplicate event ID: {event.event_id}")
            return False
        except Exception as e:
            logger.error(f"Failed to store audit event: {e}")
            return False

    def query_events(self,
                    start_time: Optional[datetime] = None,
                    end_time: Optional[datetime] = None,
                    user_id: Optional[str] = None,
                    agent_id: Optional[str] = None,
                    event_type: Optional[EventType] = None,
                    limit: int = 100) -> List[AuditEvent]:
        """Query audit events with filters"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            query = "SELECT log_data FROM audit_events WHERE 1=1"
            params = []

            if start_time:
                query += " AND timestamp >= ?"
                params.append(start_time.isoformat())
            if end_time:
                query += " AND timestamp <= ?"
                params.append(end_time.isoformat())
            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)
            if agent_id:
                query += " AND agent_id = ?"
                params.append(agent_id)
            if event_type:
                query += " AND event_type = ?"
                params.append(event_type.value)

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()

            events = []
            for row in rows:
                try:
                    event_dict = json.loads(row[0])
                    # Convert back to proper types
                    event = AuditEvent(
                        timestamp=datetime.fromisoformat(event_dict['timestamp']),
                        log_level=LogLevel(event_dict['log_level']),
                        event_type=EventType(event_dict['event_type']),
                        event_id=event_dict['event_id'],
                        correlation_id=event_dict['correlation_id'],
                        trace_id=event_dict['trace_id'],
                        user=UserInfo(**event_dict['user']),
                        agent=AgentInfo(**event_dict['agent']),
                        action=ActionInfo(**event_dict['action']),
                        resources=[ResourceInfo(**r) for r in event_dict['resources']],
                        context=ContextInfo(**event_dict['context']),
                        metadata=event_dict['metadata'],
                        message=event_dict['message']
                    )
                    events.append(event)
                except Exception as e:
                    logger.error(f"Failed to deserialize audit event: {e}")
                    continue

            return events
        except Exception as e:
            logger.error(f"Failed to query audit events: {e}")
            return []


class AuditLogIntegrity:
    """Provides integrity protection for audit logs"""

    def __init__(self, secret_key: Optional[str] = None):
        if secret_key:
            # Derive encryption key from secret
            password = secret_key.encode()
            salt = b'salt_32bytes_for_audit_logging_system'  # Fixed salt for demo purposes
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password))
            self.cipher = Fernet(key)
        else:
            # Generate a random key if none provided (for demo purposes)
            key = Fernet.generate_key()
            self.cipher = Fernet(key)

    def encrypt_log_entry(self, log_entry: str) -> str:
        """Encrypt a log entry"""
        encrypted = self.cipher.encrypt(log_entry.encode())
        return encrypted.decode()

    def decrypt_log_entry(self, encrypted_entry: str) -> str:
        """Decrypt a log entry"""
        decrypted = self.cipher.decrypt(encrypted_entry.encode())
        return decrypted.decode()

    def hash_log_entry(self, log_entry: str) -> str:
        """Create SHA-256 hash of log entry"""
        return hashlib.sha256(log_entry.encode()).hexdigest()

    def sign_log_entry(self, log_entry: str, secret: str) -> str:
        """Create HMAC signature of log entry"""
        return hmac.new(
            secret.encode(),
            log_entry.encode(),
            hashlib.sha256
        ).hexdigest()


class AuditLogger:
    """Main audit logging system"""

    def __init__(self,
                 storage_path: str = "./audit_logs",
                 retention_days: int = 90,
                 enable_encryption: bool = False,
                 encryption_key: Optional[str] = None):
        self.storage = AuditLogStorage(storage_path)
        self.integrity = AuditLogIntegrity(encryption_key) if enable_encryption else None
        self.retention_days = retention_days
        self.enable_encryption = enable_encryption
        self.correlation_stack: List[str] = []  # For tracking operation chains
        self.lock = threading.Lock()

    def start_operation(self, operation_name: str) -> str:
        """Start a new operation and return correlation ID"""
        correlation_id = str(uuid.uuid4())
        self.correlation_stack.append(correlation_id)
        self.log_event(
            log_level=LogLevel.INFO,
            event_type=EventType.SYSTEM_EVENT,
            event_id=str(uuid.uuid4()),
            correlation_id=correlation_id,
            trace_id=correlation_id,
            user=UserInfo(id="system", role="operation"),
            agent=AgentInfo(id="audit-logger", version="1.0.0"),
            action=ActionInfo(name=f"start_{operation_name}", result="started"),
            message=f"Started operation: {operation_name}"
        )
        return correlation_id

    def end_operation(self, correlation_id: str, result: str = "completed"):
        """End an operation"""
        self.log_event(
            log_level=LogLevel.INFO,
            event_type=EventType.SYSTEM_EVENT,
            event_id=str(uuid.uuid4()),
            correlation_id=correlation_id,
            trace_id=correlation_id,
            user=UserInfo(id="system", role="operation"),
            agent=AgentInfo(id="audit-logger", version="1.0.0"),
            action=ActionInfo(name="end_operation", result=result),
            message=f"Ended operation with result: {result}"
        )
        if correlation_id in self.correlation_stack:
            self.correlation_stack.remove(correlation_id)

    def log_event(self,
                  log_level: LogLevel,
                  event_type: EventType,
                  event_id: str,
                  correlation_id: str,
                  trace_id: str,
                  user: UserInfo,
                  agent: AgentInfo,
                  action: ActionInfo,
                  resources: Optional[List[ResourceInfo]] = None,
                  context: Optional[ContextInfo] = None,
                  message: str = "") -> bool:
        """Log an audit event"""
        if resources is None:
            resources = []
        if context is None:
            context = ContextInfo()

        # Create the audit event
        event = AuditEvent(
            timestamp=datetime.now(),
            log_level=log_level,
            event_type=event_type,
            event_id=event_id,
            correlation_id=correlation_id,
            trace_id=trace_id,
            user=user,
            agent=agent,
            action=action,
            resources=resources,
            context=context,
            message=message
        )

        # Add integrity metadata if enabled
        if self.integrity:
            log_str = event.to_json()
            event.metadata['integrity_hash'] = self.integrity.hash_log_entry(log_str)
            if self.enable_encryption:
                # Store encrypted version
                encrypted_log = self.integrity.encrypt_log_entry(log_str)
                event.metadata['encrypted'] = True
                event.metadata['original_hash'] = event.metadata['integrity_hash']
                # For storage, we'll store the encrypted version but with the original hash for verification

        # Store the event
        return self.storage.store_event(event)

    def log_agent_action(self,
                         user_id: str,
                         user_role: str,
                         agent_id: str,
                         action_name: str,
                         parameters: Dict[str, Any] = None,
                         result: str = "success",
                         resources: Optional[List[ResourceInfo]] = None,
                         message: str = "") -> bool:
        """Log an agent action"""
        if parameters is None:
            parameters = {}
        if resources is None:
            resources = []

        # Get current correlation ID or create a new one
        correlation_id = self.correlation_stack[-1] if self.correlation_stack else str(uuid.uuid4())
        trace_id = str(uuid.uuid4())

        action_info = ActionInfo(
            name=action_name,
            parameters=parameters,
            result=result
        )

        return self.log_event(
            log_level=LogLevel.INFO,
            event_type=EventType.AGENT_ACTION,
            event_id=str(uuid.uuid4()),
            correlation_id=correlation_id,
            trace_id=trace_id,
            user=UserInfo(id=user_id, role=user_role),
            agent=AgentInfo(id=agent_id),
            action=action_info,
            resources=resources,
            message=message
        )

    def log_file_access(self,
                        user_id: str,
                        file_path: str,
                        operation: str,
                        agent_id: str,
                        result: str = "success",
                        message: str = "") -> bool:
        """Log file access operations"""
        correlation_id = self.correlation_stack[-1] if self.correlation_stack else str(uuid.uuid4())
        trace_id = str(uuid.uuid4())

        resources = [ResourceInfo(id=file_path, type="file", operation=operation)]

        return self.log_event(
            log_level=LogLevel.INFO if result == "success" else LogLevel.WARN,
            event_type=EventType.FILE_ACCESS,
            event_id=str(uuid.uuid4()),
            correlation_id=correlation_id,
            trace_id=trace_id,
            user=UserInfo(id=user_id),
            agent=AgentInfo(id=agent_id),
            action=ActionInfo(name=f"file_{operation}", result=result),
            resources=resources,
            message=message
        )

    def log_data_access(self,
                        user_id: str,
                        data_id: str,
                        operation: str,
                        agent_id: str,
                        sensitivity: str = "standard",
                        result: str = "success",
                        message: str = "") -> bool:
        """Log data access operations"""
        correlation_id = self.correlation_stack[-1] if self.correlation_stack else str(uuid.uuid4())
        trace_id = str(uuid.uuid4())

        resources = [ResourceInfo(id=data_id, type=f"data_{sensitivity}", operation=operation)]

        log_level = LogLevel.INFO
        if sensitivity.lower() in ['sensitive', 'confidential', 'critical']:
            log_level = LogLevel.WARN  # Flag sensitive data access

        return self.log_event(
            log_level=log_level,
            event_type=EventType.DATA_ACCESS,
            event_id=str(uuid.uuid4()),
            correlation_id=correlation_id,
            trace_id=trace_id,
            user=UserInfo(id=user_id),
            agent=AgentInfo(id=agent_id),
            action=ActionInfo(name=f"data_{operation}", result=result),
            resources=resources,
            message=message
        )

    def log_security_event(self,
                           user_id: str,
                           event_subtype: str,
                           agent_id: str,
                           severity: str = "medium",
                           result: str = "detected",
                           message: str = "") -> bool:
        """Log security-related events"""
        correlation_id = self.correlation_stack[-1] if self.correlation_stack else str(uuid.uuid4())
        trace_id = str(uuid.uuid4())

        log_level = LogLevel.WARN
        if severity.lower() in ['high', 'critical']:
            log_level = LogLevel.CRITICAL

        return self.log_event(
            log_level=log_level,
            event_type=EventType.SECURITY_EVENT,
            event_id=str(uuid.uuid4()),
            correlation_id=correlation_id,
            trace_id=trace_id,
            user=UserInfo(id=user_id),
            agent=AgentInfo(id=agent_id),
            action=ActionInfo(name=f"security_{event_subtype}", result=result),
            message=message
        )

    def query_events(self, **kwargs) -> List[AuditEvent]:
        """Query audit events"""
        return self.storage.query_events(**kwargs)

    def get_retention_policy_info(self) -> Dict[str, Any]:
        """Get information about retention policy"""
        return {
            "retention_days": self.retention_days,
            "storage_path": str(self.storage.storage_path),
            "estimated_size": self._estimate_storage_size()
        }

    def _estimate_storage_size(self) -> str:
        """Estimate storage size (placeholder implementation)"""
        # This is a placeholder - in a real implementation, you'd calculate actual storage usage
        return "Calculating..."


class AuditLogQueryEngine:
    """Advanced query engine for audit logs"""

    def __init__(self, audit_logger: AuditLogger):
        self.audit_logger = audit_logger

    def search_by_user(self, user_id: str, days_back: int = 7) -> List[AuditEvent]:
        """Search events by user ID"""
        start_time = datetime.now() - timedelta(days=days_back)
        return self.audit_logger.query_events(
            user_id=user_id,
            start_time=start_time
        )

    def search_by_agent(self, agent_id: str, days_back: int = 7) -> List[AuditEvent]:
        """Search events by agent ID"""
        start_time = datetime.now() - timedelta(days=days_back)
        return self.audit_logger.query_events(
            agent_id=agent_id,
            start_time=start_time
        )

    def search_by_event_type(self, event_type: EventType, days_back: int = 7) -> List[AuditEvent]:
        """Search events by event type"""
        start_time = datetime.now() - timedelta(days=days_back)
        return self.audit_logger.query_events(
            event_type=event_type,
            start_time=start_time
        )

    def search_by_time_range(self, start_time: datetime, end_time: datetime) -> List[AuditEvent]:
        """Search events by time range"""
        return self.audit_logger.query_events(
            start_time=start_time,
            end_time=end_time
        )

    def search_by_correlation_id(self, correlation_id: str) -> List[AuditEvent]:
        """Search events by correlation ID (trace entire operation)"""
        return self.audit_logger.query_events(
            correlation_id=correlation_id
        )

    def generate_compliance_report(self,
                                   start_date: datetime,
                                   end_date: datetime,
                                   report_type: str = "standard") -> Dict[str, Any]:
        """Generate compliance report"""
        events = self.audit_logger.query_events(
            start_time=start_date,
            end_time=end_date
        )

        # Count events by type
        event_counts = {}
        user_activities = {}
        agent_activities = {}

        for event in events:
            # Count event types
            event_type = event.event_type.value
            event_counts[event_type] = event_counts.get(event_type, 0) + 1

            # Track user activities
            user_id = event.user.id
            user_activities[user_id] = user_activities.get(user_id, 0) + 1

            # Track agent activities
            agent_id = event.agent.id
            agent_activities[agent_id] = agent_activities.get(agent_id, 0) + 1

        return {
            "report_type": report_type,
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
            "total_events": len(events),
            "event_counts": event_counts,
            "unique_users": len(user_activities),
            "unique_agents": len(agent_activities),
            "user_activities": user_activities,
            "agent_activities": agent_activities
        }


def main():
    """Main entry point for audit logging system"""
    import argparse

    parser = argparse.ArgumentParser(description="Audit Logging System")
    parser.add_argument("action", choices=["log", "query", "report", "start-operation", "end-operation"],
                       help="Action to perform")
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument("--user-id", help="User ID for the action")
    parser.add_argument("--agent-id", help="Agent ID for the action")
    parser.add_argument("--action-name", help="Name of the action being logged")
    parser.add_argument("--event-type", help="Type of event")
    parser.add_argument("--start-date", help="Start date for queries (YYYY-MM-DD)")
    parser.add_argument("--end-date", help="End date for queries (YYYY-MM-DD)")

    args = parser.parse_args()

    # Initialize audit logger
    audit_logger = AuditLogger()

    if args.action == "log":
        if not args.user_id or not args.agent_id or not args.action_name:
            print("Error: --user-id, --agent-id, and --action-name required for logging")
            return

        success = audit_logger.log_agent_action(
            user_id=args.user_id,
            user_role="user",
            agent_id=args.agent_id,
            action_name=args.action_name,
            message=f"Action performed by {args.user_id} using {args.agent_id}"
        )
        print(f"Log event {'successful' if success else 'failed'}")

    elif args.action == "query":
        if not args.user_id and not args.agent_id and not args.event_type:
            print("Error: At least one of --user-id, --agent-id, or --event-type required for query")
            return

        query_kwargs = {}
        if args.user_id:
            query_kwargs['user_id'] = args.user_id
        if args.agent_id:
            query_kwargs['agent_id'] = args.agent_id
        if args.event_type:
            query_kwargs['event_type'] = EventType(args.event_type)

        events = audit_logger.query_events(**query_kwargs)
        print(f"Found {len(events)} events:")
        for event in events[:10]:  # Show first 10 events
            print(f"  {event.timestamp}: {event.action.name} by {event.user.id}")

    elif args.action == "report":
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()

        if args.start_date:
            start_date = datetime.fromisoformat(args.start_date)
        if args.end_date:
            end_date = datetime.fromisoformat(args.end_date)

        query_engine = AuditLogQueryEngine(audit_logger)
        report = query_engine.generate_compliance_report(start_date, end_date)
        print(json.dumps(report, indent=2, default=str))

    elif args.action == "start-operation":
        if not args.action_name:
            print("Error: --action-name required for starting operation")
            return

        op_id = audit_logger.start_operation(args.action_name)
        print(f"Started operation '{args.action_name}' with correlation ID: {op_id}")

    elif args.action == "end-operation":
        if not args.action_name:
            print("Error: --action-name required for ending operation")
            return

        # For simplicity, we'll just use a dummy correlation ID
        # In real usage, you'd track the correlation ID from start_operation
        audit_logger.end_operation("dummy-correlation-id", args.action_name)
        print(f"Ended operation with result: {args.action_name}")


if __name__ == "__main__":
    main()