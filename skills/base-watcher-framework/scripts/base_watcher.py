#!/usr/bin/env python3
"""
BaseWatcher - Abstract base class for continuous monitoring and event emission.

This module provides the core abstraction for building watchers that monitor
various sources and emit events to Obsidian vault folders as Markdown files.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional
import asyncio
import logging
import uuid

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Standard event types for watchers."""
    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    ERROR = "error"
    INFO = "info"
    WARNING = "warning"
    CUSTOM = "custom"


class WatcherState(Enum):
    """Watcher lifecycle states."""
    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class WatcherEvent:
    """
    Represents an event captured by a watcher.
    
    Attributes:
        event_type: Type of event (created, modified, deleted, etc.)
        source: Identifier of the source that generated the event
        data: Event payload (varies by watcher type)
        timestamp: When the event occurred
        watcher_name: Name of the watcher that captured the event
        event_id: Unique identifier for the event
        metadata: Additional context about the event
    """
    event_type: EventType
    source: str
    data: Any
    timestamp: datetime = field(default_factory=datetime.now)
    watcher_name: str = ""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    metadata: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert event to dictionary representation."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "source": self.source,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "watcher_name": self.watcher_name,
            "metadata": self.metadata
        }


@dataclass
class WatcherConfig:
    """
    Configuration for a watcher instance.
    
    Attributes:
        name: Unique identifier for this watcher
        poll_interval: Seconds between poll cycles (for polling watchers)
        retry_attempts: Number of retries on failure
        retry_delay: Seconds between retry attempts
        enabled: Whether the watcher is active
        filters: Event filters to apply
        custom_config: Watcher-specific configuration
    """
    name: str
    poll_interval: float = 5.0
    retry_attempts: int = 3
    retry_delay: float = 1.0
    enabled: bool = True
    filters: dict = field(default_factory=dict)
    custom_config: dict = field(default_factory=dict)


