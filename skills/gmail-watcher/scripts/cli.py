#!/usr/bin/env python3
"""
Gmail Watcher CLI - Monitor Gmail and create action files.

Usage:
    python cli.py watch --credentials ./credentials.json --output ./Needs_Action
    python cli.py auth --credentials ./credentials.json
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

from gmail_watcher import GmailWatcher, GmailWatcherConfig
from action_emitter import ActionFileEmitter, ActionEmitterConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        description="Gmail Watcher - Monitor emails and create action files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Authenticate with Gmail (first time setup)
  python cli.py auth --credentials ./credentials.json
  
  # Watch for unread emails
  python cli.py watch --credentials ./credentials.json --output ./Needs_Action
  
  # Watch for important emails only
  python cli.py watch --credentials ./credentials.json --important --output ./vault/Needs_Action
  
  # Watch with custom interval
  python cli.py watch --credentials ./credentials.json --interval 30 --output ./Needs_Action
"""
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Auth command
    auth_parser = subparsers.add_parser("auth", help="Authenticate with Gmail")
    auth_parser.add_argument(
        "--credentials",
        required=True,
        help="Path to Google OAuth credentials.json"
    )
    auth_parser.add_argument(
        "--token",
        default="token.json",
        help="Path to save OAuth token (default: token.json)"
    )
    
    # Watch command
    watch_parser = subparsers.add_parser("watch", help="Watch Gmail for emails")
    watch_parser.add_argument(
        "--credentials",
        required=True,
        help="Path to Google OAuth credentials.json"
    )
    watch_parser.add_argument(
        "--token",
        default="token.json",
        help="Path to OAuth token (default: token.json)"
    )
    watch_parser.add_argument(
        "--output",
        required=True,
        help="Path for action files (e.g., ./Needs_Action)"
    )
    watch_parser.add_argument(
        "--unread",
        action="store_true",
        default=True,
        help="Watch for unread emails (default: True)"
    )
    watch_parser.add_argument(
        "--important",
        action="store_true",
        help="Watch for important emails"
    )
    watch_parser.add_argument(
        "--labels",
        nargs="+",
        default=[],
        help="Watch for specific labels"
    )
    watch_parser.add_argument(
        "--interval",
        type=float,
        default=60.0,
        help="Poll interval in seconds (default: 60)"
    )
    watch_parser.add_argument(
        "--max-results",
        type=int,
        default=20,
        help="Maximum emails per poll (default: 20)"
    )
    watch_parser.add_argument(
        "--no-priority-folders",
        action="store_true",
        help="Don't organize by priority folders"
    )
    
    return parser


def run_auth(args: argparse.Namespace) -> None:
    """Run authentication flow."""
    from google_auth_oauthlib.flow import InstalledAppFlow
    
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
    
    creds_path = Path(args.credentials)
    if not creds_path.exists():
        print(f"Error: Credentials file not found: {creds_path}")
        print("\nTo get credentials.json:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create a project and enable Gmail API")
        print("3. Create OAuth 2.0 credentials (Desktop app)")
        print("4. Download and save as credentials.json")
        sys.exit(1)
    
    print("Starting OAuth authentication flow...")
    print("A browser window will open for Google sign-in.\n")
    
    flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
    creds = flow.run_local_server(port=0)
    
    token_path = Path(args.token)
    token_path.write_text(creds.to_json())
    
    print(f"\nAuthentication successful!")
    print(f"Token saved to: {token_path}")
    print("\nYou can now run: python cli.py watch --credentials ./credentials.json --output ./Needs_Action")


async def run_watch(args: argparse.Namespace) -> None:
    """Run Gmail watcher."""
    # Create watcher config
    watcher_config = GmailWatcherConfig(
        name="gmail-watcher",
        credentials_path=args.credentials,
        token_path=args.token,
        filter_unread=args.unread,
        filter_important=args.important,
        filter_labels=args.labels,
        poll_interval=args.interval,
        max_results=args.max_results
    )
    
    # Create emitter config
    emitter_config = ActionEmitterConfig(
        output_path=args.output,
        use_priority_folders=not args.no_priority_folders
    )
    
    # Create instances
    watcher = GmailWatcher(watcher_config)
    emitter = ActionFileEmitter(emitter_config)
    
    # Wire up event handling
    def handle_event(event):
        filepath = emitter.emit(event)
        if filepath:
            logger.info(f"Created action file: {filepath}")
    
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
    logger.info("Starting Gmail watcher...")
    logger.info(f"Credentials: {args.credentials}")
    logger.info(f"Output: {args.output}")
    logger.info(f"Filters: unread={args.unread}, important={args.important}")
    logger.info(f"Poll interval: {args.interval}s")
    
    await watcher.start()
    logger.info("Watcher started. Press Ctrl+C to stop.")
    
    try:
        await stop_event.wait()
    except KeyboardInterrupt:
        pass
    finally:
        await watcher.stop()
        logger.info("Gmail watcher stopped")


def main():
    """CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == "auth":
        run_auth(args)
    elif args.command == "watch":
        asyncio.run(run_watch(args))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
