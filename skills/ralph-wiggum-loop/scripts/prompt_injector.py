#!/usr/bin/env python3
"""
Prompt Injector for Ralph Wiggum Loop

Re-injects continuation prompts when Claude attempts to exit before task completion.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional

import structlog

from .models import RalphWiggumConfig, TaskStatus, TrackedTask

logger = structlog.get_logger()


class PromptInjector:
    """Generates and injects continuation prompts for incomplete tasks"""

    def __init__(self, config: RalphWiggumConfig = None):
        self.config = config or RalphWiggumConfig()
        self.logger = logger.bind(component="PromptInjector")

    def get_continuation_prompt(self, task: TrackedTask, context: dict = None) -> str:
        """
        Generate a continuation prompt for an incomplete task.

        Args:
            task: The task that needs continuation
            context: Optional additional context (errors, previous output, etc.)

        Returns:
            Continuation prompt string
        """
        iteration = task.iteration_count + 1
        max_iter = task.max_iterations

        # Build the continuation prompt
        prompt_parts = [
            f"## Task Continuation (Iteration {iteration}/{max_iter})",
            "",
            f"**Task:** {task.name}",
            f"**Source File:** {task.source_file}",
            f"**Status:** {task.status.value}",
            "",
            "---",
            "",
            "The task is not yet complete. Please continue working on it.",
            "",
        ]

        # Add completion criteria reminder
        prompt_parts.extend([
            "**Completion Criteria:**",
            self._format_completion_criteria(task),
            "",
        ])

        # Add context if provided
        if context:
            if context.get("last_error"):
                prompt_parts.extend([
                    "**Previous Error:**",
                    f"```",
                    context["last_error"],
                    "```",
                    "",
                ])

            if context.get("last_output"):
                prompt_parts.extend([
                    "**Previous Output (truncated):**",
                    f"```",
                    context["last_output"][:500],
                    "```",
                    "",
                ])

            if context.get("hints"):
                prompt_parts.extend([
                    "**Hints:**",
                    *[f"- {hint}" for hint in context["hints"]],
                    "",
                ])

        # Add instructions
        prompt_parts.extend([
            "---",
            "",
            "**Instructions:**",
            "1. Review the task requirements and current state",
            "2. Continue from where you left off",
            "3. Move the task file to `/vault/Done/` when complete",
            f"4. You have {max_iter - iteration} iterations remaining",
            "",
        ])

        # Add warning if running low on iterations
        if iteration >= max_iter - 2:
            prompt_parts.extend([
                "**WARNING:** Running low on iterations. Please prioritize completing the task.",
                "",
            ])

        return "\n".join(prompt_parts)

    def _format_completion_criteria(self, task: TrackedTask) -> str:
        """Format completion criteria as human-readable string"""
        criteria = task.completion_criteria

        if criteria.type.value == "file_moved":
            return f"- Move file to `{criteria.destination_folder or self.config.done_folder}`"
        elif criteria.type.value == "status_marker":
            markers = criteria.status_markers or self.config.completion_markers
            return f"- Add one of these markers to the file: {', '.join(markers)}"
        elif criteria.type.value == "custom_criteria":
            return f"- Custom criteria: `{criteria.custom_check}`"
        else:
            return "- Unknown completion criteria"

    def get_failure_prompt(self, task: TrackedTask, reason: str) -> str:
        """
        Generate a failure notification prompt when max iterations reached.

        Args:
            task: The failed task
            reason: Reason for failure

        Returns:
            Failure prompt string
        """
        return f"""## Task Failed

**Task:** {task.name}
**Source File:** {task.source_file}
**Iterations Used:** {task.iteration_count}/{task.max_iterations}
**Reason:** {reason}

The task has been moved to `/vault/Failed/` for manual review.

**Next Steps:**
1. Review the task history for debugging
2. Check if the completion criteria were achievable
3. Consider breaking the task into smaller subtasks
4. Manually complete the task or re-queue with adjusted parameters
"""

    def get_success_prompt(self, task: TrackedTask) -> str:
        """
        Generate a success notification prompt.

        Args:
            task: The completed task

        Returns:
            Success prompt string
        """
        duration = ""
        if task.started_at and task.completed_at:
            delta = task.completed_at - task.started_at
            duration = f"\n**Duration:** {delta}"

        return f"""## Task Completed Successfully

