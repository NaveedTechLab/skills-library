#!/usr/bin/env python3
"""
FileSystemWatcher - Monitor filesystem for changes.

Watches directories for file creation, modification, and deletion events.
Supports glob patterns for filtering and recursive directory monitoring.
"""

import os
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import fnmatch

from base_watcher import BaseWatcher, WatcherConfig, WatcherEvent, EventType


@dataclass
class FileState:
    """Tracks state of a file for change detection."""
    path: str
    mtime: float
    size: int
    hash: Optional[str] = None
    
    @classmethod
    def from_path(cls, path: Path, compute_hash: bool = False) -> "FileState":
        """Create FileState from a file path."""
        stat = path.stat()
        file_hash = None
        
        if compute_hash and path.is_file():
            try:
                file_hash = hashlib.md5(path.read_bytes()).hexdigest()
            except (IOError, PermissionError):
                pass
                
        return cls(
            path=str(path),
            mtime=stat.st_mtime,
            size=stat.st_size,
            hash=file_hash
        )


@dataclass
class FSWatcherConfig(WatcherConfig):
    """
    Configuration for FileSystemWatcher.
    
    Attributes:
        watch_path: Directory or file to monitor
        patterns: Glob patterns to include (e.g., ["*.md", "*.txt"])
        ignore_patterns: Glob patterns to exclude (e.g., [".git/*", "__pycache__/*"])
        recursive: Watch subdirectories recursively
        use_hash: Use content hashing for change detection (slower but more accurate)
        ignore_hidden: Skip hidden files and directories
    """
    watch_path: str = "."
    patterns: list = field(default_factory=lambda: ["*"])
    ignore_patterns: list = field(default_factory=lambda: [".git/*", "__pycache__/*", "*.pyc"])
    recursive: bool = True
    use_hash: bool = False
    ignore_hidden: bool = True


class FileSystemWatcher(BaseWatcher):
    """
    Watcher that monitors filesystem for changes.
    
    Detects file creation, modification, and deletion by comparing
    filesystem state between poll cycles.
    
    Example:
        config = FSWatcherConfig(
            name="docs-watcher",
            watch_path="/path/to/docs",
            patterns=["*.md", "*.txt"],
            poll_interval=2.0
        )
        
        watcher = FileSystemWatcher(config)
        watcher.on_event(lambda e: print(f"File {e.event_type}: {e.data['path']}"))
        
        await watcher.start()
    """
    
    def __init__(self, config: FSWatcherConfig):
        super().__init__(config)
        self.fs_config = config
        self._file_states: dict[str, FileState] = {}
        self._watch_path: Optional[Path] = None
    
    async def _setup(self) -> None:
        """Initialize file state tracking."""
        self._watch_path = Path(self.fs_config.watch_path).resolve()
        
        if not self._watch_path.exists():
            raise FileNotFoundError(f"Watch path does not exist: {self._watch_path}")
        
        # Build initial file state
        self._file_states = self._scan_files()
    
    async def _teardown(self) -> None:
        """Clean up resources."""
        self._file_states.clear()
    
    async def _poll(self) -> list[WatcherEvent]:
        """Poll filesystem for changes."""
        events = []
        current_states = self._scan_files()
        
        # Detect created and modified files
        for path, state in current_states.items():
            if path not in self._file_states:
                events.append(self._create_file_event(EventType.CREATED, path, state))
            else:
                old_state = self._file_states[path]
                if self._is_modified(old_state, state):
                    events.append(self._create_file_event(EventType.MODIFIED, path, state))
        
        # Detect deleted files
        for path in self._file_states:
            if path not in current_states:
                events.append(self._create_file_event(
                    EventType.DELETED, 
                    path, 
                    self._file_states[path]
                ))
        
        # Update state
        self._file_states = current_states
        
        return events
    
    def _scan_files(self) -> dict[str, FileState]:
        """Scan watch path and build file state dictionary."""
        states = {}
        
        if self._watch_path.is_file():
            if self._matches_patterns(self._watch_path):
                states[str(self._watch_path)] = FileState.from_path(
                    self._watch_path, 
                    self.fs_config.use_hash
                )
            return states
        
        # Directory scanning
        if self.fs_config.recursive:
            iterator = self._watch_path.rglob("*")
        else:
            iterator = self._watch_path.glob("*")
        
        for path in iterator:
            if not path.is_file():
                continue
                
            if self._should_ignore(path):
                continue
                
            if self._matches_patterns(path):
                try:
                    states[str(path)] = FileState.from_path(path, self.fs_config.use_hash)
                except (IOError, PermissionError):
                    continue
        
        return states
    
    def _matches_patterns(self, path: Path) -> bool:
        """Check if path matches any include pattern."""
        name = path.name
        return any(fnmatch.fnmatch(name, p) for p in self.fs_config.patterns)
    
    def _should_ignore(self, path: Path) -> bool:
        """Check if path should be ignored."""
        # Ignore hidden files/dirs
        if self.fs_config.ignore_hidden:
            if any(part.startswith('.') for part in path.parts):
                return True
        
        # Check ignore patterns
        rel_path = str(path.relative_to(self._watch_path))
        return any(fnmatch.fnmatch(rel_path, p) for p in self.fs_config.ignore_patterns)
    
    def _is_modified(self, old: FileState, new: FileState) -> bool:
        """Determine if file was modified."""
        if self.fs_config.use_hash:
            return old.hash != new.hash
        return old.mtime != new.mtime or old.size != new.size
    
    def _create_file_event(
        self, 
        event_type: EventType, 
        path: str, 
        state: FileState
    ) -> WatcherEvent:
        """Create a file-specific event."""
        file_path = Path(path)
        
        return self._create_event(
            event_type=event_type,
            data={
                "path": path,
                "filename": file_path.name,
                "extension": file_path.suffix,
                "size": state.size,
                "mtime": state.mtime
            },
            source=path,
            relative_path=str(file_path.relative_to(self._watch_path)) if self._watch_path else path
        )


# Convenience function
def watch_directory(
    path: str,
    patterns: list[str] = None,
    recursive: bool = True,
    poll_interval: float = 5.0
) -> FileSystemWatcher:
    """
    Create a FileSystemWatcher with common defaults.
    
    Args:
        path: Directory to watch
        patterns: File patterns to match (default: all files)
        recursive: Watch subdirectories
        poll_interval: Seconds between polls
        
    Returns:
        Configured FileSystemWatcher instance
    """
    config = FSWatcherConfig(
        name=f"fs-watcher-{Path(path).name}",
        watch_path=path,
        patterns=patterns or ["*"],
        recursive=recursive,
        poll_interval=poll_interval
    )
    return FileSystemWatcher(config)
