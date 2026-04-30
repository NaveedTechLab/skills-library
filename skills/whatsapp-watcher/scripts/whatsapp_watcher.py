#!/usr/bin/env python3
"""
WhatsAppWatcher - Monitor WhatsApp Web for keyword-triggered messages.

Uses Playwright for browser automation to monitor WhatsApp Web.
Extends BaseWatcher for integration with WatcherRegistry and emitters.
"""

import asyncio
import json
import re
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

try:
    from playwright.async_api import async_playwright, Browser, Page, BrowserContext
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


# WhatsApp Web selectors (may need updates as WhatsApp changes)
SELECTORS = {
    "qr_code": 'canvas[aria-label="Scan me!"]',
    "qr_code_alt": 'div[data-testid="qrcode"]',
    "main_screen": 'div[data-testid="chat-list"]',
    "chat_list": 'div[data-testid="chat-list"] div[data-testid="cell-frame-container"]',
    "active_chat": 'div[data-testid="conversation-panel-wrapper"]',
    "message_list": 'div[data-testid="conversation-panel-messages"]',
    "message_in": 'div[data-testid="msg-container"] div.message-in',
    "message_out": 'div[data-testid="msg-container"] div.message-out',
    "message_text": 'span.selectable-text',
    "message_time": 'div[data-testid="msg-meta"] span',
    "chat_title": 'header span[data-testid="conversation-info-header-chat-title"]',
    "unread_indicator": 'span[data-testid="icon-unread-count"]',
    "side_panel": 'div[data-testid="chatlist-header"]',
}


@dataclass
class MessageData:
    """Parsed WhatsApp message data."""
    message_id: str
    chat_name: str
    chat_type: str  # "individual" or "group"
    sender: str
    text: str
    timestamp: datetime
    is_incoming: bool
    has_media: bool
    matched_triggers: list
    priority: str


@dataclass
class TriggerRule:
    """Keyword/regex trigger rule with priority."""
    pattern: str
    is_regex: bool = False
    priority: str = "normal"  # urgent, high, normal, low
    case_sensitive: bool = False
    name: str = ""
    
    def matches(self, text: str) -> bool:
        """Check if text matches this trigger."""
        if self.is_regex:
            flags = 0 if self.case_sensitive else re.IGNORECASE
            return bool(re.search(self.pattern, text, flags))
        else:
            if self.case_sensitive:
                return self.pattern in text
            return self.pattern.lower() in text.lower()


@dataclass
class WhatsAppWatcherConfig(WatcherConfig):
    """
    Configuration for WhatsAppWatcher.
    
    Attributes:
        session_path: Path to store browser session (for QR persistence)
        headless: Run browser in headless mode (False for QR scan)
        triggers: List of TriggerRule objects
        monitor_all_chats: Monitor all chats or only unread
        include_outgoing: Also monitor outgoing messages
        screenshot_on_trigger: Take screenshot when triggered
        browser_type: Browser to use (chromium, firefox, webkit)
        user_data_dir: Custom user data directory for persistence
    """
    session_path: str = "./whatsapp_session"
    headless: bool = False
    triggers: list = field(default_factory=list)
    monitor_all_chats: bool = True
    include_outgoing: bool = False
    screenshot_on_trigger: bool = False
    browser_type: str = "chromium"
    user_data_dir: Optional[str] = None