**Task:** {task.name}
**Source File:** {task.source_file}
**Iterations Used:** {task.iteration_count}/{task.max_iterations}{duration}

The task has been marked as complete and moved to `/vault/Done/`.
"""

    def get_emergency_stop_prompt(self) -> str:
        """Generate emergency stop notification prompt"""
        return """## Emergency Stop Activated

The Ralph Wiggum Loop has been stopped by emergency stop file.

**Action Required:**
1. Remove the `.ralph_stop` file to resume operations
2. Review any in-progress tasks
3. Check system logs for issues

All active tasks have been paused but not marked as failed.
"""

    def create_task_file(self, task: TrackedTask, output_folder: str = None) -> Optional[str]:
        """
        Create a task file in the Needs_Action folder.

        Args:
            task: The task to create a file for
            output_folder: Optional output folder (defaults to needs_action_folder)

        Returns:
            Path to created file, or None if failed
        """
        folder = Path(output_folder or self.config.needs_action_folder)
        folder.mkdir(parents=True, exist_ok=True)

        filename = f"{task.id}_{self._sanitize_filename(task.name)}.md"
        filepath = folder / filename

        content = f"""---
task_id: {task.id}
name: {task.name}
status: {task.status.value}
created_at: {task.created_at.isoformat()}
max_iterations: {task.max_iterations}
---

# {task.name}

## Description
{task.metadata.get('description', 'No description provided.')}

## Source
{task.source_file}

## Completion Criteria
{self._format_completion_criteria(task)}

## Progress
- [ ] Task started
- [ ] Work in progress
- [ ] Task completed

## Notes
_Add notes here as you work on the task._
"""

        try:
            filepath.write_text(content, encoding="utf-8")
            self.logger.info("Task file created", task_id=task.id, path=str(filepath))
            return str(filepath)
        except Exception as e:
            self.logger.error("Failed to create task file", task_id=task.id, error=str(e))
            return None

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize a string for use as a filename"""
        # Replace spaces and special characters
        sanitized = name.lower()
        for char in [" ", "/", "\\", ":", "*", "?", '"', "<", ">", "|"]:
            sanitized = sanitized.replace(char, "_")
        # Limit length
        return sanitized[:50]

    def move_task_file(self, task: TrackedTask, destination_folder: str) -> bool:
        """
        Move a task file to a destination folder.

        Args:
            task: The task whose file should be moved
            destination_folder: Target folder

        Returns:
            True if successful, False otherwise
        """
        source = Path(task.source_file)
        dest_folder = Path(destination_folder)

        if not source.exists():
            self.logger.warning("Source file not found", path=str(source))
            return False

        dest_folder.mkdir(parents=True, exist_ok=True)
        dest_path = dest_folder / source.name

        try:
            source.rename(dest_path)
            self.logger.info("Task file moved", source=str(source), destination=str(dest_path))
            return True
        except Exception as e:
            self.logger.error("Failed to move task file", error=str(e))
            return False


class ContinuationPromptBuilder:
    """Builder for creating customized continuation prompts"""

    def __init__(self, task: TrackedTask):
        self.task = task
        self._context = {}
        self._custom_instructions = []
        self._priority = "normal"

    def with_error(self, error: str) -> "ContinuationPromptBuilder":
        """Add error context"""
        self._context["last_error"] = error
        return self

    def with_output(self, output: str) -> "ContinuationPromptBuilder":
        """Add previous output context"""
        self._context["last_output"] = output
        return self

    def with_hints(self, hints: list) -> "ContinuationPromptBuilder":
        """Add hints for the agent"""
        self._context["hints"] = hints
        return self

    def with_instruction(self, instruction: str) -> "ContinuationPromptBuilder":
        """Add custom instruction"""
        self._custom_instructions.append(instruction)
        return self

    def with_priority(self, priority: str) -> "ContinuationPromptBuilder":
        """Set priority level (low, normal, high, critical)"""
        self._priority = priority
        return self

    def build(self) -> str:
        """Build the continuation prompt"""
        injector = PromptInjector()
        prompt = injector.get_continuation_prompt(self.task, self._context)

        if self._custom_instructions:
            prompt += "\n**Additional Instructions:**\n"
            for instr in self._custom_instructions:
                prompt += f"- {instr}\n"

        if self._priority != "normal":
            prompt = f"**Priority: {self._priority.upper()}**\n\n" + prompt

        return prompt
