---
name: base-watcher-framework
description: Implement reusable Python BaseWatcher abstractions for continuous monitoring and event emission into Obsidian vault folders. Use when building file system watchers, API monitors, or any continuous monitoring solution that outputs Markdown events to Obsidian. Triggers for tasks involving: (1) monitoring directories for file changes, (2) polling REST APIs for updates, (3) emitting structured events to Obsidian notes, (4) creating custom watchers extending BaseWatcher.
---

# Base Watcher Framework

A Python framework for continuous monitoring of various sources (file system, APIs, custom) with automatic event emission to Obsidian vault folders as Markdown files.

## Quick Start

### Watch a Directory

```python
import asyncio
from scripts.fs_watcher import watch_directory
from scripts.obsidian_emitter import emit_to_vault

async def main():
    # Create watcher and emitter
    watcher = watch_directory("./docs", patterns=["*.md"])
    emitter = emit_to_vault("/path/to/obsidian/vault")
    
    # Connect and start
    watcher.on_event(emitter.emit)
    await watcher.start()
    
    # Run until stopped
    await asyncio.sleep(3600)
    await watcher.stop()

asyncio.run(main())
```

### CLI Usage

```bash
# Watch directory, emit to vault
python scripts/cli.py watch ./docs --vault /path/to/vault --patterns "*.md"

# Run from config file
python scripts/cli.py run --config watchers.yaml --vault /path/to/vault

# Create sample config
python scripts/cli.py init --output watchers.yaml
```

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌──────────────────┐
│  BaseWatcher    │────▶│ WatcherRegistry │────▶│ ObsidianEmitter  │
│  (abstract)     │     │   (manages)     │     │   (outputs)      │
└────────┬────────┘     └─────────────────┘     └──────────────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌────────┐
│  FS    │ │  API   │
│Watcher │ │Watcher │
└────────┘ └────────┘
```

## Core Components

### BaseWatcher

Abstract base class - extend to create custom watchers.

```python
from scripts.base_watcher import BaseWatcher, WatcherConfig, EventType

class MyWatcher(BaseWatcher):
    async def _setup(self):
        # Initialize resources (connections, state)
        pass
    
    async def _teardown(self):
        # Clean up resources
        pass
    
    async def _poll(self) -> list[WatcherEvent]:
        # Check for changes, return events
        data = await self.fetch_data()
        return [self._create_event(EventType.MODIFIED, data)]
```

### FileSystemWatcher

Monitor directories for file changes.

```python
from scripts.fs_watcher import FileSystemWatcher, FSWatcherConfig

config = FSWatcherConfig(
    name="my-watcher",
    watch_path="./src",
    patterns=["*.py", "*.js"],
    ignore_patterns=[".git/*", "__pycache__/*"],
    recursive=True,
    poll_interval=5.0
)
watcher = FileSystemWatcher(config)
```

### APIWatcher

Monitor REST APIs for changes.

```python
from scripts.api_watcher import APIWatcher, APIWatcherConfig, AuthType, ChangeStrategy

config = APIWatcherConfig(
    name="github-releases",
    url="https://api.github.com/repos/owner/repo/releases/latest",
    auth_type=AuthType.BEARER,
    auth_credentials="ghp_token",
    change_strategy=ChangeStrategy.FIELD_COMPARE,
    compare_fields=["tag_name", "published_at"],
    poll_interval=300
)
watcher = APIWatcher(config)
```

### WatcherRegistry

Manage multiple watchers centrally.

```python
from scripts.registry import WatcherRegistry

registry = WatcherRegistry()
registry.register(fs_watcher)
registry.register(api_watcher)

# Central event handling
registry.on_event(lambda e: print(f"Event: {e.event_type}"))

await registry.start_all()
# ... later
await registry.stop_all()
```

### ObsidianEmitter

Emit events as Markdown to Obsidian vault.

```python
from scripts.obsidian_emitter import ObsidianEmitter, EmitterConfig

config = EmitterConfig(
    vault_path="/path/to/obsidian",
    default_folder="automation/events",
    use_daily_folders=True,
    folder_mapping={
        "created": "automation/new-files",
        "api-watcher": "automation/api-updates"
    }
)
emitter = ObsidianEmitter(config)
registry.on_event(emitter.emit)
```

## Event Types

| Type | Description |
|------|-------------|
| `CREATED` | New item detected |
| `MODIFIED` | Existing item changed |
| `DELETED` | Item removed |
| `ERROR` | Error occurred |
| `INFO` | Informational |
| `WARNING` | Warning condition |
| `CUSTOM` | Custom event type |

## Configuration File Format

```yaml
watchers:
  - type: filesystem
    name: docs-watcher
    config:
      watch_path: ./docs
      patterns: ["*.md"]
      poll_interval: 5.0
      
  - type: api
    name: github-watcher
    config:
      url: https://api.github.com/repos/...
      poll_interval: 300
      auth_type: bearer
      auth_credentials: ${GITHUB_TOKEN}
```

## Creating Custom Watchers

See [references/extending.md](references/extending.md) for detailed guide on:
- Extending BaseWatcher
- Custom event types
- Integrating with ObsidianEmitter
- Testing watchers

## Scripts Reference

| Script | Purpose |
|--------|---------|
| `base_watcher.py` | Abstract base class and core types |
| `fs_watcher.py` | File system monitoring |
| `api_watcher.py` | REST API monitoring |
| `registry.py` | Multi-watcher management |
| `obsidian_emitter.py` | Markdown output to Obsidian |
| `cli.py` | Command-line interface |

## Dependencies

**Required:**
- Python 3.10+

**Optional:**
- `aiohttp` - For APIWatcher
- `pyyaml` - For YAML config files
