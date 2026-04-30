# Scheduler Cron Integration - Usage Examples

## Overview
This document provides practical examples of how to use the Scheduler Cron Integration skill for various scheduling scenarios including daily summaries, weekly audits, and other recurring operations.

## Installation and Setup

### Prerequisites
```bash
pip install croniter structlog
```

### Basic Initialization
```python
from scheduler_cron_integration.scripts.job_manager import create_job_manager, setup_default_jobs

# Create a job manager with default configuration
job_manager = create_job_manager()

# Start the scheduler and monitoring
job_manager.start()

# Setup common default jobs
setup_default_jobs(job_manager)
```

## Basic Job Scheduling Examples

### Simple Daily Job
```python
from scheduler_cron_integration.scripts.job_manager import JobPriority

# Create a simple daily job
job_id = job_manager.create_job(
    job_id="daily_backup",
    name="Daily Backup",
    cron_expression="0 2 * * *",  # Every day at 2 AM
    callback="perform_backup",
    description="Perform daily system backup",
    timeout_seconds=3600,  # 1 hour timeout
    priority=JobPriority.HIGH
)

if job_id:
    print(f"Job scheduled with ID: {job_id}")
else:
    print("Failed to schedule job")
```

### Weekly Audit Job
```python
# Create a weekly audit job
job_manager.create_job(
    job_id="weekly_security_audit",
    name="Weekly Security Audit",
    cron_expression="0 1 * * SUN",  # Every Sunday at 1 AM
    callback="perform_security_audit",
    description="Perform comprehensive security audit",
    max_retries=2,
    retry_delay_seconds=60
)
```

### Monthly Cleanup Job
```python
# Create a monthly cleanup job
job_manager.create_job(
    job_id="monthly_cleanup",
    name="Monthly Cleanup",
    cron_expression="0 3 1 * *",  # 1st of every month at 3 AM
    callback="cleanup_old_files",
    args=("logs/",),  # Pass directory as argument
    kwargs={"retention_days": 30},  # Keep files for 30 days
    description="Clean up old log files"
)
```

## Advanced Scheduling Examples

### Job with Custom Callback Function
```python
def custom_summary_task(report_type: str = "daily"):
    """Custom function to generate different types of reports"""
    print(f"Generating {report_type} summary...")

    # Simulate report generation
    import time
    time.sleep(2)  # Simulate work

    result = f"Generated {report_type} summary at {time.time()}"
    print(result)
    return result

# Schedule job with custom function
job_manager.create_job(
    job_id="custom_summary",
    name="Custom Summary Report",
    cron_expression="0 8 * * *",  # Every day at 8 AM
    callback=custom_summary_task,
    args=("weekly",),  # Generate weekly reports
    description="Generate custom summary reports"
)
```

### Job with Specific Timezone
```python
# Schedule job in a specific timezone
job_manager.create_job(
    job_id="pst_daily_task",
    name="Daily Task in PST",
    cron_expression="0 9 * * *",  # 9 AM
    callback="perform_daily_task",
    timezone="America/Los_Angeles",  # PST timezone
    description="Daily task that runs in Pacific time"
)
```

### Job with Extended Cron Format (with seconds)
```python
# Schedule a job that runs every 30 seconds
job_manager.create_job(
    job_id="heartbeat_check",
    name="Heartbeat Check",
    cron_expression="*/30 * * * * *",  # Every 30 seconds
    callback="check_system_heartbeat",
    timeout_seconds=10,
    description="Check system heartbeat every 30 seconds"
)
```

## Job Management Examples

### Pausing and Resuming Jobs
```python
# Pause a job
success = job_manager.pause_job("daily_backup")
if success:
    print("Daily backup job paused")

# Resume the job later
success = job_manager.resume_job("daily_backup")
if success:
    print("Daily backup job resumed")
```

### Updating Job Schedule
```python
# Change the schedule of an existing job
success = job_manager.update_job(
    "daily_backup",
    cron_expression="0 3 * * *"  # Move to 3 AM instead of 2 AM
)
if success:
    print("Daily backup schedule updated")
```

