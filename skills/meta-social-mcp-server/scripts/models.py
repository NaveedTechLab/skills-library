#!/usr/bin/env python3
"""
Data models for Meta Social MCP Server

Pydantic models for Facebook and Instagram API operations.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MediaType(str, Enum):
    """Types of media for posts"""
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
    CAROUSEL = "CAROUSEL"
    REEL = "REELS"


class PostStatus(str, Enum):
    """Status of a social media post"""
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    FAILED = "failed"


class ApprovalStatus(str, Enum):
    """Approval status for HITL workflow"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class MetaConfig(BaseModel):
    """Configuration for Meta API connection"""
    app_id: str = Field(default="", description="Meta App ID")
    app_secret: str = Field(default="", description="Meta App Secret")
    access_token: str = Field(default="", description="Long-lived access token")
    page_id: str = Field(default="", description="Default Facebook Page ID")
    instagram_account_id: str = Field(default="", description="Instagram Business Account ID")
    api_version: str = Field(default="v21.0", description="Graph API version")
    timeout_seconds: int = Field(default=30, description="Request timeout")

    # Approval settings
    require_approval_for_posts: bool = Field(default=True, description="Require approval for posts")
    require_approval_for_reels: bool = Field(default=True, description="Require approval for reels")
    approval_timeout_hours: int = Field(default=48, description="Approval timeout")

    # Content limits
    max_text_length: int = Field(default=63206, description="Max text length")
    max_hashtags: int = Field(default=30, description="Max hashtags")
    max_images_carousel: int = Field(default=10, description="Max images in carousel")

    class Config:
        extra = "allow"


class FacebookPage(BaseModel):
    """Facebook Page information"""
    id: str
    name: str
    access_token: Optional[str] = None
    category: Optional[str] = None
    category_list: List[Dict[str, str]] = Field(default_factory=list)
    followers_count: Optional[int] = None
    fan_count: Optional[int] = None


class MediaAsset(BaseModel):
    """Media asset for posts"""
    url: str = Field(..., description="Media URL")
    media_type: MediaType = Field(default=MediaType.IMAGE, description="Media type")
    alt_text: Optional[str] = Field(default=None, description="Alt text")
    thumbnail_url: Optional[str] = Field(default=None, description="Thumbnail URL for video")


class FacebookPost(BaseModel):
    """Facebook post model"""
    id: Optional[str] = None
    page_id: str = Field(..., description="Page ID")
    message: str = Field(default="", description="Post message")
    link: Optional[str] = Field(default=None, description="URL to share")
    media_assets: List[MediaAsset] = Field(default_factory=list, description="Media attachments")
    scheduled_publish_time: Optional[datetime] = Field(default=None, description="Scheduled time")
    status: PostStatus = Field(default=PostStatus.DRAFT, description="Post status")
    created_time: Optional[datetime] = Field(default=None, description="Creation time")
    published: bool = Field(default=False, description="Is published")

    # Engagement metrics
    likes_count: int = Field(default=0)
    comments_count: int = Field(default=0)
    shares_count: int = Field(default=0)
    reach: int = Field(default=0)

    def to_graph_api_params(self) -> Dict[str, Any]:
        """Convert to Graph API parameters"""
        params = {}
        if self.message:
            params["message"] = self.message
        if self.link:
            params["link"] = self.link
        if self.scheduled_publish_time:
            params["scheduled_publish_time"] = int(self.scheduled_publish_time.timestamp())
            params["published"] = False
        return params


class InstagramPost(BaseModel):
    """Instagram post model"""
    id: Optional[str] = None
    account_id: str = Field(..., description="Instagram Business Account ID")
    caption: str = Field(default="", description="Post caption")
    media_type: MediaType = Field(default=MediaType.IMAGE, description="Media type")
    media_url: Optional[str] = Field(default=None, description="Media URL")
    media_urls: List[str] = Field(default_factory=list, description="URLs for carousel")
    location_id: Optional[str] = Field(default=None, description="Location ID")
    status: PostStatus = Field(default=PostStatus.DRAFT, description="Post status")
    created_time: Optional[datetime] = Field(default=None)
    permalink: Optional[str] = Field(default=None, description="Post permalink")

    # Engagement metrics
    likes_count: int = Field(default=0)
    comments_count: int = Field(default=0)
    reach: int = Field(default=0)
    impressions: int = Field(default=0)


class InstagramReel(BaseModel):
    """Instagram Reel model"""
    id: Optional[str] = None
    account_id: str = Field(..., description="Instagram Business Account ID")
    video_url: str = Field(..., description="Video URL")
    caption: str = Field(default="", description="Reel caption")
    share_to_feed: bool = Field(default=True, description="Also share to feed")
    cover_url: Optional[str] = Field(default=None, description="Cover image URL")
    status: PostStatus = Field(default=PostStatus.DRAFT)
    created_time: Optional[datetime] = Field(default=None)
    permalink: Optional[str] = Field(default=None)

    # Engagement metrics
    plays_count: int = Field(default=0)
    likes_count: int = Field(default=0)
    comments_count: int = Field(default=0)
    reach: int = Field(default=0)


class PageInsights(BaseModel):
    """Facebook Page insights"""
    page_id: str
    period: str = "day"
    metrics: Dict[str, Any] = Field(default_factory=dict)
    date_range: Dict[str, str] = Field(default_factory=dict)


class InstagramInsights(BaseModel):
    """Instagram account insights"""
    account_id: str
    period: str = "day"
    metrics: Dict[str, Any] = Field(default_factory=dict)
    date_range: Dict[str, str] = Field(default_factory=dict)


class ApprovalRequest(BaseModel):
    """Approval request for HITL workflow"""
    id: str = Field(..., description="Unique approval request ID")
    platform: str = Field(..., description="facebook or instagram")
    operation: str = Field(..., description="Operation type")
    content_type: str = Field(default="post", description="post, reel, story")
    data: Dict[str, Any] = Field(default_factory=dict, description="Post data")
    preview_url: Optional[str] = Field(default=None, description="Preview URL")
    status: ApprovalStatus = Field(default=ApprovalStatus.PENDING)
    requested_by: str = Field(default="claude")
    requested_at: datetime = Field(default_factory=datetime.now)
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    expires_at: Optional[datetime] = None
    context: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "platform": self.platform,
            "operation": self.operation,
            "content_type": self.content_type,
            "data": self.data,
            "preview_url": self.preview_url,
            "status": self.status.value,
            "requested_by": self.requested_by,
            "requested_at": self.requested_at.isoformat() if self.requested_at else None,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "rejection_reason": self.rejection_reason,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "context": self.context,
        }


class GraphAPIError(BaseModel):
    """Meta Graph API error response"""
    code: int
    message: str
    type: Optional[str] = None
    error_subcode: Optional[int] = None
    fbtrace_id: Optional[str] = None
