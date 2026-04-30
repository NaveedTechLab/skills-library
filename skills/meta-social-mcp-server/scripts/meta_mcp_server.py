#!/usr/bin/env python3
"""
Meta Social MCP Server

FastMCP server providing Facebook and Instagram integration with HITL controls.
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

from .approval_workflow import MetaSocialApprovalWorkflow
from .facebook_api_client import FacebookAPIClient, FacebookAPIError
from .instagram_api_client import InstagramAPIClient, InstagramAPIError
from .models import ApprovalStatus, MediaType, MetaConfig

logger = structlog.get_logger()

# Initialize FastMCP server
mcp = FastMCP("Meta Social MCP Server")

# Global instances
_config: Optional[MetaConfig] = None
_fb_client: Optional[FacebookAPIClient] = None
_ig_client: Optional[InstagramAPIClient] = None
_workflow: Optional[MetaSocialApprovalWorkflow] = None


def get_config() -> MetaConfig:
    global _config
    if _config is None:
        _config = MetaConfig()
    return _config


def get_workflow() -> MetaSocialApprovalWorkflow:
    global _workflow
    if _workflow is None:
        _workflow = MetaSocialApprovalWorkflow(get_config())
    return _workflow


async def get_fb_client() -> FacebookAPIClient:
    global _fb_client
    if _fb_client is None:
        _fb_client = FacebookAPIClient(get_config())
    return _fb_client


async def get_ig_client() -> InstagramAPIClient:
    global _ig_client
    if _ig_client is None:
        _ig_client = InstagramAPIClient(get_config())
    return _ig_client


# ========== Facebook Tools ==========

@mcp.tool()
async def facebook_list_pages() -> Dict[str, Any]:
    """
    List all Facebook pages the user manages.

    No HITL required - read-only operation.

    Returns:
        List of pages with id, name, and follower counts

    Example:
        facebook_list_pages()
    """
    try:
        client = await get_fb_client()
        async with client:
            pages = await client.get_pages()

        return {
            "success": True,
            "count": len(pages),
            "pages": [
                {
                    "id": p.id,
                    "name": p.name,
                    "category": p.category,
                    "followers_count": p.followers_count,
                    "fan_count": p.fan_count
                }
                for p in pages
            ]
        }
    except FacebookAPIError as e:
        return {"success": False, "error": str(e), "code": e.code}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
async def facebook_create_post(
    page_id: str,
    message: str,
    link: str = None,
    media_urls: List[str] = None
) -> Dict[str, Any]:
    """
    Create a post on a Facebook page.

    HITL: Always requires approval.

    Args:
        page_id: Facebook Page ID
        message: Post message/text
        link: Optional URL to share
        media_urls: Optional list of image/video URLs

    Returns:
        Approval request ID (post created after approval)

    Example:
        facebook_create_post(
            page_id="123456789",
            message="Check out our latest update!",
            link="https://example.com"
        )
    """
    try:
        workflow = get_workflow()

        request = workflow.create_approval_request(
            platform="facebook",
            operation="create_post",
            content_type="post",
            data={
                "page_id": page_id,
                "message": message,
                "link": link,
                "media_urls": media_urls or []
            },
            context={"has_media": bool(media_urls)}
        )

        return {
            "success": True,
            "requires_approval": True,
            "approval_request_id": request.id,
            "message": f"Post requires approval. Request ID: {request.id}"
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
async def facebook_schedule_post(
    page_id: str,
    message: str,
    scheduled_time: str,
    link: str = None,
    media_urls: List[str] = None
) -> Dict[str, Any]:
    """
    Schedule a post for future publication on a Facebook page.

    HITL: Always requires approval.

    Args:
        page_id: Facebook Page ID
        message: Post message
        scheduled_time: ISO datetime for publication (e.g., "2024-01-20T14:00:00Z")
        link: Optional URL to share
        media_urls: Optional media URLs

    Returns:
        Approval request ID

    Example:
        facebook_schedule_post(
            page_id="123456789",
            message="Coming soon!",
            scheduled_time="2024-01-20T14:00:00Z"
        )
    """
    try:
        workflow = get_workflow()

        request = workflow.create_approval_request(
            platform="facebook",
            operation="schedule_post",
            content_type="post",
            data={
                "page_id": page_id,
                "message": message,
                "scheduled_time": scheduled_time,
                "link": link,
                "media_urls": media_urls or []
            },
            context={"scheduled": True, "scheduled_time": scheduled_time}
        )

        return {
            "success": True,
            "requires_approval": True,
            "approval_request_id": request.id,
            "scheduled_time": scheduled_time,
            "message": f"Scheduled post requires approval. Request ID: {request.id}"
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
async def facebook_get_insights(
    page_id: str,
    metrics: List[str] = None,
    period: str = "day",
    date_preset: str = "last_7d"
) -> Dict[str, Any]:
    """
    Get engagement metrics for a Facebook page.

    No HITL required - read-only operation.

    Args:
        page_id: Facebook Page ID
        metrics: Metrics to retrieve (default: impressions, reach, engaged_users)
        period: day, week, days_28
        date_preset: today, yesterday, last_7d, last_30d

    Returns:
        Page insights and metrics

    Example:
        facebook_get_insights(page_id="123456789", date_preset="last_7d")
    """
    try:
        client = await get_fb_client()
        async with client:
            insights = await client.get_page_insights(page_id, metrics, period, date_preset)

        return {
            "success": True,
            "page_id": insights.page_id,
            "period": insights.period,
            "metrics": insights.metrics
        }

    except FacebookAPIError as e:
        return {"success": False, "error": str(e), "code": e.code}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ========== Instagram Tools ==========

@mcp.tool()
async def instagram_create_post(
    account_id: str,
    caption: str,
    media_url: str,
    media_type: str = "IMAGE",
    location_id: str = None
) -> Dict[str, Any]:
    """
    Create a post on Instagram.

    HITL: Always requires approval.

    Args:
        account_id: Instagram Business Account ID
        caption: Post caption
        media_url: Public URL to image or video
        media_type: IMAGE or VIDEO
        location_id: Optional location tag ID

    Returns:
        Approval request ID

    Example:
        instagram_create_post(
            account_id="17841400000000000",
            caption="Beautiful sunset! #nature #photography",
            media_url="https://example.com/sunset.jpg"
        )
    """
    try:
        workflow = get_workflow()

        request = workflow.create_approval_request(
            platform="instagram",
            operation="create_post",
            content_type="post",
            data={
                "account_id": account_id,
                "caption": caption,
                "media_url": media_url,
                "media_type": media_type,
                "location_id": location_id
            },
            context={"media_type": media_type}
        )

        return {
            "success": True,
            "requires_approval": True,
            "approval_request_id": request.id,
            "message": f"Instagram post requires approval. Request ID: {request.id}"
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
async def instagram_create_reel(
    account_id: str,
    video_url: str,
    caption: str,
    share_to_feed: bool = True,
    cover_url: str = None
) -> Dict[str, Any]:
    """
    Create an Instagram Reel.

    HITL: Always requires approval.

    Args:
        account_id: Instagram Business Account ID
        video_url: Public URL to video
        caption: Reel caption
        share_to_feed: Also share to feed (default: True)
        cover_url: Optional cover image URL

    Returns:
        Approval request ID

    Example:
        instagram_create_reel(
            account_id="17841400000000000",
            video_url="https://example.com/reel.mp4",
            caption="Check out this amazing trick! #viral"
        )
    """
    try:
        workflow = get_workflow()

        request = workflow.create_approval_request(
            platform="instagram",
            operation="create_reel",
            content_type="reel",
            data={
                "account_id": account_id,
                "video_url": video_url,
                "caption": caption,
                "share_to_feed": share_to_feed,
                "cover_url": cover_url
            },
            context={"content_type": "reel", "share_to_feed": share_to_feed}
        )

        return {
            "success": True,
            "requires_approval": True,
            "approval_request_id": request.id,
            "message": f"Instagram Reel requires approval. Request ID: {request.id}"
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
async def instagram_get_insights(
    account_id: str,
    metrics: List[str] = None,
    period: str = "day"
) -> Dict[str, Any]:
    """
    Get Instagram account insights.

    No HITL required - read-only operation.

    Args:
        account_id: Instagram Business Account ID
        metrics: Metrics to retrieve (default: impressions, reach, profile_views)
        period: day, week, days_28

    Returns:
        Account insights and metrics

    Example:
        instagram_get_insights(account_id="17841400000000000")
    """
    try:
        client = await get_ig_client()
        async with client:
            insights = await client.get_account_insights(account_id, metrics, period)

        return {
            "success": True,
            "account_id": insights.account_id,
            "period": insights.period,
            "metrics": insights.metrics
        }

    except InstagramAPIError as e:
        return {"success": False, "error": str(e), "code": e.code}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ========== Approval Tools ==========

@mcp.tool()
async def meta_execute_approved_request(approval_request_id: str) -> Dict[str, Any]:
    """
    Execute an approved content request.

    This publishes the content after human approval.

    Args:
        approval_request_id: The approval request ID to execute

    Returns:
        Execution result with post ID

    Example:
        meta_execute_approved_request("meta_approval_abc123")
    """
    try:
        workflow = get_workflow()
        request = workflow.get_request(approval_request_id)

        if not request:
            return {"success": False, "error": "Request not found"}

        if request.status != ApprovalStatus.APPROVED:
            return {"success": False, "error": f"Request not approved. Status: {request.status.value}"}

        data = request.data

        if request.platform == "facebook":
            client = await get_fb_client()
            async with client:
                if request.operation == "create_post":
                    post_id = await client.create_post(
                        page_id=data["page_id"],
                        message=data.get("message", ""),
                        link=data.get("link"),
                        media_urls=data.get("media_urls", [])
                    )
                elif request.operation == "schedule_post":
                    scheduled_time = datetime.fromisoformat(data["scheduled_time"].replace("Z", "+00:00"))
                    post_id = await client.schedule_post(
                        page_id=data["page_id"],
                        message=data.get("message", ""),
                        scheduled_time=scheduled_time,
                        link=data.get("link"),
                        media_urls=data.get("media_urls", [])
                    )
                else:
                    return {"success": False, "error": f"Unknown operation: {request.operation}"}

            return {
                "success": True,
                "platform": "facebook",
                "operation": request.operation,
                "post_id": post_id,
                "message": f"Facebook {request.operation} executed successfully"
            }

        elif request.platform == "instagram":
            client = await get_ig_client()
            async with client:
                if request.operation == "create_post":
                    media_id = await client.create_post(
                        account_id=data["account_id"],
                        caption=data.get("caption", ""),
                        media_url=data["media_url"],
                        media_type=MediaType(data.get("media_type", "IMAGE")),
                        location_id=data.get("location_id")
                    )
                elif request.operation == "create_reel":
                    media_id = await client.create_reel(
                        account_id=data["account_id"],
                        video_url=data["video_url"],
                        caption=data.get("caption", ""),
                        share_to_feed=data.get("share_to_feed", True),
                        cover_url=data.get("cover_url")
                    )
                else:
                    return {"success": False, "error": f"Unknown operation: {request.operation}"}

            return {
                "success": True,
                "platform": "instagram",
                "operation": request.operation,
                "media_id": media_id,
                "message": f"Instagram {request.operation} executed successfully"
            }

        else:
            return {"success": False, "error": f"Unknown platform: {request.platform}"}

    except (FacebookAPIError, InstagramAPIError) as e:
        return {"success": False, "error": str(e), "code": e.code}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
async def meta_get_pending_approvals(platform: str = None) -> Dict[str, Any]:
    """
    Get all pending approval requests.

    Args:
        platform: Optional filter by platform (facebook/instagram)

    Returns:
        List of pending approval requests

    Example:
        meta_get_pending_approvals(platform="instagram")
    """
    try:
        workflow = get_workflow()
        requests = workflow.get_pending_requests(platform)

        return {
            "success": True,
            "count": len(requests),
            "requests": [r.to_dict() for r in requests]
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
async def meta_approve_request(
    approval_request_id: str,
    approved_by: str = "human"
) -> Dict[str, Any]:
    """
    Approve a pending content request.

    Args:
        approval_request_id: Request to approve
        approved_by: Approver identifier

    Returns:
        Approval status

    Example:
        meta_approve_request("meta_approval_abc123", approved_by="social_manager")
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
            "message": "Approved. Use meta_execute_approved_request to publish."
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
async def meta_reject_request(
    approval_request_id: str,
    rejected_by: str = "human",
    reason: str = None
) -> Dict[str, Any]:
    """
    Reject a pending content request.

    Args:
        approval_request_id: Request to reject
        rejected_by: Rejector identifier
        reason: Rejection reason

    Returns:
        Rejection status

    Example:
        meta_reject_request("meta_approval_abc123", reason="Content not aligned with brand")
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
    logger.info("Meta Social MCP Server starting...")


@mcp.on_shutdown()
async def shutdown():
    logger.info("Meta Social MCP Server shut down")


def main():
    logger.info("Starting Meta Social MCP Server...")
    mcp.run()


if __name__ == "__main__":
    main()
