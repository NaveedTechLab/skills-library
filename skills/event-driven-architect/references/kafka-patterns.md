# Kafka Patterns Reference

## Table of Contents
1. [Topic Design](#topic-design)
2. [Event Schema Design](#event-schema-design)
3. [Producer Patterns](#producer-patterns)
4. [Consumer Patterns](#consumer-patterns)
5. [Error Handling](#error-handling)

---

## Topic Design

### Naming Convention

```
<domain>.<entity>.<event-type>

Examples:
  todos.task.created
  todos.task.completed
  todos.task.deleted
  users.account.registered
  notifications.email.sent
```

### Topic Configuration

```yaml
# For Todo application
topics:
  - name: todos.task.created
    partitions: 3
    replication-factor: 3
    config:
      retention.ms: 604800000  # 7 days
      cleanup.policy: delete

  - name: todos.task.events
    partitions: 6
    replication-factor: 3
    config:
      retention.ms: 2592000000  # 30 days
      cleanup.policy: compact   # Keep latest per key
```

### Partition Strategy

| Strategy | Use When | Key Example |
|----------|----------|-------------|
| By Entity ID | Order matters per entity | `todo.id` |
| By User ID | User-scoped processing | `user.id` |
| Round Robin | Order doesn't matter | null key |
| By Region | Geographic isolation | `region` |

```python
# Partition by todo_id ensures order per todo
producer.send(
    topic="todos.task.events",
    key=str(todo_id).encode(),  # Partition key
    value=event_json
)
```

---

## Event Schema Design

### CloudEvents Format (Recommended)

```json
{
  "specversion": "1.0",
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "source": "/todos/api",
  "type": "todos.task.created",
  "datacontenttype": "application/json",
  "time": "2024-01-15T10:30:00Z",
  "data": {
    "todoId": "123",
    "title": "Buy groceries",
    "userId": "456",
    "status": "pending"
  }
}
```

### Event Types for Todo Domain

```python
# events/todo_events.py
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

@dataclass
class TodoCreated:
    event_type: Literal["todos.task.created"] = "todos.task.created"
    todo_id: str
    user_id: str
    title: str
    created_at: datetime

@dataclass
class TodoCompleted:
    event_type: Literal["todos.task.completed"] = "todos.task.completed"
    todo_id: str
    user_id: str
    completed_at: datetime

@dataclass
class TodoDeleted:
    event_type: Literal["todos.task.deleted"] = "todos.task.deleted"
    todo_id: str
    user_id: str
    deleted_at: datetime
```

### Schema Registry (Avro)

```json
{
  "type": "record",
  "name": "TodoCreated",
  "namespace": "com.todos.events",
  "fields": [
    {"name": "todo_id", "type": "string"},
    {"name": "user_id", "type": "string"},
    {"name": "title", "type": "string"},
    {"name": "status", "type": {"type": "enum", "name": "Status", "symbols": ["PENDING", "COMPLETED", "ARCHIVED"]}},
    {"name": "created_at", "type": {"type": "long", "logicalType": "timestamp-millis"}}
  ]
}
```

---

## Producer Patterns

### Transactional Outbox Pattern

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   Service   │──────│  Database   │──────│   Outbox    │
│             │      │   (Todo)    │      │   Table     │
└─────────────┘      └─────────────┘      └─────────────┘
                                                │
                                                ▼
                     ┌─────────────┐      ┌─────────────┐
                     │   Kafka     │◄─────│   Relay     │
                     │             │      │   Service   │
                     └─────────────┘      └─────────────┘
```

```sql
-- Outbox table
CREATE TABLE outbox (
    id UUID PRIMARY KEY,
    aggregate_type VARCHAR(255) NOT NULL,
    aggregate_id VARCHAR(255) NOT NULL,
    event_type VARCHAR(255) NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    published_at TIMESTAMP NULL
);

-- In transaction
BEGIN;
  INSERT INTO todos (id, title, ...) VALUES (...);
  INSERT INTO outbox (aggregate_type, aggregate_id, event_type, payload)
    VALUES ('todo', '123', 'todos.task.created', '{"todoId": "123", ...}');
COMMIT;
```

### Idempotent Producer

```python
from kafka import KafkaProducer

producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    enable_idempotence=True,  # Exactly-once semantics
    acks='all',
    retries=3,
    max_in_flight_requests_per_connection=5,
)
```

---

## Consumer Patterns

### Consumer Group Setup

```python
from kafka import KafkaConsumer

consumer = KafkaConsumer(
    'todos.task.events',
    bootstrap_servers=['localhost:9092'],
    group_id='notification-service',
    auto_offset_reset='earliest',
    enable_auto_commit=False,  # Manual commit for reliability
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
)

for message in consumer:
    try:
        process_event(message.value)
        consumer.commit()  # Commit after successful processing
    except Exception as e:
        handle_error(message, e)
```

### Idempotent Consumer

```python
# Track processed event IDs
processed_events = set()  # Use Redis/DB in production

def process_event(event):
    event_id = event['id']

    # Check if already processed
    if event_id in processed_events:
        logger.info(f"Skipping duplicate event: {event_id}")
        return

    # Process event
    handle_todo_created(event['data'])

    # Mark as processed
    processed_events.add(event_id)
```

### Event Router Pattern

```python
class EventRouter:
    def __init__(self):
        self.handlers = {}

    def register(self, event_type: str, handler):
        self.handlers[event_type] = handler

    def route(self, event: dict):
        event_type = event.get('type')
        handler = self.handlers.get(event_type)
        if handler:
            handler(event['data'])
        else:
            logger.warning(f"No handler for event type: {event_type}")

# Usage
router = EventRouter()
router.register('todos.task.created', send_notification)
router.register('todos.task.completed', update_analytics)
```

---

## Error Handling

### Dead Letter Queue (DLQ)

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   Main      │──────│  Consumer   │──X──▶│   DLQ       │
│   Topic     │      │             │      │   Topic     │
└─────────────┘      └─────────────┘      └─────────────┘
                           │
                           ▼ (success)
                     ┌─────────────┐
                     │  Database   │
                     └─────────────┘
```

```python
DLQ_TOPIC = 'todos.task.events.dlq'
MAX_RETRIES = 3

def process_with_dlq(message):
    retries = message.headers.get('retry_count', 0)

    try:
        process_event(message.value)
    except RetryableError as e:
        if retries < MAX_RETRIES:
            # Re-publish with incremented retry count
            producer.send(
                topic=message.topic,
                value=message.value,
                headers={'retry_count': retries + 1}
            )
        else:
            # Send to DLQ
            producer.send(DLQ_TOPIC, value=message.value)
    except NonRetryableError as e:
        # Send directly to DLQ
        producer.send(DLQ_TOPIC, value=message.value)
```

### Retry with Backoff

```python
import time
from functools import wraps

def retry_with_backoff(max_retries=3, base_delay=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    delay = base_delay * (2 ** attempt)
                    time.sleep(delay)
        return wrapper
    return decorator
```
