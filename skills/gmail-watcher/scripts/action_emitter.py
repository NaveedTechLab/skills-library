#!/usr/bin/env python3
"""
ActionFileEmitter - Emit email events as structured Markdown action files.

Creates actionable Markdown files in /Needs_Action folder with email details,
priority indicators, and action checkboxes.
"""

from dataclasses import dataclass, field
from datetime import datetime
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
class ActionEmitterConfig:
    """
    Configuration for ActionFileEmitter.
    
    Attributes:
        output_path: Base path for action files (default: ./Needs_Action)
        use_priority_folders: Create subfolders by priority
        file_pattern: Pattern for filenames
        include_body: Include email body in action file
        action_template: Custom template (None = default)
        auto_categories: Auto-categorize by sender/subject patterns
        category_rules: Dict of pattern -> category mappings
    """
    output_path: str = "./Needs_Action"
    use_priority_folders: bool = True
    file_pattern: str = "{date}_{time}_{sender_short}_{subject_short}"
    include_body: bool = True
    action_template: Optional[str] = None
    auto_categories: bool = True
    category_rules: dict = field(default_factory=lambda: {
        r"invoice|payment|bill": "finance",
        r"meeting|calendar|schedule": "meetings",
        r"github|gitlab|pull request|PR": "development",
        r"urgent|asap|immediately": "urgent",
        r"newsletter|digest|weekly": "newsletters"
    })


DEFAULT_ACTION_TEMPLATE = """---
type: email-action
status: pending
priority: {priority}
category: {category}
created: {created}
due: {due}
source: gmail
message_id: {message_id}
tags:
{tags_yaml}
---

# {priority_emoji} {subject}

## Email Details

| Field | Value |
|-------|-------|
| **From** | {sender} <{sender_email}> |
| **To** | {recipient} |
| **Date** | {email_date} |
| **Labels** | {labels} |
| **Attachments** | {attachments} |

## Summary

> {snippet}

{body_section}

## Required Actions

- [ ] Review email content
- [ ] {primary_action}
- [ ] Mark as complete when done

## Notes

_Add your notes here..._

---
*Auto-generated from Gmail on {created}*
"""

PRIORITY_CONFIG = {
    "urgent": {"emoji": "🔴", "folder": "01_Urgent", "due_days": 0},
    "high": {"emoji": "🟠", "folder": "02_High", "due_days": 1},
    "normal": {"emoji": "🟡", "folder": "03_Normal", "due_days": 3},
    "low": {"emoji": "🟢", "folder": "04_Low", "due_days": 7}
}


