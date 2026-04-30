#!/usr/bin/env python3
"""
Content Management System for LinkedIn Posting Automation

Manages post templates, content libraries, and content moderation
"""

import asyncio
import hashlib
import json
import os
import re
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union
from uuid import uuid4

import structlog

from linkedin_api_integration import LinkedInPost, PostStatus, MediaType, MediaAsset
from approval_workflow import ApprovalLevel, ApprovalStatus

logger = structlog.get_logger()


class ContentType(Enum):
    """Types of content"""
    POST = "post"
    ARTICLE = "article"
    RECIPE = "recipe"  # For content templates
    TEMPLATE = "template"


class ContentStatus(Enum):
    """Status of content items"""
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class ContentCategory(Enum):
    """Categories for content"""
    NEWS = "news"
    INSIGHTS = "insights"
    ANNOUNCEMENTS = "announcements"
    EDUCATIONAL = "educational"
    PROMOTIONAL = "promotional"
    THOUGHT_LEADERSHIP = "thought_leadership"
    INDUSTRY_UPDATE = "industry_update"


@dataclass
class ContentTag:
    """Tag for content categorization"""
    id: str
    name: str
    description: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ContentTemplate:
    """Template for creating content"""
    id: str
    name: str
    description: str
    content_structure: Dict[str, Any]  # JSON schema defining the template
    default_values: Dict[str, Any] = field(default_factory=dict)
    category: ContentCategory = ContentCategory.NEWS
    tags: List[ContentTag] = field(default_factory=list)
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True


@dataclass
class ContentItem:
    """A piece of content in the management system"""
    id: str
    title: str
    content: str
    content_type: ContentType
    status: ContentStatus
    category: ContentCategory
    tags: List[ContentTag] = field(default_factory=list)
    hashtags: List[str] = field(default_factory=list)
    media_attachments: List[MediaAsset] = field(default_factory=list)
    author: str = ""
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    published_at: Optional[datetime] = None
    scheduled_for: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    template_id: Optional[str] = None


@dataclass
class ContentModerationRule:
    """Rule for content moderation"""
    id: str
    name: str
    description: str
    rule_type: str  # "regex", "keyword", "length", "custom"
    rule_pattern: str  # Pattern to match against
    severity: str  # "warning", "error", "block"
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ContentModerationResult:
    """Result of content moderation"""
    is_approved: bool
    violations: List[str]
    warnings: List[str]
    suggestions: List[str]


class ContentStorageInterface:
    """Interface for content storage"""

    def save_content_item(self, item: ContentItem) -> bool:
        """Save a content item"""
        raise NotImplementedError

    def get_content_item(self, item_id: str) -> Optional[ContentItem]:
        """Get a content item by ID"""
        raise NotImplementedError

    def get_content_items(self,
                         status: Optional[ContentStatus] = None,
                         category: Optional[ContentCategory] = None,
                         author: Optional[str] = None,
                         limit: int = 50,
                         offset: int = 0) -> List[ContentItem]:
        """Get content items with optional filters"""
        raise NotImplementedError

    def save_content_template(self, template: ContentTemplate) -> bool:
        """Save a content template"""
        raise NotImplementedError

    def get_content_template(self, template_id: str) -> Optional[ContentTemplate]:
        """Get a content template by ID"""
        raise NotImplementedError

    def get_content_templates(self, active_only: bool = True) -> List[ContentTemplate]:
        """Get content templates"""
        raise NotImplementedError

    def save_moderation_rule(self, rule: ContentModerationRule) -> bool:
        """Save a moderation rule"""
        raise NotImplementedError

    def get_moderation_rules(self, enabled_only: bool = True) -> List[ContentModerationRule]:
        """Get moderation rules"""
        raise NotImplementedError