class WhatsAppWatcher(BaseWatcher):
    """
    Watcher that monitors WhatsApp Web for keyword-triggered messages.
    
    Uses Playwright for browser automation with session persistence.
    
    Example:
        config = WhatsAppWatcherConfig(
            name="whatsapp-monitor",
            triggers=[
                TriggerRule("urgent", priority="urgent"),
                TriggerRule("@task", priority="high"),
                TriggerRule(r"deadline.*tomorrow", is_regex=True, priority="high"),
            ],
            poll_interval=5.0
        )
        
        watcher = WhatsAppWatcher(config)
        watcher.on_event(lambda e: print(f"Triggered: {e.data['text']}"))
        
        await watcher.start()
    """
    
    def __init__(self, config: WhatsAppWatcherConfig):
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError(
                "Playwright required. Install with:\n"
                "pip install playwright\n"
                "playwright install chromium"
            )
        
        super().__init__(config)
        self.wa_config = config
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._seen_messages: set = set()
        self._is_authenticated = False
        self._on_qr_callback: Optional[Callable] = None
    
    def on_qr_code(self, callback: Callable[[str], None]) -> "WhatsAppWatcher":
        """
        Register callback for QR code display.
        
        Args:
            callback: Function called with message when QR needs scanning
            
        Returns:
            Self for chaining
        """
        self._on_qr_callback = callback
        return self
    
    async def _setup(self) -> None:
        """Initialize Playwright and WhatsApp Web."""
        self._playwright = await async_playwright().start()
        
        # Setup browser with persistent context
        session_path = Path(self.wa_config.session_path).resolve()
        session_path.mkdir(parents=True, exist_ok=True)
        
        browser_type = getattr(self._playwright, self.wa_config.browser_type)
        
        # Use persistent context for session storage
        self._context = await browser_type.launch_persistent_context(
            user_data_dir=str(session_path),
            headless=self.wa_config.headless,
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        
        self._page = await self._context.new_page()
        
        # Navigate to WhatsApp Web
        await self._page.goto("https://web.whatsapp.com", wait_until="networkidle")
        
        # Wait for authentication
        await self._wait_for_auth()
        
        # Build initial seen messages set
        await self._scan_initial_messages()
    
    async def _teardown(self) -> None:
        """Clean up browser resources."""
        if self._page:
            await self._page.close()
        if self._context:
            await self._context.close()
        if self._playwright:
            await self._playwright.stop()
        
        self._page = None
        self._context = None
        self._browser = None
        self._playwright = None
        self._seen_messages.clear()
    
    async def _poll(self) -> list[WatcherEvent]:
        """Poll WhatsApp Web for new messages."""
        events = []
        
        try:
            # Check if still authenticated
            if not await self._check_auth():
                events.append(self._create_event(
                    EventType.WARNING,
                    data={"message": "WhatsApp session expired, re-authentication needed"},
                    source="whatsapp:auth"
                ))
                return events
            
            # Scan for new messages
            messages = await self._scan_messages()
            
            for msg in messages:
                msg_id = f"{msg.chat_name}:{msg.timestamp.isoformat()}:{hash(msg.text)}"
                
                if msg_id in self._seen_messages:
                    continue
                
                self._seen_messages.add(msg_id)
                
                # Check triggers
                matched_triggers = self._check_triggers(msg.text)
                
                if matched_triggers:
                    msg.matched_triggers = matched_triggers
                    msg.priority = self._get_highest_priority(matched_triggers)
                    
                    # Take screenshot if configured
                    screenshot_path = None
                    if self.wa_config.screenshot_on_trigger:
                        screenshot_path = await self._take_screenshot(msg)
                    
                    events.append(self._create_message_event(msg, screenshot_path))
        
        except Exception as e:
            events.append(self._create_event(
                EventType.ERROR,
                data={"error": str(e)},
                source="whatsapp:poll"
            ))
        
        return events
    
    async def _wait_for_auth(self, timeout: int = 120000) -> None:
        """Wait for WhatsApp Web authentication."""
        try:
            # Check if already logged in
            main_screen = await self._page.query_selector(SELECTORS["main_screen"])
            if main_screen:
                self._is_authenticated = True
                return
            
            # Wait for QR code or main screen
            if self._on_qr_callback:
                self._on_qr_callback("Please scan the QR code in the browser window")
            
            # Wait for main screen to appear (user scanned QR)
            await self._page.wait_for_selector(
                SELECTORS["main_screen"],
                timeout=timeout
            )
            
            self._is_authenticated = True
            
        except Exception as e:
            raise RuntimeError(f"WhatsApp authentication failed: {e}")
    
    async def _check_auth(self) -> bool:
        """Check if still authenticated."""
        try:
            main_screen = await self._page.query_selector(SELECTORS["main_screen"])
            return main_screen is not None
        except:
            return False
    
    async def _scan_initial_messages(self) -> None:
        """Scan existing messages to avoid re-triggering."""
        try:
            messages = await self._scan_messages()
            for msg in messages:
                msg_id = f"{msg.chat_name}:{msg.timestamp.isoformat()}:{hash(msg.text)}"
                self._seen_messages.add(msg_id)
        except:
            pass
    
    async def _scan_messages(self) -> list[MessageData]:
        """Scan visible messages from active chats."""
        messages = []
        
        try:
            # Get all chat items with unread messages
            chat_items = await self._page.query_selector_all(SELECTORS["chat_list"])
            
            for chat_item in chat_items[:10]:  # Limit to first 10 chats
                try:
                    # Check for unread indicator
                    unread = await chat_item.query_selector(SELECTORS["unread_indicator"])
                    
                    if not self.wa_config.monitor_all_chats and not unread:
                        continue
                    
                    # Click to open chat
                    await chat_item.click()
                    await asyncio.sleep(0.5)
                    
                    # Get chat name
                    chat_title_el = await self._page.query_selector(SELECTORS["chat_title"])
                    chat_name = await chat_title_el.inner_text() if chat_title_el else "Unknown"
                    
                    # Determine chat type (group chats have different styling)
                    chat_type = "group" if "group" in (await chat_item.get_attribute("class") or "") else "individual"
                    
                    # Get messages
                    msg_elements = await self._page.query_selector_all(SELECTORS["message_in"])
                    
                    for msg_el in msg_elements[-5:]:  # Last 5 incoming messages
                        try:
                            text_el = await msg_el.query_selector(SELECTORS["message_text"])
                            text = await text_el.inner_text() if text_el else ""
                            
                            if not text:
                                continue
                            
                            # Get timestamp
                            time_el = await msg_el.query_selector(SELECTORS["message_time"])
                            time_str = await time_el.inner_text() if time_el else ""
                            
                            # Parse time (WhatsApp shows HH:MM format)
                            try:
                                today = datetime.now()
                                time_parts = time_str.split(":")
                                msg_time = today.replace(
                                    hour=int(time_parts[0]),
                                    minute=int(time_parts[1]),
                                    second=0,
                                    microsecond=0
                                )
                            except:
                                msg_time = datetime.now()
                            
                            # Get sender for group chats
                            sender = chat_name
                            if chat_type == "group":
                                sender_el = await msg_el.query_selector('span[data-testid="author"]')
                                if sender_el:
                                    sender = await sender_el.inner_text()
                            
                            messages.append(MessageData(
                                message_id=f"{chat_name}:{msg_time.isoformat()}",
                                chat_name=chat_name,
                                chat_type=chat_type,
                                sender=sender,
                                text=text,
                                timestamp=msg_time,
                                is_incoming=True,
                                has_media=False,  # TODO: detect media
                                matched_triggers=[],
                                priority="normal"
                            ))
                        except:
                            continue
                except:
                    continue
        except Exception as e:
            pass
        
        return messages
    
    def _check_triggers(self, text: str) -> list[TriggerRule]:
        """Check text against all triggers."""
        matched = []
        
        for trigger in self.wa_config.triggers:
            if trigger.matches(text):
                matched.append(trigger)
        
        return matched
    
    def _get_highest_priority(self, triggers: list[TriggerRule]) -> str:
        """Get highest priority from matched triggers."""
        priority_order = {"urgent": 0, "high": 1, "normal": 2, "low": 3}
        
        if not triggers:
            return "normal"
        
        return min(triggers, key=lambda t: priority_order.get(t.priority, 2)).priority
    
    async def _take_screenshot(self, msg: MessageData) -> Optional[str]:
        """Take screenshot of current chat."""
        try:
            screenshot_dir = Path(self.wa_config.session_path) / "screenshots"
            screenshot_dir.mkdir(exist_ok=True)
            
            filename = f"{msg.timestamp.strftime('%Y%m%d_%H%M%S')}_{msg.chat_name[:20]}.png"
            filepath = screenshot_dir / filename
            
            await self._page.screenshot(path=str(filepath))
            return str(filepath)
        except:
            return None
    
    def _create_message_event(self, msg: MessageData, screenshot_path: Optional[str]) -> WatcherEvent:
        """Create event from message data."""
        trigger_names = [t.name or t.pattern for t in msg.matched_triggers]
        
        return self._create_event(
            EventType.CREATED,
            data={
                "message_id": msg.message_id,
                "chat_name": msg.chat_name,
                "chat_type": msg.chat_type,
                "sender": msg.sender,
                "text": msg.text,
                "timestamp": msg.timestamp.isoformat(),
                "is_incoming": msg.is_incoming,
                "has_media": msg.has_media,
                "matched_triggers": trigger_names,
                "priority": msg.priority,
                "screenshot": screenshot_path
            },
            source=f"whatsapp:{msg.chat_name}",
            message_type="whatsapp",
            priority=msg.priority
        )


def create_triggers_from_config(config: list[dict]) -> list[TriggerRule]:
    """
    Create TriggerRule objects from config dictionaries.
    
    Args:
        config: List of trigger configurations
        
    Example:
        triggers = create_triggers_from_config([
            {"pattern": "urgent", "priority": "urgent"},
            {"pattern": r"@task\\s+\\w+", "is_regex": True, "priority": "high"},
        ])
    """
    return [TriggerRule(**t) for t in config]


# Convenience function
def watch_whatsapp(
    triggers: list[dict],
    session_path: str = "./whatsapp_session",
    headless: bool = False,
    poll_interval: float = 5.0
) -> WhatsAppWatcher:
    """
    Create a WhatsAppWatcher with common defaults.
    
    Args:
        triggers: List of trigger configs
        session_path: Path for session storage
        headless: Run in headless mode
        poll_interval: Seconds between polls
        
    Returns:
        Configured WhatsAppWatcher
    """
    config = WhatsAppWatcherConfig(
        name="whatsapp-watcher",
        session_path=session_path,
        headless=headless,
        triggers=create_triggers_from_config(triggers),
        poll_interval=poll_interval
    )
    return WhatsAppWatcher(config)