class ActionFileEmitter:
    """
    Emits email events as structured Markdown action files.
    
    Creates actionable notes in /Needs_Action folder with:
    - Priority-based organization
    - YAML frontmatter for automation
    - Action checkboxes
    - Email metadata and preview
    
    Example:
        config = ActionEmitterConfig(
            output_path="./vault/Needs_Action",
            use_priority_folders=True
        )
        
        emitter = ActionFileEmitter(config)
        gmail_watcher.on_event(emitter.emit)
    """
    
    def __init__(self, config: ActionEmitterConfig):
        self.config = config
        self._output_path = Path(config.output_path).resolve()
        self._template = config.action_template or DEFAULT_ACTION_TEMPLATE
        self._categorizers: list[Callable[[dict], str]] = []
        
        # Ensure output directory exists
        self._output_path.mkdir(parents=True, exist_ok=True)
    
    def add_categorizer(self, func: Callable[[dict], str]) -> "ActionFileEmitter":
        """
        Add custom categorization function.
        
        Args:
            func: Function(email_data) -> category_string
            
        Returns:
            Self for chaining
        """
        self._categorizers.append(func)
        return self
    
    def emit(self, event: WatcherEvent) -> Optional[Path]:
        """
        Emit event as action file.
        
        Args:
            event: WatcherEvent from GmailWatcher
            
        Returns:
            Path to created file, or None if not an email event
        """
        # Only process email events
        if not event.metadata.get('email_type') == 'gmail':
            return None
        
        if event.event_type == EventType.ERROR:
            return None
        
        data = event.data
        
        # Determine category and priority
        category = self._categorize(data)
        priority = data.get('priority', 'normal')
        
        # Resolve output folder
        folder = self._resolve_folder(priority, category)
        folder.mkdir(parents=True, exist_ok=True)
        
        # Generate filename
        filename = self._generate_filename(data)
        filepath = folder / f"{filename}.md"
        
        # Handle duplicates
        if filepath.exists():
            counter = 1
            while filepath.exists():
                filepath = folder / f"{filename}_{counter}.md"
                counter += 1
        
        # Generate content
        content = self._format_action(data, priority, category)
        
        # Write file
        filepath.write_text(content, encoding='utf-8')
        
        return filepath
    
    def _resolve_folder(self, priority: str, category: str) -> Path:
        """Determine output folder based on priority and category."""
        folder = self._output_path
        
        if self.config.use_priority_folders:
            priority_info = PRIORITY_CONFIG.get(priority, PRIORITY_CONFIG['normal'])
            folder = folder / priority_info['folder']
        
        if category and category != "general":
            folder = folder / category
        
        return folder
    
    def _generate_filename(self, data: dict) -> str:
        """Generate filename from pattern."""
        now = datetime.now()
        
        # Extract sender short name
        sender = data.get('sender', 'unknown')
        sender_short = re.sub(r'[^\w]', '', sender)[:20]
        
        # Extract subject short
        subject = data.get('subject', 'no-subject')
        subject_short = re.sub(r'[^\w\s]', '', subject)[:30].strip().replace(' ', '_')
        
        replacements = {
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H%M"),
            "sender_short": sender_short,
            "subject_short": subject_short,
            "message_id": data.get('message_id', '')[:8]
        }
        
        filename = self.config.file_pattern
        for key, value in replacements.items():
            filename = filename.replace(f"{{{key}}}", value)
        
        return self._sanitize_filename(filename)
    
    def _categorize(self, data: dict) -> str:
        """Determine category for email."""
        # Try custom categorizers first
        for categorizer in self._categorizers:
            try:
                result = categorizer(data)
                if result:
                    return result
            except Exception:
                pass
        
        # Auto-categorize if enabled
        if self.config.auto_categories:
            text = f"{data.get('subject', '')} {data.get('sender', '')} {data.get('snippet', '')}"
            text_lower = text.lower()
            
            for pattern, category in self.config.category_rules.items():
                if re.search(pattern, text_lower):
                    return category
        
        return "general"
    
    def _format_action(self, data: dict, priority: str, category: str) -> str:
        """Format email data as action file content."""
        priority_info = PRIORITY_CONFIG.get(priority, PRIORITY_CONFIG['normal'])
        now = datetime.now()
        
        # Calculate due date
        from datetime import timedelta
        due_date = now + timedelta(days=priority_info['due_days'])
        
        # Build tags
        tags = [f"email/{category}", f"priority/{priority}"]
        if data.get('is_important'):
            tags.append("important")
        if data.get('has_attachments'):
            tags.append("has-attachments")
        tags_yaml = "\n".join(f"  - {tag}" for tag in tags)
        
        # Build body section
        body_section = ""
        if self.config.include_body and data.get('body_preview'):
            body_section = f"\n## Email Body Preview\n\n{data['body_preview']}\n"
        
        # Determine primary action based on category
        primary_actions = {
            "finance": "Review and process payment/invoice",
            "meetings": "Confirm attendance or reschedule",
            "development": "Review code changes or respond",
            "urgent": "Respond immediately",
            "newsletters": "Read or unsubscribe if not needed",
            "general": "Review and respond as needed"
        }
        primary_action = primary_actions.get(category, primary_actions['general'])
        
        # Format attachments
        attachments = data.get('attachment_names', [])
        attachments_str = ", ".join(attachments) if attachments else "None"
        
        # Format labels
        labels = data.get('labels', [])
        labels_str = ", ".join(labels) if labels else "None"
        
        content = self._template.format(
            priority=priority,
            priority_emoji=priority_info['emoji'],
            category=category,
            created=now.strftime("%Y-%m-%d %H:%M"),
            due=due_date.strftime("%Y-%m-%d"),
            message_id=data.get('message_id', ''),
            tags_yaml=tags_yaml,
            subject=data.get('subject', '(No Subject)'),
            sender=data.get('sender', 'Unknown'),
            sender_email=data.get('sender_email', ''),
            recipient=data.get('recipient', ''),
            email_date=data.get('date', ''),
            labels=labels_str,
            attachments=attachments_str,
            snippet=data.get('snippet', ''),
            body_section=body_section,
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
        return name.strip('_')[:100]


# Convenience function
def emit_to_needs_action(
    output_path: str = "./Needs_Action",
    use_priority_folders: bool = True
) -> ActionFileEmitter:
    """
    Create an ActionFileEmitter with common defaults.
    
    Args:
        output_path: Path for action files
        use_priority_folders: Organize by priority
        
    Returns:
        Configured ActionFileEmitter
    """
    config = ActionEmitterConfig(
        output_path=output_path,
        use_priority_folders=use_priority_folders
    )
    return ActionFileEmitter(config)
