# Watchdog Process Manager Configuration Guide

## Overview

The Watchdog Process Manager uses flexible configuration files to define processes, monitoring policies, and alerting rules. This guide covers all configuration options and best practices.

## Configuration File Format

Configuration files can be in JSON or YAML format. The top-level structure is:

```yaml
processes:
  - name: "my-service"
    command: "python my_service.py"
    restart_policy: "always"
    # ... process configuration

alerts:
  channels:
    - name: "email-notifications"
      type: "email"
      # ... channel configuration
  rules:
    - name: "critical_failures"
      conditions:
        alert_types: ["process_failure"]
      actions: ["email", "slack"]
```

## Process Configuration

### Basic Process Definition

```yaml
processes:
  - name: "file-watcher"                           # Unique process name
    command: "python file_watcher.py --config conf.yaml"  # Command to execute
    autostart: true                               # Start automatically (default: true)
    working_dir: "/opt/myapp"                     # Working directory
    restart_policy: "always"                      # Restart policy
```

### Environment Variables

```yaml
processes:
  - name: "api-server"
    command: "python api_server.py"
    environment:
      LOG_LEVEL: "INFO"
      DATABASE_URL: "postgresql://localhost/mydb"
      PORT: "8080"
```

### Restart Policies

The system supports several restart policies:

- `always`: Always restart failed processes (default)
- `on-failure`: Only restart if process exits with non-zero code
- `never`: Don't restart, just log the failure
- `exponential-backoff`: Increase delay between restart attempts

```yaml
processes:
  - name: "batch-processor"
    command: "python processor.py"
    restart_policy: "exponential-backoff"
    max_restarts: 5              # Max restarts in the window
    restart_window: 60           # Time window in seconds
```

### Resource Limits

Monitor and enforce resource usage:

```yaml
processes:
  - name: "memory-intensive-app"
    command: "python app.py"
    resource_limits:
      cpu_percent: 80            # Max CPU percentage
      memory_mb: 1024            # Max memory in MB
```

### Health Checks

Configure different types of health checks:

#### Heartbeat Health Check
```yaml
processes:
  - name: "web-server"
    command: "python server.py"
    health_check:
      type: "heartbeat"
      interval: 30               # Check every 30 seconds
      timeout: 10                # Timeout after 10 seconds
```

#### Resource Health Check
```yaml
processes:
  - name: "data-processor"
    command: "python processor.py"
    health_check:
      type: "resource"
      interval: 60
      cpu_percent: 90            # Alert if CPU > 90%
      memory_mb: 2048            # Alert if memory > 2048MB
```

### Output Redirection

Redirect process output to files:

```yaml
processes:
  - name: "logger-service"
    command: "python logger.py"
    stdout_file: "/var/log/logger-stdout.log"
    stderr_file: "/var/log/logger-stderr.log"
```

## Alert Configuration

### Email Channel

```yaml
alerts:
  channels:
    - name: "email-notifications"
      type: "email"
      smtp_server: "smtp.gmail.com"
      smtp_port: 587
      username: "your-email@gmail.com"
      password: "your-app-password"
      from_email: "your-email@gmail.com"
      to_emails:
        - "admin@example.com"
        - "ops-team@example.com"
```

### Slack Channel

```yaml
alerts:
  channels:
    - name: "slack-alerts"
      type: "slack"
      webhook_url: "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
      channel: "#operations"
      username: "WatchdogBot"
```

### Webhook Channel

```yaml
alerts:
  channels:
    - name: "webhook-notifications"
      type: "webhook"
      url: "https://api.example.com/alerts"
      method: "POST"
      headers:
        Authorization: "Bearer your-token"
        Content-Type: "application/json"
```

### Log Channel

```yaml
alerts:
  channels:
    - name: "system-logs"
      type: "log"
      log_level: "WARNING"
      logger_name: "watchdog.alerts"
```

### Alert Rules

Define which alerts go to which channels:

```yaml
alerts:
  rules:
    - name: "critical_failures"
      conditions:
        alert_types: ["process_failure", "restart_limit_exceeded"]
        severity: "critical"
      actions: ["email", "slack"]

    - name: "warnings"
      conditions:
        alert_types: ["resource_violation", "system_health_violation"]
        severity: "warning"
      actions: ["log", "webhook"]
```

