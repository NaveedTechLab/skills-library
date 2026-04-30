#!/usr/bin/env python3
"""
Filesystem Watcher CLI - Monitor directories and create metadata files.

Usage:
    python cli.py watch ~/Downloads --vault /path/to/vault
    python cli.py watch ./inbox --vault ./vault --patterns "*.pdf" "*.docx"
"""

import argparse
import asyncio
import logging
import signal
import sys
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent))
BASE_WATCHER_PATH = Path(__file__).parent.parent.parent / "base-watcher-framework" / "scripts"
if BASE_WATCHER_PATH.exists():
    sys.path.insert(0, str(BASE_WATCHER_PATH))

from drop_watcher import DropWatcher, DropWatcherConfig
from metadata_emitter import MetadataEmitter, MetadataEmitterConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        description="Filesystem Watcher - Monitor directories for dropped files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Watch Downloads folder
  python cli.py watch ~/Downloads --vault /path/to/obsidian/vault
  
  # Watch multiple directories
  python cli.py watch ~/Downloads ~/Desktop/Inbox --vault ./vault
  
  # Watch for specific file types
  python cli.py watch ./inbox --vault ./vault --patterns "*.pdf" "*.docx" "*.xlsx"
  
  # Watch recursively
  python cli.py watch ./projects --vault ./vault --recursive
  
  # Move processed files
  python cli.py watch ./inbox --vault ./vault --move-processed
