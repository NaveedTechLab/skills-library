#!/usr/bin/env python3
"""
Job Management System for Scheduler Cron Integration

Provides advanced job management capabilities including creation, monitoring,
and lifecycle management of scheduled jobs.
"""

import asyncio
import json
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union
from uuid import uuid4

import structlog
from scheduler_core import (
    JobDefinition, JobExecutionRecord, JobState, JobStatus,
    JobPriority, SQLiteJobStorage, Scheduler, create_job_definition
)

logger = structlog.get_logger()


class JobEventType(Enum):
    """Types of job events for monitoring"""
    JOB_CREATED = "job_created"
    JOB_SCHEDULED = "job_scheduled"
    JOB_STARTED = "job_started"
    JOB_COMPLETED = "job_completed"
    JOB_FAILED = "job_failed"
    JOB_PAUSED = "job_paused"
    JOB_RESUMED = "job_resumed"
    JOB_CANCELLED = "job_cancelled"
    JOB_UPDATED = "job_updated"


@dataclass
class JobEvent:
    """Event representing a job lifecycle change"""
    id: str
    job_id: str
    event_type: JobEventType
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)
    user: Optional[str] = None


class JobEventManager:
    """Manages job events and notifications"""

    def __init__(self):
        self.event_handlers: Dict[JobEventType, List[Callable]] = {}
        self.event_queue = []
        self.lock = threading.Lock()

    def register_handler(self, event_type: JobEventType, handler: Callable):
        """Register a handler for specific event types"""
        with self.lock:
            if event_type not in self.event_handlers:
                self.event_handlers[event_type] = []
            self.event_handlers[event_type].append(handler)

    def unregister_handler(self, event_type: JobEventType, handler: Callable):
        """Unregister a handler for specific event types"""
        with self.lock:
            if event_type in self.event_handlers:
                if handler in self.event_handlers[event_type]:
                    self.event_handlers[event_type].remove(handler)

    def emit_event(self, event: JobEvent):
        """Emit an event and notify all registered handlers"""
        with self.lock:
            self.event_queue.append(event)

            if event.event_type in self.event_handlers:
                for handler in self.event_handlers[event.event_type]:
                    try:
                        handler(event)
                    except Exception as e:
                        logger.error("Error in event handler", event=event.id, error=str(e))


class JobMonitor:
    """Monitors job execution and health"""

    def __init__(self, scheduler: Scheduler):
        self.scheduler = scheduler
        self.event_manager = JobEventManager()
        self.health_checks = {}
        self.alert_handlers = []
        self.monitoring_active = False
        self.monitoring_thread = None
        self.stop_event = threading.Event()

    def start_monitoring(self):
        """Start the monitoring system"""
        if self.monitoring_active:
            return

        self.monitoring_active = True
        self.stop_event.clear()
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()

        logger.info("Job monitoring started")

    def stop_monitoring(self):
        """Stop the monitoring system"""
        if not self.monitoring_active:
            return

        self.monitoring_active = False
        self.stop_event.set()

        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=2)

        logger.info("Job monitoring stopped")

    def _monitoring_loop(self):
        """Main monitoring loop"""
        while not self.stop_event.is_set() and self.monitoring_active:
            try:
                self._perform_health_checks()
                # Check every 30 seconds
                self.stop_event.wait(timeout=30)
            except Exception as e:
                logger.error("Error in monitoring loop", error=str(e))
                self.stop_event.wait(timeout=5)

    def _perform_health_checks(self):
        """Perform health checks on all jobs"""
        all_jobs = self.scheduler.jobs

        for job_id, job_state in all_jobs.items():
            try:
                self._check_job_health(job_id, job_state)
            except Exception as e:
                logger.error("Error checking job health", job_id=job_id, error=str(e))

    def _check_job_health(self, job_id: str, job_state: JobState):
        """Check the health of a specific job"""
        # Check if job is stuck in running state
        if (job_state.current_status == JobStatus.RUNNING and
            job_state.last_run_time and
            datetime.now() - job_state.last_run_time > timedelta(hours=1)):

            details = {
                "job_id": job_id,
                "duration": (datetime.now() - job_state.last_run_time).total_seconds(),
                "expected_timeout": job_state.job_definition.timeout_seconds
            }

            event = JobEvent(
                id=str(uuid4()),
                job_id=job_id,
                event_type=JobEventType.JOB_FAILED,
                timestamp=datetime.now(),
                details=details,
                user="system"
            )

            self.event_manager.emit_event(event)
            logger.warning("Job appears to be stuck", job_id=job_id, **details)

    def register_alert_handler(self, handler: Callable):
        """Register a handler for alerts"""
        self.alert_handlers.append(handler)

    def unregister_alert_handler(self, handler: Callable):
        """Unregister an alert handler"""
        if handler in self.alert_handlers:
            self.alert_handlers.remove(handler)


