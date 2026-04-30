#!/usr/bin/env python3
"""
WhatsAppActionEmitter - Emit WhatsApp messages as Markdown action files.

Creates actionable Markdown files for triggered WhatsApp messages with
priority organization and action checkboxes.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Callable
import re
import sys

# Add base-watcher-framework to path
BASE_WATCHER_PATH = Path(__file__).parent.parent.parent / "base-watcher-framework" / "scripts"
if BASE_WATCHER_PATH.exists():
    sys.path.insert(0, str(BASE_WATCHER_PATH))

from base_watcher import WatcherEvent, EventType


@dataclass
class WhatsAppEmitterConfig:
    """
    Configuration for WhatsAppActionEmitter.
    
    Attributes:
        output_path: Base path for action files
        use_priority_folders: Create subfolders by priority
        use_chat_folders: Create subfolders by chat name
        file_pattern: Pattern for filenames
        include_screenshot: Embed screenshot if available
        action_template: Custom template (None = default)
        auto_categories: Auto-categorize by message content
    """
    output_path: str = "./Needs_Action"
    use_priority_folders: bool = True
    use_chat_folders: bool = False
    file_pattern: str = "{date}_{time}_{chat_short}_{trigger}"
    include_screenshot: bool = True
    action_template: Optional[str] = None
    auto_categories: dict = field(default_factory=lambda: {
        r"meeting|call|schedule": "meetings",
        r"task|todo|do this": "tasks",
        r"pay|invoice|money": "finance",
        r"bug|error|fix": "development",
        r"urgent|asap|now": "urgent"
    })


DEFAULT_WHATSAPP_TEMPLATE = """---
type: whatsapp-action
status: pending
priority: {priority}
category: {category}
created: {created}
due: {due}
source: whatsapp
chat: {chat_name}
sender: {sender}
triggers: {triggers_yaml}
tags:
{tags_yaml}
---

# {priority_emoji} WhatsApp: {chat_name}

## Message Details

| Field | Value |
|-------|-------|
| **From** | {sender} |
| **Chat** | {chat_name} ({chat_type}) |
| **Time** | {timestamp} |
| **Triggers** | {triggers_list} |

## Message

> {message_text}

{screenshot_section}

## Required Actions

- [ ] Review message
- [ ] {primary_action}
- [ ] Respond if needed
- [ ] Mark as complete

## Notes

_Add your notes here..._

## Quick Replies

Copy and paste these if needed:

- "Got it, I'll handle this"
- "Thanks for letting me know"
- "I'll get back to you shortly"

