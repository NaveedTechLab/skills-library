---
name: gmail-watcher
description: Monitor Gmail for unread and important emails, creating structured Markdown action files in /Needs_Action folder. Extends BaseWatcher framework with Google OAuth2 authentication. Use when implementing email monitoring, inbox automation, email-to-task conversion, or building personal productivity systems that need Gmail integration.
---

# Gmail Watcher

Monitor Gmail inbox and automatically create actionable Markdown files for emails requiring attention.

## Prerequisites

1. **Google Cloud Project** with Gmail API enabled
2. **OAuth2 credentials** (credentials.json from Google Cloud Console)
3. **Python packages**: `pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client`
4. **BaseWatcher framework** (in sibling directory)

## Quick Start

### 1. Authenticate

```bash
python scripts/cli.py auth --credentials ./credentials.json
```

### 2. Start Watching

```bash
python scripts/cli.py watch --credentials ./credentials.json --output ./Needs_Action
```

### 3. Python Usage

```python
import asyncio
from scripts.gmail_watcher import watch_gmail
from scripts.action_emitter import emit_to_needs_action

async def main():
    watcher = watch_gmail(
        credentials_path="./credentials.json",
        filter_unread=True,
        filter_important=True
    )
    emitter = emit_to_needs_action("./Needs_Action")
    
    watcher.on_event(emitter.emit)
    await watcher.start()
    
    await asyncio.sleep(3600)  # Run for 1 hour
    await watcher.stop()

asyncio.run(main())
```

## Output Structure

```
Needs_Action/
├── 01_Urgent/
│   └── 2024-01-15_1030_John_Meeting_reminder.md
├── 02_High/
│   ├── finance/
│   │   └── 2024-01-15_0900_Accounting_Invoice.md
│   └── development/
│       └── 2024-01-15_1100_GitHub_PR_review.md
├── 03_Normal/
│   └── general/
│       └── 2024-01-15_0800_Client_Project_update.md
└── 04_Low/
    └── newsletters/
```

## Action File Format

```markdown
---
type: email-action
status: pending
priority: high
category: development
created: 2024-01-15 10:30
due: 2024-01-16
source: gmail
message_id: abc123
tags:
  - email/development
  - priority/high
---

# 🟠 PR Review Request

## Email Details

| Field | Value |
|-------|-------|
| **From** | John Doe <john@example.com> |
| **Date** | 2024-01-15 10:30 |

## Summary

> Please review the authentication changes...

## Required Actions

- [ ] Review email content
- [ ] Review code changes or respond
- [ ] Mark as complete when done
```

## Configuration

### GmailWatcherConfig

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `credentials_path` | str | "credentials.json" | OAuth credentials file |
| `token_path` | str | "token.json" | Token storage path |
| `filter_unread` | bool | True | Watch unread emails |
| `filter_important` | bool | False | Watch important emails |
| `filter_labels` | list | [] | Watch specific labels |
| `poll_interval` | float | 60.0 | Seconds between polls |
| `max_results` | int | 20 | Max emails per poll |

### ActionEmitterConfig

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `output_path` | str | "./Needs_Action" | Output directory |
| `use_priority_folders` | bool | True | Organize by priority |
| `auto_categories` | bool | True | Auto-categorize emails |

## Auto-Categorization

Emails are categorized by subject/sender patterns:

| Pattern | Category |
|---------|----------|
| invoice, payment, bill | finance |
| meeting, calendar, schedule | meetings |
| github, PR, pull request | development |
| urgent, asap | urgent |
| newsletter, digest | newsletters |

## CLI Reference

```bash
# Authenticate
python scripts/cli.py auth --credentials ./credentials.json

# Watch with defaults
python scripts/cli.py watch --credentials ./creds.json --output ./Needs_Action

# Watch important only
python scripts/cli.py watch --credentials ./creds.json --important --output ./Needs_Action

# Custom interval
python scripts/cli.py watch --credentials ./creds.json --interval 30 --output ./Needs_Action

# Watch specific labels
python scripts/cli.py watch --credentials ./creds.json --labels INBOX Projects --output ./Needs_Action
```

## Integration with Registry

```python
from base_watcher_framework.scripts.registry import get_registry
from scripts.gmail_watcher import GmailWatcher, GmailWatcherConfig
from scripts.action_emitter import emit_to_needs_action

registry = get_registry()

config = GmailWatcherConfig(
    name="gmail-inbox",
    credentials_path="./credentials.json",
    filter_unread=True,
    filter_important=True
)

registry.register(GmailWatcher(config))
registry.on_event(emit_to_needs_action("./Needs_Action").emit)

await registry.start_all()
```

## Gmail API Setup

See [references/gmail-setup.md](references/gmail-setup.md) for detailed Google Cloud Console setup instructions.
