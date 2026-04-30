"""
Ralph Wiggum Loop - Autonomous Task Completion System

Ensures Claude Code persists until tasks are fully completed.
"""

from .ralph_wiggum import RalphWiggumLoop, TaskState, TaskStatus
from .task_tracker import TaskTracker, TrackedTask
from .completion_detector import CompletionDetector, CompletionCriteria
from .prompt_injector import PromptInjector

__all__ = [
    "RalphWiggumLoop",
    "TaskState",
    "TaskStatus",
    "TaskTracker",
    "TrackedTask",
    "CompletionDetector",
    "CompletionCriteria",
    "PromptInjector",
]
