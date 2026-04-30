#!/usr/bin/env python3
"""
Completion Detector for Ralph Wiggum Loop

Detects task completion based on various criteria:
- File moved to /Done folder
- Status markers in file content
- Custom completion criteria
"""

import os
from pathlib import Path
from typing import Optional, Tuple

import structlog

from .models import CompletionCriteria, CompletionType, RalphWiggumConfig, TrackedTask

logger = structlog.get_logger()


class CompletionDetector:
    """Detects task completion based on configured criteria"""

    def __init__(self, config: RalphWiggumConfig = None):
        self.config = config or RalphWiggumConfig()
        self.logger = logger.bind(component="CompletionDetector")

    def check_completion(self, task: TrackedTask) -> Tuple[bool, str]:
        """
        Check if a task is complete based on its completion criteria.

        Returns:
            Tuple of (is_complete, reason)
        """
        criteria = task.completion_criteria

        if criteria.type == CompletionType.FILE_MOVED:
            return self._check_file_moved(task)
        elif criteria.type == CompletionType.STATUS_MARKER:
            return self._check_status_marker(task)
        elif criteria.type == CompletionType.CUSTOM_CRITERIA:
            return self._check_custom_criteria(task)
        else:
            self.logger.warning("Unknown completion type", type=criteria.type)
            return False, f"Unknown completion type: {criteria.type}"

    def _check_file_moved(self, task: TrackedTask) -> Tuple[bool, str]:
        """Check if the task file has been moved to the Done folder"""
        source_path = Path(task.source_file)
        source_filename = source_path.name

        # Determine destination folder
        done_folder = Path(
            task.completion_criteria.destination_folder or self.config.done_folder
        )

        # Check if file exists in Done folder
        done_path = done_folder / source_filename

        if done_path.exists():
            self.logger.info("Task file found in Done folder", task_id=task.id, path=str(done_path))
            return True, f"File moved to {done_folder}"

        # Also check if the original file no longer exists (moved somewhere)
        if not source_path.exists():
            # File moved, check if it's in the done folder with a different name
            # or has been processed
            self.logger.info("Source file no longer exists", task_id=task.id, source=str(source_path))

            # Look for files with similar names in Done folder
            for done_file in done_folder.glob("*"):
                if source_filename.split(".")[0] in done_file.name:
                    return True, f"Related file found in Done: {done_file.name}"

            # If file is gone but not in Done, it might still be processing
            return False, "Source file not found, may be in transit"

        return False, "File not yet in Done folder"

    def _check_status_marker(self, task: TrackedTask) -> Tuple[bool, str]:
        """Check if the task file contains a completion status marker"""
        source_path = Path(task.source_file)

        if not source_path.exists():
            # File might have been moved, check Done folder
            return self._check_file_moved(task)

        try:
            content = source_path.read_text(encoding="utf-8")
            markers = task.completion_criteria.status_markers or self.config.completion_markers

            for marker in markers:
                if marker.lower() in content.lower():
                    self.logger.info(
                        "Completion marker found",
                        task_id=task.id,
                        marker=marker
                    )
                    return True, f"Found completion marker: {marker}"

            return False, "No completion marker found in file"

        except Exception as e:
            self.logger.error("Failed to read task file", task_id=task.id, error=str(e))
            return False, f"Error reading file: {str(e)}"

    def _check_custom_criteria(self, task: TrackedTask) -> Tuple[bool, str]:
        """Check custom completion criteria"""
        custom_check = task.completion_criteria.custom_check

        if not custom_check:
            self.logger.warning("No custom check defined", task_id=task.id)
            return False, "No custom criteria defined"

        try:
            # Create a safe evaluation context
            context = {
                "task": task,
                "source_file": Path(task.source_file),
                "done_folder": Path(self.config.done_folder),
                "exists": os.path.exists,
                "Path": Path,
            }

            # Evaluate the custom criteria
            # Note: In production, this should use a safer evaluation method
            result = eval(custom_check, {"__builtins__": {}}, context)

            if result:
                return True, "Custom criteria satisfied"
            else:
                return False, "Custom criteria not yet satisfied"

        except Exception as e:
            self.logger.error("Custom criteria evaluation failed", task_id=task.id, error=str(e))
            return False, f"Custom criteria error: {str(e)}"

    def check_max_iterations(self, task: TrackedTask) -> Tuple[bool, str]:
        """Check if task has exceeded maximum iterations"""
        if task.iteration_count >= task.max_iterations:
            return True, f"Max iterations ({task.max_iterations}) reached"
        return False, f"Iteration {task.iteration_count}/{task.max_iterations}"

    def check_emergency_stop(self) -> bool:
        """Check if emergency stop file exists"""
        stop_file = Path(self.config.emergency_stop_file)
        if stop_file.exists():
            self.logger.warning("Emergency stop file detected")
            return True
        return False

    def get_completion_status(self, task: TrackedTask) -> dict:
        """Get detailed completion status for a task"""
        is_complete, reason = self.check_completion(task)
        max_exceeded, iteration_status = self.check_max_iterations(task)
        emergency_stop = self.check_emergency_stop()

        return {
            "task_id": task.id,
            "is_complete": is_complete,
            "completion_reason": reason,
            "max_iterations_exceeded": max_exceeded,
            "iteration_status": iteration_status,
            "emergency_stop": emergency_stop,
            "current_iteration": task.iteration_count,
            "max_iterations": task.max_iterations,
            "should_continue": not is_complete and not max_exceeded and not emergency_stop
        }


class CompletionCriteriaBuilder:
    """Builder class for creating completion criteria"""

    def __init__(self):
        self._type = CompletionType.FILE_MOVED
        self._destination_folder = None
        self._status_markers = ["status: completed", "## Completed"]
        self._custom_check = None

    def file_moved_to(self, folder: str) -> "CompletionCriteriaBuilder":
        """Complete when file is moved to specified folder"""
        self._type = CompletionType.FILE_MOVED
        self._destination_folder = folder
        return self

    def status_marker(self, markers: list) -> "CompletionCriteriaBuilder":
        """Complete when file contains any of the specified markers"""
        self._type = CompletionType.STATUS_MARKER
        self._status_markers = markers
        return self

    def custom(self, expression: str) -> "CompletionCriteriaBuilder":
        """Complete when custom expression evaluates to True"""
        self._type = CompletionType.CUSTOM_CRITERIA
        self._custom_check = expression
        return self

    def build(self) -> CompletionCriteria:
        """Build the completion criteria"""
        return CompletionCriteria(
            type=self._type,
            destination_folder=self._destination_folder,
            status_markers=self._status_markers,
            custom_check=self._custom_check
        )


# Convenience function
def create_file_moved_criteria(done_folder: str = "./vault/Done/") -> CompletionCriteria:
    """Create criteria for file-moved completion detection"""
    return CompletionCriteriaBuilder().file_moved_to(done_folder).build()


def create_status_marker_criteria(markers: list = None) -> CompletionCriteria:
    """Create criteria for status-marker completion detection"""
    return CompletionCriteriaBuilder().status_marker(
        markers or ["status: completed", "## Completed"]
    ).build()
