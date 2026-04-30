---
name: calendar-mcp-server
description: MCP server enabling Claude Code to create, update, and query Google Calendar events with HITL approval for shared calendar modifications. Use when Claude needs to manage scheduling, create meetings, check availability, or automate calendar operations.
---

# Calendar MCP Server

MCP server for Google Calendar integration with Human-in-the-Loop (HITL) approval controls for sensitive calendar operations.

## Prerequisites

1. **Google Cloud Project** with Google Calendar API enabled
2. **OAuth2 credentials** (`credentials.json` from Google Cloud Console)
3. **Python packages**: `pip install -r assets/requirements.txt`
4. **FastMCP** (optional, for native MCP transport): `pip install fastmcp`

## Quick Start

### 1. Set Up Google Calendar API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create or select a project
3. Enable the **Google Calendar API**
4. Create OAuth 2.0 credentials (Desktop Application)
5. Download `credentials.json` to your working directory

### 2. Configure Environment

```bash
export GOOGLE_CALENDAR_CREDENTIALS="./credentials.json"
export GOOGLE_CALENDAR_TOKEN="./calendar_token.json"
export CALENDAR_APPROVAL_DIR="./Pending_Approval"
```

### 3. Start the Server

```bash
python scripts/calendar_mcp_server.py --credentials ./credentials.json
```

### 4. Python Usage

```python
from scripts.calendar_mcp_server import CalendarMCPServer

server = CalendarMCPServer(
    credentials_path="./credentials.json",
    token_path="./calendar_token.json"
)

# List upcoming events
events = server.list_events(
    calendar_id="primary",
    time_min="2026-02-01T00:00:00Z",
    time_max="2026-02-28T23:59:59Z",
    max_results=10
)

# Create an event (HITL required for shared calendars)
result = server.create_event(
    calendar_id="primary",
    summary="Team Standup",
    start="2026-02-10T09:00:00",
    end="2026-02-10T09:30:00",
    description="Daily standup meeting",
    attendees=["alice@company.com", "bob@company.com"],
    location="Conference Room A"
)

# Check availability
busy_slots = server.check_availability(
    calendar_id="primary",
    time_min="2026-02-10T08:00:00Z",
    time_max="2026-02-10T18:00:00Z"
)
```

## MCP Tools

| Tool | Description | HITL Required |
|------|-------------|---------------|
| `list_events` | List upcoming calendar events | No |
| `get_event` | Get details of a specific event | No |
| `create_event` | Create a new calendar event | Yes (shared calendars / external attendees) |
| `update_event` | Update an existing event | Yes |
| `delete_event` | Delete a calendar event | Always |
| `check_availability` | Check free/busy status | No |

## HITL Controls

| Operation | Trigger | Approval Method |
|-----------|---------|-----------------|
| Create event with external attendees | Attendees outside organization domain | File-based approval in `/Pending_Approval/` |
| Create event on shared calendar | Calendar ID is not `primary` | File-based approval |
| Update any event | Always | File-based approval |
| Delete any event | Always | File-based approval |
| Create personal event (no attendees) | Never | Auto-approved |
| List / Get / Check availability | Never | No approval needed |

## Configuration Options

### CalendarConfig

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `credentials_path` | str | `"credentials.json"` | Path to Google OAuth credentials |
| `token_path` | str | `"calendar_token.json"` | Path to store/load OAuth token |
| `default_calendar_id` | str | `"primary"` | Default calendar to operate on |
| `approval_dir` | str | `"./Pending_Approval"` | Directory for HITL approval files |
| `approval_timeout_seconds` | int | `3600` | Timeout for pending approvals |
| `organization_domains` | list | `[]` | Internal domains (external attendees trigger HITL) |
| `auto_approve_personal` | bool | `True` | Auto-approve events with no attendees on primary calendar |
| `max_results_default` | int | `25` | Default max results for list queries |
| `timezone` | str | `"UTC"` | Default timezone for events |

## Output Structure

Approval files are written to `Pending_Approval/calendar/`:

```
Pending_Approval/
  calendar/
    2026-02-06_1030_create_Team_Standup.md
    2026-02-06_1045_delete_Old_Meeting.md
```

### Approval File Format

```markdown
---
type: calendar-approval
status: pending
operation: create_event
created: 2026-02-06 10:30
expires: 2026-02-06 11:30
calendar_id: primary
---

# Calendar Operation: Create Event

## Event Details

| Field | Value |
|-------|-------|
| **Summary** | Team Standup |
| **Start** | 2026-02-10 09:00 |
| **End** | 2026-02-10 09:30 |
| **Attendees** | alice@company.com, bob@company.com |
| **Location** | Conference Room A |

## Actions

- [ ] Approve this operation
- [ ] Reject this operation

> To approve: change status to `approved` and save
> To reject: change status to `rejected` and save
```

## Google Calendar API Setup

1. Visit [Google Cloud Console](https://console.cloud.google.com/apis/library/calendar-json.googleapis.com)
2. Enable the Google Calendar API
3. Go to Credentials > Create Credentials > OAuth 2.0 Client ID
4. Select "Desktop application" as the application type
5. Download the credentials JSON file
6. Place it at the configured `credentials_path`

## Integration with Other Skills

```python
from scripts.calendar_mcp_server import CalendarMCPServer
from scripts.config_manager import CalendarConfig

config = CalendarConfig(
    credentials_path="./credentials.json",
    organization_domains=["company.com", "subsidiary.com"],
    auto_approve_personal=True
)

server = CalendarMCPServer(config=config)
```
