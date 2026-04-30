#!/usr/bin/env python3
"""
Twitter API Client

Async client for X API v2.
"""

import asyncio
import base64
import hashlib
import os
import secrets
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import httpx
import structlog

from .models import MediaType, MediaUpload, Tweet, TweetThread, TwitterConfig
from .rate_limiter import RateLimiter

logger = structlog.get_logger()


class TwitterAPIError(Exception):
    """Custom exception for Twitter API errors"""

    def __init__(self, message: str, code: int = None, error_type: str = None):
        super().__init__(message)
        self.code = code
        self.error_type = error_type


class TwitterAPIClient:
    """
    Async client for X API v2.

    Supports OAuth 2.0 authentication with PKCE.
    """

    API_BASE = "https://api.twitter.com/2"
    UPLOAD_BASE = "https://upload.twitter.com/1.1"
    OAUTH_BASE = "https://twitter.com/i/oauth2"

    def __init__(self, config: TwitterConfig = None):
        self.config = config or TwitterConfig()
        self._load_env_config()

        self.rate_limiter = RateLimiter(self.config)
        self._client: Optional[httpx.AsyncClient] = None
        self.logger = logger.bind(component="TwitterAPIClient")

    def _load_env_config(self):
        """Load configuration from environment"""
        if os.getenv("TWITTER_CLIENT_ID"):
            self.config.client_id = os.getenv("TWITTER_CLIENT_ID")
        if os.getenv("TWITTER_CLIENT_SECRET"):
            self.config.client_secret = os.getenv("TWITTER_CLIENT_SECRET")
        if os.getenv("TWITTER_ACCESS_TOKEN"):
            self.config.access_token = os.getenv("TWITTER_ACCESS_TOKEN")
        if os.getenv("TWITTER_ACCESS_TOKEN_SECRET"):
            self.config.access_token_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
        if os.getenv("TWITTER_BEARER_TOKEN"):
            self.config.bearer_token = os.getenv("TWITTER_BEARER_TOKEN")

    async def __aenter__(self):
        self._client = httpx.AsyncClient(timeout=self.config.timeout_seconds)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()

    def _get_auth_headers(self, use_bearer: bool = False) -> Dict[str, str]:
        """Get authentication headers"""
        if use_bearer and self.config.bearer_token:
            return {"Authorization": f"Bearer {self.config.bearer_token}"}
        elif self.config.access_token:
            # For OAuth 2.0 user context
            return {"Authorization": f"Bearer {self.config.access_token}"}
        else:
            raise TwitterAPIError("No authentication credentials configured")

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Dict[str, Any] = None,
        json_data: Dict[str, Any] = None,
        use_bearer: bool = False,
        rate_limit_endpoint: str = None
    ) -> Dict[str, Any]:
        """Make API request"""
        if not self._client:
            self._client = httpx.AsyncClient(timeout=self.config.timeout_seconds)

        # Check rate limit
        rl_endpoint = rate_limit_endpoint or endpoint.split("/")[-1]
        allowed, reason = self.rate_limiter.check_rate_limit(f"tweets/{rl_endpoint}")
        if not allowed:
            raise TwitterAPIError(f"Rate limit exceeded: {reason}")

        url = f"{self.API_BASE}/{endpoint.lstrip('/')}"
        headers = self._get_auth_headers(use_bearer)

        try:
            if method.upper() == "GET":
                response = await self._client.get(url, params=params, headers=headers)
            elif method.upper() == "POST":
                response = await self._client.post(url, json=json_data, headers=headers)
            elif method.upper() == "DELETE":
                response = await self._client.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported method: {method}")

            # Update rate limits from headers
            self.rate_limiter.update_from_headers(
                f"tweets/{rl_endpoint}",
                dict(response.headers)
            )
            self.rate_limiter.record_request(f"tweets/{rl_endpoint}")

            result = response.json()

            if response.status_code >= 400:
                error = result.get("errors", [{}])[0] if "errors" in result else result
                raise TwitterAPIError(
                    error.get("message", error.get("detail", "Unknown error")),
                    code=response.status_code,
                    error_type=error.get("type")
                )

            return result

        except httpx.HTTPStatusError as e:
            raise TwitterAPIError(f"HTTP error: {e.response.status_code}")
        except httpx.RequestError as e:
            raise TwitterAPIError(f"Request error: {str(e)}")

    # ========== OAuth 2.0 with PKCE ==========

    def generate_oauth_url(self, redirect_uri: str, scopes: List[str] = None) -> Dict[str, str]:
        """
        Generate OAuth 2.0 authorization URL with PKCE.

        Args:
            redirect_uri: Callback URL
            scopes: OAuth scopes

        Returns:
            Dict with authorization_url, state, and code_verifier
        """
        if scopes is None:
            scopes = ["tweet.read", "tweet.write", "users.read", "offline.access"]

        # Generate PKCE code verifier and challenge
        code_verifier = secrets.token_urlsafe(32)
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).decode().rstrip("=")

        state = secrets.token_urlsafe(16)

        params = {
            "response_type": "code",
            "client_id": self.config.client_id,
            "redirect_uri": redirect_uri,
            "scope": " ".join(scopes),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256"
        }

        auth_url = f"{self.OAUTH_BASE}/authorize?{urlencode(params)}"

        return {
            "authorization_url": auth_url,
            "state": state,
            "code_verifier": code_verifier
        }

    async def exchange_code_for_token(
        self,
        code: str,
        redirect_uri: str,
        code_verifier: str
    ) -> Dict[str, Any]:
        """Exchange authorization code for access token"""
        if not self._client:
            self._client = httpx.AsyncClient(timeout=self.config.timeout_seconds)

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier,
            "client_id": self.config.client_id
        }

        response = await self._client.post(
            f"{self.OAUTH_BASE}/token",
            data=data,
            auth=(self.config.client_id, self.config.client_secret)
        )

        result = response.json()

        if "access_token" in result:
            self.config.access_token = result["access_token"]
            self.logger.info("Access token obtained")

        return result

    # ========== Tweet Operations ==========

    async def create_tweet(self, tweet: Tweet) -> str:
        """
        Create a tweet.

        Args:
            tweet: Tweet model with text and optional media

        Returns:
            Created tweet ID
        """
        payload = tweet.to_api_payload()

        result = await self._request(
            "POST",
            "tweets",
            json_data=payload,
            rate_limit_endpoint="create"
        )

        tweet_id = result.get("data", {}).get("id")
        self.logger.info("Tweet created", tweet_id=tweet_id)
        return tweet_id

    async def create_thread(self, thread: TweetThread) -> List[str]:
        """
        Create a thread of tweets.

        Args:
            thread: TweetThread with list of tweets

        Returns:
            List of created tweet IDs
        """
        tweet_ids = []
        previous_id = None

        for tweet in thread.tweets:
            if previous_id:
                tweet.reply_to_tweet_id = previous_id

            tweet_id = await self.create_tweet(tweet)
            tweet_ids.append(tweet_id)
            previous_id = tweet_id

            # Small delay between tweets
            await asyncio.sleep(0.5)

        self.logger.info("Thread created", tweet_count=len(tweet_ids))
        return tweet_ids

    async def delete_tweet(self, tweet_id: str) -> bool:
        """Delete a tweet"""
        result = await self._request(
            "DELETE",
            f"tweets/{tweet_id}",
            rate_limit_endpoint="delete"
        )

        deleted = result.get("data", {}).get("deleted", False)
        self.logger.info("Tweet deleted", tweet_id=tweet_id, success=deleted)
        return deleted

    async def get_tweet(
        self,
        tweet_id: str,
        expansions: List[str] = None,
        tweet_fields: List[str] = None
    ) -> Dict[str, Any]:
        """
        Get tweet by ID.

        Args:
            tweet_id: Tweet ID
            expansions: Data expansions
            tweet_fields: Tweet fields to include

        Returns:
            Tweet data
        """
        params = {}
        if expansions:
            params["expansions"] = ",".join(expansions)
        if tweet_fields:
            params["tweet.fields"] = ",".join(tweet_fields)

        result = await self._request(
            "GET",
            f"tweets/{tweet_id}",
            params=params,
            rate_limit_endpoint="get"
        )

        return result.get("data", {})

    async def get_tweets(
        self,
        tweet_ids: List[str],
        expansions: List[str] = None,
        tweet_fields: List[str] = None
    ) -> List[Dict[str, Any]]:
        """Get multiple tweets by IDs"""
        params = {"ids": ",".join(tweet_ids)}
        if expansions:
            params["expansions"] = ",".join(expansions)
        if tweet_fields:
            params["tweet.fields"] = ",".join(tweet_fields)

        result = await self._request(
            "GET",
            "tweets",
            params=params,
            rate_limit_endpoint="get"
        )

        return result.get("data", [])

    # ========== Media Operations ==========

    async def upload_media(
        self,
        media_url: str,
        media_type: MediaType = MediaType.IMAGE,
        alt_text: str = None
    ) -> MediaUpload:
        """
        Upload media for use in tweets.

        Note: Uses v1.1 media upload endpoint.

        Args:
            media_url: URL to media file
            media_type: Type of media
            alt_text: Accessibility alt text

        Returns:
            MediaUpload with media_id
        """
        if not self._client:
            self._client = httpx.AsyncClient(timeout=60)  # Longer timeout for uploads

        # Download media from URL
        media_response = await self._client.get(media_url)
        media_data = media_response.content

        # Upload to Twitter
        headers = self._get_auth_headers()

        # For images, use simple upload
        if media_type == MediaType.IMAGE:
            files = {"media": media_data}
            response = await self._client.post(
                f"{self.UPLOAD_BASE}/media/upload.json",
                files=files,
                headers=headers
            )
        else:
            # For video/GIF, would need chunked upload
            # Simplified implementation
            response = await self._client.post(
                f"{self.UPLOAD_BASE}/media/upload.json",
                files={"media": media_data},
                data={"media_category": media_type.value},
                headers=headers
            )

        result = response.json()

        if "media_id_string" not in result:
            raise TwitterAPIError("Failed to upload media", code=response.status_code)

        media_id = result["media_id_string"]

        # Add alt text if provided
        if alt_text:
            await self._client.post(
                f"{self.UPLOAD_BASE}/media/metadata/create.json",
                json={
                    "media_id": media_id,
                    "alt_text": {"text": alt_text}
                },
                headers=headers
            )

        self.logger.info("Media uploaded", media_id=media_id, type=media_type.value)

        return MediaUpload(
            media_id=media_id,
            media_type=media_type,
            url=media_url,
            alt_text=alt_text,
            upload_status="succeeded"
        )

    # ========== User Operations ==========

    async def get_me(self) -> Dict[str, Any]:
        """Get authenticated user info"""
        result = await self._request(
            "GET",
            "users/me",
            params={"user.fields": "id,name,username,profile_image_url,public_metrics"},
            rate_limit_endpoint="users/me"
        )
        return result.get("data", {})

    # ========== Rate Limits ==========

    def get_rate_limits(self, endpoint: str = None) -> Dict[str, Any]:
        """Get current rate limit status"""
        return self.rate_limiter.get_rate_limit_info(endpoint)


# Convenience function
async def create_twitter_client(config: TwitterConfig = None) -> TwitterAPIClient:
    """Create a Twitter client"""
    return TwitterAPIClient(config)


async def demo_twitter_client():
    """Demo the Twitter client"""
    print("Twitter API Client Demo")
    print("=" * 40)
    print("Note: This demo requires Twitter API credentials")
    print("Set: TWITTER_ACCESS_TOKEN, TWITTER_BEARER_TOKEN")

    print("\nExample usage:")
    print("```python")
    print("async with TwitterAPIClient() as client:")
    print("    # Create tweet")
    print("    tweet = Tweet(text='Hello Twitter!')")
    print("    tweet_id = await client.create_tweet(tweet)")
    print("")
    print("    # Create thread")
    print("    thread = TweetThread(tweets=[")
    print("        Tweet(text='1/3 First tweet'),")
    print("        Tweet(text='2/3 Second tweet'),")
    print("        Tweet(text='3/3 Third tweet')")
    print("    ])")
    print("    ids = await client.create_thread(thread)")
    print("")
    print("    # Check rate limits")
    print("    limits = client.get_rate_limits()")
    print("```")


if __name__ == "__main__":
    asyncio.run(demo_twitter_client())
