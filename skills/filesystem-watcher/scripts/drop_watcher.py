#!/usr/bin/env python3
"""
DropWatcher - Monitor filesystem for dropped files.

Extends BaseWatcher to detect new files in watch directories and
extract metadata for creating action files in Obsidian vault.
"""

import hashlib
import mimetypes
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Callable
import sys

# Add base-watcher-framework to path
BASE_WATCHER_PATH = Path(__file__).parent.parent.parent / "base-watcher-framework" / "scripts"
if BASE_WATCHER_PATH.exists():
    sys.path.insert(0, str(BASE_WATCHER_PATH))

from base_watcher import BaseWatcher, WatcherConfig, WatcherEvent, EventType


# File type categories
FILE_CATEGORIES = {
    "image": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".ico", ".tiff", ".heic"],
    "document": [".pdf", ".doc", ".docx", ".txt", ".md", ".rtf", ".odt", ".pages"],
    "spreadsheet": [".xlsx", ".xls", ".csv", ".ods", ".numbers"],
    "presentation": [".pptx", ".ppt", ".odp", ".key"],
    "audio": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma"],
    "video": [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm"],
    "archive": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"],
    "code": [".py", ".js", ".ts", ".java", ".cpp", ".c", ".h", ".css", ".html", ".json", ".yaml", ".xml"],
    "data": [".json", ".xml", ".yaml", ".yml", ".toml", ".ini", ".cfg"],
}


@dataclass
class FileMetadata:
    """Extracted file metadata."""
    path: str
    filename: str
    extension: str
    category: str
    mime_type: str
    size_bytes: int
    size_human: str
    created: datetime
    modified: datetime
    checksum: str
    
    # Extended metadata (populated by handlers)
    content_preview: str = ""
    dimensions: Optional[tuple] = None  # For images/video
    duration: Optional[float] = None    # For audio/video
    page_count: Optional[int] = None    # For documents
    exif_data: dict = field(default_factory=dict)
    custom_metadata: dict = field(default_factory=dict)


@dataclass
class DropWatcherConfig(WatcherConfig):
    """
    Configuration for DropWatcher.
    
    Attributes:
        watch_paths: List of directories to monitor
        patterns: File patterns to include (e.g., ["*"] for all)
        ignore_patterns: Patterns to exclude
        recursive: Watch subdirectories
        extract_content: Extract text content from documents
        extract_exif: Extract EXIF from images
        compute_checksum: Compute file checksums
        min_file_size: Minimum file size to process (bytes)
        max_file_size: Maximum file size to process (bytes)
        stable_time: Seconds to wait for file to stabilize
        move_processed: Move processed files to subfolder
        processed_folder: Name of processed folder
    """
    watch_paths: list = field(default_factory=lambda: ["."])
    patterns: list = field(default_factory=lambda: ["*"])
    ignore_patterns: list = field(default_factory=lambda: [
        ".*", "*.tmp", "*.part", "*.crdownload", "~*", "Thumbs.db", ".DS_Store"
    ])
    recursive: bool = False
    extract_content: bool = True
    extract_exif: bool = True
    compute_checksum: bool = True
    min_file_size: int = 0
    max_file_size: int = 500 * 1024 * 1024  # 500MB
    stable_time: float = 2.0
    move_processed: bool = False
    processed_folder: str = "_processed"