class SQLiteContentStorage(ContentStorageInterface):
    """SQLite-based content storage implementation"""

    def __init__(self, db_path: str = "./linkedin_content.db"):
        self.db_path = Path(db_path)
        self.lock = threading.Lock()
        self.init_db()

    def init_db(self):
        """Initialize the database tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Content items table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS content_items (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    content_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    category TEXT NOT NULL,
                    tags_json TEXT DEFAULT '[]',
                    hashtags_json TEXT DEFAULT '[]',
                    media_attachments_json TEXT DEFAULT '[]',
                    author TEXT,
                    created_by TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    published_at TIMESTAMP,
                    scheduled_for TIMESTAMP,
                    metadata_json TEXT DEFAULT '{}',
                    template_id TEXT,
                    created_at_index TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Content templates table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS content_templates (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    content_structure_json TEXT NOT NULL,
                    default_values_json TEXT DEFAULT '{}',
                    category TEXT NOT NULL,
                    tags_json TEXT DEFAULT '[]',
                    created_by TEXT,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    updated_at_index TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Content tags table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS content_tags (
                    id TEXT PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP NOT NULL
                )
            """)

            # Moderation rules table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS moderation_rules (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    rule_type TEXT NOT NULL,
                    rule_pattern TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    enabled BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP NOT NULL,
                    created_at_index TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_content_items_status ON content_items(status, created_at_index)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_content_items_category ON content_items(category, created_at_index)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_content_items_author ON content_items(author, created_at_index)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_content_items_scheduled ON content_items(scheduled_for)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_templates_active ON content_templates(is_active)")

            conn.commit()

    def save_content_item(self, item: ContentItem) -> bool:
        """Save a content item to the database"""
        try:
            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT OR REPLACE INTO content_items
                    (id, title, content, content_type, status, category,
                     tags_json, hashtags_json, media_attachments_json,
                     author, created_by, created_at, updated_at, published_at,
                     scheduled_for, metadata_json, template_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item.id, item.title, item.content, item.content_type.value,
                    item.status.value, item.category.value,
                    json.dumps([tag.__dict__ for tag in item.tags]),
                    json.dumps(item.hashtags),
                    json.dumps([{
                        'asset_id': asset.asset_id,
                        'media_type': asset.media_type.value,
                        'url': asset.url,
                        'alt_text': asset.alt_text,
                        'description': asset.description
                    } for asset in item.media_attachments]),
                    item.author, item.created_by,
                    item.created_at.isoformat() if isinstance(item.created_at, datetime) else item.created_at,
                    item.updated_at.isoformat() if isinstance(item.updated_at, datetime) else item.updated_at,
                    item.published_at.isoformat() if item.published_at else None,
                    item.scheduled_for.isoformat() if item.scheduled_for else None,
                    json.dumps(item.metadata),
                    item.template_id
                ))

                conn.commit()
                return True
        except Exception as e:
            logger.error("Failed to save content item", item_id=item.id, error=str(e))
            return False

    def get_content_item(self, item_id: str) -> Optional[ContentItem]:
        """Get a content item by ID"""
        try:
            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, title, content, content_type, status, category,
                           tags_json, hashtags_json, media_attachments_json,
                           author, created_by, created_at, updated_at, published_at,
                           scheduled_for, metadata_json, template_id
                    FROM content_items WHERE id = ?
                """, (item_id,))

                row = cursor.fetchone()
                if not row:
                    return None

                (id, title, content, content_type, status, category,
                 tags_json, hashtags_json, media_attachments_json,
                 author, created_by, created_at_str, updated_at_str, published_at_str,
                 scheduled_for_str, metadata_json, template_id) = row

                # Parse datetime strings
                created_at = datetime.fromisoformat(created_at_str) if created_at_str else datetime.now()
                updated_at = datetime.fromisoformat(updated_at_str) if updated_at_str else datetime.now()
                published_at = datetime.fromisoformat(published_at_str) if published_at_str else None
                scheduled_for = datetime.fromisoformat(scheduled_for_str) if scheduled_for_str else None

                # Parse JSON fields
                tags_data = json.loads(tags_json) if tags_json else []
                tags = [ContentTag(**tag_data) for tag_data in tags_data]

                hashtags = json.loads(hashtags_json) if hashtags_json else []

                media_attachments_data = json.loads(media_attachments_json) if media_attachments_json else []
                media_attachments = []
                for asset_data in media_attachments_data:
                    asset = MediaAsset(
                        asset_id=asset_data['asset_id'],
                        media_type=MediaType(asset_data['media_type']),
                        url=asset_data['url'],
                        alt_text=asset_data.get('alt_text'),
                        description=asset_data.get('description')
                    )
                    media_attachments.append(asset)

                metadata = json.loads(metadata_json) if metadata_json else {}

                return ContentItem(
                    id=id,
                    title=title,
                    content=content,
                    content_type=ContentType(content_type),
                    status=ContentStatus(status),
                    category=ContentCategory(category),
                    tags=tags,
                    hashtags=hashtags,
                    media_attachments=media_attachments,
                    author=author or "",
                    created_by=created_by,
                    created_at=created_at,
                    updated_at=updated_at,
                    published_at=published_at,
                    scheduled_for=scheduled_for,
                    metadata=metadata,
                    template_id=template_id
                )
        except Exception as e:
            logger.error("Failed to get content item", item_id=item_id, error=str(e))
            return None

    def get_content_items(self,
                         status: Optional[ContentStatus] = None,
                         category: Optional[ContentCategory] = None,
                         author: Optional[str] = None,
                         limit: int = 50,
                         offset: int = 0) -> List[ContentItem]:
        """Get content items with optional filters"""
        try:
            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                query = """
                    SELECT id, title, content, content_type, status, category,
                           tags_json, hashtags_json, media_attachments_json,
                           author, created_by, created_at, updated_at, published_at,
                           scheduled_for, metadata_json, template_id
                    FROM content_items
                    WHERE 1=1
                """
                params = []

                if status:
                    query += " AND status = ?"
                    params.append(status.value)

                if category:
                    query += " AND category = ?"
                    params.append(category.value)

                if author:
                    query += " AND author = ?"
                    params.append(author)

                query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])

                cursor.execute(query, params)

                items = []
                for row in cursor.fetchall():
                    (id, title, content, content_type, status, category,
                     tags_json, hashtags_json, media_attachments_json,
                     author, created_by, created_at_str, updated_at_str, published_at_str,
                     scheduled_for_str, metadata_json, template_id) = row

                    # Parse datetime strings
                    created_at = datetime.fromisoformat(created_at_str) if created_at_str else datetime.now()
                    updated_at = datetime.fromisoformat(updated_at_str) if updated_at_str else datetime.now()
                    published_at = datetime.fromisoformat(published_at_str) if published_at_str else None
                    scheduled_for = datetime.fromisoformat(scheduled_for_str) if scheduled_for_str else None

                    # Parse JSON fields
                    tags_data = json.loads(tags_json) if tags_json else []
                    tags = [ContentTag(**tag_data) for tag_data in tags_data]

                    hashtags = json.loads(hashtags_json) if hashtags_json else []

                    media_attachments_data = json.loads(media_attachments_json) if media_attachments_json else []
                    media_attachments = []
                    for asset_data in media_attachments_data:
                        asset = MediaAsset(
                            asset_id=asset_data['asset_id'],
                            media_type=MediaType(asset_data['media_type']),
                            url=asset_data['url'],
                            alt_text=asset_data.get('alt_text'),
                            description=asset_data.get('description')
                        )
                        media_attachments.append(asset)

                    metadata = json.loads(metadata_json) if metadata_json else {}

                    item = ContentItem(
                        id=id,
                        title=title,
                        content=content,
                        content_type=ContentType(content_type),
                        status=ContentStatus(status),
                        category=ContentCategory(category),
                        tags=tags,
                        hashtags=hashtags,
                        media_attachments=media_attachments,
                        author=author or "",
                        created_by=created_by,
                        created_at=created_at,
                        updated_at=updated_at,
                        published_at=published_at,
                        scheduled_for=scheduled_for,
                        metadata=metadata,
                        template_id=template_id
                    )
                    items.append(item)

                return items
        except Exception as e:
            logger.error("Failed to get content items", error=str(e))
            return []

    def save_content_template(self, template: ContentTemplate) -> bool:
        """Save a content template to the database"""
        try:
            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT OR REPLACE INTO content_templates
                    (id, name, description, content_structure_json, default_values_json,
                     category, tags_json, created_by, created_at, updated_at, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    template.id, template.name, template.description,
                    json.dumps(template.content_structure),
                    json.dumps(template.default_values),
                    template.category.value,
                    json.dumps([tag.__dict__ for tag in template.tags]),
                    template.created_by,
                    template.created_at.isoformat() if isinstance(template.created_at, datetime) else template.created_at,
                    template.updated_at.isoformat() if isinstance(template.updated_at, datetime) else template.updated_at,
                    template.is_active
                ))

                conn.commit()
                return True
        except Exception as e:
            logger.error("Failed to save content template", template_id=template.id, error=str(e))
            return False

    def get_content_template(self, template_id: str) -> Optional[ContentTemplate]:
        """Get a content template by ID"""
        try:
            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, name, description, content_structure_json, default_values_json,
                           category, tags_json, created_by, created_at, updated_at, is_active
                    FROM content_templates WHERE id = ?
                """, (template_id,))

                row = cursor.fetchone()
                if not row:
                    return None

                (id, name, description, content_structure_json, default_values_json,
                 category, tags_json, created_by, created_at_str, updated_at_str, is_active) = row

                # Parse datetime strings
                created_at = datetime.fromisoformat(created_at_str) if created_at_str else datetime.now()
                updated_at = datetime.fromisoformat(updated_at_str) if updated_at_str else datetime.now()

                # Parse JSON fields
                content_structure = json.loads(content_structure_json) if content_structure_json else {}
                default_values = json.loads(default_values_json) if default_values_json else {}

                tags_data = json.loads(tags_json) if tags_json else []
                tags = [ContentTag(**tag_data) for tag_data in tags_data]

                return ContentTemplate(
                    id=id,
                    name=name,
                    description=description,
                    content_structure=content_structure,
                    default_values=default_values,
                    category=ContentCategory(category),
                    tags=tags,
                    created_by=created_by,
                    created_at=created_at,
                    updated_at=updated_at,
                    is_active=is_active
                )
        except Exception as e:
            logger.error("Failed to get content template", template_id=template_id, error=str(e))
            return None

    def get_content_templates(self, active_only: bool = True) -> List[ContentTemplate]:
        """Get content templates"""
        try:
            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                query = "SELECT id, name, description, content_structure_json, default_values_json, category, tags_json, created_by, created_at, updated_at, is_active FROM content_templates"
                if active_only:
                    query += " WHERE is_active = 1"
                query += " ORDER BY created_at DESC"

                cursor.execute(query)

                templates = []
                for row in cursor.fetchall():
                    (id, name, description, content_structure_json, default_values_json,
                     category, tags_json, created_by, created_at_str, updated_at_str, is_active) = row

                    # Parse datetime strings
                    created_at = datetime.fromisoformat(created_at_str) if created_at_str else datetime.now()
                    updated_at = datetime.fromisoformat(updated_at_str) if updated_at_str else datetime.now()

                    # Parse JSON fields
                    content_structure = json.loads(content_structure_json) if content_structure_json else {}
                    default_values = json.loads(default_values_json) if default_values_json else {}

                    tags_data = json.loads(tags_json) if tags_json else []
                    tags = [ContentTag(**tag_data) for tag_data in tags_data]

                    template = ContentTemplate(
                        id=id,
                        name=name,
                        description=description,
                        content_structure=content_structure,
                        default_values=default_values,
                        category=ContentCategory(category),
                        tags=tags,
                        created_by=created_by,
                        created_at=created_at,
                        updated_at=updated_at,
                        is_active=is_active
                    )
                    templates.append(template)

                return templates
        except Exception as e:
            logger.error("Failed to get content templates", error=str(e))
            return []

    def save_moderation_rule(self, rule: ContentModerationRule) -> bool:
        """Save a moderation rule to the database"""
        try:
            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT OR REPLACE INTO moderation_rules
                    (id, name, description, rule_type, rule_pattern, severity, enabled, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    rule.id, rule.name, rule.description, rule.rule_type,
                    rule.rule_pattern, rule.severity, rule.enabled,
                    rule.created_at.isoformat() if isinstance(rule.created_at, datetime) else rule.created_at
                ))

                conn.commit()
                return True
        except Exception as e:
            logger.error("Failed to save moderation rule", rule_id=rule.id, error=str(e))
            return False

    def get_moderation_rules(self, enabled_only: bool = True) -> List[ContentModerationRule]:
        """Get moderation rules"""
        try:
            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                query = "SELECT id, name, description, rule_type, rule_pattern, severity, enabled, created_at FROM moderation_rules"
                if enabled_only:
                    query += " WHERE enabled = 1"
                query += " ORDER BY created_at DESC"

                cursor.execute(query)

                rules = []
                for row in cursor.fetchall():
                    (id, name, description, rule_type, rule_pattern, severity, enabled, created_at_str) = row

                    # Parse datetime string
                    created_at = datetime.fromisoformat(created_at_str) if created_at_str else datetime.now()

                    rule = ContentModerationRule(
                        id=id,
                        name=name,
                        description=description,
                        rule_type=rule_type,
                        rule_pattern=rule_pattern,
                        severity=severity,
                        enabled=enabled,
                        created_at=created_at
                    )
                    rules.append(rule)

                return rules
        except Exception as e:
            logger.error("Failed to get moderation rules", error=str(e))
            return []


