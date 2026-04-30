# Security Sandbox Controls - Usage Examples

## Overview
This document provides practical examples of how to use the Security Sandbox Controls skill for various scenarios including DRY_RUN mode, rate limiting, credential isolation, and permission boundaries.

## Installation and Setup

### Prerequisites
```bash
pip install cryptography redis pydantic structlog
```

### Basic Initialization
```python
from security_sandbox_controls.safety_controls import (
    SafetyControls, SafetyMode, OperationType, initialize_safety_controls
)
from security_sandbox_controls.config_manager import ConfigManager

# Initialize with default development configuration
controls = initialize_safety_controls(SafetyMode.DEVELOPMENT)

# Or initialize with custom configuration
config_manager = ConfigManager("./my_config.json")
controls = SafetyControls(config=config_manager.config)
```

## DRY_RUN Mode Examples

### Testing File Operations Safely
```python
# Execute file operations in DRY_RUN mode to simulate without making changes
result = controls.execute_operation(
    OperationType.FILE_WRITE,
    user="developer",
    path="/important/file.txt",
    content="critical data"
)

print(f"Simulation report: {result.simulation_report}")
print(f"Would have succeeded: {result.success}")
print(f"Simulation mode: {result.simulation}")
```

### Testing Network Requests
```python
# Test network operations without actually sending requests
result = controls.execute_operation(
    OperationType.NETWORK_REQUEST,
    user="api_user",
    url="https://api.example.com/data",
    method="POST",
    payload={"key": "value"}
)

if result.simulation:
    print(f"Would have sent request to: {result.params['url']}")
    print(f"Method would have been: {result.params['method']}")
```

## Rate Limiting Examples

### Custom Rate Limits
```python
from security_sandbox_controls.config_manager import SecuritySandboxConfig, RateLimitRule

# Create configuration with custom rate limits
config = SecuritySandboxConfig(
    rate_limits={
        "file_operations": RateLimitRule(max_operations=50, window_seconds=60),  # 50 ops per minute
        "network_requests": RateLimitRule(max_operations=200, window_seconds=60), # 200 ops per minute
        "system_commands": RateLimitRule(max_operations=5, window_seconds=60, burst_allowance=2), # 5 ops + 2 burst
    }
)

controls = SafetyControls(config=config)

# Attempt to execute operations
try:
    result = controls.execute_operation(OperationType.FILE_READ, user="user1", path="/file.txt")
except RateLimitExceededError as e:
    print(f"Rate limited: {e.operation}, retry after {e.retry_after} seconds")
```

### Per-User Rate Limiting
```python
from security_sandbox_controls.safety_controls import RateLimitRule

# Configure rate limits that apply per user
rate_limit_rule = RateLimitRule(
    max_operations=10,
    window_seconds=60,
    per_user=True  # Rate limit applies individually per user
)

# This will track usage separately for each user
controls.config.rate_limits["api_calls"] = rate_limit_rule

# Different users have separate rate limits
result1 = controls.execute_operation(OperationType.NETWORK_REQUEST, user="user_a", url="https://api.com")
result2 = controls.execute_operation(OperationType.NETWORK_REQUEST, user="user_b", url="https://api.com")
```

## Credential Isolation Examples

### Storing and Retrieving Credentials Securely
```python
# Store credentials securely with encryption
controls.set_credential("database_password", "super_secret_password")
controls.set_credential("api_key", "sk-1234567890abcdef", encrypt=True)

# Retrieve credentials securely
db_password = controls.get_credential("database_password", user="app_user")
api_key = controls.get_credential("api_key", user="api_user")

print(f"DB password length: {len(db_password) if db_password else 0}")
print(f"API key length: {len(api_key) if api_key else 0}")
```

### Credential Rotation
```python
# Rotate credentials automatically
success = controls.credential_manager.rotate_credential(
    "database_password",
    "new_super_secret_password"
)

if success:
    print("Credential rotated successfully")
else:
    print("Credential rotation failed")
```

## Permission Boundary Examples

### Role-Based Access Control
```python
# Assign roles to users
controls.assign_role("alice", "admin")
controls.assign_role("bob", "standard_user")
controls.assign_role("charlie", "restricted_user")

# Check permissions before operations
if controls.check_permission("alice", "file_write"):
    result = controls.execute_operation(
        OperationType.FILE_WRITE,
        user="alice",
        path="/tmp/test.txt",
        content="admin content"
    )
else:
    print("Alice doesn't have file_write permission")

# Check user's total permissions
alice_permissions = controls.get_user_permissions("alice")
print(f"Alice's permissions: {alice_permissions}")
```

### Custom Permission Checking
```python
# Define custom permissions for specific operations
controls.assign_role("service_account", "api_client")

try:
    # This will check if the user has permission for network requests
    result = controls.execute_operation(
        OperationType.NETWORK_REQUEST,
        user="service_account",
        url="https://internal-api.company.com/data"
    )
    print(f"API call result: {result.success}")
except PermissionDeniedError as e:
    print(f"Permission denied: {e}")
```

## Production Deployment Examples

