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

---

## When NOT to Use This

- **Official WhatsApp Business API use cases** — If you're building a product for customers, use the official Meta Cloud API; this tool is for personal/internal automation only
- **Sending automated replies at scale** — This skill is read-only monitoring + file creation; it doesn't send messages and is not designed for bulk outreach (violates WhatsApp ToS)
- **High-volume message processing (1000+/day)** — Playwright-based scraping has limits; use the official Business API for production-scale workloads
- **Multi-account monitoring** — Each instance manages one WhatsApp account; parallel instances on the same machine can conflict
- **Environments without a display (pure headless servers)** — First QR scan requires a visible browser; set up session locally, then transfer to server

---

## Common Mistakes

1. **Running multiple instances simultaneously** — Two watchers on the same WhatsApp account will log each other out; run one instance per account
2. **Not handling QR re-scan** — Sessions expire after ~14 days; build a re-scan notification into your monitoring or the watcher silently stops working
3. **Using `headless: True` before QR scan** — First login must be headed (visible browser); only switch to headless after session file is created
4. **Too-short `poll_interval`** — Polling every 0.5s will trigger WhatsApp's bot detection; keep at 5s minimum
5. **Not deduplicating messages** — If your watcher restarts, it may re-process old messages; track processed message IDs in a local file
6. **Broad trigger patterns** — `pattern: "hi"` will match everything; use specific patterns like `@task` or `urgent:` to avoid false positives

---

## Performance Tips

- **Save session to persistent storage** — Mount `whatsapp_session/` to a Docker volume or cloud storage so QR scans survive restarts
- **Filter by chat name** — Add `chat_filter: ["Boss", "Project Team"]` to only watch specific chats and reduce noise
- **Use regex for smart triggers** — `r"(deadline|due|by).*\d{1,2}[\/\-]\d{1,2}"` captures date-based urgency more accurately than simple keywords
- **Combine with `orchestrator-engine`** — Route different trigger categories to different downstream agents (urgent → Slack alert, @task → Jira ticket)
- **Run as a systemd service** — Use `systemd` or `pm2` to auto-restart the watcher on crash; add `--headless` flag after first QR scan

---

## Real Production Example

**Business Inquiry Auto-Triage System** (built for an AI Marketing Agency):

```python
triggers = [
    # Client urgency signals
    {"pattern": r"urgent|ASAP|immediately", "priority": "urgent"},
    {"pattern": r"@task|@todo|@action",      "priority": "high"},
    {"pattern": r"meeting.*(today|tomorrow)", "priority": "high"},
    # Lead qualification
    {"pattern": r"price|cost|quote|budget",  "priority": "normal"},
    {"pattern": r"interested|want to|can you", "priority": "low"},
]
```

Result:
- 47 business inquiries/day auto-categorized
- Sales team responded to `urgent` within 30 min (vs 4 hrs before)
- Zero missed leads — all messages saved to `Needs_Action/` for review
- Integrated with `gmail-watcher` to cross-reference email + WhatsApp from same client

---

## Related Skills

- [`gmail-watcher`](../gmail-watcher/SKILL.md) — Watch Gmail alongside WhatsApp for unified inbox automation
- [`base-watcher-framework`](../base-watcher-framework/SKILL.md) — The foundation this skill extends; learn it first
- [`orchestrator-engine`](../orchestrator-engine/SKILL.md) — Route triggered actions to different downstream agents
- [`a2a-messaging`](../a2a-messaging/SKILL.md) — Connect watcher output to multi-agent pipelines
- [`audit-logging-system`](../audit-logging-system/SKILL.md) — Log all triggered actions for compliance and review
