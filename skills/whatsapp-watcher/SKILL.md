---
name: whatsapp-watcher
description: Monitor WhatsApp Web for keyword-triggered messages using Playwright browser automation. Creates structured Markdown action files with priority levels. Extends BaseWatcher framework. Use when building WhatsApp monitoring, message-to-task conversion, keyword alerts, or personal assistant systems that need WhatsApp integration.
---

# WhatsApp Watcher

Monitor WhatsApp Web for messages containing specific keywords/patterns and automatically create actionable Markdown files.

## Prerequisites

1. **Playwright**: `pip install playwright && playwright install chromium`
2. **WhatsApp account** linked to WhatsApp Web
3. **BaseWatcher framework** (in sibling directory)

## Quick Start

### 1. Start Watcher (First Time)

```bash
python scripts/cli.py watch --output ./Needs_Action
```

A browser window opens - scan QR code with your phone.

### 2. Subsequent Runs (Session Saved)

```bash
python scripts/cli.py watch --output ./Needs_Action --headless
```

### 3. Python Usage

```python
import asyncio
from scripts.whatsapp_watcher import watch_whatsapp
from scripts.whatsapp_emitter import emit_whatsapp_actions

async def main():
    watcher = watch_whatsapp(
        triggers=[
            {"pattern": "urgent", "priority": "urgent"},
            {"pattern": "@task", "priority": "high"},
            {"pattern": r"deadline.*\d", "is_regex": True, "priority": "high"},
        ],
        poll_interval=5.0
    )
    emitter = emit_whatsapp_actions("./Needs_Action")
    
    watcher.on_event(emitter.emit)
    watcher.on_qr_code(lambda msg: print(msg))
    
    await watcher.start()
    await asyncio.sleep(3600)
    await watcher.stop()

asyncio.run(main())
```

## Trigger Configuration

### Simple Keywords

```yaml
triggers:
  - pattern: "urgent"
    priority: urgent
  - pattern: "@task"
    priority: high
```

### Regex Patterns

```yaml
triggers:
  - pattern: "deadline.*\\d{1,2}/\\d{1,2}"
    is_regex: true
    priority: high
  - pattern: "meeting.*(today|tomorrow)"
    is_regex: true
    priority: high
```

### Priority Levels

| Priority | Emoji | Due Time | Use Case |
|----------|-------|----------|----------|
| `urgent` | 🔴 | 1 hour | Immediate action needed |
| `high` | 🟠 | 4 hours | Important, same day |
| `normal` | 🟡 | 24 hours | Regular follow-up |
| `low` | 🟢 | 72 hours | FYI, when convenient |

## Output Structure

```
Needs_Action/
├── 01_Urgent/
│   └── 2024-01-15_1030_John_urgent.md
├── 02_High/
│   ├── tasks/
│   │   └── 2024-01-15_0900_Team_task.md
│   └── meetings/
│       └── 2024-01-15_1100_Boss_meeting.md
├── 03_Normal/
└── 04_Low/
```

## Action File Format

```markdown
---
type: whatsapp-action
status: pending
priority: high
category: tasks
created: 2024-01-15 10:30
due: 2024-01-15 14:30
source: whatsapp
chat: Project Team
sender: John
triggers: ["@task"]
tags:
  - whatsapp/tasks
  - priority/high
---

# 🟠 WhatsApp: Project Team

## Message Details

| Field | Value |
|-------|-------|
| **From** | John |
| **Chat** | Project Team (group) |
| **Time** | 2024-01-15T10:30:00 |

## Message

> @task Please review the design docs by EOD

## Required Actions

- [ ] Review message
- [ ] Complete the requested task
- [ ] Respond if needed
- [ ] Mark as complete
```

## CLI Reference

```bash
# Watch with default triggers
python scripts/cli.py watch --output ./Needs_Action

# Watch with custom triggers file
python scripts/cli.py watch --triggers triggers.yaml --output ./Needs_Action

# Add inline trigger
python scripts/cli.py watch --output ./Needs_Action --add-trigger "important:high"

# Headless mode (after QR scan)
python scripts/cli.py watch --headless --output ./Needs_Action

# With screenshots
python scripts/cli.py watch --screenshot --output ./Needs_Action

# Create sample triggers file
python scripts/cli.py init-triggers --output triggers.yaml
```

## Configuration

### WhatsAppWatcherConfig

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `session_path` | str | "./whatsapp_session" | Browser session storage |
| `headless` | bool | False | Run headless (needs prior QR) |
| `triggers` | list | [] | List of TriggerRule objects |
| `poll_interval` | float | 5.0 | Seconds between message scans |
| `screenshot_on_trigger` | bool | False | Capture screenshots |

### TriggerRule

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `pattern` | str | required | Keyword or regex pattern |
| `is_regex` | bool | False | Treat pattern as regex |
| `priority` | str | "normal" | urgent/high/normal/low |
| `case_sensitive` | bool | False | Case-sensitive matching |
| `name` | str | "" | Display name for trigger |

## Session Management

Session data is stored in `session_path` directory:
- First run: QR code scan required
- Subsequent runs: Auto-login (until session expires)
- Session expires: Re-scan QR code

To reset session:
```bash
rm -rf ./whatsapp_session
```

## Integration with Registry

```python
from base_watcher_framework.scripts.registry import get_registry
from scripts.whatsapp_watcher import WhatsAppWatcher, WhatsAppWatcherConfig, TriggerRule
from scripts.whatsapp_emitter import emit_whatsapp_actions

registry = get_registry()

config = WhatsAppWatcherConfig(
    name="whatsapp-monitor",
    triggers=[
        TriggerRule("urgent", priority="urgent"),
        TriggerRule("@task", priority="high"),
    ]
)

registry.register(WhatsAppWatcher(config))
registry.on_event(emit_whatsapp_actions("./Needs_Action").emit)

await registry.start_all()
```

## Selector Updates

WhatsApp Web UI changes periodically. See [references/selectors.md](references/selectors.md) for current selectors and update instructions.