class JobValidator:
    """Validates job definitions before scheduling"""

    def __init__(self):
        self.max_timeout_seconds = 86400  # 24 hours
        self.max_retries = 10
        self.reserved_job_ids = {'system', 'core', 'internal'}

    def validate_job_definition(self, job_def: JobDefinition) -> List[str]:
        """Validate a job definition and return list of errors"""
        errors = []

        # Validate job ID
        if not job_def.id or not isinstance(job_def.id, str):
            errors.append("Job ID must be a non-empty string")

        if job_def.id.lower() in self.reserved_job_ids:
            errors.append(f"Job ID '{job_def.id}' is reserved")

        # Validate name
        if not job_def.name or not isinstance(job_def.name, str):
            errors.append("Job name must be a non-empty string")

        # Validate cron expression (already validated in JobDefinition)
        try:
            from scheduler_core import CronExpressionParser
            parser = CronExpressionParser()
            parser.normalize_expression(job_def.cron_expression)
        except ValueError as e:
            errors.append(f"Invalid cron expression: {e}")

        # Validate timeout
        if not isinstance(job_def.timeout_seconds, int) or job_def.timeout_seconds <= 0:
            errors.append("Timeout must be a positive integer")

        if job_def.timeout_seconds > self.max_timeout_seconds:
            errors.append(f"Timeout exceeds maximum of {self.max_timeout_seconds} seconds")

        # Validate retries
        if not isinstance(job_def.max_retries, int) or job_def.max_retries < 0:
            errors.append("Max retries must be a non-negative integer")

        if job_def.max_retries > self.max_retries:
            errors.append(f"Max retries exceeds maximum of {self.max_retries}")

        # Validate priority
        try:
            JobPriority(job_def.priority)
        except ValueError:
            errors.append("Invalid priority level")

        # Validate timezone
        try:
            from zoneinfo import ZoneInfo
            ZoneInfo(job_def.timezone)
        except Exception:
            errors.append(f"Invalid timezone: {job_def.timezone}")

        return errors

    def is_valid_job_definition(self, job_def: JobDefinition) -> bool:
        """Check if a job definition is valid"""
        return len(self.validate_job_definition(job_def)) == 0


