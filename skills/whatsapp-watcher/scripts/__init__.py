"""
WhatsApp Watcher - Monitor WhatsApp Web for keyword-triggered messages.

Components:
- WhatsAppWatcher: Playwright-based watcher for WhatsApp Web
- TriggerRule: Keyword/regex trigger with priority
- WhatsAppActionEmitter: Create Markdown action files
"""

from .whatsapp_watcher import (
    WhatsAppWatcher,
    WhatsAppWatcherConfig,
    TriggerRule,
    MessageData,
    watch_whatsapp,
    create_triggers_from_config
)

from .whatsapp_emitter import (
    WhatsAppActionEmitter,
    WhatsAppEmitterConfig,
    emit_whatsapp_actions
)

__all__ = [
    "WhatsAppWatcher",
    "WhatsAppWatcherConfig",
    "TriggerRule",
    "MessageData",
    "watch_whatsapp",
    "create_triggers_from_config",
    "WhatsAppActionEmitter",
    "WhatsAppEmitterConfig",
    "emit_whatsapp_actions"
]

__version__ = "1.0.0"