class DropWatcher(BaseWatcher):
    """
    Watcher that monitors directories for new/dropped files.
    
    Detects new files, extracts metadata, and emits events for
    action file creation.
    
    Example:
        config = DropWatcherConfig(
            name="downloads-watcher",
            watch_paths=["~/Downloads"],
            patterns=["*.pdf", "*.docx", "*.xlsx"],
            poll_interval=5.0
        )
        
        watcher = DropWatcher(config)
        watcher.on_event(lambda e: print(f"New file: {e.data['filename']}"))
        
        await watcher.start()
    """
    
    def __init__(self, config: DropWatcherConfig):
        super().__init__(config)
        self.drop_config = config
        self._known_files: dict[str, float] = {}  # path -> mtime
        self._pending_files: dict[str, float] = {}  # path -> first_seen_time
        self._metadata_handlers: dict[str, Callable] = {}
        
        # Register default handlers
        self._register_default_handlers()
    
    def register_handler(
        self, 
        category: str, 
        handler: Callable[[Path], dict]
    ) -> "DropWatcher":
        """
        Register custom metadata handler for file category.
        
        Args:
            category: File category (image, document, etc.)
            handler: Function(path) -> metadata_dict
            
        Returns:
            Self for chaining
        """
        self._metadata_handlers[category] = handler
        return self
    
    async def _setup(self) -> None:
        """Initialize file state tracking."""
        # Resolve watch paths
        self._watch_paths = []
        for p in self.drop_config.watch_paths:
            path = Path(p).expanduser().resolve()
            if path.exists() and path.is_dir():
                self._watch_paths.append(path)
        
        if not self._watch_paths:
            raise ValueError("No valid watch paths configured")
        
        # Build initial known files set
        self._known_files = self._scan_existing_files()
    
    async def _teardown(self) -> None:
        """Clean up resources."""
        self._known_files.clear()
        self._pending_files.clear()
    
    async def _poll(self) -> list[WatcherEvent]:
        """Poll for new files."""
        import asyncio
        events = []
        current_time = datetime.now().timestamp()
        
        # Scan current files
        current_files = self._scan_existing_files()
        
        # Find new files
        for filepath, mtime in current_files.items():
            if filepath not in self._known_files:
                # New file detected
                if filepath not in self._pending_files:
                    self._pending_files[filepath] = current_time
                else:
                    # Check if file is stable
                    time_seen = self._pending_files[filepath]
                    if current_time - time_seen >= self.drop_config.stable_time:
                        # File is stable, process it
                        try:
                            event = await self._process_new_file(Path(filepath))
                            if event:
                                events.append(event)
                                self._known_files[filepath] = mtime
                                del self._pending_files[filepath]
                        except Exception as e:
                            events.append(self._create_event(
                                EventType.ERROR,
                                data={"error": str(e), "path": filepath},
                                source=filepath
                            ))
                            del self._pending_files[filepath]
        
        # Update known files with current state
        self._known_files = current_files
        
        # Clean up pending files that no longer exist
        self._pending_files = {
            k: v for k, v in self._pending_files.items() 
            if k in current_files
        }
        
        return events
    
    def _scan_existing_files(self) -> dict[str, float]:
        """Scan watch paths and return file -> mtime mapping."""
        import fnmatch
        files = {}
        
        for watch_path in self._watch_paths:
            if self.drop_config.recursive:
                iterator = watch_path.rglob("*")
            else:
                iterator = watch_path.glob("*")
            
            for path in iterator:
                if not path.is_file():
                    continue
                
                # Check ignore patterns
                if self._should_ignore(path):
                    continue
                
                # Check include patterns
                if not self._matches_patterns(path):
                    continue
                
                # Check file size
                try:
                    size = path.stat().st_size
                    if size < self.drop_config.min_file_size:
                        continue
                    if size > self.drop_config.max_file_size:
                        continue
                    
                    files[str(path)] = path.stat().st_mtime
                except (OSError, PermissionError):
                    continue
        
        return files
    
    def _should_ignore(self, path: Path) -> bool:
        """Check if file should be ignored."""
        import fnmatch
        name = path.name
        
        for pattern in self.drop_config.ignore_patterns:
            if fnmatch.fnmatch(name, pattern):
                return True
        
        return False
    
    def _matches_patterns(self, path: Path) -> bool:
        """Check if file matches include patterns."""
        import fnmatch
        
        if "*" in self.drop_config.patterns:
            return True
        
        name = path.name
        return any(fnmatch.fnmatch(name, p) for p in self.drop_config.patterns)
    
    async def _process_new_file(self, path: Path) -> Optional[WatcherEvent]:
        """Process a new file and create event."""
        # Extract basic metadata
        metadata = self._extract_basic_metadata(path)
        
        if not metadata:
            return None
        
        # Extract extended metadata based on category
        if metadata.category in self._metadata_handlers:
            try:
                handler = self._metadata_handlers[metadata.category]
                extended = handler(path)
                metadata.custom_metadata.update(extended)
                
                # Copy specific fields
                if "content_preview" in extended:
                    metadata.content_preview = extended["content_preview"]
                if "dimensions" in extended:
                    metadata.dimensions = extended["dimensions"]
                if "duration" in extended:
                    metadata.duration = extended["duration"]
                if "page_count" in extended:
                    metadata.page_count = extended["page_count"]
                if "exif_data" in extended:
                    metadata.exif_data = extended["exif_data"]
            except Exception as e:
                metadata.custom_metadata["extraction_error"] = str(e)
        
        # Move file if configured
        final_path = path
        if self.drop_config.move_processed:
            final_path = self._move_to_processed(path)
            metadata.path = str(final_path)
        
        return self._create_file_event(metadata)
    
    def _extract_basic_metadata(self, path: Path) -> Optional[FileMetadata]:
        """Extract basic file metadata."""
        try:
            stat = path.stat()
            
            # Determine category
            ext = path.suffix.lower()
            category = "other"
            for cat, extensions in FILE_CATEGORIES.items():
                if ext in extensions:
                    category = cat
                    break
            
            # Get MIME type
            mime_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
            
            # Compute checksum if configured
            checksum = ""
            if self.drop_config.compute_checksum:
                checksum = self._compute_checksum(path)
            
            return FileMetadata(
                path=str(path),
                filename=path.name,
                extension=ext,
                category=category,
                mime_type=mime_type,
                size_bytes=stat.st_size,
                size_human=self._format_size(stat.st_size),
                created=datetime.fromtimestamp(stat.st_ctime),
                modified=datetime.fromtimestamp(stat.st_mtime),
                checksum=checksum
            )
        except Exception:
            return None
    
    def _compute_checksum(self, path: Path, algorithm: str = "md5") -> str:
        """Compute file checksum."""
        hash_func = hashlib.new(algorithm)
        
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hash_func.update(chunk)
        
        return hash_func.hexdigest()
    
    def _move_to_processed(self, path: Path) -> Path:
        """Move file to processed folder."""
        processed_dir = path.parent / self.drop_config.processed_folder
        processed_dir.mkdir(exist_ok=True)
        
        new_path = processed_dir / path.name
        
        # Handle name conflicts
        counter = 1
        while new_path.exists():
            stem = path.stem
            new_path = processed_dir / f"{stem}_{counter}{path.suffix}"
            counter += 1
        
        path.rename(new_path)
        return new_path
    
    def _create_file_event(self, metadata: FileMetadata) -> WatcherEvent:
        """Create event from file metadata."""
        return self._create_event(
            EventType.CREATED,
            data={
                "path": metadata.path,
                "filename": metadata.filename,
                "extension": metadata.extension,
                "category": metadata.category,
                "mime_type": metadata.mime_type,
                "size_bytes": metadata.size_bytes,
                "size_human": metadata.size_human,
                "created": metadata.created.isoformat(),
                "modified": metadata.modified.isoformat(),
                "checksum": metadata.checksum,
                "content_preview": metadata.content_preview,
                "dimensions": metadata.dimensions,
                "duration": metadata.duration,
                "page_count": metadata.page_count,
                "exif_data": metadata.exif_data,
                "custom_metadata": metadata.custom_metadata
            },
            source=metadata.path,
            file_type="filesystem",
            category=metadata.category
        )
    
    def _register_default_handlers(self) -> None:
        """Register default metadata extraction handlers."""
        from file_handlers import (
            extract_image_metadata,
            extract_pdf_metadata,
            extract_document_metadata,
            extract_audio_metadata,
            extract_video_metadata,
            extract_archive_metadata
        )
        
        self._metadata_handlers["image"] = extract_image_metadata
        self._metadata_handlers["document"] = extract_document_metadata
        self._metadata_handlers["audio"] = extract_audio_metadata
        self._metadata_handlers["video"] = extract_video_metadata
        self._metadata_handlers["archive"] = extract_archive_metadata
    
    @staticmethod
    def _format_size(size: int) -> str:
        """Format file size in human-readable form."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


# Convenience function
def watch_drops(
    paths: list[str],
    patterns: list[str] = None,
    poll_interval: float = 5.0
) -> DropWatcher:
    """
    Create a DropWatcher with common defaults.
    
    Args:
        paths: Directories to watch
        patterns: File patterns to include
        poll_interval: Seconds between polls
        
    Returns:
        Configured DropWatcher
    """
    config = DropWatcherConfig(
        name="drop-watcher",
        watch_paths=paths,
        patterns=patterns or ["*"],
        poll_interval=poll_interval
    )
    return DropWatcher(config)
