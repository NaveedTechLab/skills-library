# Extending the BaseWatcher Framework

This guide covers creating custom watchers, custom emitters, and advanced patterns.

## Table of Contents

1. [Creating Custom Watchers](#creating-custom-watchers)
2. [Custom Event Types](#custom-event-types)
3. [Custom Emitters](#custom-emitters)
4. [Advanced Patterns](#advanced-patterns)
5. [Testing Watchers](#testing-watchers)

---

## Creating Custom Watchers

### Basic Structure

```python
from base_watcher import BaseWatcher, WatcherConfig, WatcherEvent, EventType
from dataclasses import dataclass, field

@dataclass
class MyWatcherConfig(WatcherConfig):
    """Custom config extending base."""
    my_setting: str = ""
    my_list: list = field(default_factory=list)

class MyWatcher(BaseWatcher):
    def __init__(self, config: MyWatcherConfig):
        super().__init__(config)
        self.my_config = config
        self._state = {}  # Internal state
    
    async def _setup(self) -> None:
        """Called once when watcher starts."""
        # Initialize connections, build initial state
        self._state = await self._fetch_initial_state()
    
    async def _teardown(self) -> None:
        """Called when watcher stops."""
        # Close connections, clean up
        self._state.clear()
    
    async def _poll(self) -> list[WatcherEvent]:
        """Called every poll_interval seconds."""
        events = []
        current = await self._fetch_current_state()
        
        # Compare and generate events
        for key, value in current.items():
            if key not in self._state:
                events.append(self._create_event(
                    EventType.CREATED,
                    data={"key": key, "value": value},
                    source=key
                ))
        
        self._state = current
        return events
    
    async def _fetch_initial_state(self) -> dict:
        # Implementation
        pass
    
    async def _fetch_current_state(self) -> dict:
        # Implementation
        pass
```

### Database Watcher Example

```python
@dataclass
class DBWatcherConfig(WatcherConfig):
    connection_string: str = ""
    table: str = ""
    id_column: str = "id"
    timestamp_column: str = "updated_at"

class DatabaseWatcher(BaseWatcher):
    def __init__(self, config: DBWatcherConfig):
        super().__init__(config)
        self.db_config = config
        self._last_timestamp = None
        self._conn = None
    
    async def _setup(self) -> None:
        import aiosqlite  # or asyncpg, aiomysql
        self._conn = await aiosqlite.connect(self.db_config.connection_string)
        
        # Get max timestamp
        async with self._conn.execute(
            f"SELECT MAX({self.db_config.timestamp_column}) FROM {self.db_config.table}"
        ) as cursor:
            row = await cursor.fetchone()
            self._last_timestamp = row[0]
    
    async def _teardown(self) -> None:
        if self._conn:
            await self._conn.close()
    
    async def _poll(self) -> list[WatcherEvent]:
        events = []
        
        query = f"""
            SELECT * FROM {self.db_config.table}
            WHERE {self.db_config.timestamp_column} > ?
            ORDER BY {self.db_config.timestamp_column}
        """
        
        async with self._conn.execute(query, (self._last_timestamp,)) as cursor:
            async for row in cursor:
                events.append(self._create_event(
                    EventType.MODIFIED,
                    data=dict(row),
                    source=f"{self.db_config.table}:{row[self.db_config.id_column]}"
                ))
                self._last_timestamp = row[self.db_config.timestamp_column]
        
        return events
```

### Message Queue Watcher Example

```python
@dataclass 
class MQWatcherConfig(WatcherConfig):
    broker_url: str = ""
    queue_name: str = ""
    prefetch_count: int = 10

class MessageQueueWatcher(BaseWatcher):
    def __init__(self, config: MQWatcherConfig):
        super().__init__(config)
        self.mq_config = config
        self._messages = []
    
    async def _setup(self) -> None:
        import aio_pika
        self._connection = await aio_pika.connect(self.mq_config.broker_url)
        self._channel = await self._connection.channel()
        self._queue = await self._channel.declare_queue(self.mq_config.queue_name)
        
        # Start consuming
        await self._queue.consume(self._on_message, no_ack=False)
    
    async def _on_message(self, message):
        """Buffer incoming messages."""
        self._messages.append(message)
    
    async def _teardown(self) -> None:
        await self._connection.close()
    
    async def _poll(self) -> list[WatcherEvent]:
        events = []
        
        # Process buffered messages
        while self._messages:
            msg = self._messages.pop(0)
            events.append(self._create_event(
                EventType.INFO,
                data={"body": msg.body.decode(), "routing_key": msg.routing_key},
                source=self.mq_config.queue_name
            ))
            await msg.ack()
        
        return events
```

---

## Custom Event Types

### Extending EventType

```python
from enum import Enum
from base_watcher import EventType

class MyEventType(Enum):
    # Include base types
    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    ERROR = "error"
    
    # Add custom types
    THRESHOLD_EXCEEDED = "threshold_exceeded"
    HEALTH_CHECK = "health_check"
    SYNC_STARTED = "sync_started"
    SYNC_COMPLETED = "sync_completed"
```

### Using Custom Types

```python
class MetricsWatcher(BaseWatcher):
    async def _poll(self) -> list[WatcherEvent]:
        metrics = await self._fetch_metrics()
        events = []
        
        for metric, value in metrics.items():
            if value > self.config.custom_config.get("threshold", 100):
                events.append(WatcherEvent(
                    event_type=MyEventType.THRESHOLD_EXCEEDED,  # Custom type
                    source=metric,
                    data={"metric": metric, "value": value, "threshold": 100},
                    watcher_name=self.name
                ))
        
        return events
```

---

## Custom Emitters

### JSON File Emitter

```python
import json
from pathlib import Path
from base_watcher import WatcherEvent

class JSONEmitter:
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def emit(self, event: WatcherEvent) -> Path:
        filename = f"{event.timestamp.strftime('%Y%m%d_%H%M%S')}_{event.event_id}.json"
        filepath = self.output_dir / filename
        
        filepath.write_text(json.dumps(event.to_dict(), indent=2))
        return filepath
```

### Webhook Emitter

```python
import aiohttp
from base_watcher import WatcherEvent

class WebhookEmitter:
    def __init__(self, webhook_url: str, headers: dict = None):
        self.url = webhook_url
        self.headers = headers or {}
        self._session = None
    
    async def setup(self):
        self._session = aiohttp.ClientSession(headers=self.headers)
    
    async def teardown(self):
        if self._session:
            await self._session.close()
    
    async def emit(self, event: WatcherEvent):
        async with self._session.post(self.url, json=event.to_dict()) as resp:
            return resp.status == 200
```

### Multi-Target Emitter

```python
class MultiEmitter:
    def __init__(self):
        self._emitters = []
    
    def add(self, emitter) -> "MultiEmitter":
        self._emitters.append(emitter)
        return self
    
    def emit(self, event: WatcherEvent):
        for emitter in self._emitters:
            try:
                emitter.emit(event)
            except Exception as e:
                logger.error(f"Emitter failed: {e}")
```

---

## Advanced Patterns

### Event Filtering

```python
class FilteredRegistry(WatcherRegistry):
    def __init__(self):
        super().__init__()
        self._filters = []
    
    def add_filter(self, filter_fn) -> "FilteredRegistry":
        self._filters.append(filter_fn)
        return self
    
    def _handle_event(self, event: WatcherEvent) -> None:
        # Apply filters
        for filter_fn in self._filters:
            if not filter_fn(event):
                return  # Event filtered out
        
        super()._handle_event(event)

# Usage
registry = FilteredRegistry()
registry.add_filter(lambda e: e.event_type != EventType.INFO)  # Skip INFO
registry.add_filter(lambda e: "temp" not in e.source)  # Skip temp files
```

### Event Aggregation

```python
from collections import defaultdict
from datetime import timedelta

class EventAggregator:
    def __init__(self, window: timedelta = timedelta(seconds=60)):
        self.window = window
        self._buffer = defaultdict(list)
        self._handlers = []
    
    def on_aggregate(self, handler):
        self._handlers.append(handler)
    
    def collect(self, event: WatcherEvent):
        key = (event.watcher_name, event.event_type)
        self._buffer[key].append(event)
    
    async def flush(self):
        """Call periodically to emit aggregated events."""
        for key, events in self._buffer.items():
            if events:
                aggregated = {
                    "watcher": key[0],
                    "event_type": key[1].value,
                    "count": len(events),
                    "events": [e.to_dict() for e in events]
                }
                for handler in self._handlers:
                    handler(aggregated)
        
        self._buffer.clear()
```

### Backpressure Handling

```python
import asyncio

class BackpressureWatcher(BaseWatcher):
    def __init__(self, config, max_queue_size: int = 1000):
        super().__init__(config)
        self._queue = asyncio.Queue(maxsize=max_queue_size)
    
    async def _poll(self) -> list[WatcherEvent]:
        events = await self._fetch_events()
        
        result = []
        for event in events:
            try:
                self._queue.put_nowait(event)
                result.append(event)
            except asyncio.QueueFull:
                # Drop oldest, add newest
                try:
                    self._queue.get_nowait()
                    self._queue.put_nowait(event)
                    result.append(event)
                except:
                    pass  # Queue state changed
        
        return result
```

---

## Testing Watchers

### Unit Testing

```python
import pytest
import asyncio
from base_watcher import WatcherConfig, EventType

class TestMyWatcher:
    @pytest.fixture
    def config(self):
        return MyWatcherConfig(
            name="test-watcher",
            poll_interval=0.1
        )
    
    @pytest.fixture
    def watcher(self, config):
        return MyWatcher(config)
    
    @pytest.mark.asyncio
    async def test_setup(self, watcher):
        await watcher._setup()
        assert watcher._state is not None
    
    @pytest.mark.asyncio
    async def test_poll_returns_events(self, watcher):
        await watcher._setup()
        events = await watcher._poll()
        assert isinstance(events, list)
    
    @pytest.mark.asyncio
    async def test_lifecycle(self, watcher):
        events_received = []
        watcher.on_event(lambda e: events_received.append(e))
        
        await watcher.start()
        await asyncio.sleep(0.3)  # Allow some polls
        await watcher.stop()
        
        assert watcher.state == WatcherState.STOPPED
```

### Integration Testing

```python
@pytest.mark.asyncio
async def test_full_pipeline(tmp_path):
    # Setup
    vault_path = tmp_path / "vault"
    vault_path.mkdir()
    
    watch_path = tmp_path / "watched"
    watch_path.mkdir()
    
    # Create watcher and emitter
    config = FSWatcherConfig(
        name="test",
        watch_path=str(watch_path),
        poll_interval=0.1
    )
    watcher = FileSystemWatcher(config)
    
    emitter = ObsidianEmitter(EmitterConfig(
        vault_path=str(vault_path),
        default_folder="events"
    ))
    
    watcher.on_event(emitter.emit)
    
    # Run test
    await watcher.start()
    
    # Create file
    test_file = watch_path / "test.txt"
    test_file.write_text("hello")
    
    await asyncio.sleep(0.3)
    await watcher.stop()
    
    # Verify output
    event_files = list((vault_path / "events").rglob("*.md"))
    assert len(event_files) > 0
```

### Mock Testing

```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_api_watcher_with_mock():
    config = APIWatcherConfig(
        name="test-api",
        url="https://api.example.com/data"
    )
    watcher = APIWatcher(config)
    
    mock_response = {"id": 1, "status": "updated"}
    
    with patch.object(watcher, '_fetch', new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = (mock_response, None)
        
        await watcher._setup()
        
        # Modify mock for second call
        mock_fetch.return_value = ({"id": 1, "status": "changed"}, None)
        
        events = await watcher._poll()
        
        assert len(events) == 1
        assert events[0].event_type == EventType.MODIFIED
```
