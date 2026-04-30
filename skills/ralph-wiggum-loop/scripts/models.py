#!/usr/bin/env python3
"""
Data models for Ralph Wiggum Loop

Defines task states, completion criteria, and configuration models.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class TaskStatus(Enum):
    """Status of a tracked task"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    AWAITING_COMPLETION = "awaiting_completion"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CompletionType(Enum):
    """Types of completion detection"""
    FILE_MOVED = "file_moved"           # File moved to /Done folder
    STATUS_MARKER = "status_marker"      # File contains status marker
    CUSTOM_CRITERIA = "custom_criteria"  # Custom completion logic


@dataclass
class CompletionCriteria:
    """Criteria for determining task completion"""
    type: CompletionType
    destination_folder: Optional[str] = None  # For FILE_MOVED
    status_markers: List[str] = field(default_factory=lambda: ["status: completed", "## Completed"])
    custom_check: Optional[str] = None  # Python expression for custom criteria

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "destination_folder": self.destination_folder,
            "status_markers": self.status_markers,
            "custom_check": self.custom_check
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CompletionCriteria":
        return cls(
            type=CompletionType(data.get("type", "file_moved")),
            destination_folder=data.get("destination_folder"),
            status_markers=data.get("status_markers", ["status: completed", "## Completed"]),
            custom_check=data.get("custom_check")
        )


@dataclass
class TrackedTask:
    """A task being tracked by Ralph Wiggum Loop"""
    id: str
    name: str
    source_file: str
    status: TaskStatus = TaskStatus.PENDING
    completion_criteria: CompletionCriteria = field(default_factory=lambda: CompletionCriteria(type=CompletionType.FILE_MOVED))
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    iteration_count: int = 0
    max_iterations: int = 5
    last_continuation_at: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "source_file": self.source_file,
            "status": self.status.value,
            "completion_criteria": self.completion_criteria.to_dict(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "iteration_count": self.iteration_count,
            "max_iterations": self.max_iterations,
            "last_continuation_at": self.last_continuation_at.isoformat() if self.last_continuation_at else None,
            "error_message": self.error_message,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TrackedTask":
        return cls(
            id=data["id"],
            name=data["name"],
            source_file=data["source_file"],
            status=TaskStatus(data.get("status", "pending")),
            completion_criteria=CompletionCriteria.from_dict(data.get("completion_criteria", {})),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            iteration_count=data.get("iteration_count", 0),
            max_iterations=data.get("max_iterations", 5),
            last_continuation_at=datetime.fromisoformat(data["last_continuation_at"]) if data.get("last_continuation_at") else None,
            error_message=data.get("error_message"),
            metadata=data.get("metadata", {})
        )


@dataclass
class TaskState:
    """Current state snapshot of all tracked tasks"""
    active_tasks: List[TrackedTask] = field(default_factory=list)
    global_iteration_count: int = 0
    max_global_iterations: int = 10
    emergency_stop: bool = False
    last_check_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "active_tasks": [t.to_dict() for t in self.active_tasks],
            "global_iteration_count": self.global_iteration_count,
            "max_global_iterations": self.max_global_iterations,
            "emergency_stop": self.emergency_stop,
            "last_check_at": self.last_check_at.isoformat() if self.last_check_at else None
        }


@dataclass
class RalphWiggumConfig:
    """Configuration for Ralph Wiggum Loop"""
    max_global_iterations: int = 10
    max_task_iterations: int = 5
    check_interval_seconds: int = 5
    completion_markers: List[str] = field(default_factory=lambda: ["status: completed", "## Completed"])
    done_folder: str = "./vault/Done/"
    failed_folder: str = "./vault/Failed/"
    needs_action_folder: str = "./vault/Needs_Action/"
    enable_audit_logging: bool = True
    emergency_stop_file: str = ".ralph_stop"
    database_path: str = "./ralph_wiggum.db"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_global_iterations": self.max_global_iterations,
            "max_task_iterations": self.max_task_iterations,
            "check_interval_seconds": self.check_interval_seconds,
            "completion_markers": self.completion_markers,
            "done_folder": self.done_folder,
            "failed_folder": self.failed_folder,
            "needs_action_folder": self.needs_action_folder,
            "enable_audit_logging": self.enable_audit_logging,
            "emergency_stop_file": self.emergency_stop_file,
            "database_path": self.database_path
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RalphWiggumConfig":
        return cls(
            max_global_iterations=data.get("max_global_iterations", 10),
            max_task_iterations=data.get("max_task_iterations", 5),
            check_interval_seconds=data.get("check_interval_seconds", 5),
            completion_markers=data.get("completion_markers", ["status: completed", "## Completed"]),
            done_folder=data.get("done_folder", "./vault/Done/"),
            failed_folder=data.get("failed_folder", "./vault/Failed/"),
            needs_action_folder=data.get("needs_action_folder", "./vault/Needs_Action/"),
            enable_audit_logging=data.get("enable_audit_logging", True),
            emergency_stop_file=data.get("emergency_stop_file", ".ralph_stop"),
            database_path=data.get("database_path", "./ralph_wiggum.db")
        )