class JobManager:
    """Main job management class"""

    def __init__(self, storage: Optional[SQLiteJobStorage] = None):
        self.storage = storage or SQLiteJobStorage()
        self.scheduler = Scheduler(self.storage)
        self.validator = JobValidator()
        self.monitor = JobMonitor(self.scheduler)
        self.event_manager = self.monitor.event_manager
        self.active_sessions = {}  # Track user sessions
        self.lock = threading.Lock()

    def create_job(self,
                   job_id: str,
                   name: str,
                   cron_expression: str,
                   callback: Union[str, Callable],
                   args: tuple = (),
                   kwargs: dict = None,
                   enabled: bool = True,
                   description: str = "",
                   priority: JobPriority = JobPriority.NORMAL,
                   timeout_seconds: int = 3600,
                   max_retries: int = 3,
                   retry_delay_seconds: int = 30,
                   timezone: str = "UTC",
                   user: str = "system") -> Optional[str]:
        """Create and schedule a new job"""
        job_def = create_job_definition(
            job_id=job_id,
            name=name,
            cron_expression=cron_expression,
            callback=callback,
            args=args,
            kwargs=kwargs or {},
            enabled=enabled,
            description=description,
            priority=priority,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            retry_delay_seconds=retry_delay_seconds,
            timezone=timezone
        )

        # Validate the job definition
        validation_errors = self.validator.validate_job_definition(job_def)
        if validation_errors:
            logger.error("Job validation failed", job_id=job_id, errors=validation_errors)
            return None

        # Schedule the job
        if self.scheduler.schedule_job(job_def):
            # Emit event
            event = JobEvent(
                id=str(uuid4()),
                job_id=job_id,
                event_type=JobEventType.JOB_CREATED,
                timestamp=datetime.now(),
                details={
                    "name": name,
                    "cron_expression": cron_expression,
                    "description": description
                },
                user=user
            )
            self.event_manager.emit_event(event)

            logger.info("Job created", job_id=job_id, user=user)
            return job_id
        else:
            logger.error("Failed to create job", job_id=job_id)
            return None

    def update_job(self, job_id: str, **updates) -> bool:
        """Update an existing job"""
        current_job = self.storage.load_job(job_id)
        if not current_job:
            return False

        # Update the job definition with provided values
        for key, value in updates.items():
            if hasattr(current_job, key):
                setattr(current_job, key, value)

        # Re-validate the updated job
        validation_errors = self.validator.validate_job_definition(current_job)
        if validation_errors:
            logger.error("Updated job validation failed", job_id=job_id, errors=validation_errors)
            return False

        # Save the updated job
        if self.storage.save_job(current_job):
            # Update scheduler state
            with self.scheduler.lock:
                if job_id in self.scheduler.jobs:
                    # Recalculate next run time if cron expression changed
                    if 'cron_expression' in updates:
                        next_run = self.scheduler.cron_parser.get_next_run_time(
                            current_job.cron_expression,
                            datetime.now()
                        )
                        self.scheduler.jobs[job_id].next_run_time = next_run

                    # Update the job definition in scheduler state
                    self.scheduler.jobs[job_id].job_definition = current_job

            # Emit event
            event = JobEvent(
                id=str(uuid4()),
                job_id=job_id,
                event_type=JobEventType.JOB_UPDATED,
                timestamp=datetime.now(),
                details=updates,
                user="system"
            )
            self.event_manager.emit_event(event)

            logger.info("Job updated", job_id=job_id)
            return True
        else:
            logger.error("Failed to update job", job_id=job_id)
            return False

    def delete_job(self, job_id: str, user: str = "system") -> bool:
        """Delete a scheduled job"""
        # Cancel the job in scheduler
        success = self.scheduler.cancel_job(job_id)

        if success:
            # Emit event
            event = JobEvent(
                id=str(uuid4()),
                job_id=job_id,
                event_type=JobEventType.JOB_CANCELLED,
                timestamp=datetime.now(),
                details={},
                user=user
            )
            self.event_manager.emit_event(event)

            logger.info("Job deleted", job_id=job_id, user=user)

        return success

    def pause_job(self, job_id: str, user: str = "system") -> bool:
        """Pause a scheduled job"""
        success = self.scheduler.pause_job(job_id)

        if success:
            # Emit event
            event = JobEvent(
                id=str(uuid4()),
                job_id=job_id,
                event_type=JobEventType.JOB_PAUSED,
                timestamp=datetime.now(),
                details={},
                user=user
            )
            self.event_manager.emit_event(event)

            logger.info("Job paused", job_id=job_id, user=user)

        return success

    def resume_job(self, job_id: str, user: str = "system") -> bool:
        """Resume a paused job"""
        success = self.scheduler.resume_job(job_id)

        if success:
            # Emit event
            event = JobEvent(
                id=str(uuid4()),
                job_id=job_id,
                event_type=JobEventType.JOB_RESUMED,
                timestamp=datetime.now(),
                details={},
                user=user
            )
            self.event_manager.emit_event(event)

            logger.info("Job resumed", job_id=job_id, user=user)

        return success

    def get_job_status(self, job_id: str) -> Optional[JobState]:
        """Get the current status of a job"""
        return self.scheduler.get_job_status(job_id)

    def get_job_history(self, job_id: str, limit: int = 10) -> List[JobExecutionRecord]:
        """Get execution history for a job"""
        return self.scheduler.get_job_history(job_id, limit)

    def get_all_jobs(self) -> List[JobDefinition]:
        """Get all job definitions"""
        return self.storage.list_jobs()

    def get_job_stats(self) -> Dict[str, Any]:
        """Get statistics about all jobs"""
        all_jobs = self.storage.list_jobs()
        stats = {
            "total_jobs": len(all_jobs),
            "enabled_jobs": sum(1 for j in all_jobs if j.enabled),
            "disabled_jobs": sum(1 for j in all_jobs if not j.enabled),
            "jobs_by_priority": {},
            "jobs_by_status": {}
        }

        # Count jobs by priority
        for job in all_jobs:
            priority = job.priority.name.lower()
            stats["jobs_by_priority"][priority] = stats["jobs_by_priority"].get(priority, 0) + 1

        # Count jobs by current status
        for job_id, job_state in self.scheduler.jobs.items():
            status = job_state.current_status.name.lower()
            stats["jobs_by_status"][status] = stats["jobs_by_status"].get(status, 0) + 1

        return stats

    def start(self):
        """Start the scheduler and monitoring"""
        self.scheduler.start()
        self.monitor.start_monitoring()

    def stop(self):
        """Stop the scheduler and monitoring"""
        self.monitor.stop_monitoring()
        self.scheduler.stop()

    def trigger_job_now(self, job_id: str, user: str = "system") -> Optional[str]:
        """Trigger a job to run immediately"""
        job_state = self.get_job_status(job_id)
        if not job_state:
            return None

        # Temporarily execute the job's callback
        job_def = job_state.job_definition

        # Create execution record
        execution_id = f"manual_{job_id}_{int(time.time())}_{hash(job_id) % 10000}"

        # Emit event
        event = JobEvent(
            id=str(uuid4()),
            job_id=job_id,
            event_type=JobEventType.JOB_STARTED,
            timestamp=datetime.now(),
            details={"triggered_by": user, "execution_id": execution_id},
            user=user
        )
        self.event_manager.emit_event(event)

        # Execute the job manually (bypassing scheduler)
        # This would require additional implementation in the scheduler core
        logger.info("Manual job execution triggered", job_id=job_id, user=user)
        return execution_id