---
*Auto-generated from WhatsApp on {created}*
"""

PRIORITY_CONFIG = {
    "urgent": {"emoji": "🔴", "folder": "01_Urgent", "due_hours": 1},
    "high": {"emoji": "🟠", "folder": "02_High", "due_hours": 4},
    "normal": {"emoji": "🟡", "folder": "03_Normal", "due_hours": 24},
    "low": {"emoji": "🟢", "folder": "04_Low", "due_hours": 72}
}


class WhatsAppActionEmitter:
    """
    Emits WhatsApp message events as structured Markdown action files.
    
    Creates actionable notes with:
    - Priority-based organization
    - YAML frontmatter
    - Message content and context
    - Action checkboxes
    - Optional screenshot embedding
    
    Example:
        config = WhatsAppEmitterConfig(
            output_path="./Needs_Action/WhatsApp",
            use_priority_folders=True
        )
        
        emitter = WhatsAppActionEmitter(config)
        whatsapp_watcher.on_event(emitter.emit)
    """
    
    def __init__(self, config: WhatsAppEmitterConfig):
        self.config = config
        self._output_path = Path(config.output_path).resolve()
        self._template = config.action_template or DEFAULT_WHATSAPP_TEMPLATE
        
        # Ensure output directory exists
        self._output_path.mkdir(parents=True, exist_ok=True)
    
    def emit(self, event: WatcherEvent) -> Optional[Path]:
        """
        Emit event as action file.
        
        Args:
            event: WatcherEvent from WhatsAppWatcher
            
        Returns:
            Path to created file, or None if not a WhatsApp event
        """
        # Only process WhatsApp message events
        if event.metadata.get('message_type') != 'whatsapp':
            return None
        
        if event.event_type in (EventType.ERROR, EventType.WARNING):
            return None
        
        data = event.data
        
        # Determine category and priority
        category = self._categorize(data)
        priority = data.get('priority', 'normal')
        
        # Resolve output folder
        folder = self._resolve_folder(priority, category, data.get('chat_name', 'unknown'))
        folder.mkdir(parents=True, exist_ok=True)
        
        # Generate filename
        filename = self._generate_filename(data)
        filepath = folder / f"{filename}.md"
        
        # Handle duplicates
        counter = 1
        while filepath.exists():
            filepath = folder / f"{filename}_{counter}.md"
            counter += 1
        
        # Generate content
        content = self._format_action(data, priority, category)
        
        # Write file
        filepath.write_text(content, encoding='utf-8')
        
        return filepath
    
    def _resolve_folder(self, priority: str, category: str, chat_name: str) -> Path:
        """Determine output folder."""
        folder = self._output_path
        
        if self.config.use_priority_folders:
            priority_info = PRIORITY_CONFIG.get(priority, PRIORITY_CONFIG['normal'])
            folder = folder / priority_info['folder']
        
        if self.config.use_chat_folders:
            safe_chat = self._sanitize_filename(chat_name)[:30]
            folder = folder / safe_chat
        elif category and category != "general":
            folder = folder / category
        
        return folder
    
    def _generate_filename(self, data: dict) -> str:
        """Generate filename from pattern."""
        now = datetime.now()
        
        chat_name = data.get('chat_name', 'unknown')
        chat_short = self._sanitize_filename(chat_name)[:15]
        
        triggers = data.get('matched_triggers', [])
        trigger_short = triggers[0][:10] if triggers else "msg"
        trigger_short = self._sanitize_filename(trigger_short)
        
        replacements = {
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H%M"),
            "chat_short": chat_short,
            "trigger": trigger_short,
            "sender": self._sanitize_filename(data.get('sender', 'unknown'))[:15]
        }
        
        filename = self.config.file_pattern
        for key, value in replacements.items():
            filename = filename.replace(f"{{{key}}}", value)
        
        return self._sanitize_filename(filename)
    
    def _categorize(self, data: dict) -> str:
        """Determine category from message content."""
        text = data.get('text', '')
        text_lower = text.lower()
        
        for pattern, category in self.config.auto_categories.items():
            if re.search(pattern, text_lower):
                return category
        
        return "general"
    
    def _format_action(self, data: dict, priority: str, category: str) -> str:
        """Format message data as action file content."""
        priority_info = PRIORITY_CONFIG.get(priority, PRIORITY_CONFIG['normal'])
        now = datetime.now()
        
        # Calculate due time
        due_time = now + timedelta(hours=priority_info['due_hours'])
        
        # Build tags
        tags = [
            f"whatsapp/{category}",
            f"priority/{priority}",
            f"chat/{self._sanitize_filename(data.get('chat_name', 'unknown'))}"
        ]
        if data.get('chat_type') == 'group':
            tags.append("group-chat")
        tags_yaml = "\n".join(f"  - {tag}" for tag in tags)
        
        # Build triggers yaml
        triggers = data.get('matched_triggers', [])
        triggers_yaml = "[" + ", ".join(f'"{t}"' for t in triggers) + "]"
        triggers_list = ", ".join(triggers) if triggers else "None"
        
        # Screenshot section
        screenshot_section = ""
        if self.config.include_screenshot and data.get('screenshot'):
            screenshot_path = data['screenshot']
            screenshot_section = f"\n## Screenshot\n\n![[{Path(screenshot_path).name}]]\n"
        
        # Determine primary action
        primary_actions = {
            "meetings": "Confirm attendance or reschedule",
            "tasks": "Complete the requested task",
            "finance": "Process payment or review invoice",
            "development": "Fix the reported issue",
            "urgent": "Respond immediately",
            "general": "Review and respond as needed"
        }
        primary_action = primary_actions.get(category, primary_actions['general'])
        
        content = self._template.format(
            priority=priority,
            priority_emoji=priority_info['emoji'],
            category=category,
            created=now.strftime("%Y-%m-%d %H:%M"),
            due=due_time.strftime("%Y-%m-%d %H:%M"),
            chat_name=data.get('chat_name', 'Unknown'),
            chat_type=data.get('chat_type', 'individual'),
            sender=data.get('sender', 'Unknown'),
            timestamp=data.get('timestamp', ''),
            triggers_yaml=triggers_yaml,
            triggers_list=triggers_list,
            tags_yaml=tags_yaml,
            message_text=data.get('text', ''),
            screenshot_section=screenshot_section,
            primary_action=primary_action
        )
        
        return content
    
    @staticmethod
    def _sanitize_filename(name: str) -> str:
        """Remove invalid filename characters."""
        invalid = r'<>:"/\\|?*'
        for char in invalid:
            name = name.replace(char, '_')
        name = re.sub(r'_+', '_', name)
        name = re.sub(r'\s+', '_', name)
        return name.strip('_')[:100]


# Convenience function
def emit_whatsapp_actions(
    output_path: str = "./Needs_Action/WhatsApp",
    use_priority_folders: bool = True
) -> WhatsAppActionEmitter:
    """
    Create a WhatsAppActionEmitter with common defaults.
    
    Args:
        output_path: Path for action files
        use_priority_folders: Organize by priority
        
    Returns:
        Configured WhatsAppActionEmitter
    """
    config = WhatsAppEmitterConfig(
        output_path=output_path,
        use_priority_folders=use_priority_folders
    )
    return WhatsAppActionEmitter(config)
