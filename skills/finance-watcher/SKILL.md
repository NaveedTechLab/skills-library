---
name: finance-watcher
description: Monitor banking transactions from CSV files and banking APIs, logging to Obsidian vault. Detects subscription patterns, flags unusual transactions, and generates financial summaries. Extends BaseWatcher framework. Use when building financial monitoring, expense tracking, subscription auditing, or automated bookkeeping systems.
---

# Finance Watcher

Monitor banking transactions and automatically detect subscriptions, flag large transactions, and generate financial summaries in your Obsidian vault.

## Prerequisites

1. **Python packages**: `pip install pandas watchdog`
2. **BaseWatcher framework** (in sibling directory)
3. **Bank CSV exports** or banking API credentials

## Quick Start

### 1. Import CSV

```bash
python scripts/cli.py import-csv --file ./bank_export.csv --output ./vault/Accounting
```

### 2. Start Watching

```bash
python scripts/cli.py watch --csv-dir ./bank_imports --output ./vault/Accounting
```

### 3. Audit Subscriptions

```bash
python scripts/cli.py audit-subscriptions --accounting-dir ./vault/Accounting
```

### 4. Python Usage

```python
import asyncio
from scripts.finance_watcher import watch_finances
from scripts.transaction_emitter import TransactionEmitter

async def main():
    watcher = watch_finances(csv_watch_dir="./bank_imports")
    emitter = TransactionEmitter("./vault")
    watcher.on_event(emitter.emit)
    await watcher.start()
    await asyncio.sleep(3600)
    await watcher.stop()

asyncio.run(main())
```

## Output Structure

```
vault/
├── Accounting/
│   ├── Current_Month.md       # Running transaction log
│   ├── Subscriptions.md       # Detected subscriptions
│   └── imports/               # CSV drop folder
├── Needs_Action/
│   └── FINANCE_large_tx_*.md  # Flagged transactions
└── Briefings/
    └── Financial_Summary.md   # Weekly financial summary
```

## Configuration

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `csv_watch_dir` | str | "./imports" | CSV drop folder |
| `alert_threshold` | float | 500.0 | Flag transactions above this |
| `poll_interval` | float | 300.0 | Seconds between polls |
| `subscription_patterns` | dict | (built-in) | Pattern-to-name mapping |
| `transaction_categories` | dict | (built-in) | Description-to-category mapping |

## Subscription Detection

Built-in patterns detect common subscriptions:

| Pattern | Service |
|---------|---------|
| netflix.com | Netflix |
| spotify.com | Spotify |
| adobe.com | Adobe Creative Cloud |
| notion.so | Notion |
| slack.com | Slack |
| github.com | GitHub |
| aws.amazon | AWS |

## CLI Reference

```bash
# Watch for new CSVs
python scripts/cli.py watch --csv-dir ./imports --output ./vault/Accounting

# Import a specific CSV
python scripts/cli.py import-csv --file export.csv --output ./vault/Accounting

# Analyze transactions
python scripts/cli.py analyze --accounting-dir ./vault/Accounting --days 30

# Audit subscriptions
python scripts/cli.py audit-subscriptions --accounting-dir ./vault/Accounting
```
