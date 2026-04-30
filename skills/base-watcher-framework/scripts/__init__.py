"""
BaseWatcher Framework - Continuous monitoring and event emission to Obsidian.

Core components:
- BaseWatcher: Abstract base class for all watchers
- FileSystemWatcher: Monitor filesystem for changes
- APIWatcher: Monitor REST APIs for changes
- WatcherRegistry: Central management for multiple watchers
- ObsidianEmitter: Emit events as Markdown to Obsidian vault
"""

from .base_watcher import (
    BaseWatcher,
    WatcherConfig,
    WatcherEvent,
    WatcherState,
    EventType
)

from .fs_watcher import (
    FileSystemWatcher,
    FSWatcherConfig,
    watch_directory
)

from .registry import (
    WatcherRegistry,
    RegistryStats,
    get_registry
)

from .obsidian_emitter import (
    ObsidianEmitter,
    EmitterConfig,
    emit_to_vault
)

__all__ = [
    # Base
    "BaseWatcher",
    "WatcherConfig", 
    "WatcherEvent",
    "WatcherState",
    "EventType",
    # FileSystem
    "FileSystemWatcher",
    "FSWatcherConfig",
    "watch_directory",
    # Registry
    "WatcherRegistry",
    "RegistryStats",
    "get_registry",
    # Emitter
    "ObsidianEmitter",
    "EmitterConfig",
    "emit_to_vault",
]

__version__ = "1.0.0"
