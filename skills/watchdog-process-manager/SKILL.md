---
name: watchdog-process-manager
description: Process supervisor to auto-restart failed watchers and orchestrator processes with comprehensive logging and alerting capabilities. Use when Claude needs to manage long-running processes, ensure service availability, monitor process health, or implement resilient process supervision with restart policies and notifications.
---

# Watchdog Process Manager

## Overview

The Watchdog Process Manager is a robust process supervision system that monitors, manages, and auto-restarts failed processes. It provides comprehensive logging, alerting, and health monitoring capabilities to ensure service availability and resilience.

## Core Capabilities

The watchdog process manager provides:

1. **Process Supervision**: Monitors running processes and automatically restarts failed ones
2. **Health Monitoring**: Tracks process health, resource usage, and performance metrics
3. **Logging & Auditing**: Maintains detailed logs of process lifecycle events
4. **Alerting System**: Sends notifications when processes fail or require attention
5. **Configuration Management**: Flexible configuration for different restart policies
6. **Resource Management**: Monitors and enforces resource limits

## Usage Scenarios

Use the watchdog process manager when:
- Long-running watcher processes need supervision
- Automatic restart of failed orchestrator processes is required
- Service availability and uptime must be maintained
- Process health and performance need monitoring
- Alerting is needed for process failures or anomalies
- Resource usage needs to be tracked and controlled

## Process Supervision

### Restart Policies

The watchdog supports various restart policies:

- **Always**: Always restart failed processes (default)
- **On-Failure**: Only restart if process exits with non-zero code
- **Never**: Don't restart, just log the failure
- **Exponential Backoff**: Increase delay between restart attempts

### Health Checks

Processes can be monitored using:
- **Heartbeat**: Regular signals from the process
- **Resource Usage**: CPU/memory thresholds
- **External Ping**: Network-based health checks
- **File-based**: Checking for specific file states

## Configuration

### Process Definitions

Processes are defined with configuration specifying:
- Command to execute
- Restart policy
- Environment variables
- Working directory
- Resource limits
- Health check parameters

### Example Configuration

```yaml
processes:
  - name: "file-watcher"
    command: "python file_watcher.py"
    restart_policy: "always"
    max_restarts: 5
    restart_window: 60
    environment:
      LOG_LEVEL: "INFO"
    working_dir: "/opt/watchers"
    resource_limits:
      cpu_percent: 80
      memory_mb: 512
    health_check:
      type: "heartbeat"
      interval: 30
      timeout: 10
```

## Alerting System

### Notification Channels

The system supports multiple alerting channels:
- Email notifications
- Slack messages
- Webhook calls
- System logs
- Custom notification handlers

### Alert Conditions

Alerts are triggered by:
- Process failures
- Resource threshold breaches
- Health check failures
- Restart limit exceeded
- Process stuck states

## Implementation Guidelines

### Best Practices

1. **Graceful Shutdown**: Implement proper signal handling for clean shutdowns
2. **Health Endpoints**: Expose health check endpoints for accurate monitoring
3. **Resource Limits**: Set appropriate resource limits to prevent system overload
4. **Log Rotation**: Implement log rotation to prevent disk space issues
5. **Monitoring Integration**: Integrate with existing monitoring systems

### Performance Considerations

- **Efficient Polling**: Use appropriate intervals for health checks
- **Memory Usage**: Monitor watchdog's own resource usage
- **Restart Delays**: Implement reasonable delays to prevent rapid restart cycles
- **Process Isolation**: Separate monitoring of different process types

## Resources

This skill includes example resource directories that demonstrate how to manage different aspects of process supervision:

### scripts/
Executable Python scripts for process supervision, health monitoring, and alerting functionality.

### references/
Detailed documentation for configuration formats, alerting policies, and integration guidelines.

### assets/
Template configuration files and example process definitions for common supervision scenarios.

---

The watchdog process manager enables reliable and resilient process management with comprehensive monitoring and alerting capabilities.