## Health Monitoring Configuration

### System Thresholds

Configure system-wide monitoring thresholds:

```yaml
health_monitor:
  system_thresholds:
    cpu_percent: 90             # Alert if CPU > 90%
    memory_percent: 90          # Alert if memory > 90%
    disk_percent: 90            # Alert if disk > 90%
    process_count: 1000         # Alert if > 1000 processes
  process_thresholds:
    cpu_percent: 80             # Alert if process CPU > 80%
    memory_mb: 1024             # Alert if process memory > 1024MB
    num_threads: 100            # Alert if process threads > 100
  collection_interval: 30       # Collect metrics every 30 seconds
  alert_on_violation: true      # Send alerts for violations
```

## Complete Example Configuration

```yaml
# Main processes to supervise
processes:
  - name: "file-watcher"
    command: "python /opt/watchers/file_watcher.py --config /etc/watchers/file.conf"
    restart_policy: "always"
    max_restarts: 5
    restart_window: 60
    environment:
      LOG_LEVEL: "INFO"
      PYTHONPATH: "/opt/watchers"
    working_dir: "/opt/watchers"
    resource_limits:
      cpu_percent: 80
      memory_mb: 512
    health_check:
      type: "resource"
      interval: 30
      cpu_percent: 75
      memory_mb: 480
    autostart: true
    stdout_file: "/var/log/file-watcher.out"
    stderr_file: "/var/log/file-watcher.err"

  - name: "api-server"
    command: "python /opt/api/server.py --port 8080"
    restart_policy: "on-failure"
    environment:
      DATABASE_URL: "postgresql://localhost/api_db"
      LOG_LEVEL: "INFO"
    health_check:
      type: "heartbeat"
      interval: 60
    autostart: true

# Alerting configuration
alerts:
  channels:
    - name: "email-ops"
      type: "email"
      smtp_server: "smtp.company.com"
      smtp_port: 587
      username: "watchdog@company.com"
      password: "${WATCHDOG_EMAIL_PASSWORD}"  # Use environment variable
      from_email: "watchdog@company.com"
      to_emails:
        - "ops@company.com"
        - "dev-team@company.com"

    - name: "slack-alerts"
      type: "slack"
      webhook_url: "${SLACK_WEBHOOK_URL}"  # Use environment variable
      channel: "#alerts"
      username: "Watchdog Bot"

  rules:
    - name: "critical_failures"
      conditions:
        alert_types: ["process_failure", "restart_limit_exceeded"]
        severity: "critical"
      actions: ["email-ops", "slack-alerts"]

    - name: "resource_warnings"
      conditions:
        alert_types: ["resource_violation"]
        severity: "warning"
      actions: ["email-ops"]

# Health monitoring configuration
health_monitor:
  system_thresholds:
    cpu_percent: 85
    memory_percent: 85
    disk_percent: 90
    process_count: 800
  process_thresholds:
    cpu_percent: 75
    memory_mb: 1024
    num_threads: 50
  collection_interval: 45
  alert_on_violation: true
```

## Environment Variables in Configuration

You can use environment variables in configuration files by referencing them with `${VARIABLE_NAME}` syntax:

```yaml
processes:
  - name: "database-sync"
    command: "python sync.py --db ${DATABASE_URL}"
    environment:
      SECRET_KEY: "${SECRET_KEY}"
      LOG_LEVEL: "${LOG_LEVEL:-INFO}"  # Use INFO as default if LOG_LEVEL is not set
```

## Best Practices

### Process Design
- Design processes to handle SIGTERM gracefully
- Implement proper logging in supervised processes
- Use unique names for each process
- Set appropriate resource limits to prevent system overload

### Configuration Management
- Store sensitive information (passwords, tokens) in environment variables
- Use configuration management tools to deploy configs
- Test configurations before deploying to production
- Maintain separate configs for different environments

### Alerting Strategy
- Use multiple alert channels for critical alerts
- Avoid alert fatigue by setting appropriate thresholds
- Include sufficient context in alert messages
- Regularly review and tune alert rules

### Monitoring
- Set up dashboard to visualize process health
- Monitor watchdog itself for failures
- Collect metrics for trending and capacity planning
- Implement alert correlation to reduce noise