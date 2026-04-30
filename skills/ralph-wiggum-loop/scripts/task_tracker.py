#!/usr/bin/env python3
"""
Task Tracker for Ralph Wiggum Loop

SQLite-based persistence for task state tracking.
"""

import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from uuid import uuid4

import structlog

from .models import (
    CompletionCriteria,
    CompletionType,
    RalphWiggumConfig,
    TaskStatus,
    TrackedTask,
)

logger = structlog.get_logger()


class TaskTracker:
    """SQLite-based task state persistence"""

    def __init__(self, config: RalphWiggumConfig = None):
        self.config = config or RalphWiggumConfig()
        self.db_path = Path(self.config.database_path)
        self.lock = threading.Lock()
        self.logger = logger.bind(component="TaskTracker")
        self._init_db()

    def _init_db(self):
        """Initialize database tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Tasks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    source_file TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    completion_criteria_json TEXT,
                    created_at TIMESTAMP NOT NULL,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    iteration_count INTEGER DEFAULT 0,
                    max_iterations INTEGER DEFAULT 5,
                    last_continuation_at TIMESTAMP,
                    error_message TEXT,
                    metadata_json TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Global state table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS global_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Task history table for audit
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS task_history (
                    id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    old_status TEXT,
                    new_status TEXT,
                    details TEXT,
                    timestamp TIMESTAMP NOT NULL,
                    FOREIGN KEY (task_id) REFERENCES tasks (id)
                )
            """)

            conn.commit()

        self.logger.info("Task tracker database initialized", db_path=str(self.db_path))

    def create_task(
        self,
        name: str,
        source_file: str,
        completion_criteria: CompletionCriteria = None,
        max_iterations: int = None,
        metadata: dict = None
    ) -> TrackedTask:
        """Create and persist a new tracked task"""
        task_id = f"task_{uuid4().hex[:12]}"

        if completion_criteria is None:
            completion_criteria = CompletionCriteria(
                type=CompletionType.FILE_MOVED,
                destination_folder=self.config.done_folder,
                status_markers=self.config.completion_markers
            )

        task = TrackedTask(
            id=task_id,
            name=name,
            source_file=source_file,
            status=TaskStatus.PENDING,
            completion_criteria=completion_criteria,
            created_at=datetime.now(),
            iteration_count=0,
            max_iterations=max_iterations or self.config.max_task_iterations,
            metadata=metadata or {}
        )

        self._save_task(task)
        self._log_history(task_id, "created", None, TaskStatus.PENDING.value)

        self.logger.info("Task created", task_id=task_id, name=name)
        return task

    def _save_task(self, task: TrackedTask) -> bool:
        """Save task to database"""
        try:
            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO tasks
                    (id, name, source_file, status, completion_criteria_json,
                     created_at, started_at, completed_at, iteration_count,
                     max_iterations, last_continuation_at, error_message,
                     metadata_json, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    task.id,
                    task.name,
                    task.source_file,
                    task.status.value,
                    json.dumps(task.completion_criteria.to_dict()),
                    task.created_at.isoformat() if task.created_at else None,
                    task.started_at.isoformat() if task.started_at else None,
                    task.completed_at.isoformat() if task.completed_at else None,
                    task.iteration_count,
                    task.max_iterations,
                    task.last_continuation_at.isoformat() if task.last_continuation_at else None,
                    task.error_message,
                    json.dumps(task.metadata)
                ))
                conn.commit()
                return True
        except Exception as e:
            self.logger.error("Failed to save task", task_id=task.id, error=str(e))
            return False

    def get_task(self, task_id: str) -> Optional[TrackedTask]:
        """Get a task by ID"""
        try:
            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, name, source_file, status, completion_criteria_json,
                           created_at, started_at, completed_at, iteration_count,
                           max_iterations, last_continuation_at, error_message, metadata_json
                    FROM tasks WHERE id = ?
                """, (task_id,))

                row = cursor.fetchone()
                if not row:
                    return None

                return self._row_to_task(row)
        except Exception as e:
            self.logger.error("Failed to get task", task_id=task_id, error=str(e))
            return None

    def get_active_tasks(self) -> List[TrackedTask]:
        """Get all active (non-completed, non-failed) tasks"""
        try:
            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, name, source_file, status, completion_criteria_json,
                           created_at, started_at, completed_at, iteration_count,
                           max_iterations, last_continuation_at, error_message, metadata_json
                    FROM tasks
                    WHERE status NOT IN ('completed', 'failed', 'cancelled')
                    ORDER BY created_at ASC
                """)

                tasks = []
                for row in cursor.fetchall():
                    task = self._row_to_task(row)
                    if task:
                        tasks.append(task)
                return tasks
        except Exception as e:
            self.logger.error("Failed to get active tasks", error=str(e))
            return []

    def get_tasks_by_status(self, status: TaskStatus) -> List[TrackedTask]:
        """Get all tasks with a specific status"""
        try:
            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, name, source_file, status, completion_criteria_json,
                           created_at, started_at, completed_at, iteration_count,
                           max_iterations, last_continuation_at, error_message, metadata_json
                    FROM tasks
                    WHERE status = ?
                    ORDER BY created_at ASC
                """, (status.value,))

                tasks = []
                for row in cursor.fetchall():
                    task = self._row_to_task(row)
                    if task:
                        tasks.append(task)
                return tasks
        except Exception as e:
            self.logger.error("Failed to get tasks by status", status=status.value, error=str(e))
            return []

    def _row_to_task(self, row: tuple) -> Optional[TrackedTask]:
        """Convert database row to TrackedTask"""
        try:
            (task_id, name, source_file, status, completion_criteria_json,
             created_at, started_at, completed_at, iteration_count,
             max_iterations, last_continuation_at, error_message, metadata_json) = row

            return TrackedTask(
                id=task_id,
                name=name,
                source_file=source_file,
                status=TaskStatus(status),
                completion_criteria=CompletionCriteria.from_dict(
                    json.loads(completion_criteria_json) if completion_criteria_json else {}
                ),
                created_at=datetime.fromisoformat(created_at) if created_at else datetime.now(),
                started_at=datetime.fromisoformat(started_at) if started_at else None,
                completed_at=datetime.fromisoformat(completed_at) if completed_at else None,
                iteration_count=iteration_count or 0,
                max_iterations=max_iterations or 5,
                last_continuation_at=datetime.fromisoformat(last_continuation_at) if last_continuation_at else None,
                error_message=error_message,
                metadata=json.loads(metadata_json) if metadata_json else {}
            )
        except Exception as e:
            self.logger.error("Failed to parse task row", error=str(e))
            return None

    def update_task_status(
        self,
        task_id: str,
        new_status: TaskStatus,
        error_message: str = None
    ) -> bool:
        """Update task status"""
        task = self.get_task(task_id)
        if not task:
            return False

        old_status = task.status
        task.status = new_status

        if new_status == TaskStatus.IN_PROGRESS and not task.started_at:
            task.started_at = datetime.now()
        elif new_status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
            task.completed_at = datetime.now()

        if error_message:
            task.error_message = error_message

        if self._save_task(task):
            self._log_history(task_id, "status_change", old_status.value, new_status.value)
            self.logger.info("Task status updated", task_id=task_id, old_status=old_status.value, new_status=new_status.value)
            return True

        return False

    def increment_iteration(self, task_id: str) -> Optional[int]:
        """Increment task iteration count"""
        task = self.get_task(task_id)
        if not task:
            return None

        task.iteration_count += 1
        task.last_continuation_at = datetime.now()

        if self._save_task(task):
            self._log_history(task_id, "iteration", None, None, f"Iteration {task.iteration_count}")
            return task.iteration_count

        return None

    def _log_history(
        self,
        task_id: str,
        action: str,
        old_status: str = None,
        new_status: str = None,
        details: str = None
    ):
        """Log task history entry"""
        try:
            history_id = f"hist_{uuid4().hex[:8]}"
            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO task_history
                    (id, task_id, action, old_status, new_status, details, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    history_id,
                    task_id,
                    action,
                    old_status,
                    new_status,
                    details,
                    datetime.now().isoformat()
                ))
                conn.commit()
        except Exception as e:
            self.logger.warning("Failed to log task history", task_id=task_id, error=str(e))

    def get_task_history(self, task_id: str) -> List[dict]:
        """Get history for a task"""
        try:
            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, task_id, action, old_status, new_status, details, timestamp
                    FROM task_history
                    WHERE task_id = ?
                    ORDER BY timestamp ASC
                """, (task_id,))

                history = []
                for row in cursor.fetchall():
                    history.append({
                        "id": row[0],
                        "task_id": row[1],
                        "action": row[2],
                        "old_status": row[3],
                        "new_status": row[4],
                        "details": row[5],
                        "timestamp": row[6]
                    })
                return history
        except Exception as e:
            self.logger.error("Failed to get task history", task_id=task_id, error=str(e))
            return []

    def get_global_iteration_count(self) -> int:
        """Get global iteration count"""
        try:
            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT value FROM global_state WHERE key = 'global_iteration_count'
                """)
                row = cursor.fetchone()
                return int(row[0]) if row else 0
        except Exception:
            return 0

    def increment_global_iteration(self) -> int:
        """Increment global iteration count"""
        try:
            current = self.get_global_iteration_count()
            new_count = current + 1

            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO global_state (key, value, updated_at)
                    VALUES ('global_iteration_count', ?, CURRENT_TIMESTAMP)
                """, (str(new_count),))
                conn.commit()

            return new_count
        except Exception as e:
            self.logger.error("Failed to increment global iteration", error=str(e))
            return -1

    def reset_global_iteration(self):
        """Reset global iteration count"""
        try:
            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO global_state (key, value, updated_at)
                    VALUES ('global_iteration_count', '0', CURRENT_TIMESTAMP)
                """)
                conn.commit()
        except Exception as e:
            self.logger.error("Failed to reset global iteration", error=str(e))

    def cleanup_old_tasks(self, days: int = 30) -> int:
        """Clean up tasks older than specified days"""
        try:
            from datetime import timedelta
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()

            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM tasks
                    WHERE status IN ('completed', 'failed', 'cancelled')
                    AND completed_at < ?
                """, (cutoff,))
                deleted = cursor.rowcount
                conn.commit()

            self.logger.info("Cleaned up old tasks", count=deleted, days=days)
            return deleted
        except Exception as e:
            self.logger.error("Failed to cleanup old tasks", error=str(e))
            return 0
