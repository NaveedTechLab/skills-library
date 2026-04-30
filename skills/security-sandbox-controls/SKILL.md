---
name: security-sandbox-controls
description: Enforce environment-based safety controls including DRY_RUN mode, rate limits, credential isolation, and permission boundaries. Use when hardening Claude Code environments against unintended side-effects or unauthorized access.
---

# Security Sandbox Controls

## Description
The Security Sandbox Controls skill provides environment-based safety controls including DRY_RUN mode, rate limits, credential isolation, and permission boundaries. This skill ensures that all operations within the Claude Code environment are performed safely with appropriate safeguards to prevent unintended consequences, resource exhaustion, and unauthorized access.

## Purpose
This skill implements comprehensive safety mechanisms to:
- Prevent unintended modifications during development and testing
- Limit resource consumption through rate limiting
- Isolate credentials and sensitive information
- Enforce permission boundaries and access controls
- Provide safe execution environments for potentially risky operations

## Key Features

### DRY_RUN Mode
- Simulate operations without making actual changes
- Preview the effects of operations before execution
- Safe testing of complex operations
- Detailed reporting of what would have happened

### Rate Limiting
- Configurable rate limits per operation type
- Burst allowance with token bucket algorithm
- Per-user and global rate limiting
- Adaptive rate adjustment based on system load

### Credential Isolation
- Secure storage and retrieval of credentials
- Automatic credential rotation support
- Environment-specific credential management
- Access logging for credential usage

### Permission Boundaries
- Fine-grained permission controls
- Role-based access control (RBAC)
- Temporary elevation capabilities
- Audit trails for all permission checks

## Configuration

### Default Configuration
```json
{
  "dry_run_enabled": false,
  "rate_limits": {
    "file_operations_per_minute": 100,
    "network_requests_per_minute": 50,
    "system_commands_per_minute": 20,
    "credential_access_per_minute": 10
  },
  "credentials": {
    "isolation_enabled": true,
    "auto_rotation_enabled": false,
    "rotation_interval_hours": 24
  },
  "permissions": {
    "enforcement_enabled": true,
    "default_role": "standard_user",
    "allow_dangerous_operations": false
  }
}
```

### Environment-Specific Overrides
Different configurations can be applied based on environment:
- `development`: More permissive with dry-run encouraged
- `staging`: Moderate restrictions with monitoring
- `production`: Strictest controls with extensive logging

## Usage Scenarios

### Safe Development
```python
from security_sandbox_controls import SafetyControls

# Initialize with DRY_RUN mode for safe testing
controls = SafetyControls(mode="DRY_RUN")
result = controls.execute_operation("file_write", path="/tmp/test.txt", content="test")
# Operation simulates writing but doesn't actually modify the file
print(result.simulation_report)
```

### Production Safety
```python
from security_sandbox_controls import SafetyControls

# Initialize with strict production settings
controls = SafetyControls(mode="PRODUCTION")
try:
    # Rate-limited operation
    result = controls.execute_operation("network_request", url="https://api.example.com")
except RateLimitExceededError as e:
    print(f"Rate limit exceeded: {e.retry_after}")
```

### Credential Management
```python
from security_sandbox_controls import CredentialManager

cm = CredentialManager()
# Safely retrieve isolated credentials
db_creds = cm.get_credentials("database_primary")
# Automatic access logging occurs
```

## Safety Guarantees

### Atomic Operations
- All operations are atomic when possible
- Rollback mechanisms for multi-step operations
- Consistent state preservation

### Resource Protection
- File system protections
- Network access controls
- Process execution limits
- Memory usage constraints

### Audit Trail
- Comprehensive logging of all operations
- Security event tracking
- Compliance reporting capabilities
- Forensic analysis support

## Integration Points

### With Claude Code
- Intercepts potentially dangerous operations
- Applies safety controls transparently
- Maintains normal operation flow
- Provides detailed feedback when controls are triggered

### With External Systems
- Integrates with existing IAM systems
- Compatible with enterprise SSO solutions
- Supports standard authentication protocols
- Works with existing security infrastructure

## Error Handling

### Rate Limit Exceeded
- Graceful degradation when limits are reached
- Clear indication of retry timing
- Alternative operation suggestions

### Permission Denied
- Detailed reason for denial
- Path to obtain required permissions
- Escalation procedures

### Security Violation
- Immediate operation termination
- Comprehensive security event logging
- Notification to security team

## Compliance Standards
- SOC 2 Type II compliance ready
- GDPR data protection compliant
- HIPAA security rule compatible
- NIST cybersecurity framework aligned

## Performance Considerations
- Minimal overhead for safety checks
- Asynchronous safety operations where possible
- Caching of permission decisions
- Optimized for high-throughput scenarios

## Dependencies
- `cryptography` for secure credential handling
- `redis` for rate limiting coordination (optional)
- `pydantic` for configuration validation
- `structlog` for structured logging
## When NOT to Use This Skill

- **Production systems requiring zero downtime** — sandbox controls may interfere with production traffic during initial configuration; configure in a staging environment first
- **High-throughput systems** — DRY_RUN mode and comprehensive rate limiting add overhead; profile the impact before applying to latency-sensitive production paths
- **Simple local development scripts** — full sandbox security controls are excessive for single-developer local scripts; use environment-variable guards instead

## Common Mistakes

- Forgetting to disable DRY_RUN mode before going live — code in DRY_RUN silently skips side effects; failing to flip the flag means production actions never execute
- Setting rate limits that are too aggressive for legitimate traffic — overly tight limits reject valid requests; baseline real traffic patterns before configuring limits
- Not testing sandbox controls with a red-team exercise — security controls that haven't been tested under adversarial conditions provide false assurance

## Related Skills

- [`audit-logging-system`](../audit-logging-system/SKILL.md) — Pair security sandbox controls with comprehensive audit logging
- [`code-validation-sandbox`](../code-validation-sandbox/SKILL.md) — Code-level sandbox for executing and testing code safely
- [`qa-testing-specialist`](../qa-testing-specialist/SKILL.md) — Test that security controls are working as intended
