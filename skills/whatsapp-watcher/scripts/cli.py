#!/usr/bin/env python3
"""
WhatsApp Watcher CLI - Monitor WhatsApp Web and create action files.

Usage:
    python cli.py watch --output ./Needs_Action
    python cli.py watch --triggers triggers.yaml --output ./Needs_Action
    python cli.py init-triggers --output triggers.yaml
"""

import argparse
import asyncio
import json
import logging
import signal
import sys
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent))
BASE_WATCHER_PATH = Path(__file__).parent.parent.parent / "base-watcher-framework" / "scripts"
if BASE_WATCHER_PATH.exists():
    sys.path.insert(0, str(BASE_WATCHER_PATH))

from whatsapp_watcher import (
    WhatsAppWatcher, 
    WhatsAppWatcherConfig, 
    TriggerRule,
    create_triggers_from_config
)
from whatsapp_emitter import WhatsAppActionEmitter, WhatsAppEmitterConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


DEFAULT_TRIGGERS = [
    {"pattern": "urgent", "priority": "urgent", "name": "urgent-keyword"},
    {"pattern": "asap", "priority": "urgent", "name": "asap-keyword"},
    {"pattern": "@task", "priority": "high", "name": "task-mention"},
    {"pattern": "please", "priority": "normal", "name": "please-keyword"},
    {"pattern": r"deadline.*\d", "is_regex": True, "priority": "high", "name": "deadline-date"},
    {"pattern": r"meeting.*tomorrow", "is_regex": True, "priority": "high", "name": "meeting-tomorrow"},
    {"pattern": r"call me", "is_regex": False, "priority": "high", "name": "call-request"},
]


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        description="WhatsApp Watcher - Monitor messages and create action files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start watching with default triggers
  python cli.py watch --output ./Needs_Action
  
  # Watch with custom triggers file
  python cli.py watch --triggers triggers.yaml --output ./Needs_Action
  
  # Watch in headless mode (after initial QR scan)
  python cli.py watch --headless --output ./Needs_Action
  
  # Create sample triggers file
  python cli.py init-triggers --output triggers.yaml
  
  # Add custom trigger inline
  python cli.py watch --output ./Needs_Action --add-trigger "important:high"
