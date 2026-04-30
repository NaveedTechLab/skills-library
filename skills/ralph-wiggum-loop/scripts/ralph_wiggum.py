#!/usr/bin/env python3
"""
Ralph Wiggum Loop - Main Controller

Autonomous task completion system that ensures Claude Code persists
until tasks are fully completed.
"""

import asyncio
import json
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import structlog

# Add parent path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from .completion_detector import CompletionDetector
from .models import (
    CompletionCriteria,
    CompletionType,
    RalphWiggumConfig,
    TaskState,
    TaskStatus,
    TrackedTask,
)
from .prompt_injector import PromptInjector
from .task_tracker import TaskTracker

logger = structlog.get_logger()


class RalphWiggumLoop:
    """
    Main controller for the Ralph Wiggum autonomous task loop.

    Ensures Claude Code persists until tasks are fully completed by:
    1. Tracking task state in SQLite
    2. Detecting completion via file location or markers
    3. Re-injecting continuation prompts on premature exit
    4. Enforcing iteration limits for safety
    """

    def __init__(self, config: RalphWiggumConfig = None):
        self.config = config or RalphWiggumConfig()
        self.tracker = TaskTracker(self.config)
        self.detector = CompletionDetector(self.config)
        self.injector = PromptInjector(self.config)
        self.logger = logger.bind(component="RalphWiggumLoop")

        # Callbacks for integration
        self._on_task_complete: Optional[Callable] = None
        self._on_task_failed: Optional[Callable] = None
        self._on_continuation: Optional[Callable] = None

        # Audit logger integration (optional)
        self._audit_logger = None
        self._init_audit_logger()

    def _init_audit_logger(self):
        """Initialize audit logger if available"""
        if self.config.enable_audit_logging:
            try:
                from phase_3.audit_logger import get_global_audit_logger
                self._audit_logger = get_global_audit_logger()
                self.logger.info("Audit logger initialized")
            except ImportError:
                self.logger.warning("Audit logger not available, proceeding without it")

    def register_task(
        self,
        name: str,
        source_file: str,
        completion_criteria: CompletionCriteria = None,
        max_iterations: int = None,
        metadata: dict = None
    ) -> str:
        """
        Register a new task for tracking.

        Args:
            name: Human-readable task name
            source_file: Path to the task file
            completion_criteria: How to detect completion
            max_iterations: Maximum iterations for this task
            metadata: Additional task metadata

        Returns:
            Task ID
        """
        task = self.tracker.create_task(
            name=name,
            source_file=source_file,
            completion_criteria=completion_criteria,
            max_iterations=max_iterations or self.config.max_task_iterations,
            metadata=metadata or {}
        )

        self._log_audit("task.registered", task.id, {"name": name, "source_file": source_file})
        self.logger.info("Task registered", task_id=task.id, name=name)

        return task.id

    def start_task(self, task_id: str) -> bool:
        """
        Start working on a task.

        Args:
            task_id: The task to start

        Returns:
            True if task started successfully
        """
        task = self.tracker.get_task(task_id)
        if not task:
            self.logger.error("Task not found", task_id=task_id)
            return False

        if task.status not in (TaskStatus.PENDING, TaskStatus.AWAITING_COMPLETION):
            self.logger.warning("Task cannot be started", task_id=task_id, status=task.status.value)
            return False

        self.tracker.update_task_status(task_id, TaskStatus.IN_PROGRESS)
        self._log_audit("task.started", task_id, {})

        return True

    def check_task_completion(self, task_id: str) -> Tuple[bool, str]:
        """
        Check if a task is complete.

        Args:
            task_id: The task to check

        Returns:
            Tuple of (is_complete, reason)
        """
        task = self.tracker.get_task(task_id)
        if not task:
            return False, "Task not found"

        # Check emergency stop first
        if self.detector.check_emergency_stop():
            return False, "Emergency stop active"

        # Check completion criteria
        is_complete, reason = self.detector.check_completion(task)

        if is_complete:
            self._complete_task(task, reason)
            return True, reason

        # Check max iterations
        max_exceeded, iter_status = self.detector.check_max_iterations(task)
        if max_exceeded:
            self._fail_task(task, iter_status)
            return False, iter_status

        return False, reason

    def should_continue(self, task_id: str = None) -> Tuple[bool, str, Optional[str]]:
        """
        Check if processing should continue (called by stop hook).

        Args:
            task_id: Optional specific task to check, or checks all active

        Returns:
            Tuple of (should_continue, reason, continuation_prompt)
        """
        # Check emergency stop
        if self.detector.check_emergency_stop():
            return False, "Emergency stop", None

        # Check global iteration limit
        global_count = self.tracker.get_global_iteration_count()
        if global_count >= self.config.max_global_iterations:
            self.logger.warning("Global iteration limit reached", count=global_count)
            return False, "Global iteration limit reached", None

        # If specific task provided, check it
        if task_id:
            task = self.tracker.get_task(task_id)
            if not task:
                return False, "Task not found", None

            is_complete, reason = self.check_task_completion(task_id)
            if is_complete:
                return False, reason, None

            # Task not complete, generate continuation
            return self._generate_continuation(task)

        # Check all active tasks
        active_tasks = self.tracker.get_active_tasks()
        if not active_tasks:
            return False, "No active tasks", None

        # Check each active task
        for task in active_tasks:
            is_complete, reason = self.check_task_completion(task.id)
            if not is_complete:
                # Found incomplete task, generate continuation
                return self._generate_continuation(task)

        return False, "All tasks complete", None

    def _generate_continuation(self, task: TrackedTask) -> Tuple[bool, str, str]:
        """Generate continuation prompt for a task"""
        # Increment iterations
        self.tracker.increment_iteration(task.id)
        self.tracker.increment_global_iteration()

        # Refresh task data
        task = self.tracker.get_task(task.id)

        # Check if we've exceeded limits after increment
        if task.iteration_count >= task.max_iterations:
            self._fail_task(task, "Max iterations reached")
            return False, "Max iterations reached", None

        # Generate continuation prompt
        prompt = self.injector.get_continuation_prompt(task)

        self._log_audit("task.continuation", task.id, {"iteration": task.iteration_count})

        if self._on_continuation:
            self._on_continuation(task, prompt)

        return True, f"Continuing task (iteration {task.iteration_count})", prompt

    def _complete_task(self, task: TrackedTask, reason: str):
        """Mark a task as complete"""
        self.tracker.update_task_status(task.id, TaskStatus.COMPLETED)

        # Move file to Done folder if needed
        self.injector.move_task_file(task, self.config.done_folder)

        self._log_audit("task.completed", task.id, {"reason": reason})
        self.logger.info("Task completed", task_id=task.id, reason=reason)

        if self._on_task_complete:
            self._on_task_complete(task, reason)

    def _fail_task(self, task: TrackedTask, reason: str):
        """Mark a task as failed"""
        self.tracker.update_task_status(task.id, TaskStatus.FAILED, error_message=reason)

        # Move file to Failed folder
        self.injector.move_task_file(task, self.config.failed_folder)

        self._log_audit("task.failed", task.id, {"reason": reason})
        self.logger.error("Task failed", task_id=task.id, reason=reason)

        if self._on_task_failed:
            self._on_task_failed(task, reason)

    def force_complete_task(self, task_id: str, reason: str = "Manual override") -> bool:
        """
        Force a task to complete (manual override).

        Args:
            task_id: Task to complete
            reason: Reason for forced completion

        Returns:
            True if successful
        """
        task = self.tracker.get_task(task_id)
        if not task:
            return False

        self._complete_task(task, f"FORCED: {reason}")
        return True

    def cancel_task(self, task_id: str, reason: str = "Cancelled by user") -> bool:
        """
        Cancel a task.

        Args:
            task_id: Task to cancel
            reason: Cancellation reason

        Returns:
            True if successful
        """
        task = self.tracker.get_task(task_id)
        if not task:
            return False

        self.tracker.update_task_status(task_id, TaskStatus.CANCELLED, error_message=reason)
        self._log_audit("task.cancelled", task_id, {"reason": reason})

        return True

    def get_task_status(self, task_id: str) -> Optional[dict]:
        """Get detailed status for a task"""
        task = self.tracker.get_task(task_id)
        if not task:
            return None

        completion_status = self.detector.get_completion_status(task)
        history = self.tracker.get_task_history(task_id)

        return {
            "task": task.to_dict(),
            "completion": completion_status,
            "history": history
        }

    def get_all_active_tasks(self) -> List[dict]:
        """Get all active tasks with their status"""
        tasks = self.tracker.get_active_tasks()
        return [
            {
                "task": t.to_dict(),
                "completion": self.detector.get_completion_status(t)
            }
            for t in tasks
        ]

    def get_state(self) -> TaskState:
        """Get current state snapshot"""
        return TaskState(
            active_tasks=self.tracker.get_active_tasks(),
            global_iteration_count=self.tracker.get_global_iteration_count(),
            max_global_iterations=self.config.max_global_iterations,
            emergency_stop=self.detector.check_emergency_stop(),
            last_check_at=datetime.now()
        )

    def trigger_emergency_stop(self, reason: str = "Manual stop"):
        """Create emergency stop file"""
        stop_file = Path(self.config.emergency_stop_file)
        stop_file.write_text(f"Emergency stop triggered at {datetime.now().isoformat()}\nReason: {reason}")
        self._log_audit("emergency_stop.triggered", None, {"reason": reason})
        self.logger.warning("Emergency stop triggered", reason=reason)

    def clear_emergency_stop(self):
        """Remove emergency stop file"""
        stop_file = Path(self.config.emergency_stop_file)
        if stop_file.exists():
            stop_file.unlink()
            self._log_audit("emergency_stop.cleared", None, {})
            self.logger.info("Emergency stop cleared")

    def reset(self):
        """Reset the loop state"""
        self.tracker.reset_global_iteration()
        self.clear_emergency_stop()
        self._log_audit("loop.reset", None, {})
        self.logger.info("Ralph Wiggum Loop reset")

    def _log_audit(self, action_type: str, task_id: Optional[str], metadata: dict):
        """Log to audit system if available"""
        if self._audit_logger:
            try:
                self._audit_logger.log_action(
                    action_type=f"ralph_wiggum.{action_type}",
                    target=task_id or "system",
                    approval_status="automated",
                    result="success",
                    additional_metadata=metadata
                )
            except Exception as e:
                self.logger.warning("Failed to log audit", error=str(e))

    # Callback setters
    def on_task_complete(self, callback: Callable[[TrackedTask, str], None]):
        """Set callback for task completion"""
        self._on_task_complete = callback

    def on_task_failed(self, callback: Callable[[TrackedTask, str], None]):
        """Set callback for task failure"""
        self._on_task_failed = callback

    def on_continuation(self, callback: Callable[[TrackedTask, str], None]):
        """Set callback for continuation prompts"""
        self._on_continuation = callback


