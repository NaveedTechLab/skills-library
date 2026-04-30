#!/usr/bin/env python3
"""
Twitter (X) MCP Server

FastMCP server providing X API v2 integration with HITL controls.
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

try:
    from fastmcp import FastMCP
except ImportError:
    print("fastmcp not installed. Install with: pip install fastmcp")
    sys.exit(1)

from .approval_workflow import TwitterApprovalWorkflow
from .models import ApprovalStatus, MediaType, Tweet, TweetThread, TweetType, TwitterConfig
from .twitter_api_client import TwitterAPIClient, TwitterAPIError

logger = structlog.get_logger()

# Initialize FastMCP server
mcp = FastMCP("Twitter MCP Server")

# Global instances
_config: Optional[TwitterConfig] = None
_client: Optional[TwitterAPIClient] = None
_workflow: Optional[TwitterApprovalWorkflow] = None


def get_config() -> TwitterConfig:
    global _config
    if _config is None:
        _config = TwitterConfig()
    return _config


def get_workflow() -> TwitterApprovalWorkflow:
    global _workflow
    if _workflow is None:
        _workflow = TwitterApprovalWorkflow(get_config())
    return _workflow


async def get_client() -> TwitterAPIClient:
    global _client
    if _client is None:
        _client = TwitterAPIClient(get_config())
    return _client


# ========== Tweet Tools ==========

@mcp.tool()
async def twitter_create_tweet(
    text: str,
    reply_to: str = None,
    quote_tweet_id: str = None,
    media_ids: List[str] = None
) -> Dict[str, Any]:
    """
    Create a single tweet.

    HITL: Always requires approval.

    Args:
        text: Tweet text (max 280 characters)
        reply_to: Tweet ID to reply to (optional)
        quote_tweet_id: Tweet ID to quote (optional)
        media_ids: Media IDs to attach (optional, from twitter_upload_media)

    Returns:
        Approval request ID

    Example:
        twitter_create_tweet(
            text="Hello Twitter! This is an automated tweet.",
            media_ids=["1234567890"]
        )
    """
    try:
        # Validate text length
        if len(text) > 280:
            return {
                "success": False,
                "error": f"Tweet text exceeds 280 characters ({len(text)} chars)"
            }

        workflow = get_workflow()

        request = workflow.create_approval_request(
            operation="create_tweet",
            tweet_type=TweetType.REPLY if reply_to else (TweetType.QUOTE if quote_tweet_id else TweetType.TWEET),
            data={
                "text": text,
                "reply_to": reply_to,
                "quote_tweet_id": quote_tweet_id,
                "media_ids": media_ids or []
            },
            character_count=len(text),
            media_count=len(media_ids or []),
            context={"preview": text[:100]}
        )

        return {
            "success": True,
            "requires_approval": True,
            "approval_request_id": request.id,
            "character_count": len(text),
            "message": f"Tweet requires approval. Request ID: {request.id}"
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
async def twitter_create_thread(
    tweets: List[str],
    media_ids_per_tweet: List[List[str]] = None
) -> Dict[str, Any]:
    """
    Post a thread of connected tweets.

    HITL: Always requires approval.

    Args:
        tweets: List of tweet texts (2-25 tweets)
        media_ids_per_tweet: Optional media IDs for each tweet

    Returns:
        Approval request ID

    Example:
        twitter_create_thread(
            tweets=[
                "1/3 Here's an important announcement...",
                "2/3 More details about the announcement...",
                "3/3 And that's a wrap!"
            ]
        )
    """
    try:
        # Validate thread
        if len(tweets) < 2:
            return {"success": False, "error": "Thread must have at least 2 tweets"}
        if len(tweets) > 25:
            return {"success": False, "error": "Thread cannot exceed 25 tweets"}

        # Validate each tweet
        for i, text in enumerate(tweets):
            if len(text) > 280:
                return {
                    "success": False,
                    "error": f"Tweet {i+1} exceeds 280 characters ({len(text)} chars)"
                }

        total_chars = sum(len(t) for t in tweets)
        total_media = sum(len(m) for m in (media_ids_per_tweet or []))

        workflow = get_workflow()

        # Build thread data
        thread_data = []
        for i, text in enumerate(tweets):
            tweet_data = {"text": text}
            if media_ids_per_tweet and i < len(media_ids_per_tweet):
                tweet_data["media_ids"] = media_ids_per_tweet[i]
            thread_data.append(tweet_data)

        request = workflow.create_approval_request(
            operation="create_thread",
            tweet_type=TweetType.THREAD,
            data={"tweets": thread_data},
            character_count=total_chars,
            media_count=total_media,
            context={
                "tweet_count": len(tweets),
                "preview": tweets[0][:100]
            }
        )

        return {
            "success": True,
            "requires_approval": True,
            "approval_request_id": request.id,
            "tweet_count": len(tweets),
            "total_characters": total_chars,
            "message": f"Thread requires approval. Request ID: {request.id}"
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
async def twitter_upload_media(
    media_url: str,
    media_type: str = "image",
    alt_text: str = None
) -> Dict[str, Any]:
    """
    Upload media for use in tweets.

    No HITL required - media upload itself doesn't publish anything.

    Args:
        media_url: Public URL to media file
        media_type: image, video, or gif
        alt_text: Accessibility alt text (max 1000 chars)

    Returns:
        Media ID for use in tweets

    Example:
        twitter_upload_media(
            media_url="https://example.com/image.jpg",
            media_type="image",
            alt_text="A beautiful sunset over the ocean"
        )
    """
    try:
        if alt_text and len(alt_text) > 1000:
            return {"success": False, "error": "Alt text cannot exceed 1000 characters"}

        client = await get_client()
        async with client:
            result = await client.upload_media(
                media_url=media_url,
                media_type=MediaType(media_type),
                alt_text=alt_text
            )

        return {
            "success": True,
            "media_id": result.media_id,
            "media_type": result.media_type.value,
            "upload_status": result.upload_status,
            "message": f"Media uploaded. Use media_id '{result.media_id}' in tweets."
        }

    except TwitterAPIError as e:
        return {"success": False, "error": str(e), "code": e.code}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
async def twitter_delete_tweet(tweet_id: str) -> Dict[str, Any]:
    """
    Delete a tweet.

    HITL: Always requires approval.

    Args:
        tweet_id: ID of the tweet to delete

    Returns:
        Approval request ID

    Example:
        twitter_delete_tweet(tweet_id="1234567890123456789")
    """
    try:
        workflow = get_workflow()

        request = workflow.create_approval_request(
            operation="delete_tweet",
            tweet_type=TweetType.TWEET,
            data={"tweet_id": tweet_id},
            context={"action": "delete"}
        )

        return {
            "success": True,
            "requires_approval": True,
            "approval_request_id": request.id,
            "tweet_id": tweet_id,
            "message": f"Tweet deletion requires approval. Request ID: {request.id}"
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
async def twitter_get_tweet(
    tweet_id: str,
    include_metrics: bool = True
) -> Dict[str, Any]:
    """
    Get tweet details and metrics.

    No HITL required - read-only operation.

    Args:
        tweet_id: Tweet ID
        include_metrics: Include engagement metrics

    Returns:
        Tweet data and metrics

    Example:
        twitter_get_tweet(tweet_id="1234567890123456789")
    """
    try:
        client = await get_client()
        async with client:
            tweet_fields = ["id", "text", "created_at", "author_id"]
            if include_metrics:
                tweet_fields.extend(["public_metrics"])

            tweet = await client.get_tweet(tweet_id, tweet_fields=tweet_fields)

        return {
            "success": True,
            "tweet": tweet
        }

    except TwitterAPIError as e:
        return {"success": False, "error": str(e), "code": e.code}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
async def twitter_get_rate_limits(endpoint: str = None) -> Dict[str, Any]:
    """
    Check current API rate limit status.

    No HITL required - informational only.

    Args:
        endpoint: Specific endpoint to check (optional)

    Returns:
        Rate limit information

    Example:
        twitter_get_rate_limits()
        twitter_get_rate_limits(endpoint="tweets/create")
    """
    try:
        client = await get_client()
        limits = client.get_rate_limits(endpoint)

        return {
            "success": True,
            "rate_limits": limits
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


# ========== Approval Tools ==========

@mcp.tool()
async def twitter_execute_approved_request(approval_request_id: str) -> Dict[str, Any]:
    """
    Execute an approved Twitter operation.

    This publishes the tweet/thread after human approval.

    Args:
        approval_request_id: The approval request ID to execute

    Returns:
        Execution result with tweet ID(s)

    Example:
        twitter_execute_approved_request("twitter_approval_abc123")
    """
    try:
        workflow = get_workflow()
        request = workflow.get_request(approval_request_id)

        if not request:
            return {"success": False, "error": "Request not found"}

        if request.status != ApprovalStatus.APPROVED:
            return {
                "success": False,
                "error": f"Request not approved. Status: {request.status.value}"
            }

        client = await get_client()
        async with client:
            if request.operation == "create_tweet":
                data = request.data
                tweet = Tweet(
                    text=data["text"],
                    reply_to_tweet_id=data.get("reply_to"),
                    quote_tweet_id=data.get("quote_tweet_id"),
                    media_ids=data.get("media_ids", [])
                )
                tweet_id = await client.create_tweet(tweet)

                return {
                    "success": True,
                    "operation": "create_tweet",
                    "tweet_id": tweet_id,
                    "message": f"Tweet posted with ID: {tweet_id}"
                }

            elif request.operation == "create_thread":
                tweets_data = request.data.get("tweets", [])
                tweets = []
                for t in tweets_data:
                    tweets.append(Tweet(
                        text=t["text"],
                        media_ids=t.get("media_ids", [])
                    ))

                thread = TweetThread(tweets=tweets)
                tweet_ids = await client.create_thread(thread)

                return {
                    "success": True,
                    "operation": "create_thread",
                    "tweet_ids": tweet_ids,
                    "tweet_count": len(tweet_ids),
                    "message": f"Thread posted with {len(tweet_ids)} tweets"
                }

            elif request.operation == "delete_tweet":
                tweet_id = request.data.get("tweet_id")
                deleted = await client.delete_tweet(tweet_id)

                return {
                    "success": True,
                    "operation": "delete_tweet",
                    "tweet_id": tweet_id,
                    "deleted": deleted,
                    "message": f"Tweet {tweet_id} deleted"
                }

            else:
                return {"success": False, "error": f"Unknown operation: {request.operation}"}

    except TwitterAPIError as e:
        return {"success": False, "error": str(e), "code": e.code}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
async def twitter_get_pending_approvals() -> Dict[str, Any]:
    """
    Get all pending approval requests.

    Returns:
        List of pending approval requests

    Example:
        twitter_get_pending_approvals()
    """
    try:
        workflow = get_workflow()
        requests = workflow.get_pending_requests()

        return {
            "success": True,
            "count": len(requests),
            "requests": [r.to_dict() for r in requests]
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
async def twitter_approve_request(
    approval_request_id: str,
    approved_by: str = "human"
) -> Dict[str, Any]:
    """
    Approve a pending tweet request.

    Args:
        approval_request_id: Request to approve
        approved_by: Approver identifier

    Returns:
        Approval status

    Example:
        twitter_approve_request("twitter_approval_abc123")
    """
    try:
        workflow = get_workflow()
        request = workflow.approve_request(approval_request_id, approved_by)

        if not request:
            return {"success": False, "error": "Request not found or already processed"}

        return {
            "success": True,
            "request_id": request.id,
            "status": request.status.value,
            "approved_by": request.approved_by,
            "message": "Approved. Use twitter_execute_approved_request to post."
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
async def twitter_reject_request(
    approval_request_id: str,
    rejected_by: str = "human",
    reason: str = None
) -> Dict[str, Any]:
    """
    Reject a pending tweet request.

    Args:
        approval_request_id: Request to reject
        rejected_by: Rejector identifier
        reason: Rejection reason

    Returns:
        Rejection status

    Example:
        twitter_reject_request("twitter_approval_abc123", reason="Content needs revision")
    """
    try:
        workflow = get_workflow()
        request = workflow.reject_request(approval_request_id, rejected_by, reason)

        if not request:
            return {"success": False, "error": "Request not found or already processed"}

        return {
            "success": True,
            "request_id": request.id,
            "status": request.status.value,
            "rejection_reason": reason
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


# ========== Server Lifecycle ==========

@mcp.on_startup()
async def startup():
    logger.info("Twitter MCP Server starting...")


@mcp.on_shutdown()
async def shutdown():
    logger.info("Twitter MCP Server shut down")


def main():
    logger.info("Starting Twitter MCP Server...")
    mcp.run()


if __name__ == "__main__":
    main()
