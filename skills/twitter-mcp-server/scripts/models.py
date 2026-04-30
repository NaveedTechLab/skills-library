#!/usr/bin/env python3
"""
Data models for Twitter MCP Server

Pydantic models for X API v2 operations.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


class MediaType(str, Enum):
    """Twitter media types"""
    IMAGE = "image"
    VIDEO = "video"
    GIF = "animated_gif"


class TweetType(str, Enum):
    """Types of tweets"""
    TWEET = "tweet"
    REPLY = "reply"
    QUOTE = "quote"
    THREAD = "thread"


class ApprovalStatus(str, Enum):
    """Approval status"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class TwitterConfig(BaseModel):
    """Configuration for Twitter API"""
    client_id: str = Field(default="", description="OAuth 2.0 Client ID")
    client_secret: str = Field(default="", description="OAuth 2.0 Client Secret")
    access_token: str = Field(default="", description="Access Token")
    access_token_secret: str = Field(default="", description="Access Token Secret")
    bearer_token: str = Field(default="", description="Bearer Token for app-only auth")
    api_version: str = Field(default="2", description="API version")
    timeout_seconds: int = Field(default=30, description="Request timeout")

    # Approval settings
    require_approval_for_tweets: bool = Field(default=True)
    require_approval_for_threads: bool = Field(default=True)
    require_approval_for_delete: bool = Field(default=True)
    approval_timeout_hours: int = Field(default=24)

    # Rate limiting
    enable_rate_tracking: bool = Field(default=True)
    warn_at_percentage: int = Field(default=80)
    block_at_percentage: int = Field(default=95)

    class Config:
        extra = "allow"


class Tweet(BaseModel):
    """Twitter tweet model"""
    id: Optional[str] = None
    text: str = Field(..., max_length=280, description="Tweet text")
    author_id: Optional[str] = None
    conversation_id: Optional[str] = None
    created_at: Optional[datetime] = None
    reply_to_tweet_id: Optional[str] = Field(default=None, description="Tweet ID to reply to")
    quote_tweet_id: Optional[str] = Field(default=None, description="Tweet ID to quote")
    media_ids: List[str] = Field(default_factory=list, description="Media IDs to attach")
    poll_options: List[str] = Field(default_factory=list, description="Poll options")
    poll_duration_minutes: Optional[int] = Field(default=None, description="Poll duration")

    # Metrics
    retweet_count: int = Field(default=0)
    reply_count: int = Field(default=0)
    like_count: int = Field(default=0)
    quote_count: int = Field(default=0)
    impression_count: int = Field(default=0)

    @validator("text")
    def validate_text_length(cls, v):
        if len(v) > 280:
            raise ValueError("Tweet text cannot exceed 280 characters")
        return v

    def to_api_payload(self) -> Dict[str, Any]:
        """Convert to X API v2 payload"""
        payload = {"text": self.text}

        if self.reply_to_tweet_id:
            payload["reply"] = {"in_reply_to_tweet_id": self.reply_to_tweet_id}

        if self.quote_tweet_id:
            payload["quote_tweet_id"] = self.quote_tweet_id

        if self.media_ids:
            payload["media"] = {"media_ids": self.media_ids}

        if self.poll_options and len(self.poll_options) >= 2:
            payload["poll"] = {
                "options": self.poll_options,
                "duration_minutes": self.poll_duration_minutes or 1440
            }

        return payload


class TweetThread(BaseModel):
    """A thread of connected tweets"""
    id: Optional[str] = None
    tweets: List[Tweet] = Field(..., min_items=2, description="Tweets in thread")
    created_at: Optional[datetime] = None

    @validator("tweets")
    def validate_thread_length(cls, v):
        if len(v) < 2:
            raise ValueError("Thread must have at least 2 tweets")
        if len(v) > 25:
            raise ValueError("Thread cannot exceed 25 tweets")
        return v


class MediaUpload(BaseModel):
    """Media upload model"""
    media_id: Optional[str] = None
    media_key: Optional[str] = None
    media_type: MediaType = Field(default=MediaType.IMAGE)
    url: Optional[str] = Field(default=None, description="Source URL")
    alt_text: Optional[str] = Field(default=None, max_length=1000)
    width: Optional[int] = None
    height: Optional[int] = None
    duration_ms: Optional[int] = None  # For video
    upload_status: str = Field(default="pending")


class RateLimitInfo(BaseModel):
    """Rate limit information"""
    endpoint: str
    limit: int
    remaining: int
    reset_at: datetime
    used: int = 0

    @property
    def percentage_used(self) -> float:
        return (self.used / self.limit) * 100 if self.limit > 0 else 0

    @property
    def seconds_until_reset(self) -> int:
        delta = self.reset_at - datetime.now()
        return max(0, int(delta.total_seconds()))


class ApprovalRequest(BaseModel):
    """Approval request for HITL workflow"""
    id: str = Field(..., description="Unique approval request ID")
    operation: str = Field(..., description="Operation type")
    tweet_type: TweetType = Field(default=TweetType.TWEET)
    data: Dict[str, Any] = Field(default_factory=dict)
    character_count: int = Field(default=0)
    media_count: int = Field(default=0)
    status: ApprovalStatus = Field(default=ApprovalStatus.PENDING)
    requested_by: str = Field(default="claude")
    requested_at: datetime = Field(default_factory=datetime.now)
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    expires_at: Optional[datetime] = None
    context: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "operation": self.operation,
            "tweet_type": self.tweet_type.value,
            "data": self.data,
            "character_count": self.character_count,
            "media_count": self.media_count,
            "status": self.status.value,
            "requested_by": self.requested_by,
            "requested_at": self.requested_at.isoformat() if self.requested_at else None,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "rejection_reason": self.rejection_reason,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "context": self.context,
        }


class TwitterAPIResponse(BaseModel):
    """Standard API response wrapper"""
    data: Optional[Dict[str, Any]] = None
    includes: Optional[Dict[str, Any]] = None
    errors: Optional[List[Dict[str, Any]]] = None
    meta: Optional[Dict[str, Any]] = None


class TwitterError(BaseModel):
    """Twitter API error"""
    code: int
    message: str
    type: Optional[str] = None
    detail: Optional[str] = None
