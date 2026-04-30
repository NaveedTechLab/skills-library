# Scheduler Cron Integration Skill

## Overview
The Scheduler Cron Integration skill provides scheduled execution capabilities for recurring operations such as daily summaries and weekly audits. This skill enables Claude Code to automatically execute tasks at specified intervals using cron-like expressions and provides a comprehensive task scheduling system.

## Features

### Cron Expression Support
- Standard cron expression parsing (* * * * *)
- Extended cron features (seconds, named months/days)
- Predefined schedules (@hourly, @daily, @weekly, @monthly, @yearly)
- Complex interval specifications

### Job Management
- Create, update, delete scheduled jobs
- Job persistence across restarts
- Execution history and logging
- Job status monitoring (running, paused, completed)
- Error handling and retry mechanisms

### Schedule Types
- Time-based scheduling (minute, hour, day, month, weekday)
- Interval-based scheduling (every N minutes/hours/days)
- Fixed-point scheduling (specific dates/times)
- Conditional scheduling (based on system conditions)

### Execution Engine
- Concurrent job execution
- Resource management and load balancing
- Execution context isolation
- Timeout and cancellation support
- Parallel and sequential execution modes

## Components

### Core Modules
- `scheduler_core.py`: Main scheduling engine and job execution
- `job_manager.py`: Advanced job management and monitoring
- `cron_parser.py`: Cron expression parsing and validation
- `config_manager.py`: Configuration management system
- `SKILL.md`: Main skill documentation

### Reference Materials
- `references/usage_examples.md`: Comprehensive usage examples
- `assets/example_config.json`: Example configuration file
- `assets/requirements.txt`: Dependencies

### Test Suite
- `test_scheduler_cron_integration.py`: Comprehensive test suite

## Usage

### Installation
```bash
pip install -r .claude/skills/scheduler-cron-integration/assets/requirements.txt
```

### Basic Usage
```python
from scheduler_cron_integration.scripts.job_manager import create_job_manager, setup_default_jobs

# Create a job manager
job_manager = create_job_manager()

# Start the scheduler
job_manager.start()

# Create a simple daily job
job_manager.create_job(
    job_id="daily_summary",
    name="Daily Summary Report",
    cron_expression="0 9 * * *",  # Every day at 9 AM
    callback="generate_daily_summary",
    description="Generates daily summary report"
)

# Setup common default jobs
setup_default_jobs(job_manager)
```

### Advanced Usage
```python
from scheduler_cron_integration.scripts.job_manager import JobPriority

# Create a job with custom settings
job_manager.create_job(
    job_id="weekly_audit",
    name="Weekly Security Audit",
    cron_expression="0 2 * * 0",  # Every Sunday at 2 AM
    callback="perform_security_audit",
    timeout_seconds=3600,  # 1 hour timeout
    max_retries=3,
    retry_delay_seconds=300,  # 5 minutes between retries
    priority=JobPriority.HIGH,
    description="Performs weekly security audit"
)

# Pause a job
job_manager.pause_job("daily_summary")

# Resume a job
job_manager.resume_job("daily_summary")

# Get job status
status = job_manager.get_job_status("daily_summary")
print(f"Next run: {status.next_run_time}")

# Get execution history
history = job_manager.get_job_history("daily_summary", limit=5)
for record in history:
    print(f"Run at {record.start_time}: {record.status.value}")
```

### Configuration
The skill supports multiple configuration approaches:

1. **Default Configuration**: Automatically creates sensible defaults
2. **Custom Configuration**: Load from JSON/YAML files
3. **Runtime Configuration**: Update settings dynamically

## Security Considerations
- Secure execution context for scheduled tasks
- Permission checking for scheduled operations
- Audit logging for all scheduled activities
- Protection against infinite loops/cascading failures

## Performance Considerations
- Efficient cron expression evaluation
- Minimal resource overhead for scheduler
- Scalable job management
- Optimized storage for job definitions

## Integration

### With Claude Code
- Trigger scheduled operations through Claude commands
- Integrate with existing tool execution framework
- Support for scheduled file operations
- Automatic execution of maintenance tasks

### With External Systems
- API call scheduling
- Database operation scheduling
- File system operation scheduling
- Third-party service integration

## Testing

The skill includes a comprehensive test suite that validates:
- Module imports and basic functionality
- Cron expression parsing
- Job scheduling and management
- Configuration management
- Error handling

Run the tests with:
```bash
python test_scheduler_cron_integration.py
```

## Examples

For comprehensive examples of usage scenarios, see:
- `references/usage_examples.md`
- Various scheduling patterns and configurations
- Integration examples with Claude Code workflows
- Advanced job management scenarios