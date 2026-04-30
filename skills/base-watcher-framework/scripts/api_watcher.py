#!/usr/bin/env python3
"""
APIWatcher - Monitor REST APIs and web endpoints for changes.

Polls HTTP endpoints and detects changes in response data.
Supports various change detection strategies and authentication methods.
"""

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from enum import Enum

try:
    import aiohttp
except ImportError:
    aiohttp = None

from base_watcher import BaseWatcher, WatcherConfig, WatcherEvent, EventType


class ChangeStrategy(Enum):
    """Strategies for detecting changes in API responses."""
    FULL_HASH = "full_hash"      # Hash entire response
    FIELD_COMPARE = "field"      # Compare specific fields
    TIMESTAMP = "timestamp"      # Use response timestamp field
    ETAG = "etag"               # Use HTTP ETag header
    CUSTOM = "custom"            # Custom comparison function


class AuthType(Enum):
    """Authentication types for API requests."""
    NONE = "none"
    BEARER = "bearer"
    BASIC = "basic"
    API_KEY = "api_key"
    CUSTOM = "custom"


@dataclass
class APIWatcherConfig(WatcherConfig):
    """
    Configuration for APIWatcher.
    
    Attributes:
        url: Endpoint URL to monitor
        method: HTTP method (GET, POST, etc.)
        headers: Additional request headers
        params: Query parameters
        body: Request body for POST/PUT
        auth_type: Authentication method
        auth_credentials: Auth credentials (token, username:password, etc.)
        change_strategy: How to detect changes
        compare_fields: Fields to compare (for FIELD_COMPARE strategy)
        timestamp_field: Field containing timestamp (for TIMESTAMP strategy)
        timeout: Request timeout in seconds
        success_codes: HTTP codes considered successful
    """
    url: str = ""
    method: str = "GET"
    headers: dict = field(default_factory=dict)
    params: dict = field(default_factory=dict)
    body: Optional[dict] = None
    auth_type: AuthType = AuthType.NONE
    auth_credentials: str = ""
    change_strategy: ChangeStrategy = ChangeStrategy.FULL_HASH
    compare_fields: list = field(default_factory=list)
    timestamp_field: str = "updated_at"
    timeout: float = 30.0
    success_codes: list = field(default_factory=lambda: [200, 201])


