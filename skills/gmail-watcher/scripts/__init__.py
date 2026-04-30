"""
Gmail Watcher - Monitor Gmail for actionable emails.

Components:
- GmailWatcher: BaseWatcher extension for Gmail API
- ActionFileEmitter: Create Markdown action files in /Needs_Action
"""

from .gmail_watcher import (
    GmailWatcher,
    GmailWatcherConfig,
    EmailData,
    watch_gmail
)

from .action_emitter import (
    ActionFileEmitter,
    ActionEmitterConfig,
    emit_to_needs_action
)

__all__ = [
    "GmailWatcher",
    "GmailWatcherConfig",
    "EmailData",
    "watch_gmail",
    "ActionFileEmitter",
    "ActionEmitterConfig",
    "emit_to_needs_action"
]

__version__ = "1.0.0"