### Production Configuration
```python
from security_sandbox_controls.config_manager import create_production_config

# Create production-safe configuration
create_production_config("./prod_security_config.json")

# Load production configuration
prod_config_manager = ConfigManager("./prod_security_config.json")
prod_controls = SafetyControls(config=prod_config_manager.config)

# In production, dangerous operations are disabled by default
try:
    # This will raise SecurityViolationError in production mode
    result = prod_controls.execute_operation(
        OperationType.SYSTEM_COMMAND,
        user="user",
        command="rm -rf /"
    )
except SecurityViolationError as e:
    print(f"Blocked dangerous operation: {e}")
```

### Environment-Specific Configuration
```python
from security_sandbox_controls.config_manager import ConfigManager

# Get configuration appropriate for current environment
config_manager = ConfigManager()
current_env = os.getenv("ENVIRONMENT", "development")

if current_env == "production":
    env_config = config_manager.get_environment_config("production")
elif current_env == "staging":
    env_config = config_manager.get_environment_config("staging")
else:
    env_config = config_manager.get_environment_config("development")

controls = SafetyControls(config=env_config)
```

## Advanced Usage Examples

### Batch Operation Safety
```python
# Execute multiple operations safely with rate limiting
operations = [
    (OperationType.FILE_READ, {"path": "/file1.txt"}),
    (OperationType.FILE_READ, {"path": "/file2.txt"}),
    (OperationType.NETWORK_REQUEST, {"url": "https://api.com/data1"}),
    (OperationType.NETWORK_REQUEST, {"url": "https://api.com/data2"}),
]

results = []
for op_type, params in operations:
    try:
        result = controls.execute_operation(op_type, user="batch_user", **params)
        results.append(result)
    except RateLimitExceededError:
        print(f"Rate limit hit, pausing before continuing...")
        time.sleep(1)  # Wait before continuing
        continue

successful_ops = sum(1 for r in results if r.success)
print(f"Successfully executed {successful_ops}/{len(operations)} operations")
```

### Audit Trail Generation
```python
# Generate audit reports from the audit log
audit_log = controls.get_audit_log()

# Filter for specific user
user_audit_entries = [entry for entry in audit_log if entry["user"] == "suspicious_user"]

# Filter for failed operations
failed_ops = [entry for entry in audit_log if not entry["success"]]

# Generate summary statistics
from collections import Counter
op_counts = Counter(entry["operation"] for entry in audit_log)
print(f"Operation distribution: {dict(op_counts)}")

# Export audit log
with open("audit_report.json", "w") as f:
    json.dump(audit_log, f, indent=2)
```

## Error Handling Examples

### Comprehensive Error Handling
```python
from security_sandbox_controls.safety_controls import (
    RateLimitExceededError,
    PermissionDeniedError,
    SecurityViolationError
)

def safe_operation_wrapper(controls, operation_type, user, **params):
    try:
        result = controls.execute_operation(operation_type, user, **params)
        return result
    except RateLimitExceededError as e:
        print(f"Rate limited: {e.operation}, retry after {e.retry_after}s")
        return None
    except PermissionDeniedError as e:
        print(f"Permission denied for {user}: {e}")
        return None
    except SecurityViolationError as e:
        print(f"Security violation: {e}")
        # Log security event
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

# Usage
result = safe_operation_wrapper(
    controls,
    OperationType.FILE_WRITE,
    "user",
    path="/test.txt",
    content="test"
)
```

## Integration Examples

### With Claude Code Workflow
```python
# Integrate with Claude Code operations
def cluade_code_safe_execute(claude_controls, operation, **params):
    """
    Wrapper to ensure all Claude Code operations go through safety controls
    """
    # Map Claude Code operations to security operation types
    op_mapping = {
        "file_read": OperationType.FILE_READ,
        "file_write": OperationType.FILE_WRITE,
        "network_request": OperationType.NETWORK_REQUEST,
        "shell_execute": OperationType.SYSTEM_COMMAND
    }

    security_op = op_mapping.get(operation)
    if not security_op:
        raise ValueError(f"Unknown operation: {operation}")

    # Execute through safety controls
    result = claude_controls.execute_operation(security_op, user="claude_user", **params)
    return result
```

## Configuration Examples

### Sample Configuration Files

#### Development Configuration (`dev_config.json`)
```json
{
  "mode": "DEVELOPMENT",
  "dry_run_enabled": true,
  "rate_limits": {
    "file_operations": {
      "max_operations": 1000,
      "window_seconds": 60,
      "burst_allowance": 100
    },
    "network_requests": {
      "max_operations": 500,
      "window_seconds": 60,
      "burst_allowance": 50
    }
  },
  "credentials_isolated": true,
  "permission_enforcement": false,
  "dangerous_operations_allowed": true,
  "audit_logging": true,
  "environment": "development"
}
```

#### Production Configuration (`prod_config.json`)
```json
{
  "mode": "PRODUCTION",
  "dry_run_enabled": false,
  "rate_limits": {
    "file_operations": {
      "max_operations": 50,
      "window_seconds": 60
    },
    "network_requests": {
      "max_operations": 25,
      "window_seconds": 60
    },
    "system_commands": {
      "max_operations": 5,
      "window_seconds": 60
    },
    "credential_access": {
      "max_operations": 5,
      "window_seconds": 60
    }
  },
  "credentials_isolated": true,
  "permission_enforcement": true,
  "dangerous_operations_allowed": false,
  "audit_logging": true,
  "environment": "production"
}
```

These examples demonstrate the flexibility and power of the Security Sandbox Controls skill in various scenarios while maintaining safety and compliance requirements.