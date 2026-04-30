---
name: email-mcp-server
description: MCP server enabling Claude Code to draft, send, and search emails via Gmail with HITL (Human-in-the-Loop) enforcement. Use when Claude needs to interact with Gmail for email operations while maintaining human oversight and approval for sensitive actions.
---

# Email MCP Server

## Overview

The Email MCP Server is a Model Context Protocol (MCP) server that enables Claude Code to interact with Gmail for email operations. It provides secure, human-monitored access to email functionality with Human-in-the-Loop (HITL) enforcement for sensitive operations.

## Core Capabilities

The email MCP server provides:

1. **Email Drafting**: Compose emails with rich formatting and attachments
2. **Email Sending**: Send emails with appropriate HITL approvals
3. **Email Search**: Search and retrieve emails based on various criteria
4. **HITL Enforcement**: Human oversight for sensitive email operations
5. **Security Controls**: Authentication and access management
6. **Audit Trail**: Logging of all email operations

## Usage Scenarios

Use the email MCP server when:
- Claude needs to draft professional emails
- Automated email sending with human approval is required
- Email searching and retrieval is needed
- Human oversight is mandatory for email operations
- Compliance with email policies is required
- Integration with Gmail is necessary

## Architecture

The server follows MCP standards and provides secure access to Gmail with appropriate safeguards:

- **Authentication Layer**: OAuth2 with Google
- **Authorization Layer**: Role-based access control
- **HITL Gateway**: Approval workflow for sensitive operations
- **API Layer**: MCP-compliant endpoints for email operations
- **Audit Layer**: Comprehensive logging and tracking

## MCP Endpoints

### Available Operations

The server exposes these MCP-compatible operations:

- `draft_email`: Create a new email draft
- `send_email`: Send an email (requires HITL approval)
- `search_emails`: Search emails by criteria
- `get_email`: Retrieve specific email content
- `list_labels`: Get available Gmail labels
- `create_label`: Create new labels
- `get_thread`: Retrieve email thread
- `get_profile`: Get user profile information

### HITL Enforcement

Certain operations require human approval:
- Sending emails to external domains
- Sending emails with attachments over size limits
- Sending emails with sensitive keywords
- Bulk email operations

## Security Considerations

### Authentication

- OAuth2 with Google Workspace/Gmail
- Secure token storage and refresh
- Session management
- Device verification

### Authorization

- Scope-based permissions (read/write/send)
- Role-based access control
- Domain restrictions
- Rate limiting

### HITL Controls

- Approval workflows for sensitive operations
- Human verification for critical actions
- Audit trail for all operations
- Escalation procedures

## Configuration

### Required Setup

1. Google Cloud Project with Gmail API enabled
2. OAuth2 credentials (client ID and secret)
3. Authorized redirect URIs
4. HITL approval endpoints (optional)

### Example Configuration

```json
{
  "gmail": {
    "client_id": "your-client-id",
    "client_secret": "your-client-secret",
    "scopes": ["https://www.googleapis.com/auth/gmail.modify", "https://www.googleapis.com/auth/gmail.send"],
    "redirect_uris": ["http://localhost:8080/oauth/callback"]
  },
  "hitl": {
    "enabled": true,
    "approval_required": {
      "external_recipients": true,
      "attachment_size_mb": 10,
      "sensitive_keywords": ["confidential", "private", "urgent"]
    }
  },
  "server": {
    "port": 8080,
    "host": "localhost"
  }
}
```

## HITL Workflow

### Standard Workflow

1. Claude requests email operation
2. Server evaluates HITL requirements
3. If approval required, notify human reviewer
4. Human approves/rejects operation
5. Server executes approved operation
6. Result returned to Claude

### Emergency Override

For urgent operations, emergency override procedures are available with additional authentication.

## Resources

This skill includes example resource directories that demonstrate how to implement email operations with MCP compliance:

### scripts/
Python scripts for MCP server implementation, Gmail API integration, and HITL workflows.

### references/
Documentation for Gmail API integration, OAuth2 setup, and HITL procedures.

### assets/
Configuration templates and example implementations for various email scenarios.

---

The email MCP server enables secure and compliant email operations with appropriate human oversight.