"""
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Watch command
    watch_parser = subparsers.add_parser("watch", help="Watch directories for files")
    watch_parser.add_argument(
        "paths",
        nargs="+",
        help="Directories to watch"
    )
    watch_parser.add_argument(
        "--vault",
        required=True,
        help="Path to Obsidian vault"
    )
    watch_parser.add_argument(
        "--folder",
        default="FileDrops",
        help="Folder within vault for file notes (default: FileDrops)"
    )
    watch_parser.add_argument(
        "--patterns",
        nargs="+",
        default=["*"],
        help="File patterns to include (default: all files)"
    )
    watch_parser.add_argument(
        "--ignore",
        nargs="+",
        default=[".*", "*.tmp", "*.part", "Thumbs.db"],
        help="Patterns to ignore"
    )
    watch_parser.add_argument(
        "--recursive",
        action="store_true",
        help="Watch subdirectories recursively"
    )
    watch_parser.add_argument(
        "--interval",
        type=float,
        default=5.0,
        help="Poll interval in seconds (default: 5)"
    )
    watch_parser.add_argument(
        "--no-category-folders",
        action="store_true",
        help="Don't organize by file category"
    )
    watch_parser.add_argument(
        "--date-folders",
        action="store_true",
        help="Organize by date folders"
    )
    watch_parser.add_argument(
        "--move-processed",
        action="store_true",
        help="Move processed files to _processed folder"
    )
    watch_parser.add_argument(
        "--no-content",
        action="store_true",
        help="Don't extract content preview"
    )
    watch_parser.add_argument(
        "--no-checksum",
        action="store_true",
        help="Don't compute file checksums"
    )
    watch_parser.add_argument(
        "--min-size",
        type=int,
        default=0,
        help="Minimum file size in bytes"
    )
    watch_parser.add_argument(
        "--max-size",
        type=int,
        default=500*1024*1024,
        help="Maximum file size in bytes (default: 500MB)"
    )
    
    # Scan command (one-time scan)
    scan_parser = subparsers.add_parser("scan", help="One-time scan of directories")
    scan_parser.add_argument(
        "paths",
        nargs="+",
        help="Directories to scan"
    )
    scan_parser.add_argument(
        "--vault",
        required=True,
        help="Path to Obsidian vault"
    )
    scan_parser.add_argument(
        "--folder",
        default="FileDrops",
        help="Folder within vault for file notes"
    )
    scan_parser.add_argument(
        "--patterns",
        nargs="+",
        default=["*"],
        help="File patterns to include"
    )
    scan_parser.add_argument(
        "--recursive",
        action="store_true",
        help="Scan subdirectories recursively"
    )
    
    return parser


async def run_watch(args: argparse.Namespace) -> None:
    """Run filesystem watcher."""
    # Resolve paths
    watch_paths = [str(Path(p).expanduser().resolve()) for p in args.paths]
    
    # Create watcher config
    watcher_config = DropWatcherConfig(
        name="drop-watcher",
        watch_paths=watch_paths,
        patterns=args.patterns,
        ignore_patterns=args.ignore,
        recursive=args.recursive,
        poll_interval=args.interval,
        extract_content=not args.no_content,
        compute_checksum=not args.no_checksum,
        move_processed=args.move_processed,
        min_file_size=args.min_size,
        max_file_size=args.max_size
    )
    
    # Create emitter config
    emitter_config = MetadataEmitterConfig(
        vault_path=args.vault,
        output_folder=args.folder,
        use_category_folders=not args.no_category_folders,
        use_date_folders=args.date_folders
    )
    
    # Create instances
    watcher = DropWatcher(watcher_config)
    emitter = MetadataEmitter(emitter_config)
    
    # Wire up event handling
    def handle_event(event):
        filepath = emitter.emit(event)
        if filepath:
            logger.info(f"Created: {filepath.name} for {event.data.get('filename', 'unknown')}")
    
    watcher.on_event(handle_event)
    watcher.on_error(lambda e: logger.error(f"Watcher error: {e}"))
    
    # Set up signal handling
    stop_event = asyncio.Event()
    
    def signal_handler():
        logger.info("Received shutdown signal")
        stop_event.set()
    
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, signal_handler)
        except NotImplementedError:
            signal.signal(sig, lambda s, f: signal_handler())
    
    # Start watching
    logger.info("Starting filesystem watcher...")
    logger.info(f"Watching: {', '.join(watch_paths)}")
    logger.info(f"Patterns: {args.patterns}")
    logger.info(f"Vault: {args.vault}/{args.folder}")
    logger.info(f"Poll interval: {args.interval}s")
    
    await watcher.start()
    logger.info("Watcher started. Press Ctrl+C to stop.")
    
    try:
        await stop_event.wait()
    except KeyboardInterrupt:
        pass
    finally:
        await watcher.stop()
        logger.info("Filesystem watcher stopped")


async def run_scan(args: argparse.Namespace) -> None:
    """Run one-time directory scan."""
    import fnmatch
    from file_handlers import (
        extract_image_metadata,
        extract_pdf_metadata,
        extract_document_metadata,
        extract_audio_metadata,
        extract_video_metadata,
        extract_archive_metadata
    )
    
    # File category mapping
    FILE_CATEGORIES = {
        "image": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg"],
        "document": [".pdf", ".doc", ".docx", ".txt", ".md", ".rtf"],
        "spreadsheet": [".xlsx", ".xls", ".csv"],
        "audio": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"],
        "video": [".mp4", ".mkv", ".avi", ".mov", ".wmv"],
        "archive": [".zip", ".rar", ".7z", ".tar", ".gz"],
    }
    
    handlers = {
        "image": extract_image_metadata,
        "document": extract_document_metadata,
        "audio": extract_audio_metadata,
        "video": extract_video_metadata,
        "archive": extract_archive_metadata,
    }
    
    # Create emitter
    emitter_config = MetadataEmitterConfig(
        vault_path=args.vault,
        output_folder=args.folder,
        use_category_folders=True
    )
    emitter = MetadataEmitter(emitter_config)
    
    # Scan directories
    files_found = 0
    files_processed = 0
    
    for path_str in args.paths:
        watch_path = Path(path_str).expanduser().resolve()
        
        if not watch_path.exists():
            logger.warning(f"Path does not exist: {watch_path}")
            continue
        
        logger.info(f"Scanning: {watch_path}")
        
        if args.recursive:
            iterator = watch_path.rglob("*")
        else:
            iterator = watch_path.glob("*")
        
        for filepath in iterator:
            if not filepath.is_file():
                continue
            
            # Check patterns
            if "*" not in args.patterns:
                if not any(fnmatch.fnmatch(filepath.name, p) for p in args.patterns):
                    continue
            
            files_found += 1
            
            # Determine category
            ext = filepath.suffix.lower()
            category = "other"
            for cat, extensions in FILE_CATEGORIES.items():
                if ext in extensions:
                    category = cat
                    break
            
            # Build metadata
            try:
                stat = filepath.stat()
                
                data = {
                    "path": str(filepath),
                    "filename": filepath.name,
                    "extension": ext,
                    "category": category,
                    "mime_type": "",
                    "size_bytes": stat.st_size,
                    "size_human": _format_size(stat.st_size),
                    "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "checksum": "",
                    "content_preview": "",
                    "custom_metadata": {}
                }
                
                # Extract extended metadata
                if category in handlers:
                    try:
                        extended = handlers[category](filepath)
                        data["custom_metadata"].update(extended)
                        if "content_preview" in extended:
                            data["content_preview"] = extended["content_preview"]
                    except:
                        pass
                
                # Create mock event
                from base_watcher import WatcherEvent, EventType
                from datetime import datetime
                
                event = WatcherEvent(
                    event_type=EventType.CREATED,
                    source=str(filepath),
                    data=data,
                    metadata={"file_type": "filesystem", "category": category}
                )
                
                # Emit
                result = emitter.emit(event)
                if result:
                    files_processed += 1
                    logger.info(f"Processed: {filepath.name}")
                    
            except Exception as e:
                logger.error(f"Error processing {filepath}: {e}")
    
    logger.info(f"Scan complete: {files_processed}/{files_found} files processed")


def _format_size(size: int) -> str:
    """Format file size."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def main():
    """CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == "watch":
        asyncio.run(run_watch(args))
    elif args.command == "scan":
        from datetime import datetime
        asyncio.run(run_scan(args))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
