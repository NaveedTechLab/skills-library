#!/usr/bin/env python3
"""
Facebook API Client

Async client for Facebook Graph API v21.
"""

import asyncio
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
import structlog

from .models import (
    FacebookPage,
    FacebookPost,
    MediaAsset,
    MediaType,
    MetaConfig,
    PageInsights,
)

logger = structlog.get_logger()


class FacebookAPIError(Exception):
    """Custom exception for Facebook API errors"""

    def __init__(self, message: str, code: int = None, error_type: str = None):
        super().__init__(message)
        self.code = code
        self.error_type = error_type


class FacebookAPIClient:
    """
    Async client for Facebook Graph API.

    Supports Facebook Pages posting, scheduling, and insights.
    """

    BASE_URL = "https://graph.facebook.com"

    def __init__(self, config: MetaConfig = None):
        self.config = config or MetaConfig()
        self._load_env_config()

        self.api_version = self.config.api_version
        self.access_token = self.config.access_token
        self.default_page_id = self.config.page_id

        self._client: Optional[httpx.AsyncClient] = None
        self.logger = logger.bind(component="FacebookAPIClient")

    def _load_env_config(self):
        """Load configuration from environment"""
        if os.getenv("META_APP_ID"):
            self.config.app_id = os.getenv("META_APP_ID")
        if os.getenv("META_APP_SECRET"):
            self.config.app_secret = os.getenv("META_APP_SECRET")
        if os.getenv("META_ACCESS_TOKEN"):
            self.config.access_token = os.getenv("META_ACCESS_TOKEN")
        if os.getenv("META_PAGE_ID"):
            self.config.page_id = os.getenv("META_PAGE_ID")

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
        data: Dict[str, Any] = None,
        access_token: str = None
    ) -> Dict[str, Any]:
        """Make API request"""
        if not self._client:
            self._client = httpx.AsyncClient(timeout=self.config.timeout_seconds)

        url = self._get_url(endpoint)

        # Add access token to params
        params = params or {}
        params["access_token"] = access_token or self.access_token

        try:
            if method.upper() == "GET":
                response = await self._client.get(url, params=params)
            elif method.upper() == "POST":
                response = await self._client.post(url, params=params, data=data)
            elif method.upper() == "DELETE":
                response = await self._client.delete(url, params=params)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            result = response.json()

            if "error" in result:
                error = result["error"]
                raise FacebookAPIError(
                    error.get("message", "Unknown error"),
                    code=error.get("code"),
                    error_type=error.get("type")
                )

            return result

        except httpx.HTTPStatusError as e:
            raise FacebookAPIError(f"HTTP error: {e.response.status_code}")
        except httpx.RequestError as e:
            raise FacebookAPIError(f"Request error: {str(e)}")

    # ========== Pages ==========

    async def get_pages(self) -> List[FacebookPage]:
        """Get all pages the user manages"""
        result = await self._request(
            "GET",
            "me/accounts",
            params={"fields": "id,name,access_token,category,category_list,followers_count,fan_count"}
        )

        pages = []
        for page_data in result.get("data", []):
            pages.append(FacebookPage(
                id=page_data["id"],
                name=page_data["name"],
                access_token=page_data.get("access_token"),
                category=page_data.get("category"),
                category_list=page_data.get("category_list", []),
                followers_count=page_data.get("followers_count"),
                fan_count=page_data.get("fan_count")
            ))

        self.logger.info("Retrieved pages", count=len(pages))
        return pages

    async def get_page(self, page_id: str) -> FacebookPage:
        """Get page details"""
        result = await self._request(
            "GET",
            page_id,
            params={"fields": "id,name,access_token,category,followers_count,fan_count"}
        )

        return FacebookPage(
            id=result["id"],
            name=result["name"],
            access_token=result.get("access_token"),
            category=result.get("category"),
            followers_count=result.get("followers_count"),
            fan_count=result.get("fan_count")
        )

    async def get_page_access_token(self, page_id: str) -> str:
        """Get page access token"""
        pages = await self.get_pages()
        for page in pages:
            if page.id == page_id and page.access_token:
                return page.access_token

        raise FacebookAPIError(f"No access token found for page {page_id}")

    # ========== Posts ==========

    async def create_post(
        self,
        page_id: str,
        message: str,
        link: str = None,
        media_urls: List[str] = None,
        page_access_token: str = None
    ) -> str:
        """
        Create a post on a Facebook page.

        Args:
            page_id: Page ID
            message: Post message
            link: URL to share
            media_urls: Media URLs (images/videos)
            page_access_token: Page access token

        Returns:
            Post ID
        """
        # Get page token if not provided
        if not page_access_token:
            page_access_token = await self.get_page_access_token(page_id)

        # Handle media
        if media_urls and len(media_urls) == 1:
            # Single photo/video
            endpoint = f"{page_id}/photos" if self._is_image(media_urls[0]) else f"{page_id}/videos"
            data = {"url": media_urls[0]}
            if message:
                data["message" if self._is_image(media_urls[0]) else "description"] = message

            result = await self._request("POST", endpoint, data=data, access_token=page_access_token)

        elif media_urls and len(media_urls) > 1:
            # Multiple photos (unpublished first, then published post)
            photo_ids = []
            for url in media_urls:
                result = await self._request(
                    "POST",
                    f"{page_id}/photos",
                    data={"url": url, "published": "false"},
                    access_token=page_access_token
                )
                photo_ids.append(result["id"])

            # Create post with attached photos
            data = {"message": message}
            for i, photo_id in enumerate(photo_ids):
                data[f"attached_media[{i}]"] = f'{{"media_fbid":"{photo_id}"}}'

            result = await self._request("POST", f"{page_id}/feed", data=data, access_token=page_access_token)

        else:
            # Text post or link share
            data = {}
            if message:
                data["message"] = message
            if link:
                data["link"] = link

            result = await self._request("POST", f"{page_id}/feed", data=data, access_token=page_access_token)

        post_id = result.get("id") or result.get("post_id")
        self.logger.info("Post created", page_id=page_id, post_id=post_id)
        return post_id

    async def schedule_post(
        self,
        page_id: str,
        message: str,
        scheduled_time: datetime,
        link: str = None,
        media_urls: List[str] = None,
        page_access_token: str = None
    ) -> str:
        """
        Schedule a post for future publication.

        Args:
            page_id: Page ID
            message: Post message
            scheduled_time: When to publish
            link: URL to share
            media_urls: Media URLs
            page_access_token: Page access token

        Returns:
            Post ID
        """
        if not page_access_token:
            page_access_token = await self.get_page_access_token(page_id)

        data = {
            "message": message,
            "published": "false",
            "scheduled_publish_time": int(scheduled_time.timestamp())
        }
        if link:
            data["link"] = link

        # For scheduled posts with media, we need to use the photo endpoint
        if media_urls and len(media_urls) == 1 and self._is_image(media_urls[0]):
            data["url"] = media_urls[0]
            result = await self._request(
                "POST",
                f"{page_id}/photos",
                data=data,
                access_token=page_access_token
            )
        else:
            result = await self._request(
                "POST",
                f"{page_id}/feed",
                data=data,
                access_token=page_access_token
            )

        post_id = result.get("id") or result.get("post_id")
        self.logger.info("Post scheduled", page_id=page_id, post_id=post_id, scheduled_time=scheduled_time)
        return post_id

    async def get_post(self, post_id: str) -> FacebookPost:
        """Get post details"""
        result = await self._request(
            "GET",
            post_id,
            params={"fields": "id,message,created_time,full_picture,permalink_url,shares,reactions.summary(true),comments.summary(true)"}
        )

        return FacebookPost(
            id=result["id"],
            page_id=result["id"].split("_")[0],
            message=result.get("message", ""),
            created_time=datetime.fromisoformat(result["created_time"].replace("Z", "+00:00")) if result.get("created_time") else None,
            published=True,
            likes_count=result.get("reactions", {}).get("summary", {}).get("total_count", 0),
            comments_count=result.get("comments", {}).get("summary", {}).get("total_count", 0),
            shares_count=result.get("shares", {}).get("count", 0)
        )

    async def delete_post(self, post_id: str) -> bool:
        """Delete a post"""
        await self._request("DELETE", post_id)
        self.logger.info("Post deleted", post_id=post_id)
        return True

    # ========== Insights ==========

    async def get_page_insights(
        self,
        page_id: str,
        metrics: List[str] = None,
        period: str = "day",
        date_preset: str = "last_7d"
    ) -> PageInsights:
        """
        Get page insights.

        Args:
            page_id: Page ID
            metrics: Metrics to retrieve
            period: day, week, days_28, month, lifetime
            date_preset: today, yesterday, this_week, last_week, etc.

        Returns:
            PageInsights with metrics
        """
        if metrics is None:
            metrics = [
                "page_impressions",
                "page_impressions_unique",
                "page_engaged_users",
                "page_post_engagements",
                "page_fans",
                "page_fan_adds"
            ]

        page_access_token = await self.get_page_access_token(page_id)

        result = await self._request(
            "GET",
            f"{page_id}/insights",
            params={
                "metric": ",".join(metrics),
                "period": period,
                "date_preset": date_preset
            },
            access_token=page_access_token
        )

        insights_data = {}
        for item in result.get("data", []):
            metric_name = item.get("name")
            values = item.get("values", [])
            if values:
                insights_data[metric_name] = values[-1].get("value", 0)

        return PageInsights(
            page_id=page_id,
            period=period,
            metrics=insights_data
        )

    async def get_post_insights(
        self,
        post_id: str,
        metrics: List[str] = None
    ) -> Dict[str, Any]:
        """Get post-level insights"""
        if metrics is None:
            metrics = [
                "post_impressions",
                "post_impressions_unique",
                "post_engaged_users",
                "post_clicks"
            ]

        result = await self._request(
            "GET",
            f"{post_id}/insights",
            params={"metric": ",".join(metrics)}
        )

        insights = {}
        for item in result.get("data", []):
            metric_name = item.get("name")
            values = item.get("values", [])
            if values:
                insights[metric_name] = values[0].get("value", 0)

        return insights

    # ========== Helpers ==========

    def _is_image(self, url: str) -> bool:
        """Check if URL points to an image"""
        image_extensions = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
        return any(url.lower().endswith(ext) for ext in image_extensions)


# Convenience function
async def create_facebook_client(config: MetaConfig = None) -> FacebookAPIClient:
    """Create a Facebook client"""
    client = FacebookAPIClient(config)
    return client


async def demo_facebook_client():
    """Demo the Facebook client"""
    print("Facebook API Client Demo")
    print("=" * 40)
    print("Note: This demo requires Meta API credentials")
    print("Set environment variables: META_ACCESS_TOKEN, META_PAGE_ID")

    print("\nExample usage:")
    print("```python")
    print("async with FacebookAPIClient() as client:")
    print("    # Get pages")
    print("    pages = await client.get_pages()")
    print("")
    print("    # Create post")
    print("    post_id = await client.create_post(")
    print("        page_id='123456789',")
    print("        message='Hello from Claude!'")
    print("    )")
    print("")
    print("    # Get insights")
    print("    insights = await client.get_page_insights('123456789')")
    print("```")


if __name__ == "__main__":
    asyncio.run(demo_facebook_client())
