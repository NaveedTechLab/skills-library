# Email MCP Server Implementation Guide

## Overview

This guide provides detailed information about implementing the Email MCP Server for Gmail integration with Human-in-the-Loop (HITL) enforcement.

## Prerequisites

### Google Cloud Platform Setup

1. **Create a Google Cloud Project**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Note the Project ID

2. **Enable Gmail API**:
   - Navigate to APIs & Services > Library
   - Search for "Gmail API"
   - Click "Enable"

3. **Create OAuth 2.0 Credentials**:
   - Go to APIs & Services > Credentials
   - Click "Create Credentials" > "OAuth 2.0 Client IDs"
   - Application type: Desktop Application
   - Download the credentials JSON file
   - Save as `credentials.json` in your project directory

4. **Configure OAuth Consent Screen** (if required):
   - If you're using a personal account, you may need to configure the consent screen
   - Go to APIs & Services > OAuth consent screen
   - Select "External" user type
   - Fill in required information
   - Add your email to test users if publishing is required

## Configuration

### Server Configuration

The server uses a JSON configuration file with the following structure:

```json
{
  "credentials_path": "credentials.json",
  "token_path": "token.pickle",
  "server": {
    "host": "localhost",
    "port": 8080
  },
  "hitl": {
    "enabled": true,
    "approval_timeout": 3600,
    "approval_required": {
      "external_recipients": true,
      "attachment_size_mb": 10,
      "sensitive_keywords": ["confidential", "private", "urgent", "sensitive", "classified"]
    }
  },
  "email_settings": {
    "default_signature": "--\nSent via Claude Email MCP Server",
    "max_attachment_size_mb": 25,
    "rate_limit": {
      "requests_per_minute": 10,
      "burst_size": 5
    }
  }
}
```

### HITL Configuration

The Human-in-the-Loop system can be configured with various triggers:

- **External Recipients**: Require approval for emails sent outside your organization
- **Attachment Size**: Require approval for large attachments
- **Sensitive Keywords**: Require approval when certain keywords are detected
- **Rate Limiting**: Limit the number of operations per time period

## MCP Endpoints

### Available Endpoints

#### POST /draft_email
Draft a new email message.

Request body:
```json
{
  "to": "recipient@example.com",
  "subject": "Email Subject",
  "body": "Email body content",
  "cc": "cc@example.com",
  "bcc": "bcc@example.com",
  "attachments": ["/path/to/file.pdf"],
  "html_body": "<html><body>HTML content</body></html>"
}
```

Response:
```json
{
  "success": true,
  "draft_id": "draft123"
}
```

#### POST /send_email
Send an email with HITL approval if required.

Request body:
```json
{
  "to": "recipient@example.com",
  "subject": "Email Subject",
  "body": "Email body content",
  "requester": "Claude"
}
```

Response:
- If no approval needed: `{"success": true, "result": "message123"}`
- If approval needed: `{"success": true, "result": "APPROVAL_NEEDED:request123"}`

#### POST /search_emails
Search emails based on criteria.

Request body:
```json
{
  "query": "from:someone@example.com",
  "max_results": 10,
  "before_date": "2023-12-31",
  "after_date": "2023-01-01"
}
```

Response:
```json
{
  "success": true,
  "emails": [...]
}
```

#### GET /get_email/{message_id}
Retrieve a specific email by message ID.

#### GET /list_labels
Get all Gmail labels.

#### POST /create_label
Create a new label.

Request body:
```json
{
  "name": "New Label"
}
```

#### GET /profile
Get user profile information.

#### GET /approval_requests
Get pending approval requests.

#### POST /approve_request
Approve a pending request.

Request body:
```json
{
  "request_id": "req123",
  "approved_by": "user@example.com"
}
```

#### POST /reject_request
Reject a pending request.

Request body:
```json
{
  "request_id": "req123",
  "rejected_by": "user@example.com",
  "reason": "Reason for rejection"
}
```

## HITL Workflow Implementation

### Approval Process

1. **Request Submission**: Claude submits an email operation request
2. **Trigger Evaluation**: Server checks if HITL approval is required
3. **Approval Creation**: If required, creates an approval request
4. **Notification**: System notifies approvers (via configured channels)
5. **Review**: Human reviewer examines the request
6. **Decision**: Approver accepts or rejects the request
7. **Execution**: If approved, the operation proceeds

### Approval Criteria

The system can require approval based on:

- **Domain Checking**: Emails to external domains
- **Content Analysis**: Sensitive keywords in subject/body
- **Size Thresholds**: Large attachments
- **Frequency Limits**: Too many requests in a time period
- **Recipient Lists**: Bulk emails or specific high-value targets

## Security Considerations

### Authentication

- OAuth2 with Google Workspace/Gmail
- Secure token storage using pickle (in production, consider encrypted storage)
- Token refresh handling
- Scope minimization (only request necessary permissions)

### Authorization

- Principle of least privilege
- Role-based access control
- Domain restrictions
- IP whitelisting (if applicable)

### Data Protection

- Encrypt sensitive data in transit (HTTPS)
- Secure credential storage
- Audit logging for all operations
- Data retention policies

## Error Handling

The server implements comprehensive error handling:

- **Gmail API Errors**: Wrapped with meaningful messages
- **Network Issues**: Retry logic with exponential backoff
- **Authentication Failures**: Clear error messages and re-authentication prompts
- **Rate Limiting**: Proper HTTP status codes and retry-after headers

## Monitoring and Logging

### Log Categories

- **Access Logs**: All API requests and responses
- **Approval Logs**: HITL approval activities
- **Error Logs**: Technical errors and exceptions
- **Security Logs**: Authentication events and permission changes

### Metrics

The server should track:

- Request volume and response times
- Approval request rates
- Error rates by type
- User activity patterns

## Testing

### Unit Tests

- Gmail API wrapper functionality
- HITL approval logic
- Configuration validation
- Error handling paths

### Integration Tests

- End-to-end email operations
- Approval workflow
- Authentication flows
- API endpoint functionality

## Deployment

### Production Considerations

- **SSL/TLS**: Use HTTPS in production
- **Reverse Proxy**: Deploy behind nginx/Apache for production
- **Process Management**: Use systemd/supervisor for process management
- **Security**: Firewall rules, regular updates
- **Backup**: Regular backups of tokens and configuration

### Environment Variables

Consider using environment variables for sensitive configuration:

```
GMAIL_CREDENTIALS_PATH=/secure/path/credentials.json
EMAIL_SERVER_HOST=0.0.0.0
EMAIL_SERVER_PORT=8080
HITL_APPROVAL_TIMEOUT=7200
```

## Troubleshooting

### Common Issues

1. **Authentication Errors**:
   - Verify credentials.json format
   - Check OAuth consent screen configuration
   - Ensure correct scopes are granted

2. **Permission Errors**:
   - Verify Gmail API is enabled
   - Check user account permissions
   - Confirm OAuth consent for required scopes

3. **Network Issues**:
   - Verify internet connectivity
   - Check firewall/proxy settings
   - Confirm required ports are open

4. **Token Issues**:
   - Delete token.pickle to force re-authentication
   - Check file permissions for token storage
   - Verify token refresh functionality

## Compliance and Governance

### Audit Trail

Maintain comprehensive logs of:
- All email operations
- Approval decisions
- User access and authentication
- Configuration changes

### Compliance Requirements

- Data retention policies
- Access controls for sensitive emails
- Approval workflows for regulated communications
- Regular security reviews

This implementation provides a secure, compliant foundation for Claude Code to interact with Gmail while maintaining appropriate human oversight.