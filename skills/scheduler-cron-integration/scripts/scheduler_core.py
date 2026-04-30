#!/usr/bin/env python3
"""
Scheduler Cron Integration - Core scheduling functionality

Implements scheduled execution for recurring operations such as daily summaries and weekly audits
"""

import asyncio
import concurrent.futures
import croniter
import datetime
import enum
import functools
import json
import os
import queue
import sqlite3
import threading
import time
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from threading import Event, Lock, Thread
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from zoneinfo import ZoneInfo

import structlog
from croniter import croniter

logger = structlog.get_logger()


class JobStatus(Enum):
    """Status of a scheduled job"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class JobPriority(Enum):
    """Priority levels for job execution"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class JobDefinition:
    """Definition of a scheduled job"""
    id: str
    name: str
    cron_expression: str
    callback: Union[str, Callable]  # Either function name or callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    enabled: bool = True
    description: str = ""
    priority: JobPriority = JobPriority.NORMAL
    timeout_seconds: int = 3600  # 1 hour default
    max_retries: int = 3
    retry_delay_seconds: int = 30
    timezone: str = "UTC"

    def __post_init__(self):
        # Validate cron expression
        try:
            croniter(self.cron_expression, datetime.now())
        except ValueError:
            raise ValueError(f"Invalid cron expression: {self.cron_expression}")


@dataclass
class JobExecutionRecord:
    """Record of a job execution"""
    job_id: str
    execution_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: JobStatus = JobStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    duration_seconds: Optional[float] = None
    attempt_number: int = 1


@dataclass
class JobState:
    """Current state of a job"""
    job_definition: JobDefinition
    next_run_time: Optional[datetime] = None
    last_run_time: Optional[datetime] = None
    last_result: Optional[Any] = None
    execution_count: int = 0
    failure_count: int = 0
    current_status: JobStatus = JobStatus.PENDING
    paused: bool = False
    next_retry_time: Optional[datetime] = None


class JobStorageInterface(ABC):
    """Abstract interface for job storage"""

    @abstractmethod
    def save_job(self, job_def: JobDefinition) -> bool:
        """Save a job definition"""
        pass

    @abstractmethod
    def load_job(self, job_id: str) -> Optional[JobDefinition]:
        """Load a job definition by ID"""
        pass

    @abstractmethod
    def delete_job(self, job_id: str) -> bool:
        """Delete a job definition"""
        pass

    @abstractmethod
    def list_jobs(self) -> List[JobDefinition]:
        """List all job definitions"""
        pass

    @abstractmethod
    def save_execution_record(self, record: JobExecutionRecord) -> bool:
        """Save an execution record"""
        pass

    @abstractmethod
    def get_execution_records(self, job_id: str, limit: int = 10) -> List[JobExecutionRecord]:
        """Get execution records for a job"""
        pass


