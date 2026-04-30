#!/usr/bin/env python3
"""
MetadataEmitter - Emit file metadata as Markdown action files.

Creates structured Markdown files for dropped files with full metadata,
preview content, and action checkboxes in Obsidian vault.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional
import re
import sys

# Add base-watcher-framework to path
BASE_WATCHER_PATH = Path(__file__).parent.parent.parent / "base-watcher-framework" / "scripts"
if BASE_WATCHER_PATH.exists():
    sys.path.insert(0, str(BASE_WATCHER_PATH))

from base_watcher import WatcherEvent, EventType


@dataclass
class MetadataEmitterConfig:
    """
    Configuration for MetadataEmitter.
    
    Attributes:
        vault_path: Path to Obsidian vault
        output_folder: Folder within vault for file notes
        use_category_folders: Create subfolders by file category
        use_date_folders: Create subfolders by date
        file_pattern: Pattern for note filenames
        link_to_file: Create file:// link to original file
        embed_preview: Embed content preview in note
        action_template: Custom template (None = default)
    """
    vault_path: str = ""
    output_folder: str = "FileDrops"
    use_category_folders: bool = True
    use_date_folders: bool = False
    file_pattern: str = "{date}_{filename}"
    link_to_file: bool = True
    embed_preview: bool = True
    action_template: Optional[str] = None


DEFAULT_FILE_TEMPLATE = """---
type: file-drop
status: pending
category: {category}
created: {created}
source_path: "{source_path}"
filename: "{filename}"
extension: "{extension}"
mime_type: "{mime_type}"
size: {size_bytes}
checksum: "{checksum}"
tags:
{tags_yaml}
---

# {category_emoji} {filename}

## File Information

| Property | Value |
|----------|-------|
| **Filename** | {filename} |
| **Type** | {category} ({extension}) |
| **Size** | {size_human} |
| **MIME** | {mime_type} |
| **Created** | {file_created} |
| **Modified** | {file_modified} |
| **Checksum** | `{checksum_short}` |

{file_link_section}

{extended_metadata_section}

{content_preview_section}

## Actions

- [ ] Review file
- [ ] {primary_action}
- [ ] Organize/rename if needed
- [ ] Mark as processed

## Notes

_Add your notes about this file..._

---
*Auto-generated on {created}*
"""

CATEGORY_CONFIG = {
    "image": {"emoji": "🖼️", "action": "View and tag image"},
    "document": {"emoji": "📄", "action": "Read and summarize document"},
    "spreadsheet": {"emoji": "📊", "action": "Review data and extract insights"},
    "presentation": {"emoji": "📽️", "action": "Review presentation content"},
    "audio": {"emoji": "🎵", "action": "Listen and add notes"},
    "video": {"emoji": "🎬", "action": "Watch and add notes"},
    "archive": {"emoji": "📦", "action": "Extract and organize contents"},
    "code": {"emoji": "💻", "action": "Review code"},
    "data": {"emoji": "🗃️", "action": "Analyze data structure"},
    "other": {"emoji": "📎", "action": "Review file"}
}


class MetadataEmitter:
    """
    Emits file drop events as structured Markdown files.
    
    Creates notes in Obsidian vault with:
    - Full file metadata
    - Category-based organization
    - Content previews
    - Links to original file
    - Action checkboxes
    
    Example:
        config = MetadataEmitterConfig(
            vault_path="/path/to/vault",
            output_folder="FileDrops",
            use_category_folders=True
        )
        
        emitter = MetadataEmitter(config)
        drop_watcher.on_event(emitter.emit)
    """
    
    def __init__(self, config: MetadataEmitterConfig):
        self.config = config
        self._vault_path = Path(config.vault_path).resolve()
        self._template = config.action_template or DEFAULT_FILE_TEMPLATE
        
        # Ensure vault exists
        if not self._vault_path.exists():
            raise FileNotFoundError(f"Vault path does not exist: {self._vault_path}")
    
    def emit(self, event: WatcherEvent) -> Optional[Path]:
        """
        Emit event as metadata file.
        
        Args:
            event: WatcherEvent from DropWatcher
            
        Returns:
            Path to created file, or None if not a file event
        """
        # Only process file events
        if event.metadata.get('file_type') != 'filesystem':
            return None
        
        if event.event_type == EventType.ERROR:
            return None
        
        data = event.data
        category = data.get('category', 'other')
        
        # Resolve output folder
        folder = self._resolve_folder(category, data)
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
        content = self._format_metadata(data, category)
        
        # Write file
        filepath.write_text(content, encoding='utf-8')
        
        return filepath
    
    def _resolve_folder(self, category: str, data: dict) -> Path:
        """Determine output folder."""
        folder = self._vault_path / self.config.output_folder
        
        if self.config.use_date_folders:
            now = datetime.now()
            folder = folder / now.strftime("%Y/%m-%B")
        
        if self.config.use_category_folders:
            folder = folder / category
        
        return folder
    
    def _generate_filename(self, data: dict) -> str:
        """Generate note filename from pattern."""
        now = datetime.now()
        
        original_filename = Path(data.get('filename', 'unknown')).stem
        safe_filename = self._sanitize_filename(original_filename)[:40]
        
        replacements = {
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H%M"),
            "filename": safe_filename,
            "category": data.get('category', 'other'),
            "extension": data.get('extension', '').lstrip('.')
        }
        
        result = self.config.file_pattern
        for key, value in replacements.items():
            result = result.replace(f"{{{key}}}", value)
        
        return self._sanitize_filename(result)
    
    def _format_metadata(self, data: dict, category: str) -> str:
        """Format file data as Markdown note."""
        now = datetime.now()
        cat_info = CATEGORY_CONFIG.get(category, CATEGORY_CONFIG['other'])
        
        # Build tags
        tags = [
            f"file/{category}",
            f"extension/{data.get('extension', 'unknown').lstrip('.')}"
        ]
        tags_yaml = "\n".join(f"  - {tag}" for tag in tags)
        
        # File link section
        file_link_section = ""
        if self.config.link_to_file:
            source_path = data.get('path', '')
            file_uri = Path(source_path).as_uri() if source_path else ""
            file_link_section = f"""