class ContentModerationEngine:
    """Engine for moderating content based on rules"""

    def __init__(self, storage: ContentStorageInterface):
        self.storage = storage
        self.logger = logger.bind(component="ContentModerationEngine")

    def evaluate_content(self, content: Union[str, ContentItem]) -> ContentModerationResult:
        """Evaluate content against moderation rules"""
        # Get content text
        if isinstance(content, ContentItem):
            content_text = content.content
            hashtags = content.hashtags
        else:
            content_text = content
            hashtags = []

        violations = []
        warnings = []
        suggestions = []

        # Get all active moderation rules
        rules = self.storage.get_moderation_rules(enabled_only=True)

        for rule in rules:
            try:
                if rule.rule_type == "regex":
                    # Apply regex pattern
                    pattern = re.compile(rule.rule_pattern, re.IGNORECASE)
                    if pattern.search(content_text):
                        if rule.severity == "error":
                            violations.append(f"Content violates rule '{rule.name}': {rule.description}")
                        elif rule.severity == "warning":
                            warnings.append(f"Content flagged by rule '{rule.name}': {rule.description}")
                        else:  # block
                            violations.append(f"Content blocked by rule '{rule.name}': {rule.description}")

                elif rule.rule_type == "keyword":
                    # Check for specific keywords
                    keyword = rule.rule_pattern.lower()
                    if keyword in content_text.lower():
                        if rule.severity == "error":
                            violations.append(f"Content contains prohibited keyword '{keyword}'")
                        elif rule.severity == "warning":
                            warnings.append(f"Content contains keyword '{keyword}' that requires review")
                        else:  # block
                            violations.append(f"Content blocked for containing keyword '{keyword}'")

                elif rule.rule_type == "length":
                    # Check content length
                    try:
                        min_len, max_len = map(int, rule.rule_pattern.split('-'))
                        if len(content_text) < min_len or len(content_text) > max_len:
                            if rule.severity == "error":
                                violations.append(f"Content length ({len(content_text)}) outside allowed range ({rule.rule_pattern})")
                            elif rule.severity == "warning":
                                warnings.append(f"Content length ({len(content_text)}) is at boundary of allowed range ({rule.rule_pattern})")
                    except ValueError:
                        self.logger.warning("Invalid length rule format", rule_pattern=rule.rule_pattern)

                elif rule.rule_type == "hashtag_count":
                    # Check hashtag count
                    max_hashtags = int(rule.rule_pattern)
                    if len(hashtags) > max_hashtags:
                        if rule.severity == "error":
                            violations.append(f"Hashtag count ({len(hashtags)}) exceeds limit ({max_hashtags})")
                        elif rule.severity == "warning":
                            warnings.append(f"Hashtag count ({len(hashtags)}) is high, consider reducing")

            except Exception as e:
                self.logger.error("Error applying moderation rule", rule_id=rule.id, error=str(e))

        # Check for common issues
        if len(content_text.strip()) == 0:
            violations.append("Content cannot be empty")

        if len(content_text) > 3000:  # LinkedIn's character limit
            suggestions.append("Consider shortening content to under 3000 characters for better engagement")

        # Check for all caps (might be spam)
        if content_text.isupper() and len(content_text) > 10:
            warnings.append("Content is in all caps, which may appear as spam")

        is_approved = len(violations) == 0

        result = ContentModerationResult(
            is_approved=is_approved,
            violations=violations,
            warnings=warnings,
            suggestions=suggestions
        )

        self.logger.info("Content moderation completed",
                         content_length=len(content_text),
                         violations=len(violations),
                         warnings=len(warnings))

        return result

    def add_moderation_rule(self, name: str, description: str, rule_type: str,
                          rule_pattern: str, severity: str = "warning") -> bool:
        """Add a new moderation rule"""
        rule = ContentModerationRule(
            id=f"rule_{uuid4().hex[:8]}",
            name=name,
            description=description,
            rule_type=rule_type,
            rule_pattern=rule_pattern,
            severity=severity
        )
        return self.storage.save_moderation_rule(rule)