"""
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Watch command
    watch_parser = subparsers.add_parser("watch", help="Watch WhatsApp for messages")
    watch_parser.add_argument(
        "--output",
        required=True,
        help="Path for action files (e.g., ./Needs_Action)"
    )
    watch_parser.add_argument(
        "--triggers",
        help="Path to triggers YAML/JSON file"
    )
    watch_parser.add_argument(
        "--add-trigger",
        action="append",
        dest="extra_triggers",
        default=[],
        help="Add trigger as 'pattern:priority' (can use multiple times)"
    )
    watch_parser.add_argument(
        "--session",
        default="./whatsapp_session",
        help="Path for session storage (default: ./whatsapp_session)"
    )
    watch_parser.add_argument(
        "--headless",
        action="store_true",
        help="Run in headless mode (requires prior QR scan)"
    )
    watch_parser.add_argument(
        "--interval",
        type=float,
        default=5.0,
        help="Poll interval in seconds (default: 5)"
    )
    watch_parser.add_argument(
        "--screenshot",
        action="store_true",
        help="Take screenshot when triggered"
    )
    watch_parser.add_argument(
        "--no-priority-folders",
        action="store_true",
        help="Don't organize by priority folders"
    )
    
    # Init triggers command
    init_parser = subparsers.add_parser("init-triggers", help="Create sample triggers file")
    init_parser.add_argument(
        "--output",
        default="triggers.yaml",
        help="Output file path (default: triggers.yaml)"
    )
    init_parser.add_argument(
        "--format",
        choices=["yaml", "json"],
        default="yaml",
        help="Output format (default: yaml)"
    )
    
    return parser


def load_triggers(filepath: str) -> list[dict]:
    """Load triggers from YAML or JSON file."""
    path = Path(filepath)
    content = path.read_text()
    
    if path.suffix in (".yaml", ".yml"):
        try:
            import yaml
            return yaml.safe_load(content).get("triggers", [])
        except ImportError:
            logger.error("PyYAML required for YAML files: pip install pyyaml")
            sys.exit(1)
    else:
        return json.loads(content).get("triggers", [])


def parse_inline_trigger(trigger_str: str) -> dict:
    """Parse inline trigger format 'pattern:priority'."""
    parts = trigger_str.split(":")
    if len(parts) >= 2:
        return {"pattern": parts[0], "priority": parts[1], "name": parts[0]}
    return {"pattern": parts[0], "priority": "normal", "name": parts[0]}


async def run_watch(args: argparse.Namespace) -> None:
    """Run WhatsApp watcher."""
    # Load triggers
    triggers = DEFAULT_TRIGGERS.copy()
    
    if args.triggers:
        triggers = load_triggers(args.triggers)
        logger.info(f"Loaded {len(triggers)} triggers from {args.triggers}")
    
    # Add extra inline triggers
    for trigger_str in args.extra_triggers:
        triggers.append(parse_inline_trigger(trigger_str))
    
    # Create watcher config
    watcher_config = WhatsAppWatcherConfig(
        name="whatsapp-watcher",
        session_path=args.session,
        headless=args.headless,
        triggers=create_triggers_from_config(triggers),
        poll_interval=args.interval,
        screenshot_on_trigger=args.screenshot
    )
    
    # Create emitter config
    emitter_config = WhatsAppEmitterConfig(
        output_path=args.output,
        use_priority_folders=not args.no_priority_folders,
        include_screenshot=args.screenshot
    )
    
    # Create instances
    watcher = WhatsAppWatcher(watcher_config)
    emitter = WhatsAppActionEmitter(emitter_config)
    
    # Wire up event handling
    def handle_event(event):
        filepath = emitter.emit(event)
        if filepath:
            logger.info(f"Created action file: {filepath}")
    
    def handle_qr(msg):
        logger.info(f"QR Code: {msg}")
        print("\n" + "="*50)
        print("SCAN QR CODE IN BROWSER WINDOW")
        print("="*50 + "\n")
    
    watcher.on_event(handle_event)
    watcher.on_error(lambda e: logger.error(f"Watcher error: {e}"))
    watcher.on_qr_code(handle_qr)
    
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
    logger.info("Starting WhatsApp watcher...")
    logger.info(f"Session: {args.session}")
    logger.info(f"Output: {args.output}")
    logger.info(f"Triggers: {len(triggers)} configured")
    logger.info(f"Poll interval: {args.interval}s")
    
    if not args.headless:
        print("\n" + "="*50)
        print("A browser window will open.")
        print("Scan the QR code with your phone if prompted.")
        print("="*50 + "\n")
    
    await watcher.start()
    logger.info("Watcher started. Press Ctrl+C to stop.")
    
    try:
        await stop_event.wait()
    except KeyboardInterrupt:
        pass
    finally:
        await watcher.stop()
        logger.info("WhatsApp watcher stopped")


def create_sample_triggers(output_path: str, fmt: str) -> None:
    """Create sample triggers file."""
    sample = {
        "triggers": [
            {
                "pattern": "urgent",
                "priority": "urgent",
                "name": "urgent-keyword",
                "is_regex": False,
                "case_sensitive": False
            },
            {
                "pattern": "asap",
                "priority": "urgent",
                "name": "asap-keyword"
            },
            {
                "pattern": "@task",
                "priority": "high",
                "name": "task-mention"
            },
            {
                "pattern": "please help",
                "priority": "high",
                "name": "help-request"
            },
            {
                "pattern": r"deadline.*\\d{1,2}/\\d{1,2}",
                "is_regex": True,
                "priority": "high",
                "name": "deadline-date"
            },
            {
                "pattern": r"meeting.*(today|tomorrow)",
                "is_regex": True,
                "priority": "high",
                "name": "meeting-soon"
            },
            {
                "pattern": "call me",
                "priority": "high",
                "name": "call-request"
            },
            {
                "pattern": r"invoice|payment|bill",
                "is_regex": True,
                "priority": "normal",
                "name": "finance-related"
            },
            {
                "pattern": "fyi",
                "priority": "low",
                "name": "fyi-info"
            }
        ]
    }
    
    path = Path(output_path)
    
    if fmt == "yaml":
        try:
            import yaml
            content = yaml.dump(sample, default_flow_style=False, sort_keys=False)
        except ImportError:
            logger.warning("PyYAML not installed, using JSON format")
            content = json.dumps(sample, indent=2)
            path = path.with_suffix(".json")
    else:
        content = json.dumps(sample, indent=2)
    
    path.write_text(content)
    print(f"Created sample triggers file: {path}")
    print("\nTrigger priorities:")
    print("  - urgent: Immediate attention (due in 1 hour)")
    print("  - high: Important (due in 4 hours)")
    print("  - normal: Regular priority (due in 24 hours)")
    print("  - low: Low priority (due in 72 hours)")


def main():
    """CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == "watch":
        asyncio.run(run_watch(args))
    elif args.command == "init-triggers":
        create_sample_triggers(args.output, args.format)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