## Quick Access

- **Open file**: [{data.get('filename', 'unknown')}]({file_uri})
- **Folder**: `{Path(source_path).parent if source_path else 'unknown'}`
"""
        
        # Extended metadata section
        extended_metadata_section = self._format_extended_metadata(data, category)
        
        # Content preview section
        content_preview_section = ""
        if self.config.embed_preview and data.get('content_preview'):
            preview = data['content_preview']
            if len(preview) > 500:
                preview = preview[:500] + "..."
            content_preview_section = f"""
## Content Preview

```
{preview}
```
"""
        
        # Format checksum
        checksum = data.get('checksum', '')
        checksum_short = checksum[:12] if checksum else 'N/A'
        
        content = self._template.format(
            category=category,
            category_emoji=cat_info['emoji'],
            created=now.strftime("%Y-%m-%d %H:%M"),
            source_path=data.get('path', ''),
            filename=data.get('filename', 'unknown'),
            extension=data.get('extension', ''),
            mime_type=data.get('mime_type', 'unknown'),
            size_bytes=data.get('size_bytes', 0),
            size_human=data.get('size_human', 'unknown'),
            checksum=checksum,
            checksum_short=checksum_short,
            tags_yaml=tags_yaml,
            file_created=data.get('created', ''),
            file_modified=data.get('modified', ''),
            file_link_section=file_link_section,
            extended_metadata_section=extended_metadata_section,
            content_preview_section=content_preview_section,
            primary_action=cat_info['action']
        )
        
        return content
    
    def _format_extended_metadata(self, data: dict, category: str) -> str:
        """Format category-specific extended metadata."""
        sections = []
        
        if category == "image":
            if data.get('dimensions'):
                dims = data['dimensions']
                sections.append(f"| **Dimensions** | {dims[0]} x {dims[1]} |")
            if data.get('format'):
                sections.append(f"| **Format** | {data['format']} |")
            if data.get('camera_make'):
                sections.append(f"| **Camera** | {data.get('camera_make', '')} {data.get('camera_model', '')} |")
            if data.get('date_taken'):
                sections.append(f"| **Date Taken** | {data['date_taken']} |")
                
        elif category == "document":
            if data.get('page_count'):
                sections.append(f"| **Pages** | {data['page_count']} |")
            if data.get('title'):
                sections.append(f"| **Title** | {data['title']} |")
            if data.get('author'):
                sections.append(f"| **Author** | {data['author']} |")
            if data.get('word_count'):
                sections.append(f"| **Words** | {data['word_count']:,} |")
            if data.get('line_count'):
                sections.append(f"| **Lines** | {data['line_count']:,} |")
                
        elif category == "audio":
            if data.get('duration'):
                mins = int(data['duration'] // 60)
                secs = int(data['duration'] % 60)
                sections.append(f"| **Duration** | {mins}:{secs:02d} |")
            if data.get('artist'):
                sections.append(f"| **Artist** | {data['artist']} |")
            if data.get('title'):
                sections.append(f"| **Title** | {data['title']} |")
            if data.get('album'):
                sections.append(f"| **Album** | {data['album']} |")
            if data.get('bitrate'):
                sections.append(f"| **Bitrate** | {data['bitrate']} kbps |")
                
        elif category == "video":
            if data.get('duration'):
                mins = int(data['duration'] // 60)
                secs = int(data['duration'] % 60)
                sections.append(f"| **Duration** | {mins}:{secs:02d} |")
            if data.get('dimensions'):
                dims = data['dimensions']
                sections.append(f"| **Resolution** | {dims[0]} x {dims[1]} |")
            if data.get('fps'):
                sections.append(f"| **FPS** | {data['fps']} |")
            if data.get('codec'):
                sections.append(f"| **Codec** | {data['codec']} |")
                
        elif category == "archive":
            if data.get('file_count'):
                sections.append(f"| **Files** | {data['file_count']} |")
            if data.get('total_uncompressed'):
                size = self._format_size(data['total_uncompressed'])
                sections.append(f"| **Uncompressed** | {size} |")
            if data.get('file_list'):
                files = data['file_list'][:10]
                file_list = "\n".join(f"- `{f}`" for f in files)
                if len(data['file_list']) > 10:
                    file_list += f"\n- _...and {len(data['file_list']) - 10} more_"
                sections.append(f"\n### Contents\n\n{file_list}")
                
        elif category == "data":
            if data.get('type'):
                sections.append(f"| **Structure** | {data['type']} |")
            if data.get('item_count'):
                sections.append(f"| **Items** | {data['item_count']} |")
            if data.get('key_count'):
                sections.append(f"| **Keys** | {data['key_count']} |")
            if data.get('row_count'):
                sections.append(f"| **Rows** | {data['row_count']} |")
            if data.get('column_count'):
                sections.append(f"| **Columns** | {data['column_count']} |")
            if data.get('headers'):
                headers = ", ".join(data['headers'][:10])
                sections.append(f"| **Headers** | {headers} |")
        
        # Check for custom metadata
        custom = data.get('custom_metadata', {})
        for key, value in custom.items():
            if key not in ['extraction_error', 'note'] and value:
                sections.append(f"| **{key.replace('_', ' ').title()}** | {value} |")
        
        if sections:
            # Check if there's a non-table section
            table_rows = [s for s in sections if s.startswith('|')]
            other_sections = [s for s in sections if not s.startswith('|')]
            
            result = ""
            if table_rows:
                result = "\n## Extended Metadata\n\n| Property | Value |\n|----------|-------|\n"
                result += "\n".join(table_rows)
            if other_sections:
                result += "\n" + "\n".join(other_sections)
            
            return result
        
        return ""
    
    @staticmethod
    def _sanitize_filename(name: str) -> str:
        """Remove invalid filename characters."""
        invalid = r'<>:"/\\|?*'
        for char in invalid:
            name = name.replace(char, '_')
        name = re.sub(r'_+', '_', name)
        name = re.sub(r'\s+', '_', name)
        return name.strip('_')[:100]
    
    @staticmethod
    def _format_size(size: int) -> str:
        """Format file size in human-readable form."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


# Convenience function
def emit_file_metadata(
    vault_path: str,
    output_folder: str = "FileDrops",
    use_category_folders: bool = True
) -> MetadataEmitter:
    """
    Create a MetadataEmitter with common defaults.
    
    Args:
        vault_path: Path to Obsidian vault
        output_folder: Folder for file notes
        use_category_folders: Organize by file category
        
    Returns:
        Configured MetadataEmitter
    """
    config = MetadataEmitterConfig(
        vault_path=vault_path,
        output_folder=output_folder,
        use_category_folders=use_category_folders
    )
    return MetadataEmitter(config)
