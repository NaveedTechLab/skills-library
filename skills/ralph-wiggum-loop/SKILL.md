# Ralph Wiggum Loop

## Description
The Ralph Wiggum Loop is an autonomous task completion system that ensures Claude Code persists until tasks are fully completed. Named after the Simpsons character known for his persistence, this system tracks task state and re-injects continuation prompts when Claude attempts to exit before task completion.

## Purpose
This skill implements the "autonomous task loop" pattern required for Platinum tier Personal AI Employee certification. It ensures that long-running tasks are completed to specification without human intervention, while maintaining safety limits and audit trails.

## Key Features

### Task Persistence
- SQLite-based task state tracking
- Continuation prompt injection on premature exit
- Max iteration safety limits (configurable)
- Task timeout handling

### Completion Detection
- File-based completion detection (check `/vault/Done/` folder)
- Status marker detection (`status: completed`)
- Custom completion criteria support
- Partial completion tracking

### Safety Controls
- Maximum global iterations (default: 10)
- Maximum per-task iterations (default: 5)
- Configurable check intervals
- Emergency stop capability
- Full audit logging integration

### Vault Integration
Uses the standard vault folder structure:
- `/vault/Inbox/` - New items
- `/vault/Needs_Action/` - Items to process
- `/vault/Pending_Approval/` - Awaiting human approval
- `/vault/Approved/` - Ready for execution
- `/vault/Done/` - Completed tasks (Ralph Wiggum checks here)
- `/vault/Rejected/` - Rejected items
- `/vault/Failed/` - Max iterations reached

## Configuration

### Default Configuration
```json
{
  "ralph_wiggum": {
    "max_global_iterations": 10,
    "max_task_iterations": 5,
    "check_interval_seconds": 5,
    "completion_markers": ["status: completed", "## Completed"],
    "done_folder": "/vault/Done/",
    "failed_folder": "/vault/Failed/",
    "enable_audit_logging": true,
    "emergency_stop_file": ".ralph_stop"
  }
}
```

## How It Works

```
1. Task registered → tracked in SQLite with unique ID
2. Claude Code works on task
3. Claude Code tries to exit
4. Stop hook intercepts:
   - Check: Is task file in /Done folder?
   - YES → Allow exit, mark task complete
   - NO → Re-inject continuation prompt
5. Repeat until:
   - Task marked complete (file in /Done), OR
   - max_iterations reached (move to /Failed), OR
   - Emergency stop triggered
```

## Usage Scenarios

### Register a Task
```python
from ralph_wiggum import RalphWiggumLoop

loop = RalphWiggumLoop()

# Register a new task for tracking
task_id = loop.register_task(
    name="Process monthly invoices",
    source_file="/vault/Needs_Action/invoices-2024-01.md",
    completion_criteria={
        "type": "file_moved",
        "destination": "/vault/Done/"
    }
)
```

### Check Task Completion
```python
# Called by stop hook
is_complete = loop.check_task_completion(task_id)

if not is_complete:
    # Get continuation prompt
    prompt = loop.get_continuation_prompt(task_id)
    # Inject prompt for continued processing
```

### Force Task Completion
```python
# For emergency situations or manual override
loop.force_complete_task(task_id, reason="Manual override by admin")
```

## Integration Points

### With Vault System
- Monitors vault folders for task files
- Moves completed tasks to Done folder
- Moves failed tasks to Failed folder

### With Audit Logger
- Logs all task state changes
- Records iteration counts
- Tracks completion criteria checks

### With Safety Enforcer
- Respects safety boundaries
- Halts on prohibited actions
- Requires approval for high-risk tasks

## Security Considerations
- Emergency stop file for immediate halt
- Iteration limits prevent infinite loops
- All actions logged for audit
- No execution of arbitrary code

## Performance Considerations
- Lightweight SQLite storage
- Configurable check intervals
- Efficient file system monitoring
- Minimal memory footprint

## Dependencies
- `aiosqlite` for async database operations
- `watchdog` for file system monitoring
- Integration with phase-3 audit_logger
- Integration with phase-3 safety_enforcer