### Getting Job Status and History
```python
# Get current job status
status = job_manager.get_job_status("daily_backup")
if status:
    print(f"Next run: {status.next_run_time}")
    print(f"Last run: {status.last_run_time}")
    print(f"Execution count: {status.execution_count}")

# Get job execution history
history = job_manager.get_job_history("daily_backup", limit=5)
for record in history:
    print(f"Run at {record.start_time}: {record.status.value}")
    if record.error:
        print(f"  Error: {record.error}")
```

## Event Monitoring Examples

### Registering Event Handlers
```python
from scheduler_cron_integration.scripts.job_manager import JobEventType, JobEvent

def on_job_completed(event: JobEvent):
    """Handler for job completion events"""
    print(f"Job {event.job_id} completed successfully!")

def on_job_failed(event: JobEvent):
    """Handler for job failure events"""
    print(f"Job {event.job_id} failed: {event.details.get('error', 'Unknown error')}")

# Register event handlers
job_manager.event_manager.register_handler(JobEventType.JOB_COMPLETED, on_job_completed)
job_manager.event_manager.register_handler(JobEventType.JOB_FAILED, on_job_failed)
```

### Monitoring Job Statistics
```python
# Get overall statistics
stats = job_manager.get_job_stats()
print(f"Total jobs: {stats['total_jobs']}")
print(f"Enabled jobs: {stats['enabled_jobs']}")
print(f"Disabled jobs: {stats['disabled_jobs']}")
print(f"Jobs by priority: {stats['jobs_by_priority']}")
print(f"Jobs by status: {stats['jobs_by_status']}")
```

## Complex Scheduling Scenarios

### Business Days Only Job
```python
# Schedule a job to run only on business days (Monday to Friday)
job_manager.create_job(
    job_id="business_daily",
    name="Business Daily Task",
    cron_expression="0 9 * * 1-5",  # 9 AM, Monday to Friday
    callback="perform_business_task",
    description="Task that runs only on business days"
)
```

### End of Month Job
```python
# Schedule a job for approximately the end of each month
# Note: Since days vary by month, this runs multiple times near month end
job_manager.create_job(
    job_id="month_end_processing",
    name="Month End Processing",
    cron_expression="0 22 25-31 * *",  # Between 25th and 31st, at 10 PM
    callback="process_month_end_tasks",
    description="Process month-end tasks (runs multiple times for safety)"
)
```

### Multiple Time Zone Jobs
```python
# Create jobs for different time zones
timezones = [
    ("America/New_York", "east_coast_report"),
    ("America/Los_Angeles", "west_coast_report"),
    ("Europe/London", "uk_report")
]

for tz, job_name in timezones:
    job_manager.create_job(
        job_id=job_name,
        name=f"{job_name.replace('_', ' ').title()}",
        cron_expression="0 9 * * *",  # 9 AM in respective timezone
        callback="generate_regional_report",
        kwargs={"region": job_name.split('_')[0]},
        timezone=tz,
        description=f"Generate report for {tz} timezone"
    )
```

## Error Handling Examples

### Comprehensive Error Handling
```python
def safe_job_operation():
    """Example of a job operation with error handling"""
    try:
        # Perform the actual job operation
        result = perform_actual_work()
        return result
    except SpecificError as e:
        # Handle specific errors
        logger.error("Specific error occurred", error=str(e))
        raise  # Re-raise to let scheduler handle retries
    except Exception as e:
        # Handle general errors
        logger.error("Unexpected error in job", error=str(e))
        raise  # Re-raise to let scheduler handle retries

# Schedule job with error handling
job_manager.create_job(
    job_id="safe_operation",
    name="Safe Operation",
    cron_expression="0 * * * *",  # Every hour
    callback=safe_job_operation,
    max_retries=3,  # Retry up to 3 times
    retry_delay_seconds=300  # Wait 5 minutes between retries
)
```

