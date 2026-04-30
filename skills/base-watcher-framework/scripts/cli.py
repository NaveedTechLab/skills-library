#!/usr/bin/env python3
"""
Watcher CLI - Command-line interface for managing watchers.

Provides commands to start, stop, and manage watchers from the command line.
"""

import argparse
import asyncio
import logging
import signal
import sys
from pathlib import Path

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from base_watcher import WatcherEvent
from registry import WatcherRegistry, get_registry
from fs_watcher import FileSystemWatcher, FSWatcherConfig
from obsidian_emitter import ObsidianEmitter, EmitterConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        description="Watcher Framework CLI - Monitor sources and emit to Obsidian",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Watch a directory and emit to Obsidian vault
  watcher watch /path/to/source --vault /path/to/obsidian/vault
  
  # Watch with specific patterns
  watcher watch ./docs --patterns "*.md" "*.txt" --vault ./obsidian
  
  # Load watchers from config file
  watcher run --config watchers.yaml --vault ./obsidian
  
  # Show status of running watchers
  watcher status
"""
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Watch command
    watch_parser = subparsers.add_parser("watch", help="Watch a directory")
    watch_parser.add_argument("path", help="Path to watch")
    watch_parser.add_argument("--name", help="Watcher name", default=None)
    watch_parser.add_argument(
        "--patterns", 
        nargs="+", 
        default=["*"],
        help="File patterns to match (default: *)"
    )
    watch_parser.add_argument(
        "--ignore", 
        nargs="+", 
        default=[".git/*", "__pycache__/*"],
        help="Patterns to ignore"
    )
    watch_parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Don't watch subdirectories"
    )
    watch_parser.add_argument(
        "--interval",
        type=float,
        default=5.0,
        help="Poll interval in seconds (default: 5)"
    )
    watch_parser.add_argument(
        "--vault",
        required=True,
        help="Obsidian vault path for event output"
    )
    watch_parser.add_argument(
        "--folder",
        default="watcher-events",
        help="Folder within vault for events (default: watcher-events)"
    )
    
    # Run command (from config)
    run_parser = subparsers.add_parser("run", help="Run watchers from config file")
    run_parser.add_argument(
        "--config",
        required=True,
        help="Path to configuration file (JSON or YAML)"
    )
    run_parser.add_argument(
        "--vault",
        required=True,
        help="Obsidian vault path for event output"
    )
    run_parser.add_argument(
        "--folder",
        default="watcher-events",
        help="Folder within vault for events"
    )
    
    # Status command
    subparsers.add_parser("status", help="Show watcher status")
    
    # Init command (create sample config)
    init_parser = subparsers.add_parser("init", help="Create sample configuration file")
    init_parser.add_argument(
        "--output",
        default="watchers.yaml",
        help="Output file path (default: watchers.yaml)"
    )
    
    return parser


async def run_watch(args: argparse.Namespace) -> None:
    """Run a single directory watcher."""
    registry = get_registry()
    
    # Create emitter
    emitter_config = EmitterConfig(
        vault_path=args.vault,
        default_folder=args.folder
    )
    emitter = ObsidianEmitter(emitter_config)
    
    # Create watcher
    watcher_name = args.name or f"fs-{Path(args.path).name}"
    config = FSWatcherConfig(
        name=watcher_name,
        watch_path=args.path,
        patterns=args.patterns,
        ignore_patterns=args.ignore,
        recursive=not args.no_recursive,
        poll_interval=args.interval
    )
    
    watcher = FileSystemWatcher(config)
    registry.register(watcher)
    
    # Connect emitter
    registry.on_event(emitter.emit)
    
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
            # Windows doesn't support add_signal_handler
            signal.signal(sig, lambda s, f: signal_handler())
    
    # Start watching
    logger.info(f"Starting watcher: {watcher_name}")
    logger.info(f"Watching: {args.path}")
    logger.info(f"Patterns: {args.patterns}")
    logger.info(f"Emitting to: {args.vault}/{args.folder}")
    
    await registry.start_all()
    
    try:
        await stop_event.wait()
    except KeyboardInterrupt:
        pass
    finally:
        await registry.stop_all()
        logger.info("Watcher stopped")


async def run_from_config(args: argparse.Namespace) -> None:
    """Run watchers from configuration file."""
    registry = get_registry()
    
    # Register watcher types
    from fs_watcher import FileSystemWatcher
    try:
        from api_watcher import APIWatcher
        registry.register_type("api", APIWatcher)
    except ImportError:
        logger.warning("APIWatcher not available (missing aiohttp)")
    
    registry.register_type("filesystem", FileSystemWatcher)
    
    # Load config
    registry.load_from_config(args.config)
    
    # Create emitter
    emitter_config = EmitterConfig(
        vault_path=args.vault,
        default_folder=args.folder
    )
    emitter = ObsidianEmitter(emitter_config)
    registry.on_event(emitter.emit)
    
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
    
    # Start all watchers
    logger.info(f"Starting {len(registry.list_watchers())} watchers from config")
    await registry.start_all()
    
    try:
        await stop_event.wait()
    except KeyboardInterrupt:
        pass
    finally:
        await registry.stop_all()


def show_status() -> None:
    """Display current watcher status."""
    registry = get_registry()
    status = registry.status()
    stats = registry.get_stats()
    
    if not status:
        print("No watchers registered")
        return
    
    print("\nWatcher Status:")
    print("-" * 40)
    for name, state in status.items():
        print(f"  {name}: {state}")
    
    print("\nStatistics:")
    print(f"  Total watchers: {stats.total_watchers}")
    print(f"  Running: {stats.running}")
    print(f"  Paused: {stats.paused}")
    print(f"  Stopped: {stats.stopped}")
    print(f"  Total events: {stats.total_events}")
    print(f"  Errors: {stats.errors}")


def create_sample_config(output_path: str) -> None:
    """Create a sample configuration file."""
    sample_config = """# Watcher Configuration
# Add watchers to monitor different sources

watchers:
  # File system watcher example
  - type: filesystem
    name: docs-watcher
    config:
      watch_path: ./docs
      patterns:
        - "*.md"
        - "*.txt"
      ignore_patterns:
        - ".git/*"
        - "__pycache__/*"
      recursive: true
      poll_interval: 5.0

  # API watcher example (requires aiohttp)
  # - type: api
  #   name: github-releases
  #   config:
  #     url: https://api.github.com/repos/owner/repo/releases/latest
  #     poll_interval: 300
  #     auth_type: bearer
  #     auth_credentials: your_token_here
"""
    
    Path(output_path).write_text(sample_config)
    print(f"Created sample configuration: {output_path}")


def main():
    """CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == "watch":
        asyncio.run(run_watch(args))
    elif args.command == "run":
        asyncio.run(run_from_config(args))
    elif args.command == "status":
        show_status()
    elif args.command == "init":
        create_sample_config(args.output)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