class ContentManager:
    """Main content management system"""

    def __init__(self, storage: ContentStorageInterface = None):
        self.storage = storage or SQLiteContentStorage()
        self.moderation_engine = ContentModerationEngine(self.storage)
        self.logger = logger.bind(component="ContentManager")

    def create_content_item(self,
                           title: str,
                           content: str,
                           content_type: ContentType,
                           category: ContentCategory,
                           author: str,
                           hashtags: List[str] = None,
                           media_attachments: List[MediaAsset] = None,
                           template_id: Optional[str] = None) -> Optional[ContentItem]:
        """Create a new content item"""
        item_id = f"content_{uuid4().hex[:8]}"

        item = ContentItem(
            id=item_id,
            title=title,
            content=content,
            content_type=content_type,
            status=ContentStatus.DRAFT,
            category=category,
            hashtags=hashtags or [],
            media_attachments=media_attachments or [],
            author=author,
            created_by=author,
            template_id=template_id
        )

        if self.storage.save_content_item(item):
            self.logger.info("Content item created", item_id=item_id, title=title)
            return item
        else:
            self.logger.error("Failed to create content item", title=title)
            return None

    def update_content_item(self, item_id: str, **updates) -> bool:
        """Update a content item"""
        item = self.storage.get_content_item(item_id)
        if not item:
            return False

        # Apply updates
        for key, value in updates.items():
            if hasattr(item, key):
                setattr(item, key, value)

        # Update timestamp
        item.updated_at = datetime.now()

        success = self.storage.save_content_item(item)
        if success:
            self.logger.info("Content item updated", item_id=item_id)
        else:
            self.logger.error("Failed to update content item", item_id=item_id)

        return success

    def submit_content_for_review(self, item_id: str, submitter: str) -> bool:
        """Submit content for review/approval"""
        item = self.storage.get_content_item(item_id)
        if not item:
            return False

        if item.status != ContentStatus.DRAFT:
            self.logger.error("Only draft content can be submitted for review", item_id=item_id, status=item.status.value)
            return False

        # Moderate the content first
        moderation_result = self.moderation_engine.evaluate_content(item)
        if not moderation_result.is_approved:
            self.logger.warning("Content failed moderation", item_id=item_id, violations=moderation_result.violations)
            # We could either reject or allow submission with warnings
            # For now, we'll allow submission but log the issues
            for violation in moderation_result.violations:
                self.logger.warning("Moderation violation", item_id=item_id, violation=violation)

        # Update status to review
        item.status = ContentStatus.REVIEW
        item.updated_at = datetime.now()

        success = self.storage.save_content_item(item)
        if success:
            self.logger.info("Content submitted for review", item_id=item_id, submitter=submitter)
        else:
            self.logger.error("Failed to submit content for review", item_id=item_id)

        return success

    def approve_content(self, item_id: str, approver: str) -> bool:
        """Approve content for publishing"""
        item = self.storage.get_content_item(item_id)
        if not item:
            return False

        if item.status != ContentStatus.REVIEW:
            self.logger.error("Only review content can be approved", item_id=item_id, status=item.status.value)
            return False

        item.status = ContentStatus.APPROVED
        item.updated_at = datetime.now()

        success = self.storage.save_content_item(item)
        if success:
            self.logger.info("Content approved", item_id=item_id, approver=approver)
        else:
            self.logger.error("Failed to approve content", item_id=item_id)

        return success

    def create_content_from_template(self, template_id: str, fill_data: Dict[str, Any],
                                   author: str, title: str = None) -> Optional[ContentItem]:
        """Create content from a template"""
        template = self.storage.get_content_template(template_id)
        if not template:
            self.logger.error("Template not found", template_id=template_id)
            return None

        # Generate content from template and fill data
        try:
            # This is a simplified template filling approach
            # In a real implementation, this would be more sophisticated
            if 'template_content' in template.default_values:
                content = template.default_values['template_content']
            else:
                content = template.description  # Fallback

            # Replace placeholders in content
            for key, value in fill_data.items():
                placeholder = f"{{{key}}}"
                content = content.replace(placeholder, str(value))

            # Use template title if no title provided
            if not title:
                title = template.name

            # Create content item
            item = ContentItem(
                id=f"content_{uuid4().hex[:8]}",
                title=title,
                content=content,
                content_type=ContentType.POST,  # Default to post
                status=ContentStatus.DRAFT,
                category=template.category,
                hashtags=fill_data.get('hashtags', []),
                author=author,
                created_by=author,
                template_id=template_id
            )

            if self.storage.save_content_item(item):
                self.logger.info("Content created from template", item_id=item.id, template_id=template_id)
                return item
            else:
                self.logger.error("Failed to create content from template", template_id=template_id)
                return None

        except Exception as e:
            self.logger.error("Error creating content from template", template_id=template_id, error=str(e))
            return None

    def create_content_template(self, name: str, description: str,
                              content_structure: Dict[str, Any],
                              category: ContentCategory,
                              created_by: str) -> Optional[ContentTemplate]:
        """Create a new content template"""
        template_id = f"tmpl_{uuid4().hex[:8]}"

        template = ContentTemplate(
            id=template_id,
            name=name,
            description=description,
            content_structure=content_structure,
            category=category,
            created_by=created_by
        )

        if self.storage.save_content_template(template):
            self.logger.info("Content template created", template_id=template_id, name=name)
            return template
        else:
            self.logger.error("Failed to create content template", name=name)
            return None

    def search_content(self, query: str, limit: int = 10) -> List[ContentItem]:
        """Search content by text query"""
        try:
            # Get all content items and filter by query
            all_items = self.storage.get_content_items(limit=1000)  # Get a large set to search
            query_lower = query.lower()

            matching_items = []
            for item in all_items:
                if (query_lower in item.title.lower() or
                    query_lower in item.content.lower() or
                    query_lower in ' '.join(item.hashtags).lower()):
                    matching_items.append(item)

                if len(matching_items) >= limit:
                    break  # Limit results

            self.logger.info("Content search completed", query=query, results=len(matching_items))
            return matching_items
        except Exception as e:
            self.logger.error("Error searching content", query=query, error=str(e))
            return []

    def get_content_calendar(self, start_date: datetime, end_date: datetime) -> List[ContentItem]:
        """Get scheduled content for a date range"""
        try:
            all_items = self.storage.get_content_items()
            calendar_items = []

            for item in all_items:
                if (item.scheduled_for and
                    start_date <= item.scheduled_for <= end_date and
                    item.status in [ContentStatus.APPROVED, ContentStatus.PUBLISHED]):
                    calendar_items.append(item)

            # Sort by scheduled date
            calendar_items.sort(key=lambda x: x.scheduled_for or x.created_at)

            self.logger.info("Content calendar retrieved",
                           start_date=start_date,
                           end_date=end_date,
                           items=len(calendar_items))
            return calendar_items
        except Exception as e:
            self.logger.error("Error getting content calendar", start_date=start_date, end_date=end_date, error=str(e))
            return []

    def get_content_statistics(self) -> Dict[str, Any]:
        """Get content statistics"""
        try:
            all_items = self.storage.get_content_items()

            stats = {
                'total_content': len(all_items),
                'by_status': {},
                'by_category': {},
                'by_content_type': {},
                'by_month': {}
            }

            for item in all_items:
                # Count by status
                status = item.status.value
                stats['by_status'][status] = stats['by_status'].get(status, 0) + 1

                # Count by category
                category = item.category.value
                stats['by_category'][category] = stats['by_category'].get(category, 0) + 1

                # Count by content type
                ctype = item.content_type.value
                stats['by_content_type'][ctype] = stats['by_content_type'].get(ctype, 0) + 1

                # Count by month
                month_key = item.created_at.strftime('%Y-%m')
                stats['by_month'][month_key] = stats['by_month'].get(month_key, 0) + 1

            return stats
        except Exception as e:
            self.logger.error("Error getting content statistics", error=str(e))
            return {}