class APIWatcher(BaseWatcher):
    """
    Watcher that monitors REST API endpoints for changes.
    
    Polls an HTTP endpoint and detects changes based on configured strategy.
    
    Example:
        config = APIWatcherConfig(
            name="github-releases",
            url="https://api.github.com/repos/owner/repo/releases/latest",
            auth_type=AuthType.BEARER,
            auth_credentials="ghp_xxxxx",
            change_strategy=ChangeStrategy.FIELD_COMPARE,
            compare_fields=["tag_name", "published_at"],
            poll_interval=60.0
        )
        
        watcher = APIWatcher(config)
        watcher.on_event(lambda e: print(f"New release: {e.data}"))
        
        await watcher.start()
    """
    
    def __init__(self, config: APIWatcherConfig):
        if aiohttp is None:
            raise ImportError("aiohttp is required for APIWatcher: pip install aiohttp")
        
        super().__init__(config)
        self.api_config = config
        self._session: Optional[aiohttp.ClientSession] = None
        self._last_hash: Optional[str] = None
        self._last_data: Optional[dict] = None
        self._last_etag: Optional[str] = None
        self._custom_comparator: Optional[Callable[[Any, Any], bool]] = None
    
    def set_comparator(self, func: Callable[[Any, Any], bool]) -> "APIWatcher":
        """
        Set custom comparison function for CUSTOM strategy.
        
        Args:
            func: Function(old_data, new_data) -> bool indicating change
            
        Returns:
            Self for chaining
        """
        self._custom_comparator = func
        return self
    
    async def _setup(self) -> None:
        """Initialize HTTP session."""
        headers = self._build_headers()
        timeout = aiohttp.ClientTimeout(total=self.api_config.timeout)
        self._session = aiohttp.ClientSession(headers=headers, timeout=timeout)
        
        # Initial fetch to establish baseline
        data, etag = await self._fetch()
        self._last_hash = self._hash_data(data)
        self._last_data = data
        self._last_etag = etag
    
    async def _teardown(self) -> None:
        """Close HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None
    
    async def _poll(self) -> list[WatcherEvent]:
        """Poll API endpoint for changes."""
        events = []
        
        try:
            data, etag = await self._fetch()
            
            if self._has_changed(data, etag):
                events.append(self._create_api_event(data))
                
                # Update state
                self._last_hash = self._hash_data(data)
                self._last_data = data
                self._last_etag = etag
                
        except aiohttp.ClientError as e:
            events.append(self._create_event(
                EventType.ERROR,
                data={"error": str(e), "url": self.api_config.url},
                source=self.api_config.url
            ))
        
        return events
    
    async def _fetch(self) -> tuple[Any, Optional[str]]:
        """Fetch data from the API endpoint."""
        method = self.api_config.method.upper()
        
        kwargs = {"params": self.api_config.params}
        if self.api_config.body and method in ("POST", "PUT", "PATCH"):
            kwargs["json"] = self.api_config.body
        
        # Add ETag header for conditional requests
        headers = {}
        if self._last_etag and self.api_config.change_strategy == ChangeStrategy.ETAG:
            headers["If-None-Match"] = self._last_etag
        
        async with self._session.request(
            method,
            self.api_config.url,
            headers=headers,
            **kwargs
        ) as response:
            # Handle 304 Not Modified
            if response.status == 304:
                return self._last_data, self._last_etag
            
            if response.status not in self.api_config.success_codes:
                raise aiohttp.ClientResponseError(
                    response.request_info,
                    response.history,
                    status=response.status,
                    message=f"Unexpected status: {response.status}"
                )
            
            etag = response.headers.get("ETag")
            
            content_type = response.headers.get("Content-Type", "")
            if "application/json" in content_type:
                data = await response.json()
            else:
                data = await response.text()
            
            return data, etag
    
    def _build_headers(self) -> dict:
        """Build request headers including authentication."""
        headers = dict(self.api_config.headers)
        headers.setdefault("Accept", "application/json")
        
        auth = self.api_config.auth_type
        creds = self.api_config.auth_credentials
        
        if auth == AuthType.BEARER:
            headers["Authorization"] = f"Bearer {creds}"
        elif auth == AuthType.API_KEY:
            # Assume header name is in format "X-API-Key:value"
            if ":" in creds:
                key, value = creds.split(":", 1)
                headers[key] = value
            else:
                headers["X-API-Key"] = creds
        elif auth == AuthType.BASIC:
            import base64
            encoded = base64.b64encode(creds.encode()).decode()
            headers["Authorization"] = f"Basic {encoded}"
        
        return headers
    
    def _hash_data(self, data: Any) -> str:
        """Create hash of data for comparison."""
        if isinstance(data, dict):
            serialized = json.dumps(data, sort_keys=True)
        else:
            serialized = str(data)
        return hashlib.sha256(serialized.encode()).hexdigest()
    
    def _has_changed(self, data: Any, etag: Optional[str]) -> bool:
        """Determine if data has changed based on strategy."""
        strategy = self.api_config.change_strategy
        
        if strategy == ChangeStrategy.ETAG:
            if etag and self._last_etag:
                return etag != self._last_etag
            # Fall back to hash if no etag
            return self._hash_data(data) != self._last_hash
        
        if strategy == ChangeStrategy.FULL_HASH:
            return self._hash_data(data) != self._last_hash
        
        if strategy == ChangeStrategy.FIELD_COMPARE:
            if not isinstance(data, dict) or not isinstance(self._last_data, dict):
                return self._hash_data(data) != self._last_hash
            
            for field_path in self.api_config.compare_fields:
                old_val = self._get_nested(self._last_data, field_path)
                new_val = self._get_nested(data, field_path)
                if old_val != new_val:
                    return True
            return False
        
        if strategy == ChangeStrategy.TIMESTAMP:
            if not isinstance(data, dict):
                return True
            
            new_ts = self._get_nested(data, self.api_config.timestamp_field)
            old_ts = self._get_nested(self._last_data or {}, self.api_config.timestamp_field)
            return new_ts != old_ts
        
        if strategy == ChangeStrategy.CUSTOM:
            if self._custom_comparator:
                return self._custom_comparator(self._last_data, data)
            return self._hash_data(data) != self._last_hash
        
        return False
    
    def _get_nested(self, data: dict, path: str) -> Any:
        """Get nested value from dict using dot notation."""
        parts = path.split(".")
        current = data
        
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list) and part.isdigit():
                idx = int(part)
                current = current[idx] if idx < len(current) else None
            else:
                return None
        
        return current
    
    def _create_api_event(self, data: Any) -> WatcherEvent:
        """Create an API change event."""
        changes = {}
        
        if self.api_config.change_strategy == ChangeStrategy.FIELD_COMPARE:
            if isinstance(data, dict) and isinstance(self._last_data, dict):
                for field_path in self.api_config.compare_fields:
                    old_val = self._get_nested(self._last_data, field_path)
                    new_val = self._get_nested(data, field_path)
                    if old_val != new_val:
                        changes[field_path] = {"old": old_val, "new": new_val}
        
        return self._create_event(
            EventType.MODIFIED,
            data={
                "response": data,
                "changes": changes,
                "url": self.api_config.url
            },
            source=self.api_config.url
        )


# Convenience function
def watch_api(
    url: str,
    poll_interval: float = 60.0,
    auth_token: Optional[str] = None,
    compare_fields: Optional[list] = None
) -> APIWatcher:
    """
    Create an APIWatcher with common defaults.
    
    Args:
        url: API endpoint URL
        poll_interval: Seconds between polls
        auth_token: Bearer token for authentication
        compare_fields: Fields to compare for changes
        
    Returns:
        Configured APIWatcher instance
    """
    config = APIWatcherConfig(
        name=f"api-watcher-{hash(url) % 10000}",
        url=url,
        poll_interval=poll_interval,
        auth_type=AuthType.BEARER if auth_token else AuthType.NONE,
        auth_credentials=auth_token or "",
        change_strategy=ChangeStrategy.FIELD_COMPARE if compare_fields else ChangeStrategy.FULL_HASH,
        compare_fields=compare_fields or []
    )
    return APIWatcher(config)