class BaseWatcher(ABC):
    """
    Abstract base class for all watchers.
    
    Subclasses must implement:
        - _setup(): Initialize watcher resources
        - _teardown(): Clean up resources
        - _poll() or _watch(): Monitor for events
        
    Example:
        class MyWatcher(BaseWatcher):
            async def _setup(self):
                self.connection = await connect_to_source()
                
            async def _teardown(self):
                await self.connection.close()
                
            async def _poll(self) -> list[WatcherEvent]:
                data = await self.connection.fetch_changes()
                return [self._create_event(EventType.MODIFIED, item) for item in data]
    """
    
    def __init__(self, config: WatcherConfig):
        """
        Initialize the watcher with configuration.
        
        Args:
            config: WatcherConfig instance with watcher settings
        """
        self.config = config
        self._state = WatcherState.IDLE
        self._event_handlers: list[Callable[[WatcherEvent], None]] = []
        self._error_handlers: list[Callable[[Exception], None]] = []
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        
    @property
    def name(self) -> str:
        """Get watcher name."""
        return self.config.name
    
    @property
    def state(self) -> WatcherState:
        """Get current watcher state."""
        return self._state
    
    @property
    def is_running(self) -> bool:
        """Check if watcher is actively running."""
        return self._state == WatcherState.RUNNING
    
    def on_event(self, handler: Callable[[WatcherEvent], None]) -> "BaseWatcher":
        """
        Register an event handler.
        
        Args:
            handler: Callback function that receives WatcherEvent instances
            
        Returns:
            Self for method chaining
        """
        self._event_handlers.append(handler)
        return self
    
    def on_error(self, handler: Callable[[Exception], None]) -> "BaseWatcher":
        """
        Register an error handler.
        
        Args:
            handler: Callback function that receives exceptions
            
        Returns:
            Self for method chaining
        """
        self._error_handlers.append(handler)
        return self
    
    async def start(self) -> None:
        """
        Start the watcher.
        
        Initializes resources and begins monitoring.
        """
        if self._state in (WatcherState.RUNNING, WatcherState.STARTING):
            logger.warning(f"Watcher {self.name} is already running or starting")
            return
            
        self._state = WatcherState.STARTING
        self._stop_event.clear()
        
        try:
            await self._setup()
            self._state = WatcherState.RUNNING
            self._task = asyncio.create_task(self._run_loop())
            logger.info(f"Watcher {self.name} started")
        except Exception as e:
            self._state = WatcherState.ERROR
            self._emit_error(e)
            raise
    
    async def stop(self) -> None:
        """
        Stop the watcher gracefully.
        
        Signals the monitoring loop to stop and cleans up resources.
        """
        if self._state in (WatcherState.STOPPED, WatcherState.STOPPING):
            return
            
        self._state = WatcherState.STOPPING
        self._stop_event.set()
        
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=10.0)
            except asyncio.TimeoutError:
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
        
        try:
            await self._teardown()
        except Exception as e:
            logger.error(f"Error during teardown: {e}")
            
        self._state = WatcherState.STOPPED
        logger.info(f"Watcher {self.name} stopped")
    
    async def pause(self) -> None:
        """Pause the watcher temporarily."""
        if self._state == WatcherState.RUNNING:
            self._state = WatcherState.PAUSED
            logger.info(f"Watcher {self.name} paused")
    
    async def resume(self) -> None:
        """Resume a paused watcher."""
        if self._state == WatcherState.PAUSED:
            self._state = WatcherState.RUNNING
            logger.info(f"Watcher {self.name} resumed")
    
    async def _run_loop(self) -> None:
        """Main monitoring loop."""
        retry_count = 0
        
        while not self._stop_event.is_set():
            if self._state == WatcherState.PAUSED:
                await asyncio.sleep(0.1)
                continue
                
            try:
                events = await self._poll()
                retry_count = 0  # Reset on success
                
                for event in events:
                    if self._should_emit(event):
                        event.watcher_name = self.name
                        self._emit_event(event)
                        
            except Exception as e:
                retry_count += 1
                self._emit_error(e)
                
                if retry_count >= self.config.retry_attempts:
                    logger.error(f"Max retries reached for {self.name}")
                    self._state = WatcherState.ERROR
                    break
                    
                await asyncio.sleep(self.config.retry_delay)
                continue
            
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self.config.poll_interval
                )
            except asyncio.TimeoutError:
                pass
    
    def _emit_event(self, event: WatcherEvent) -> None:
        """Dispatch event to all registered handlers."""
        for handler in self._event_handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Error in event handler: {e}")
    
    def _emit_error(self, error: Exception) -> None:
        """Dispatch error to all registered handlers."""
        for handler in self._error_handlers:
            try:
                handler(error)
            except Exception as e:
                logger.error(f"Error in error handler: {e}")
    
    def _should_emit(self, event: WatcherEvent) -> bool:
        """
        Check if event passes configured filters.
        
        Override in subclasses for custom filtering logic.
        """
        filters = self.config.filters
        
        if "event_types" in filters:
            if event.event_type.value not in filters["event_types"]:
                return False
                
        return True
    
    def _create_event(
        self,
        event_type: EventType,
        data: Any,
        source: Optional[str] = None,
        **metadata
    ) -> WatcherEvent:
        """
        Factory method to create events with consistent defaults.
        
        Args:
            event_type: Type of event
            data: Event payload
            source: Event source (defaults to watcher name)
            **metadata: Additional metadata fields
            
        Returns:
            Configured WatcherEvent instance
        """
        return WatcherEvent(
            event_type=event_type,
            source=source or self.name,
            data=data,
            watcher_name=self.name,
            metadata=metadata
        )
    
    @abstractmethod
    async def _setup(self) -> None:
        """
        Initialize watcher resources.
        
        Called once when the watcher starts.
        Subclasses should set up connections, file handles, etc.
        """
        pass
    
    @abstractmethod
    async def _teardown(self) -> None:
        """
        Clean up watcher resources.
        
        Called when the watcher stops.
        Subclasses should close connections, release handles, etc.
        """
        pass
    
    @abstractmethod
    async def _poll(self) -> list[WatcherEvent]:
        """
        Poll for new events.
        
        Called periodically based on poll_interval.
        
        Returns:
            List of events captured since last poll
        """
        pass
