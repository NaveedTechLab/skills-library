---
name: slack-mcp-server
description: MCP server enabling Claude Code to send messages, read channels, manage threads, and search Slack workspaces with HITL approval for external communications. Use when Claude needs Slack integration for team communication, notifications, or workflow automation.
---

# Slack MCP Server

## Overview

The Slack MCP Server is a Model Context Protocol (MCP) server built with FastMCP that enables Claude Code to interact with Slack workspaces. It provides secure, human-monitored access to Slack functionality with Human-in-the-Loop (HITL) enforcement for sensitive operations such as messaging external channels, sending DMs to new users, file uploads, and bulk messaging.

## Prerequisites

### Slack Bot Token

1. Create a Slack App at https://api.slack.com/apps
2. Navigate to **OAuth & Permissions**
3. Add the following Bot Token Scopes:

| Scope | Purpose |
|---|---|
| `channels:read` | List and get info about public channels |
| `channels:history` | Read messages in public channels |
| `groups:read` | List and get info about private channels |
| `groups:history` | Read messages in private channels |
| `chat:write` | Send messages as the bot |
| `files:write` | Upload files |
| `files:read` | Read file metadata |
| `reactions:write` | Add emoji reactions |
| `reactions:read` | Read emoji reactions |
| `search:read` | Search messages in the workspace |
| `users:read` | Read user profiles |
| `im:history` | Read DM history |
| `im:write` | Open DM channels |

4. Install the app to your workspace
5. Copy the **Bot User OAuth Token** (starts with `xoxb-`)

### Environment Variables

```bash
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token        # Optional: for Socket Mode
SLACK_DEFAULT_CHANNEL=general               # Optional: default channel
SLACK_SIGNING_SECRET=your-signing-secret    # Optional: for request verification
```

## Quick Start

```bash
# Install dependencies
pip install -r .claude/skills/slack-mcp-server/assets/requirements.txt

# Set environment variable
export SLACK_BOT_TOKEN=xoxb-your-bot-token

# Run the server
python .claude/skills/slack-mcp-server/scripts/slack_mcp_server.py
```

## MCP Tools

### Available Operations

| Tool | Description | HITL Required |
|---|---|---|
| `send_message` | Send a message to a channel or thread | External channels only |
| `read_channel` | Read recent messages from a channel | No |
| `search_messages` | Search messages across the workspace | No |
| `list_channels` | List channels in the workspace | No |
| `get_channel_info` | Get detailed channel information | No |
| `upload_file` | Upload a file to a channel | Always |
| `add_reaction` | Add an emoji reaction to a message | No |
| `get_thread` | Get all replies in a thread | No |

### Python Usage

```python
from slack_mcp_server import create_slack_mcp_server

# Create and run the server
server = create_slack_mcp_server()
server.run()
```

### Tool Examples

```python
# Send a message
await send_message(channel="#general", text="Hello from Claude!")

# Send a threaded reply
await send_message(channel="#general", text="Reply here", thread_ts="1234567890.123456")

# Read last 10 messages
messages = await read_channel(channel="#general", limit=10)

# Search workspace
results = await search_messages(query="deployment update", count=5)

# Upload a file
await upload_file(channel="#general", content="Report data...", filename="report.txt", title="Daily Report")

# Add a reaction
await add_reaction(channel="#general", timestamp="1234567890.123456", emoji="thumbsup")

# Get thread replies
thread = await get_thread(channel="#general", thread_ts="1234567890.123456")
```

## HITL Controls

### Approval Matrix

| Action | Condition | HITL Required |
|---|---|---|
| Send message | Internal channel | No |
| Send message | External/shared channel | Yes |
| Send DM | Previously messaged user | No |
| Send DM | New user (first contact) | Yes |
| Upload file | Any channel | Yes |
| Bulk messages | More than 3 in 60 seconds | Yes |
| Add reaction | Any message | No |
| Read channel | Any channel | No |
| Search messages | Any query | No |

### Approval Workflow

1. Claude requests a HITL-gated operation
2. An approval request is written to `Pending_Approval/` directory
3. Human reviews and approves or rejects via the approval file
4. On approval, the operation executes and result is returned
5. All decisions are audit-logged

## Configuration

### config_manager.py Settings

```python
@dataclass
class SlackConfig:
    bot_token: str              # SLACK_BOT_TOKEN
    app_token: str              # SLACK_APP_TOKEN (optional)
    default_channel: str        # Default channel for messages
    hitl_enabled: bool          # Enable/disable HITL globally
    hitl_external_channels: bool # Require approval for external channels
    hitl_new_dm_users: bool     # Require approval for new DM recipients
    hitl_file_uploads: bool     # Require approval for file uploads
    hitl_bulk_threshold: int    # Message count triggering bulk HITL
    hitl_bulk_window_seconds: int # Window for counting bulk messages
    rate_limit_per_minute: int  # Max API calls per minute
    rate_limit_per_second: int  # Max API calls per second
    audit_log_path: str         # Path to audit log file
    approval_dir: str           # Directory for pending approvals
    approval_timeout_seconds: int # How long approvals remain valid
```

### Rate Limiting

The server enforces Slack API rate limits:
- **Tier 1**: 1 request per second (most write operations)
- **Tier 2**: 20 requests per minute (search, list operations)
- **Tier 3**: 50 requests per minute (read operations)

Custom rate limits can be configured via `SlackConfig`.

## Architecture

```
slack_mcp_server.py      -- FastMCP server with 8 tool endpoints
approval_workflow.py     -- HITL approval engine with file-based workflow
config_manager.py        -- Configuration dataclass and environment loader
```

## Security Considerations

- Bot tokens are loaded from environment variables, never hardcoded
- All write operations are audit-logged with timestamps and context
- HITL approval is enforced for sensitive operations before execution
- Rate limiting prevents accidental API abuse
- File uploads always require human approval regardless of destination
- The approval directory should have restricted filesystem permissions

## Resources

### scripts/
Python scripts for the FastMCP server, HITL approval workflow, and configuration management.

### assets/
Requirements file and configuration templates.

---

The Slack MCP server enables secure and compliant Slack workspace operations with appropriate human oversight.
