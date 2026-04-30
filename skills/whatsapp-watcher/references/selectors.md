# WhatsApp Web Selectors Reference

WhatsApp Web frequently updates its UI. This document tracks CSS selectors used by the watcher.

## Current Selectors (as of 2024)

### Authentication

```python
SELECTORS = {
    # QR Code (login screen)
    "qr_code": 'canvas[aria-label="Scan me!"]',
    "qr_code_alt": 'div[data-testid="qrcode"]',
    
    # Main screen (indicates logged in)
    "main_screen": 'div[data-testid="chat-list"]',
}
```

### Chat List

```python
SELECTORS = {
    # Chat list container
    "chat_list": 'div[data-testid="chat-list"] div[data-testid="cell-frame-container"]',
    
    # Unread message indicator
    "unread_indicator": 'span[data-testid="icon-unread-count"]',
    
    # Side panel header
    "side_panel": 'div[data-testid="chatlist-header"]',
}
```

### Active Chat

```python
SELECTORS = {
    # Conversation panel
    "active_chat": 'div[data-testid="conversation-panel-wrapper"]',
    
    # Message list container
    "message_list": 'div[data-testid="conversation-panel-messages"]',
    
    # Chat title in header
    "chat_title": 'header span[data-testid="conversation-info-header-chat-title"]',
}
```

### Messages

```python
SELECTORS = {
    # Incoming messages
    "message_in": 'div[data-testid="msg-container"] div.message-in',
    
    # Outgoing messages
    "message_out": 'div[data-testid="msg-container"] div.message-out',
    
    # Message text content
    "message_text": 'span.selectable-text',
    
    # Message timestamp
    "message_time": 'div[data-testid="msg-meta"] span',
    
    # Message author (in groups)
    "message_author": 'span[data-testid="author"]',
}
```

## Updating Selectors

When WhatsApp Web updates break the watcher:

### 1. Inspect Elements

1. Open WhatsApp Web in browser
2. Right-click element → Inspect
3. Look for `data-testid` attributes (most stable)
4. Note CSS classes as fallback

### 2. Find Stable Attributes

Priority order for selectors:
1. `data-testid` - Most stable, set by WhatsApp
2. `aria-label` - Accessibility attributes, fairly stable
3. `role` - ARIA roles
4. CSS classes - Least stable, change frequently

### 3. Update whatsapp_watcher.py

```python
# In whatsapp_watcher.py, update SELECTORS dict
SELECTORS = {
    "qr_code": 'NEW_SELECTOR_HERE',
    # ...
}
```

### 4. Test Changes

```python
# Quick test script
import asyncio
from playwright.async_api import async_playwright

async def test_selectors():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto("https://web.whatsapp.com")
        
        # Test each selector
        for name, selector in SELECTORS.items():
            el = await page.query_selector(selector)
            print(f"{name}: {'FOUND' if el else 'NOT FOUND'}")
        
        await browser.close()

asyncio.run(test_selectors())
```

## Common Issues

### QR Code Not Detected

Try alternative selectors:
```python
# Primary
'canvas[aria-label="Scan me!"]'

# Alternatives
'div[data-testid="qrcode"]'
'div._19vUU canvas'  # Class-based (less stable)
```

### Messages Not Found

Check message container structure:
```python
# The message structure is typically:
# div[data-testid="msg-container"]
#   └── div.message-in (or .message-out)
#       └── div[data-testid="msg-text"]
#           └── span.selectable-text
```

### Chat Title Missing

Try fallbacks:
```python
# Primary
'header span[data-testid="conversation-info-header-chat-title"]'

# Fallback
'header span[title]'
'div[data-testid="conversation-header"] span'
```

## Selector Testing Tools

### Playwright Inspector

```bash
# Launch with inspector
PWDEBUG=1 python scripts/cli.py watch --output ./test
```

### Browser Console

```javascript
// Test selector in browser console
document.querySelector('div[data-testid="chat-list"]')

// Get all data-testid values
[...document.querySelectorAll('[data-testid]')].map(e => e.dataset.testid)
```

## Version History

| Date | WhatsApp Change | Selectors Updated |
|------|-----------------|-------------------|
| 2024-01 | Initial version | All selectors |

## Fallback Strategy

The watcher uses a fallback pattern:

```python
async def _find_element(self, primary: str, fallback: str = None):
    el = await self._page.query_selector(primary)
    if not el and fallback:
        el = await self._page.query_selector(fallback)
    return el
```

Add fallbacks for critical selectors to improve reliability.
