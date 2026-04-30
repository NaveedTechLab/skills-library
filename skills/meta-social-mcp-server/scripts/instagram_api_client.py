#!/usr/bin/env python3
"""
Instagram API Client

Async client for Instagram Graph API (Business/Creator accounts).
"""

import asyncio
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
import structlog

from .models import (
    InstagramInsights,
    InstagramPost,
    InstagramReel,
    MediaType,
    MetaConfig,
)

logger = structlog.get_logger()


class InstagramAPIError(Exception):
    """Custom exception for Instagram API errors"""

    def __init__(self, message: str, code: int = None, error_type: str = None):
        super().__init__(message)
        self.code = code
        self.error_type = error_type


class InstagramAPIClient:
    """
    Async client for Instagram Graph API.

    Supports Instagram Business/Creator account posting and insights.
    """

    BASE_URL = "https://graph.facebook.com"

    def __init__(self, config: MetaConfig = None):
        self.config = config or MetaConfig()
        self._load_env_config()

        self.api_version = self.config.api_version
        self.access_token = self.config.access_token
        self.default_account_id = self.config.instagram_account_id

        self._client: Optional[httpx.AsyncClient] = None
        self.logger = logger.bind(component="InstagramAPIClient")

    def _load_env_config(self):
        """Load configuration from environment"""
        if os.getenv("META_ACCESS_TOKEN"):
            self.config.access_token = os.getenv("META_ACCESS_TOKEN")
        if os.getenv("META_INSTAGRAM_ACCOUNT_ID"):
            self.config.instagram_account_id = os.getenv("META_INSTAGRAM_ACCOUNT_ID")

    async def __aenter__(self):
        self._client = httpx.AsyncClient(timeout=self.config.timeout_seconds)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()

    def _get_url(self, endpoint: str) -> str:
        """Build API URL"""
        return f"{self.BASE_URL}/{self.api_version}/{endpoint.lstrip('/')}"

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Dict[str, Any] = None,
        data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Make API request"""
        if not self._client:
            self._client = httpx.AsyncClient(timeout=self.config.timeout_seconds)

        url = self._get_url(endpoint)

        params = params or {}
        params["access_token"] = self.access_token

        try:
            if method.upper() == "GET":
                response = await self._client.get(url, params=params)
            elif method.upper() == "POST":
                response = await self._client.post(url, params=params, data=data)
            else:
                raise ValueError(f"Unsupported method: {method}")

            result = response.json()

            if "error" in result:
                error = result["error"]
                raise InstagramAPIError(
                    error.get("message", "Unknown error"),
                    code=error.get("code"),
                    error_type=error.get("type")
                )

            return result

        except httpx.HTTPStatusError as e:
            raise InstagramAPIError(f"HTTP error: {e.response.status_code}")
        except httpx.RequestError as e:
            raise InstagramAPIError(f"Request error: {str(e)}")

    # ========== Account ==========

    async def get_account_info(self, account_id: str = None) -> Dict[str, Any]:
        """Get Instagram account information"""
        account_id = account_id or self.default_account_id

        result = await self._request(
            "GET",
            account_id,
            params={"fields": "id,username,name,biography,followers_count,follows_count,media_count,profile_picture_url"}
        )

        return result

    # ========== Posts ==========

    async def create_post(
        self,
        account_id: str,
        caption: str,
        media_url: str,
        media_type: MediaType = MediaType.IMAGE,
        location_id: str = None
    ) -> str:
        """
        Create an Instagram post.

        Uses the Content Publishing API:
        1. Create media container
        2. Publish container

        Args:
            account_id: Instagram Business Account ID
            caption: Post caption
            media_url: URL to image (must be publicly accessible)
            media_type: IMAGE or VIDEO
            location_id: Optional location tag

        Returns:
            Published media ID
        """
        # Step 1: Create container
        container_params = {
            "caption": caption,
        }

        if media_type == MediaType.IMAGE:
            container_params["image_url"] = media_url
        elif media_type == MediaType.VIDEO:
            container_params["video_url"] = media_url
            container_params["media_type"] = "VIDEO"

        if location_id:
            container_params["location_id"] = location_id

        container_result = await self._request(
            "POST",
            f"{account_id}/media",
            params=container_params
        )

        container_id = container_result["id"]
        self.logger.info("Media container created", container_id=container_id)

        # For video, wait for processing
        if media_type == MediaType.VIDEO:
            await self._wait_for_container_ready(container_id)

        # Step 2: Publish
        publish_result = await self._request(
            "POST",
            f"{account_id}/media_publish",
            params={"creation_id": container_id}
        )

        media_id = publish_result["id"]
        self.logger.info("Post published", media_id=media_id)
        return media_id

    async def create_carousel_post(
        self,
        account_id: str,
        caption: str,
        media_urls: List[str]
    ) -> str:
        """
        Create a carousel post with multiple images.

        Args:
            account_id: Instagram Business Account ID
            caption: Post caption
            media_urls: List of image URLs (2-10 items)

        Returns:
            Published media ID
        """
        if len(media_urls) < 2 or len(media_urls) > 10:
            raise InstagramAPIError("Carousel requires 2-10 images")

        # Step 1: Create individual containers for each item
        children_ids = []
        for url in media_urls:
            result = await self._request(
                "POST",
                f"{account_id}/media",
                params={
                    "image_url": url,
                    "is_carousel_item": "true"
                }
            )
            children_ids.append(result["id"])

        # Step 2: Create carousel container
        carousel_result = await self._request(
            "POST",
            f"{account_id}/media",
            params={
                "caption": caption,
                "media_type": "CAROUSEL",
                "children": ",".join(children_ids)
            }
        )

        carousel_id = carousel_result["id"]

        # Step 3: Publish
        publish_result = await self._request(
            "POST",
            f"{account_id}/media_publish",
            params={"creation_id": carousel_id}
        )

        media_id = publish_result["id"]
        self.logger.info("Carousel published", media_id=media_id, items=len(media_urls))
        return media_id

    async def create_reel(
        self,
        account_id: str,
        video_url: str,
        caption: str,
        share_to_feed: bool = True,
        cover_url: str = None
    ) -> str:
        """
        Create an Instagram Reel.

        Args:
            account_id: Instagram Business Account ID
            video_url: URL to video (must be publicly accessible)
            caption: Reel caption
            share_to_feed: Also share to feed
            cover_url: Optional cover image URL

        Returns:
            Published Reel ID
        """
        # Step 1: Create Reel container
        container_params = {
            "video_url": video_url,
            "caption": caption,
            "media_type": "REELS",
            "share_to_feed": str(share_to_feed).lower()
        }

        if cover_url:
            container_params["cover_url"] = cover_url

        container_result = await self._request(
            "POST",
            f"{account_id}/media",
            params=container_params
        )

        container_id = container_result["id"]
        self.logger.info("Reel container created", container_id=container_id)

        # Wait for video processing
        await self._wait_for_container_ready(container_id)

        # Step 2: Publish
        publish_result = await self._request(
            "POST",
            f"{account_id}/media_publish",
            params={"creation_id": container_id}
        )

        reel_id = publish_result["id"]
        self.logger.info("Reel published", reel_id=reel_id)
        return reel_id

    async def _wait_for_container_ready(
        self,
        container_id: str,
        max_attempts: int = 30,
        interval: int = 5
    ):
        """Wait for media container to be ready for publishing"""
        for attempt in range(max_attempts):
            result = await self._request(
                "GET",
                container_id,
                params={"fields": "status_code,status"}
            )

            status = result.get("status_code")
            if status == "FINISHED":
                return
            elif status == "ERROR":
                raise InstagramAPIError(f"Media processing failed: {result.get('status')}")

            self.logger.debug("Waiting for media processing", attempt=attempt, status=status)
            await asyncio.sleep(interval)

        raise InstagramAPIError("Media processing timeout")

    async def get_media(self, media_id: str) -> InstagramPost:
        """Get media details"""
        result = await self._request(
            "GET",
            media_id,
            params={"fields": "id,caption,media_type,media_url,permalink,timestamp,like_count,comments_count"}
        )

        return InstagramPost(
            id=result["id"],
            account_id="",  # Not returned in this call
            caption=result.get("caption", ""),
            media_type=MediaType(result.get("media_type", "IMAGE")),
            media_url=result.get("media_url"),
            permalink=result.get("permalink"),
            created_time=datetime.fromisoformat(result["timestamp"].replace("Z", "+00:00")) if result.get("timestamp") else None,
            likes_count=result.get("like_count", 0),
            comments_count=result.get("comments_count", 0)
        )

    async def get_recent_media(
        self,
        account_id: str = None,
        limit: int = 25
    ) -> List[InstagramPost]:
        """Get recent media for an account"""
        account_id = account_id or self.default_account_id

        result = await self._request(
            "GET",
            f"{account_id}/media",
            params={
                "fields": "id,caption,media_type,media_url,permalink,timestamp,like_count,comments_count",
                "limit": limit
            }
        )

        posts = []
        for item in result.get("data", []):
            posts.append(InstagramPost(
                id=item["id"],
                account_id=account_id,
                caption=item.get("caption", ""),
                media_type=MediaType(item.get("media_type", "IMAGE")),
                media_url=item.get("media_url"),
                permalink=item.get("permalink"),
                created_time=datetime.fromisoformat(item["timestamp"].replace("Z", "+00:00")) if item.get("timestamp") else None,
                likes_count=item.get("like_count", 0),
                comments_count=item.get("comments_count", 0)
            ))

        return posts

    # ========== Insights ==========

    async def get_account_insights(
        self,
        account_id: str = None,
        metrics: List[str] = None,
        period: str = "day"
    ) -> InstagramInsights:
        """
        Get account insights.

        Args:
            account_id: Instagram Business Account ID
            metrics: Metrics to retrieve
            period: day, week, days_28, lifetime

        Returns:
            InstagramInsights
        """
        account_id = account_id or self.default_account_id

        if metrics is None:
            metrics = [
                "impressions",
                "reach",
                "profile_views",
                "follower_count"
            ]

        result = await self._request(
            "GET",
            f"{account_id}/insights",
            params={
                "metric": ",".join(metrics),
                "period": period
            }
        )

        insights_data = {}
        for item in result.get("data", []):
            metric_name = item.get("name")
            values = item.get("values", [])
            if values:
                insights_data[metric_name] = values[-1].get("value", 0)

        return InstagramInsights(
            account_id=account_id,
            period=period,
            metrics=insights_data
        )

    async def get_media_insights(
        self,
        media_id: str,
        metrics: List[str] = None
    ) -> Dict[str, Any]:
        """Get media-level insights"""
        if metrics is None:
            metrics = ["impressions", "reach", "engagement", "saved"]

        result = await self._request(
            "GET",
            f"{media_id}/insights",
            params={"metric": ",".join(metrics)}
        )

        insights = {}
        for item in result.get("data", []):
            metric_name = item.get("name")
            values = item.get("values", [])
            if values:
                insights[metric_name] = values[0].get("value", 0)

        return insights

    # ========== Hashtags ==========

    async def search_hashtag(self, hashtag: str, account_id: str = None) -> str:
        """Search for a hashtag and get its ID"""
        account_id = account_id or self.default_account_id

        result = await self._request(
            "GET",
            "ig_hashtag_search",
            params={
                "user_id": account_id,
                "q": hashtag.lstrip("#")
            }
        )

        data = result.get("data", [])
        if data:
            return data[0]["id"]

        raise InstagramAPIError(f"Hashtag not found: {hashtag}")


# Convenience function
async def create_instagram_client(config: MetaConfig = None) -> InstagramAPIClient:
    """Create an Instagram client"""
    return InstagramAPIClient(config)


async def demo_instagram_client():
    """Demo the Instagram client"""
    print("Instagram API Client Demo")
    print("=" * 40)
    print("Note: This demo requires Meta API credentials")
    print("Set: META_ACCESS_TOKEN, META_INSTAGRAM_ACCOUNT_ID")

    print("\nExample usage:")
    print("```python")
    print("async with InstagramAPIClient() as client:")
    print("    # Create post")
    print("    media_id = await client.create_post(")
    print("        account_id='17841400000000000',")
    print("        caption='Hello Instagram!',")
    print("        media_url='https://example.com/image.jpg'")
    print("    )")
    print("")
    print("    # Create Reel")
    print("    reel_id = await client.create_reel(")
    print("        account_id='17841400000000000',")
    print("        video_url='https://example.com/video.mp4',")
    print("        caption='My first Reel!'")
    print("    )")
    print("")
    print("    # Get insights")
    print("    insights = await client.get_account_insights()")
    print("```")


if __name__ == "__main__":
    asyncio.run(demo_instagram_client())
