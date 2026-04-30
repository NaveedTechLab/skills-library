"""
Filesystem Watcher - Monitor directories for dropped files.

Components:
- DropWatcher: BaseWatcher extension for filesystem monitoring
- MetadataEmitter: Create Markdown files with extracted metadata
- File Handlers: Type-specific metadata extraction
"""

from .drop_watcher import (
    DropWatcher,
    DropWatcherConfig,
    FileMetadata,
    watch_drops
)

from .metadata_emitter import (
    MetadataEmitter,
    MetadataEmitterConfig,
    emit_file_metadata
)

from .file_handlers import (
    extract_image_metadata,
    extract_pdf_metadata,
    extract_document_metadata,
    extract_audio_metadata,
    extract_video_metadata,
    extract_archive_metadata,
    extract_code_metadata,
    extract_data_metadata
)

__all__ = [
    "DropWatcher",
    "DropWatcherConfig",
    "FileMetadata",
    "watch_drops",
    "MetadataEmitter",
    "MetadataEmitterConfig",
    "emit_file_metadata",
    "extract_image_metadata",
    "extract_pdf_metadata",
    "extract_document_metadata",
    "extract_audio_metadata",
    "extract_video_metadata",
    "extract_archive_metadata",
    "extract_code_metadata",
    "extract_data_metadata"
]

__version__ = "1.0.0"