# Convenience functions
def setup_default_jobs(job_manager: JobManager) -> bool:
    """Setup common default jobs like daily summaries and weekly audits"""
    try:
        # Daily summary job
        job_manager.create_job(
            job_id="daily_summary",
            name="Daily Summary Report",
            cron_expression="0 9 * * *",  # Every day at 9 AM
            callback="generate_daily_summary",
            description="Generates daily summary report",
            user="system"
        )

        # Weekly audit job
        job_manager.create_job(
            job_id="weekly_audit",
            name="Weekly Security Audit",
            cron_expression="0 2 * * 0",  # Every Sunday at 2 AM
            callback="perform_weekly_audit",
            description="Performs weekly security audit",
            user="system"
        )

        # Monthly cleanup job
        job_manager.create_job(
            job_id="monthly_cleanup",
            name="Monthly System Cleanup",
            cron_expression="0 1 1 * *",  # First day of every month at 1 AM
            callback="perform_monthly_cleanup",
            description="Cleans up old logs and temporary files",
            user="system"
        )

        logger.info("Default jobs created successfully")
        return True

    except Exception as e:
        logger.error("Failed to create default jobs", error=str(e))
        return False


def create_job_manager(storage_path: str = "./scheduled_jobs.db") -> JobManager:
    """Create and return a configured job manager instance"""
    storage = SQLiteJobStorage(storage_path)
    job_manager = JobManager(storage)

    # Register common event handlers
    def log_job_event(event: JobEvent):
        logger.info(
            f"Job event: {event.event_type.value}",
            job_id=event.job_id,
            event_id=event.id,
            user=event.user
        )

    job_manager.event_manager.register_handler(JobEventType.JOB_CREATED, log_job_event)
    job_manager.event_manager.register_handler(JobEventType.JOB_STARTED, log_job_event)
    job_manager.event_manager.register_handler(JobEventType.JOB_COMPLETED, log_job_event)
    job_manager.event_manager.register_handler(JobEventType.JOB_FAILED, log_job_event)

    return job_manager


if __name__ == "__main__":
    # Demo of job manager functionality
    print("Job Manager Demo")
    print("=" * 40)

    # Create job manager
    jm = create_job_manager()

    # Setup default jobs
    setup_default_jobs(jm)

    # Start the system
    jm.start()

    print("Job manager started with default jobs")
    print("Jobs created:")
    for job in jm.get_all_jobs():
        print(f"  - {job.name} ({job.id}): {job.cron_expression}")

    # Show stats
    stats = jm.get_job_stats()
    print(f"\nJob Statistics:")
    print(f"  Total jobs: {stats['total_jobs']}")
    print(f"  Enabled jobs: {stats['enabled_jobs']}")
    print(f"  Disabled jobs: {stats['disabled_jobs']}")

    # Let it run briefly
    try:
        print("\nScheduler running... Press Ctrl+C to stop")
        import time
        time.sleep(10)  # Run for 10 seconds
    except KeyboardInterrupt:
        print("\nShutting down...")

    # Stop the system
    jm.stop()
    print("Job manager stopped")