class SQLiteJobStorage(JobStorageInterface):
    """SQLite-based job storage implementation"""

    def __init__(self, db_path: str = "./scheduled_jobs.db"):
        self.db_path = Path(db_path)
        self.lock = Lock()
        self.init_db()

    def init_db(self):
        """Initialize the database tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Jobs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    cron_expression TEXT NOT NULL,
                    callback TEXT NOT NULL,
                    args_json TEXT DEFAULT '{}',
                    kwargs_json TEXT DEFAULT '{}',
                    enabled BOOLEAN DEFAULT 1,
                    description TEXT,
                    priority INTEGER DEFAULT 2,
                    timeout_seconds INTEGER DEFAULT 3600,
                    max_retries INTEGER DEFAULT 3,
                    retry_delay_seconds INTEGER DEFAULT 30,
                    timezone TEXT DEFAULT 'UTC',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Execution records table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS execution_records (
                    execution_id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP,
                    status TEXT NOT NULL,
                    result_json TEXT,
                    error TEXT,
                    duration_seconds REAL,
                    attempt_number INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (job_id) REFERENCES jobs (id)
                )
            """)

            conn.commit()

    def save_job(self, job_def: JobDefinition) -> bool:
        """Save a job definition to the database"""
        try:
            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT OR REPLACE INTO jobs
                    (id, name, cron_expression, callback, args_json, kwargs_json,
                     enabled, description, priority, timeout_seconds, max_retries,
                     retry_delay_seconds, timezone, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    job_def.id, job_def.name, job_def.cron_expression,
                    str(job_def.callback), json.dumps(job_def.args),
                    json.dumps(job_def.kwargs), job_def.enabled,
                    job_def.description, job_def.priority.value,
                    job_def.timeout_seconds, job_def.max_retries,
                    job_def.retry_delay_seconds, job_def.timezone
                ))

                conn.commit()
                return True
        except Exception as e:
            logger.error("Failed to save job", job_id=job_def.id, error=str(e))
            return False

    def load_job(self, job_id: str) -> Optional[JobDefinition]:
        """Load a job definition from the database"""
        try:
            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, name, cron_expression, callback, args_json, kwargs_json,
                           enabled, description, priority, timeout_seconds, max_retries,
                           retry_delay_seconds, timezone
                    FROM jobs WHERE id = ?
                """, (job_id,))

                row = cursor.fetchone()
                if not row:
                    return None

                (id, name, cron_expression, callback, args_json, kwargs_json,
                 enabled, description, priority_val, timeout_seconds, max_retries,
                 retry_delay_seconds, timezone) = row

                return JobDefinition(
                    id=id,
                    name=name,
                    cron_expression=cron_expression,
                    callback=callback,  # This might be a string representation
                    args=tuple(json.loads(args_json)),
                    kwargs=json.loads(kwargs_json),
                    enabled=bool(enabled),
                    description=description,
                    priority=JobPriority(priority_val),
                    timeout_seconds=timeout_seconds,
                    max_retries=max_retries,
                    retry_delay_seconds=retry_delay_seconds,
                    timezone=timezone
                )
        except Exception as e:
            logger.error("Failed to load job", job_id=job_id, error=str(e))
            return None

    def delete_job(self, job_id: str) -> bool:
        """Delete a job definition from the database"""
        try:
            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error("Failed to delete job", job_id=job_id, error=str(e))
            return False

    def list_jobs(self) -> List[JobDefinition]:
        """List all job definitions from the database"""
        try:
            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, name, cron_expression, callback, args_json, kwargs_json,
                           enabled, description, priority, timeout_seconds, max_retries,
                           retry_delay_seconds, timezone
                    FROM jobs ORDER BY name
                """)

                jobs = []
                for row in cursor.fetchall():
                    (id, name, cron_expression, callback, args_json, kwargs_json,
                     enabled, description, priority_val, timeout_seconds, max_retries,
                     retry_delay_seconds, timezone) = row

                    job = JobDefinition(
                        id=id,
                        name=name,
                        cron_expression=cron_expression,
                        callback=callback,
                        args=tuple(json.loads(args_json)),
                        kwargs=json.loads(kwargs_json),
                        enabled=bool(enabled),
                        description=description,
                        priority=JobPriority(priority_val),
                        timeout_seconds=timeout_seconds,
                        max_retries=max_retries,
                        retry_delay_seconds=retry_delay_seconds,
                        timezone=timezone
                    )
                    jobs.append(job)

                return jobs
        except Exception as e:
            logger.error("Failed to list jobs", error=str(e))
            return []

    def save_execution_record(self, record: JobExecutionRecord) -> bool:
        """Save an execution record to the database"""
        try:
            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT INTO execution_records
                    (execution_id, job_id, start_time, end_time, status,
                     result_json, error, duration_seconds, attempt_number)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record.execution_id, record.job_id, record.start_time,
                    record.end_time, record.status.value,
                    json.dumps(record.result) if record.result is not None else None,
                    record.error, record.duration_seconds, record.attempt_number
                ))

                conn.commit()
                return True
        except Exception as e:
            logger.error("Failed to save execution record", execution_id=record.execution_id, error=str(e))
            return False

    def get_execution_records(self, job_id: str, limit: int = 10) -> List[JobExecutionRecord]:
        """Get execution records for a job"""
        try:
            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT execution_id, job_id, start_time, end_time, status,
                           result_json, error, duration_seconds, attempt_number
                    FROM execution_records
                    WHERE job_id = ?
                    ORDER BY start_time DESC
                    LIMIT ?
                """, (job_id, limit))

                records = []
                for row in cursor.fetchall():
                    (execution_id, job_id, start_time, end_time, status_str,
                     result_json, error, duration_seconds, attempt_number) = row

                    record = JobExecutionRecord(
                        execution_id=execution_id,
                        job_id=job_id,
                        start_time=datetime.fromisoformat(start_time) if isinstance(start_time, str) else start_time,
                        end_time=datetime.fromisoformat(end_time) if end_time and isinstance(end_time, str) else end_time,
                        status=JobStatus(status_str),
                        result=json.loads(result_json) if result_json else None,
                        error=error,
                        duration_seconds=duration_seconds,
                        attempt_number=attempt_number
                    )
                    records.append(record)

                return records
        except Exception as e:
            logger.error("Failed to get execution records", job_id=job_id, error=str(e))
            return []


class CronExpressionParser:
    """Parser for cron expressions with extended functionality"""

    def __init__(self):
        # Predefined aliases
        self.aliases = {
            '@yearly': '0 0 1 1 *',
            '@annually': '0 0 1 1 *',
            '@monthly': '0 0 1 * *',
            '@weekly': '0 0 * * 0',
            '@daily': '0 0 * * *',
            '@midnight': '0 0 * * *',
            '@hourly': '0 * * * *'
        }

    def normalize_expression(self, expression: str) -> str:
        """Normalize a cron expression (handle aliases, etc.)"""
        expr = expression.strip().lower()

        # Handle predefined aliases
        if expr in self.aliases:
            return self.aliases[expr]

        # Validate standard cron format (should have 5 or 6 parts)
        parts = expr.split()
        if len(parts) not in [5, 6]:
            raise ValueError(f"Cron expression must have 5 or 6 parts: {expression}")

        return expression

    def get_next_run_time(self, expression: str, from_time: datetime = None) -> datetime:
        """Calculate the next run time for a cron expression"""
        if from_time is None:
            from_time = datetime.now()

        normalized_expr = self.normalize_expression(expression)

        try:
            cron = croniter(normalized_expr, from_time)
            return cron.get_next(datetime)
        except ValueError as e:
            raise ValueError(f"Invalid cron expression '{expression}': {e}")

    def get_next_n_run_times(self, expression: str, n: int, from_time: datetime = None) -> List[datetime]:
        """Get the next N run times for a cron expression"""
        if from_time is None:
            from_time = datetime.now()

        normalized_expr = self.normalize_expression(expression)

        try:
            cron = croniter(normalized_expr, from_time)
            return [cron.get_next(datetime) for _ in range(n)]
        except ValueError as e:
            raise ValueError(f"Invalid cron expression '{expression}': {e}")


class JobExecutor:
    """Executes scheduled jobs with proper timeout and error handling"""

    def __init__(self, max_workers: int = 10):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.futures: Dict[str, concurrent.futures.Future] = {}
        self.lock = Lock()

    def submit_job(self, job_def: JobDefinition, execution_id: str) -> str:
        """Submit a job for execution"""
        future = self.executor.submit(
            self._execute_job_with_metadata,
            job_def, execution_id
        )

        with self.lock:
            self.futures[execution_id] = future

        return execution_id

    def _execute_job_with_metadata(self, job_def: JobDefinition, execution_id: str) -> Tuple[JobStatus, Any, str]:
        """Execute a job and return status, result, and error"""
        start_time = datetime.now()

        try:
            # Prepare the callback - if it's a string, try to resolve it
            callback = job_def.callback
            if isinstance(callback, str):
                # Try to resolve string callback to actual function
                callback = self._resolve_callback_from_string(callback)

            # Execute with timeout
            result = self._execute_with_timeout(
                callback,
                job_def.timeout_seconds,
                *job_def.args,
                **job_def.kwargs
            )

            duration = (datetime.now() - start_time).total_seconds()
            logger.info(
                "Job completed successfully",
                job_id=job_def.id,
                execution_id=execution_id,
                duration=duration
            )

            return JobStatus.COMPLETED, result, None

        except asyncio.TimeoutError:
            error_msg = f"Job timed out after {job_def.timeout_seconds} seconds"
            logger.error("Job timed out", job_id=job_def.id, execution_id=execution_id, error=error_msg)
            return JobStatus.FAILED, None, error_msg

        except Exception as e:
            error_msg = str(e)
            logger.error("Job failed", job_id=job_def.id, execution_id=execution_id, error=error_msg)
            return JobStatus.FAILED, None, error_msg

    def _resolve_callback_from_string(self, callback_str: str) -> Callable:
        """Resolve a string callback to an actual function"""
        # This is a simplified implementation
        # In a real system, you'd want more sophisticated module/function resolution
        if callback_str.startswith('lambda '):
            # Evaluate lambda expressions
            return eval(callback_str)
        else:
            # For now, return a dummy function for demonstration
            def dummy_callback(*args, **kwargs):
                logger.warning("Executing dummy callback for demo", callback=callback_str)
                return f"Executed {callback_str}"
            return dummy_callback

    def _execute_with_timeout(self, func: Callable, timeout_seconds: int, *args, **kwargs):
        """Execute a function with a timeout"""
        def target():
            return func(*args, **kwargs)

        future = self.executor.submit(target)

        try:
            result = future.result(timeout=timeout_seconds)
            return result
        except concurrent.futures.TimeoutError:
            future.cancel()
            raise asyncio.TimeoutError(f"Function timed out after {timeout_seconds} seconds")

    def is_running(self, execution_id: str) -> bool:
        """Check if a job is currently running"""
        with self.lock:
            if execution_id not in self.futures:
                return False
            return not self.futures[execution_id].done()

    def cancel_execution(self, execution_id: str) -> bool:
        """Cancel a running job execution"""
        with self.lock:
            if execution_id not in self.futures:
                return False

            future = self.futures[execution_id]
            success = future.cancel()

            if success:
                logger.info("Job execution cancelled", execution_id=execution_id)

            # Remove from futures dict
            del self.futures[execution_id]

            return success

    def shutdown(self, wait: bool = True):
        """Shutdown the executor"""
        self.executor.shutdown(wait=wait)


class Scheduler:
    """Main scheduler class that manages scheduled jobs"""

    def __init__(self, storage: JobStorageInterface = None, max_concurrent_jobs: int = 10):
        self.storage = storage or SQLiteJobStorage()
        self.executor = JobExecutor(max_concurrent_jobs)
        self.jobs: Dict[str, JobState] = {}
        self.cron_parser = CronExpressionParser()
        self.running = False
        self.scheduler_thread = None
        self.stop_event = Event()
        self.lock = Lock()

        # Load existing jobs from storage
        self._load_existing_jobs()

    def _load_existing_jobs(self):
        """Load existing jobs from storage"""
        jobs = self.storage.list_jobs()
        for job_def in jobs:
            if job_def.enabled:
                self._add_job_to_state(job_def)

    def _add_job_to_state(self, job_def: JobDefinition):
        """Add a job definition to the internal state"""
        # Calculate next run time
        next_run = self.cron_parser.get_next_run_time(
            job_def.cron_expression,
            datetime.now(ZoneInfo(job_def.timezone))
        )

        job_state = JobState(
            job_definition=job_def,
            next_run_time=next_run,
            current_status=JobStatus.PENDING
        )

        with self.lock:
            self.jobs[job_def.id] = job_state

    def schedule_job(self, job_def: JobDefinition) -> bool:
        """Schedule a new job"""
        # Save to storage first
        if not self.storage.save_job(job_def):
            return False

        # Add to internal state
        self._add_job_to_state(job_def)

        logger.info("Job scheduled", job_id=job_def.id, cron_expression=job_def.cron_expression)
        return True

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a scheduled job"""
        with self.lock:
            if job_id in self.jobs:
                del self.jobs[job_id]

        # Also remove from storage
        return self.storage.delete_job(job_id)

    def pause_job(self, job_id: str) -> bool:
        """Pause a job (will not execute until resumed)"""
        with self.lock:
            if job_id in self.jobs:
                self.jobs[job_id].paused = True
                self.jobs[job_id].current_status = JobStatus.PAUSED
                logger.info("Job paused", job_id=job_id)
                return True
        return False

    def resume_job(self, job_id: str) -> bool:
        """Resume a paused job"""
        with self.lock:
            if job_id in self.jobs:
                self.jobs[job_id].paused = False
                self.jobs[job_id].current_status = JobStatus.PENDING

                # Recalculate next run time from now
                job_def = self.jobs[job_id].job_definition
                self.jobs[job_id].next_run_time = self.cron_parser.get_next_run_time(
                    job_def.cron_expression,
                    datetime.now(ZoneInfo(job_def.timezone))
                )

                logger.info("Job resumed", job_id=job_id)
                return True
        return False

    def update_job_schedule(self, job_id: str, new_cron_expression: str) -> bool:
        """Update the schedule for a job"""
        with self.lock:
            if job_id not in self.jobs:
                return False

            # Update the job definition
            job_def = self.jobs[job_id].job_definition
            job_def.cron_expression = new_cron_expression

            # Update in storage
            if not self.storage.save_job(job_def):
                return False

            # Update next run time
            self.jobs[job_id].next_run_time = self.cron_parser.get_next_run_time(
                new_cron_expression,
                datetime.now(ZoneInfo(job_def.timezone))
            )

            logger.info("Job schedule updated", job_id=job_id, cron_expression=new_cron_expression)
            return True

    def get_job_status(self, job_id: str) -> Optional[JobState]:
        """Get the current status of a job"""
        with self.lock:
            return self.jobs.get(job_id)

    def get_job_history(self, job_id: str, limit: int = 10) -> List[JobExecutionRecord]:
        """Get execution history for a job"""
        return self.storage.get_execution_records(job_id, limit)

    def start(self):
        """Start the scheduler"""
        if self.running:
            return

        self.running = True
        self.stop_event.clear()
        self.scheduler_thread = Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()

        logger.info("Scheduler started")

    def stop(self):
        """Stop the scheduler"""
        if not self.running:
            return

        self.running = False
        self.stop_event.set()

        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)

        self.executor.shutdown(wait=True)

        logger.info("Scheduler stopped")

    def _scheduler_loop(self):
        """Main scheduler loop"""
        while not self.stop_event.is_set() and self.running:
            try:
                self._check_and_execute_jobs()
                # Sleep for a short time before next check
                self.stop_event.wait(timeout=1)  # Check every second
            except Exception as e:
                logger.error("Error in scheduler loop", error=str(e))
                # Brief pause before continuing
                self.stop_event.wait(timeout=1)

    def _check_and_execute_jobs(self):
        """Check for jobs that are ready to run and execute them"""
        now = datetime.now()

        with self.lock:
            jobs_to_run = []

            for job_id, job_state in self.jobs.items():
                if (job_state.paused or
                    job_state.current_status == JobStatus.RUNNING or
                    job_state.next_run_time is None):
                    continue

                # Check if job is ready to run
                if now >= job_state.next_run_time:
                    jobs_to_run.append(job_id)

        # Execute jobs outside the lock to avoid blocking
        for job_id in jobs_to_run:
            self._execute_job(job_id)

    def _execute_job(self, job_id: str):
        """Execute a single job"""
        with self.lock:
            if job_id not in self.jobs:
                return

            job_state = self.jobs[job_id]
            job_def = job_state.job_definition

            # Check if paused again inside lock
            if job_state.paused:
                return

        # Create execution record
        execution_id = f"{job_id}_{int(time.time())}_{hash(job_id) % 10000}"
        start_time = datetime.now()

        # Update job state
        with self.lock:
            job_state.current_status = JobStatus.RUNNING
            job_state.last_run_time = start_time
            job_state.execution_count += 1

        logger.info("Starting job execution", job_id=job_id, execution_id=execution_id)

        # Submit job to executor
        self.executor.submit_job(job_def, execution_id)

        # Update next run time
        with self.lock:
            if job_id in self.jobs:  # Check if job still exists
                next_run = self.cron_parser.get_next_run_time(
                    job_def.cron_expression,
                    datetime.now(ZoneInfo(job_def.timezone))
                )
                self.jobs[job_id].next_run_time = next_run

    def get_upcoming_runs(self, job_id: str, count: int = 5) -> List[datetime]:
        """Get upcoming run times for a job"""
        with self.lock:
            if job_id not in self.jobs:
                return []

            job_def = self.jobs[job_id].job_definition
            return self.cron_parser.get_next_n_run_times(
                job_def.cron_expression,
                count,
                datetime.now(ZoneInfo(job_def.timezone))
            )