class RalphWiggumHook:
    """
    Hook interface for integration with Claude Code stop mechanism.

    This class provides the interface that Claude Code's stop hook
    calls to determine whether to allow exit or inject continuation.
    """

    def __init__(self, loop: RalphWiggumLoop = None):
        self.loop = loop or RalphWiggumLoop()
        self.logger = logger.bind(component="RalphWiggumHook")

    def on_exit_attempt(self, context: dict = None) -> dict:
        """
        Called when Claude Code attempts to exit.

        Args:
            context: Optional context from the exit attempt

        Returns:
            Dict with:
            - allow_exit: bool - whether to allow the exit
            - continuation_prompt: str - prompt to inject if not allowing exit
            - reason: str - reason for the decision
        """
        should_continue, reason, prompt = self.loop.should_continue()

        if should_continue:
            self.logger.info("Exit blocked, continuing", reason=reason)
            return {
                "allow_exit": False,
                "continuation_prompt": prompt,
                "reason": reason
            }
        else:
            self.logger.info("Exit allowed", reason=reason)
            return {
                "allow_exit": True,
                "continuation_prompt": None,
                "reason": reason
            }

    def register_task_from_file(self, file_path: str) -> Optional[str]:
        """
        Register a task from a file in the Needs_Action folder.

        Args:
            file_path: Path to the task file

        Returns:
            Task ID if successful
        """
        path = Path(file_path)
        if not path.exists():
            return None

        # Parse task metadata from file
        content = path.read_text(encoding="utf-8")
        metadata = self._parse_task_metadata(content)

        task_id = self.loop.register_task(
            name=metadata.get("name", path.stem),
            source_file=str(path),
            metadata=metadata
        )

        return task_id

    def _parse_task_metadata(self, content: str) -> dict:
        """Parse YAML frontmatter from task file"""
        metadata = {}

        if content.startswith("---"):
            try:
                end = content.find("---", 3)
                if end > 0:
                    import yaml
                    frontmatter = content[3:end].strip()
                    metadata = yaml.safe_load(frontmatter) or {}
            except Exception:
                pass

        return metadata