### Job Validation
```python
from scheduler_cron_integration.scripts.job_manager import JobValidator

validator = JobValidator()

# Validate a job before creating it
job_def = job_manager.create_job_definition(
    job_id="test_job",
    name="Test Job",
    cron_expression="0 9 * * *",
    callback="test_callback"
)

errors = validator.validate_job_definition(job_def)
if errors:
    print("Job validation failed:")
    for error in errors:
        print(f"  - {error}")
else:
    print("Job validation passed")
    # Proceed to schedule the job
```

## Integration Examples

### Integration with Claude Code Workflows
```python
def claude_scheduled_task(file_path: str):
    """Example of a task that integrates with Claude Code operations"""
    # This function could perform file operations, API calls, etc.
    # as part of Claude Code workflows
    print(f"Processing file: {file_path}")

    # Example Claude Code integration
    # This would typically call Claude Code APIs or tools
    result = process_file_with_claude(file_path)

    return result

# Schedule Claude Code integration task
job_manager.create_job(
    job_id="claude_file_processor",
    name="Claude File Processor",
    cron_expression="*/15 * * * *",  # Every 15 minutes
    callback=claude_scheduled_task,
    args=("/path/to/watched/files/",),
    description="Process files using Claude Code operations"
)
```

### API Call Scheduling
```python
import requests

def scheduled_api_call():
    """Example of scheduling API calls"""
    try:
        response = requests.get("https://api.example.com/data", timeout=30)
        response.raise_for_status()

        # Process the response
        data = response.json()
        process_api_response(data)

        return {"status": "success", "records_processed": len(data)}
    except requests.RequestException as e:
        logger.error("API call failed", error=str(e))
        raise
    except Exception as e:
        logger.error("Error processing API response", error=str(e))
        raise

# Schedule API call
job_manager.create_job(
    job_id="scheduled_api_call",
    name="Scheduled API Call",
    cron_expression="0 */6 * * *",  # Every 6 hours
    callback=scheduled_api_call,
    timeout_seconds=60,  # 1-minute timeout for API call
    description="Regular API data synchronization"
)
```

## Configuration Examples

### Loading Custom Configuration
```python
from scheduler_cron_integration.scripts.config_manager import ConfigManager

# Load custom configuration
config_manager = ConfigManager("./custom_scheduler_config.json")
custom_config = config_manager.config

# Create job manager with custom configuration
job_manager = create_job_manager(
    storage_path=custom_config.scheduler.job_storage_path
)

# Apply other configuration settings
job_manager.scheduler.max_concurrent_jobs = custom_config.scheduler.max_concurrent_jobs
```

### Environment-Specific Configuration
```python
import os

# Determine configuration based on environment
env = os.getenv("ENVIRONMENT", "development")
config_file = f"./scheduler_config_{env.lower()}.json"

job_manager = create_job_manager(config_file)
```

## Cron Expression Examples

### Common Cron Expressions
| Expression | Meaning |
|------------|---------|
| `0 0 * * *` | Every day at midnight |
| `0 9 * * *` | Every day at 9 AM |
| `0 9 * * 1-5` | Weekdays at 9 AM |
| `0 12 * * 0` | Sundays at noon |
| `0 0 1 * *` | First day of every month |
| `0 0 1 1 *` | First day of January |
| `*/5 * * * *` | Every 5 minutes |
| `0 */2 * * *` | Every 2 hours |
| `0 22 * * 1-5` | Weekdays at 10 PM |

### Predefined Schedules
| Alias | Equivalent | Meaning |
|-------|------------|---------|
| `@yearly` | `0 0 1 1 *` | Once a year at midnight of Jan 1 |
| `@monthly` | `0 0 1 * *` | Once a month at midnight of 1st |
| `@weekly` | `0 0 * * 0` | Once a week at midnight on Sunday |
| `@daily` | `0 0 * * *` | Once a day at midnight |
| `@hourly` | `0 * * * *` | Once an hour at minute 0 |

These examples demonstrate the flexibility and power of the Scheduler Cron Integration skill for managing recurring operations in various scenarios.