# Utility functions
def create_job_definition(
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
    timezone: str = "UTC"
) -> JobDefinition:
    """Helper function to create a job definition"""
    return JobDefinition(
        id=job_id,
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


def run_scheduler_demo():
    """Demo function to show scheduler usage"""
    print("Scheduler Cron Integration Demo")
    print("=" * 40)

    # Create scheduler instance
    scheduler = Scheduler()

    # Define a sample job function
    def sample_job(task_name: str = "default"):
        print(f"Executing sample job: {task_name}")
        import random
        # Simulate some work
        time.sleep(random.uniform(0.5, 2.0))
        result = f"Completed {task_name} at {datetime.now()}"
        print(result)
        return result

    # Create a job definition
    job_def = create_job_definition(
        job_id="demo_job",
        name="Demo Job",
        cron_expression="*/10 * * * * *",  # Every 10 seconds (if seconds are supported)
        callback=sample_job,
        args=("Demo Task",),
        description="A demo job that runs every 10 seconds",
        timeout_seconds=10
    )

    # Add the job to scheduler
    if scheduler.schedule_job(job_def):
        print("Job scheduled successfully")
    else:
        print("Failed to schedule job")
        return

    # Start the scheduler
    scheduler.start()

    print("Scheduler running... Press Ctrl+C to stop")

    try:
        # Let it run for a bit
        time.sleep(30)  # Run for 30 seconds
    except KeyboardInterrupt:
        print("\nStopping scheduler...")

    # Stop the scheduler
    scheduler.stop()
    print("Scheduler stopped")


if __name__ == "__main__":
    run_scheduler_demo()