# Convenience functions
def create_content_manager(storage_path: str = "./linkedin_content.db") -> ContentManager:
    """Create and return a configured content manager"""
    storage = SQLiteContentStorage(storage_path)
    return ContentManager(storage)


def demo_content_management():
    """Demo function to show content management usage"""
    print("Content Management Demo")
    print("=" * 40)

    # Create content manager
    cm = create_content_manager()

    print("Content manager created successfully")

    # Example usage:
    print("\nExample usage:")
    print("# Create a content item")
    print("content_item = cm.create_content_item(")
    print("    title='New Product Launch',")
    print("    content='We are excited to announce our new product...',")
    print("    content_type=ContentType.POST,")
    print("    category=ContentCategory.ANNOUNCEMENTS,")
    print("    author='marketing_team',")
    print("    hashtags=['#NewProduct', '#Innovation']")
    print(")")

    print("\n# Submit content for review")
    print("cm.submit_content_for_review(content_item.id, 'content_creator')")

    print("\n# Create a content template")
    print("template = cm.create_content_template(")
    print("    name='Weekly Update Template',")
    print("    description='Template for weekly company updates',")
    print("    content_structure={'sections': ['headline', 'summary', 'call_to_action']},")
    print("    category=ContentCategory.NEWS,")
    print("    created_by='admin'")
    print(")")

    print("\n# Create content from template")
    print("weekly_update = cm.create_content_from_template(")
    print("    template_id=template.id,")
    print("    fill_data={")
    print("        'week_number': '42',")
    print("        'headline': 'This Week in Review',")
    print("        'highlights': 'Major milestone reached'")
    print("    },")
    print("    author='comms_team'")
    print(")")

    print("\n# Search content")
    print("results = cm.search_content('innovation')")
    print(f"Found {len(results)} matching items")

    print("\n# Get content calendar")
    print("from datetime import datetime, timedelta")
    print("start = datetime.now()")
    print("end = start + timedelta(days=30)")
    print("calendar = cm.get_content_calendar(start, end)")
    print(f"Calendar has {len(calendar)} scheduled items")


if __name__ == "__main__":
    demo_content_management()