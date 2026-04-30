---
name: filesystem-watcher
description: Monitor local filesystem for dropped files and generate corresponding metadata/action Markdown files in Obsidian vault. Extracts full metadata including EXIF for images, text from PDFs, audio tags, video properties, and archive contents. Extends BaseWatcher framework. Use when building file inbox automation, document processing pipelines, or media organization systems.
---

# Filesystem Watcher

Monitor directories for new files and automatically create detailed metadata notes in Obsidian vault.

## Prerequisites

1. **BaseWatcher framework** (in sibling directory)
2. **Optional dependencies** for enhanced metadata extraction:
   - Images: `pip install Pillow`
   - PDFs: `pip install pypdf` or `pip install pdfplumber`
   - Documents: `pip install python-docx`
   - Audio: `pip install mutagen` or `pip install tinytag`
   - Video: `ffprobe` (from ffmpeg) or `pip install moviepy`

## Quick Start

### Watch Directory

```bash
python scripts/cli.py watch ~/Downloads --vault /path/to/obsidian/vault
```

### Python Usage

```python
import asyncio
from scripts.drop_watcher import watch_drops
from scripts.metadata_emitter import emit_file_metadata

async def main():
    watcher = watch_drops(
        paths=["~/Downloads", "~/Desktop/Inbox"],
        patterns=["*.pdf", "*.docx", "*.jpg"],
        poll_interval=5.0
    )
    emitter = emit_file_metadata("/path/to/vault")
    
    watcher.on_event(emitter.emit)
    await watcher.start()
    
    await asyncio.sleep(3600)
    await watcher.stop()

asyncio.run(main())
```

## Output Structure

```
vault/FileDrops/
├── image/
│   └── 2024-01-15_photo.md
├── document/
│   ├── 2024-01-15_report.md
│   └── 2024-01-15_invoice.md
├── audio/
│   └── 2024-01-15_recording.md
├── video/
│   └── 2024-01-15_clip.md
└── archive/
    └── 2024-01-15_backup.md
```

## Metadata File Format

```markdown
---
type: file-drop
status: pending
category: document
source_path: "/Users/me/Downloads/report.pdf"
filename: "report.pdf"
extension: ".pdf"
size: 2457600
tags:
  - file/document
  - extension/pdf
---

# 📄 report.pdf

## File Information

| Property | Value |
|----------|-------|
| **Size** | 2.3 MB |
| **Pages** | 15 |
| **Author** | John Doe |

## Content Preview

```
Executive Summary...
```

## Actions

- [ ] Review file
- [ ] Read and summarize document
- [ ] Organize/rename if needed
```

## Supported File Types

| Category | Extensions | Metadata Extracted |
|----------|------------|-------------------|
| **Image** | jpg, png, gif, webp, svg | Dimensions, EXIF, camera info |
| **Document** | pdf, docx, txt, md | Pages, author, text preview |
| **Spreadsheet** | xlsx, csv | Rows, columns, headers |
| **Audio** | mp3, wav, flac, m4a | Duration, artist, album, bitrate |
| **Video** | mp4, mkv, avi, mov | Duration, resolution, codec, fps |
| **Archive** | zip, rar, 7z, tar.gz | File count, contents list |
| **Code** | py, js, ts, java | Line count, imports, functions |
| **Data** | json, yaml, csv, xml | Structure, keys, item count |

## CLI Reference

```bash
# Watch single directory
python scripts/cli.py watch ~/Downloads --vault ./vault

# Watch multiple directories
python scripts/cli.py watch ~/Downloads ~/Desktop/Inbox --vault ./vault

# Filter by file type
python scripts/cli.py watch ./inbox --vault ./vault --patterns "*.pdf" "*.docx"

# Watch recursively
python scripts/cli.py watch ./projects --vault ./vault --recursive

# Move processed files
python scripts/cli.py watch ./inbox --vault ./vault --move-processed

# One-time scan
python scripts/cli.py scan ~/Documents --vault ./vault --recursive

# Custom options
python scripts/cli.py watch ./inbox --vault ./vault \
  --interval 10 \
  --min-size 1024 \
  --max-size 100000000 \
  --date-folders
```

## Configuration

### DropWatcherConfig

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `watch_paths` | list | ["."] | Directories to monitor |
| `patterns` | list | ["*"] | File patterns to include |
| `ignore_patterns` | list | [".*", "*.tmp"] | Patterns to exclude |
| `recursive` | bool | False | Watch subdirectories |
| `extract_content` | bool | True | Extract text content |
| `compute_checksum` | bool | True | Calculate MD5 hash |
| `move_processed` | bool | False | Move to _processed folder |
| `stable_time` | float | 2.0 | Seconds to wait for file stability |

### MetadataEmitterConfig

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `vault_path` | str | required | Path to Obsidian vault |
| `output_folder` | str | "FileDrops" | Folder for metadata notes |
| `use_category_folders` | bool | True | Organize by file type |
| `use_date_folders` | bool | False | Organize by date |
| `link_to_file` | bool | True | Create file:// links |
| `embed_preview` | bool | True | Include content preview |

## Custom Handlers

Register custom metadata extractors:

```python
from scripts.drop_watcher import DropWatcher, DropWatcherConfig

def extract_custom_metadata(path):
    return {
        "custom_field": "value",
        "content_preview": "..."
    }

config = DropWatcherConfig(name="custom", watch_paths=["./inbox"])
watcher = DropWatcher(config)
watcher.register_handler("custom_category", extract_custom_metadata)
```

## Integration with Registry

```python
from base_watcher_framework.scripts.registry import get_registry
from scripts.drop_watcher import DropWatcher, DropWatcherConfig
from scripts.metadata_emitter import emit_file_metadata

registry = get_registry()

config = DropWatcherConfig(
    name="downloads-watcher",
    watch_paths=["~/Downloads"],
    patterns=["*.pdf", "*.docx", "*.xlsx"]
)

registry.register(DropWatcher(config))
registry.on_event(emit_file_metadata("./vault").emit)

await registry.start_all()
```

## File Stability Detection

The watcher waits for files to stabilize before processing:
- Detects file first appearance
- Waits `stable_time` seconds (default: 2s)
- Verifies file still exists and size unchanged
- Then processes and emits event

This prevents processing partially downloaded/copied files.
