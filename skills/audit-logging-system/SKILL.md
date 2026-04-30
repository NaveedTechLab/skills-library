---
name: audit-logging-system
description: Structured JSON audit logging for all agent actions with retention and traceability guarantees. Use when Claude needs to maintain comprehensive logs of all operations, track changes, ensure compliance, or provide forensic capabilities for agent activities.
---

# Audit Logging System

## Overview

The Audit Logging System provides structured JSON audit logging for all agent actions with guaranteed retention and traceability. It ensures comprehensive logging of all operations with searchable, standardized records for compliance, forensics, and accountability.

## Core Capabilities

The audit logging system provides:

1. **Structured Logging**: JSON-formatted logs with standardized fields
2. **Comprehensive Coverage**: Log all agent actions and operations
3. **Retention Management**: Automatic log rotation and retention policies
4. **Traceability**: Chain of custody and correlation between related events
5. **Search & Query**: Efficient querying of historical events
6. **Compliance**: Meet regulatory requirements for audit trails
7. **Security**: Tamper-evident logging with integrity protection

## Usage Scenarios

Use the audit logging system when:
- Tracking all agent actions for accountability
- Meeting compliance requirements (SOX, HIPAA, GDPR, etc.)
- Forensic analysis of system operations
- Monitoring for security incidents
- Debugging and troubleshooting
- Maintaining change logs for configuration management
- Providing audit trails for regulatory reporting

## Log Structure

### Standard Log Format

All logs follow a consistent JSON structure:

```json
{
  "timestamp": "2024-01-15T10:30:00.123Z",
  "log_level": "INFO",
  "event_type": "agent_action",
  "event_id": "uuid-v4-identifier",
  "correlation_id": "request-correlation-id",
  "trace_id": "distributed-trace-id",
  "user": {
    "id": "user-identifier",
    "role": "user-role",
    "session_id": "session-identifier"
  },
  "agent": {
    "id": "agent-identifier",
    "version": "agent-version",
    "type": "agent-type"
  },
  "action": {
    "name": "action-performed",
    "parameters": {},
    "result": "success|failure",
    "duration_ms": 1234
  },
  "resources": [
    {
      "id": "resource-identifier",
      "type": "resource-type",
      "operation": "read|write|delete|execute"
    }
  ],
  "context": {
    "source_ip": "client-ip-address",
    "user_agent": "client-identifier",
    "location": "geographic-location",
    "environment": "production|staging|development"
  },
  "metadata": {
    "version": "log-schema-version",
    "integrity_hash": "sha256-hash-of-previous-log"
  }
}
```

### Event Types

Common event types include:
- `agent_action`: Agent performing an operation
- `file_access`: File read/write/delete operations
- `api_call`: External API interactions
- `config_change`: Configuration modifications
- `authentication`: Login/logout events
- `authorization`: Permission checks and access decisions
- `data_access`: Reading/writing sensitive data
- `system_event`: Infrastructure events

## Retention Policies

### Standard Retention

- **Production logs**: 7 years (compliance requirement)
- **Staging logs**: 1 year
- **Development logs**: 90 days
- **Security events**: 10 years (enhanced retention)

### Log Rotation

- **Daily rotation**: New log file per day
- **Size-based rotation**: Rotate at 100MB
- **Time-based archival**: Archive after retention period

## Traceability Features

### Correlation IDs

Each operation receives a correlation ID that tracks the entire operation chain:

```json
{
  "correlation_id": "req-abc123-def456-ghi789",
  "trace_id": "trace-xyz987-wvu654-rst321"
}
```

### Chain of Custody

Related events are linked through:
- Parent-child relationships
- Transaction IDs
- Session tracking
- Cross-referenced event IDs

## Search and Query Capabilities

### Query Syntax

Structured queries using a standard syntax:
```
user.id:john AND action.result:failure AND timestamp:[2024-01-01 TO 2024-01-31]
```

### Indexing Strategy

- Timestamp-based indexing for time range queries
- User and agent ID indexing for accountability
- Event type indexing for categorization
- Resource ID indexing for data access tracking

## Security and Integrity

### Tamper Protection

- Cryptographic hashing of log entries
- Digital signatures for integrity
- Immutable log storage
- Chain of custody verification

### Access Controls

- Role-based access to audit logs
- Privileged access logging
- Segregation of duties for log management
- Secure transmission protocols

## Compliance Standards

The system supports compliance with:
- **SOX**: Financial controls and transparency
- **HIPAA**: Healthcare data protection
- **GDPR**: Data privacy and rights
- **PCI DSS**: Payment card security
- **ISO 27001**: Information security management
- **NIST**: Cybersecurity framework

## Configuration

### Basic Configuration

```json
{
  "audit_logging": {
    "enabled": true,
    "log_format": "structured_json",
    "retention_days": 2555,
    "storage_location": "/var/log/audit",
    "rotation": {
      "max_size_mb": 100,
      "compress": true,
      "keep_archives": 10
    },
    "security": {
      "integrity_protection": true,
      "encryption": "aes-256-gcm",
      "signing": true
    }
  }
}
```

### Event Filtering

Configure which events to log:

```json
{
  "event_filters": {
    "include": ["agent_action", "data_access", "config_change"],
    "exclude": ["heartbeat", "health_check"],
    "levels": ["INFO", "WARN", "ERROR", "CRITICAL"]
  }
}
```

## Integration Points

### With Agent Systems

The logging system integrates with:
- Agent core operations
- File system operations
- API calls and external integrations
- Authentication and authorization systems
- Configuration management
- Error handling and exception tracking

### External Systems

Integrates with:
- SIEM systems (Splunk, ELK, QRadar)
- Compliance reporting tools
- Security monitoring platforms
- Backup and archival systems

## Resources

This skill includes example resource directories that demonstrate how to implement audit logging:

### scripts/
Python scripts for audit log generation, management, and querying.

### references/
Documentation for log schema, compliance requirements, and integration patterns.

### assets/
Configuration templates and example implementations for various audit scenarios.

---

The audit logging system enables comprehensive tracking and accountability for all agent actions with guaranteed retention and traceability.