# Convenience functions
def create_ralph_wiggum_loop(config_path: str = None) -> RalphWiggumLoop:
    """Create a configured Ralph Wiggum Loop instance"""
    config = RalphWiggumConfig()

    if config_path:
        config_file = Path(config_path)
        if config_file.exists():
            with open(config_file) as f:
                config_data = json.load(f)
                config = RalphWiggumConfig.from_dict(config_data.get("ralph_wiggum", {}))

    return RalphWiggumLoop(config)


def demo_ralph_wiggum():
    """Demo the Ralph Wiggum Loop"""
    print("Ralph Wiggum Loop Demo")
    print("=" * 40)

    # Create loop instance
    loop = RalphWiggumLoop()

    # Register a sample task
    task_id = loop.register_task(
        name="Process test document",
        source_file="./vault/Needs_Action/test_task.md",
        metadata={"description": "Test task for demo"}
    )
    print(f"Registered task: {task_id}")

    # Start the task
    loop.start_task(task_id)
    print("Task started")

    # Check completion (will be false)
    is_complete, reason = loop.check_task_completion(task_id)
    print(f"Task complete: {is_complete}, Reason: {reason}")

    # Check if should continue
    should_continue, reason, prompt = loop.should_continue(task_id)
    print(f"Should continue: {should_continue}")
    if prompt:
        print(f"Continuation prompt preview:\n{prompt[:200]}...")

    # Get task status
    status = loop.get_task_status(task_id)
    print(f"Task status: {json.dumps(status, indent=2, default=str)}")


if __name__ == "__main__":
    demo_ralph_wiggum()
