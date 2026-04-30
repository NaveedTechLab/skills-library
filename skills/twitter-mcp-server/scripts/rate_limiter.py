#!/usr/bin/env python3
"""
Rate Limiter for Twitter MCP Server

Tracks and enforces Twitter API rate limits.
"""

import threading
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

import structlog

from .models import RateLimitInfo, TwitterConfig

logger = structlog.get_logger()


# Twitter API v2 rate limits (per 15-minute window)
RATE_LIMITS = {
    "tweets/create": {"limit": 200, "window": 900},  # POST /2/tweets
    "tweets/delete": {"limit": 50, "window": 900},   # DELETE /2/tweets/:id
    "tweets/get": {"limit": 300, "window": 900},     # GET /2/tweets/:id
    "tweets/search": {"limit": 450, "window": 900},  # GET /2/tweets/search/recent
    "media/upload": {"limit": 615, "window": 900},   # POST /1.1/media/upload
    "users/me": {"limit": 75, "window": 900},        # GET /2/users/me
}


class RateLimiter:
    """
    Rate limiter for Twitter API.

    Tracks request counts and enforces limits based on response headers.
    """

    def __init__(self, config: TwitterConfig = None):
        self.config = config or TwitterConfig()
        self.lock = threading.Lock()
        self.logger = logger.bind(component="RateLimiter")

        # Track rate limits per endpoint
        self._limits: Dict[str, RateLimitInfo] = {}

        # Track request counts
        self._request_counts: Dict[str, int] = {}
        self._window_starts: Dict[str, datetime] = {}

    def check_rate_limit(self, endpoint: str) -> Tuple[bool, Optional[str]]:
        """
        Check if we can make a request to the endpoint.

        Args:
            endpoint: Endpoint identifier (e.g., "tweets/create")

        Returns:
            Tuple of (allowed, reason)
        """
        with self.lock:
            limits = RATE_LIMITS.get(endpoint)
            if not limits:
                return True, None

            now = datetime.now()

            # Get or initialize window
            window_start = self._window_starts.get(endpoint)
            if not window_start or (now - window_start).total_seconds() >= limits["window"]:
                # Reset window
                self._window_starts[endpoint] = now
                self._request_counts[endpoint] = 0
                return True, None

            # Check current count
            current_count = self._request_counts.get(endpoint, 0)
            limit = limits["limit"]

            # Calculate percentage used
            percentage = (current_count / limit) * 100 if limit > 0 else 0

            # Check if blocked
            if percentage >= self.config.block_at_percentage:
                seconds_left = limits["window"] - int((now - window_start).total_seconds())
                return False, f"Rate limit reached ({current_count}/{limit}). Resets in {seconds_left}s"

            # Warn if approaching limit
            if percentage >= self.config.warn_at_percentage:
                self.logger.warning(
                    "Approaching rate limit",
                    endpoint=endpoint,
                    used=current_count,
                    limit=limit,
                    percentage=f"{percentage:.1f}%"
                )

            return True, None

    def record_request(self, endpoint: str):
        """Record a request to an endpoint"""
        with self.lock:
            self._request_counts[endpoint] = self._request_counts.get(endpoint, 0) + 1

    def update_from_headers(self, endpoint: str, headers: Dict[str, str]):
        """
        Update rate limit info from response headers.

        Twitter returns these headers:
        - x-rate-limit-limit: Request limit
        - x-rate-limit-remaining: Requests remaining
        - x-rate-limit-reset: Unix timestamp when limit resets
        """
        with self.lock:
            try:
                limit = int(headers.get("x-rate-limit-limit", 0))
                remaining = int(headers.get("x-rate-limit-remaining", 0))
                reset_timestamp = int(headers.get("x-rate-limit-reset", 0))

                if limit > 0:
                    reset_at = datetime.fromtimestamp(reset_timestamp)
                    self._limits[endpoint] = RateLimitInfo(
                        endpoint=endpoint,
                        limit=limit,
                        remaining=remaining,
                        reset_at=reset_at,
                        used=limit - remaining
                    )

                    # Also update our tracking
                    self._request_counts[endpoint] = limit - remaining

                    self.logger.debug(
                        "Rate limit updated",
                        endpoint=endpoint,
                        remaining=remaining,
                        limit=limit
                    )

            except (ValueError, TypeError) as e:
                self.logger.warning("Failed to parse rate limit headers", error=str(e))

    def get_rate_limit_info(self, endpoint: str = None) -> Dict[str, Any]:
        """
        Get rate limit information.

        Args:
            endpoint: Specific endpoint, or None for all

        Returns:
            Rate limit information
        """
        with self.lock:
            if endpoint:
                info = self._limits.get(endpoint)
                if info:
                    return {
                        "endpoint": info.endpoint,
                        "limit": info.limit,
                        "remaining": info.remaining,
                        "used": info.used,
                        "percentage_used": info.percentage_used,
                        "reset_at": info.reset_at.isoformat(),
                        "seconds_until_reset": info.seconds_until_reset
                    }

                # Return estimated info
                limits = RATE_LIMITS.get(endpoint, {"limit": 0, "window": 900})
                count = self._request_counts.get(endpoint, 0)
                return {
                    "endpoint": endpoint,
                    "limit": limits["limit"],
                    "remaining": max(0, limits["limit"] - count),
                    "used": count,
                    "percentage_used": (count / limits["limit"] * 100) if limits["limit"] > 0 else 0,
                    "estimated": True
                }

            # Return all tracked limits
            all_info = {}
            for ep, limits in RATE_LIMITS.items():
                info = self._limits.get(ep)
                if info:
                    all_info[ep] = {
                        "limit": info.limit,
                        "remaining": info.remaining,
                        "used": info.used,
                        "percentage_used": info.percentage_used,
                        "reset_at": info.reset_at.isoformat(),
                        "seconds_until_reset": info.seconds_until_reset
                    }
                else:
                    count = self._request_counts.get(ep, 0)
                    all_info[ep] = {
                        "limit": limits["limit"],
                        "remaining": max(0, limits["limit"] - count),
                        "used": count,
                        "percentage_used": (count / limits["limit"] * 100) if limits["limit"] > 0 else 0,
                        "estimated": True
                    }

            return all_info

    def wait_for_reset(self, endpoint: str) -> int:
        """
        Get seconds to wait for rate limit reset.

        Args:
            endpoint: Endpoint to check

        Returns:
            Seconds to wait (0 if no wait needed)
        """
        with self.lock:
            info = self._limits.get(endpoint)
            if info and info.remaining == 0:
                return info.seconds_until_reset

            # Check local tracking
            window_start = self._window_starts.get(endpoint)
            if window_start:
                limits = RATE_LIMITS.get(endpoint, {"window": 900})
                elapsed = (datetime.now() - window_start).total_seconds()
                if elapsed < limits["window"]:
                    current_count = self._request_counts.get(endpoint, 0)
                    if current_count >= limits.get("limit", float("inf")):
                        return int(limits["window"] - elapsed)

            return 0

    def reset_endpoint(self, endpoint: str):
        """Manually reset tracking for an endpoint"""
        with self.lock:
            if endpoint in self._limits:
                del self._limits[endpoint]
            if endpoint in self._request_counts:
                del self._request_counts[endpoint]
            if endpoint in self._window_starts:
                del self._window_starts[endpoint]

    def reset_all(self):
        """Reset all tracking"""
        with self.lock:
            self._limits.clear()
            self._request_counts.clear()
            self._window_starts.clear()
