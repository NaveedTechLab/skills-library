# Microservice Patterns Reference

## Table of Contents
1. [Service Decomposition](#service-decomposition)
2. [Communication Patterns](#communication-patterns)
3. [Saga Pattern](#saga-pattern)
4. [CQRS Pattern](#cqrs-pattern)
5. [Resilience Patterns](#resilience-patterns)

---

## Service Decomposition

### Todo Application Services

```
┌─────────────────────────────────────────────────────────────────┐
│                        API Gateway                               │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  Todo Service │    │  User Service │    │ Notification  │
│               │    │               │    │   Service     │
├───────────────┤    ├───────────────┤    ├───────────────┤
│ - CRUD todos  │    │ - Auth        │    │ - Email       │
│ - Status mgmt │    │ - Profiles    │    │ - Push        │
│ - Due dates   │    │ - Preferences │    │ - In-app      │
└───────────────┘    └───────────────┘    └───────────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              ▼
                    ┌───────────────┐
                    │  Event Bus    │
                    │  (Kafka)      │
                    └───────────────┘
```

### Service Boundaries

| Service | Responsibility | Events Produced | Events Consumed |
|---------|---------------|-----------------|-----------------|
| Todo | Task lifecycle | task.created, task.completed | user.deleted |
| User | Identity, auth | user.registered, user.deleted | - |
| Notification | Alerts | notification.sent | task.created, task.due |
| Analytics | Metrics | - | All events |

---

## Communication Patterns

### Event-Driven (Async)

```
Producer                    Event Bus                  Consumer
    │                           │                          │
    │──── Publish Event ───────▶│                          │
    │                           │──── Deliver Event ──────▶│
    │                           │                          │
    │                           │◀──── Acknowledge ────────│
```

**Use for:**
- Notifications
- Analytics
- Audit logging
- Cross-service data sync

### Request-Reply (Sync)

```
Service A                   Service B
    │                           │
    │──── HTTP/gRPC Request ───▶│
    │                           │──── Process
    │◀──── Response ────────────│
```

**Use for:**
- User authentication
- Real-time queries
- Validation checks

### Hybrid Pattern

```python
# Sync: Create todo and return immediately
@app.post("/todos")
async def create_todo(todo: TodoCreate):
    new_todo = await todo_service.create(todo)

    # Async: Publish event for downstream processing
    await publish_event("todos.task.created", {
        "todoId": new_todo.id,
        "userId": new_todo.user_id
    })

    return new_todo  # Return to user immediately
```

---

## Saga Pattern

### Choreography-Based Saga

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   Order     │      │  Payment    │      │  Inventory  │
│   Service   │      │   Service   │      │   Service   │
└─────────────┘      └─────────────┘      └─────────────┘
       │                    │                    │
       │ order.created      │                    │
       │───────────────────▶│                    │
       │                    │ payment.processed  │
       │                    │───────────────────▶│
       │                    │                    │ inventory.reserved
       │◀───────────────────┼────────────────────│
       │                    │                    │
```

### Todo Reminder Saga Example

```python
# Event: todo.created
# → Schedule reminder (async)
# → Update notification preferences
# → Log analytics event

@app.post("/events/todo-created")
async def handle_todo_created(event: dict):
    data = event["data"]

    # Step 1: Schedule reminder if due date exists
    if data.get("dueDate"):
        await scheduler.schedule_reminder(
            todo_id=data["todoId"],
            due_date=data["dueDate"]
        )
        await publish_event("reminder.scheduled", {
            "todoId": data["todoId"]
        })

    return {"status": "SUCCESS"}

@app.post("/events/reminder-scheduled")
async def handle_reminder_scheduled(event: dict):
    # Step 2: Update user's notification settings
    await notification_service.ensure_enabled(
        user_id=event["data"]["userId"]
    )
    return {"status": "SUCCESS"}
```

### Compensation (Rollback)

```python
class TodoSaga:
    async def execute(self, todo_data: dict):
        steps_completed = []

        try:
            # Step 1: Create todo
            todo = await todo_service.create(todo_data)
            steps_completed.append(("todo", todo.id))

            # Step 2: Schedule reminder
            reminder = await reminder_service.schedule(todo.id)
            steps_completed.append(("reminder", reminder.id))

            # Step 3: Send notification
            await notification_service.send(todo.user_id, "Todo created")
            steps_completed.append(("notification", None))

        except Exception as e:
            # Compensate in reverse order
            await self.compensate(steps_completed)
            raise

    async def compensate(self, steps: list):
        for step_type, step_id in reversed(steps):
            if step_type == "todo":
                await todo_service.delete(step_id)
            elif step_type == "reminder":
                await reminder_service.cancel(step_id)
            # Notification can't be unsent, just log
```

---

## CQRS Pattern

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                       Commands                           │
│                    (Create, Update)                      │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                   Write Model                            │
│                   (PostgreSQL)                           │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼ Events
┌─────────────────────────────────────────────────────────┐
│                    Event Store                           │
│                     (Kafka)                              │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼ Projections
┌─────────────────────────────────────────────────────────┐
│                    Read Model                            │
│               (Elasticsearch/Redis)                      │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                       Queries                            │
│                    (List, Search)                        │
└─────────────────────────────────────────────────────────┘
```

### Implementation

```python
# Command side
class TodoCommandService:
    def create(self, data: TodoCreate) -> Todo:
        todo = Todo(**data.dict())
        self.db.add(todo)
        self.db.commit()

        # Publish event for read model sync
        publish_event("todos.task.created", todo.to_dict())
        return todo

# Query side (separate service/database)
class TodoQueryService:
    def __init__(self, elasticsearch):
        self.es = elasticsearch

    def search(self, query: str, filters: dict) -> list[Todo]:
        return self.es.search(
            index="todos",
            query={"bool": {"must": [{"match": {"title": query}}]}}
        )

# Event handler to sync read model
@app.post("/events/todo-created")
async def sync_to_read_model(event: dict):
    await elasticsearch.index(
        index="todos",
        id=event["data"]["todoId"],
        document=event["data"]
    )
```

---

## Resilience Patterns

### Circuit Breaker

```python
from circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=30)
async def call_notification_service(user_id: str, message: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{NOTIFICATION_URL}/notify",
            json={"userId": user_id, "message": message}
        )
        response.raise_for_status()
```

### Bulkhead

```python
from asyncio import Semaphore

# Limit concurrent calls to external service
notification_semaphore = Semaphore(10)

async def send_notification(user_id: str, message: str):
    async with notification_semaphore:
        await notification_service.send(user_id, message)
```

### Timeout

```python
import asyncio

async def call_with_timeout(coro, timeout_seconds=5):
    try:
        return await asyncio.wait_for(coro, timeout=timeout_seconds)
    except asyncio.TimeoutError:
        logger.error("Service call timed out")
        raise ServiceUnavailableError()
```

### Graceful Degradation

```python
async def get_user_preferences(user_id: str) -> dict:
    try:
        return await user_service.get_preferences(user_id)
    except ServiceUnavailableError:
        # Return sensible defaults
        return {
            "notifications_enabled": True,
            "email_frequency": "daily"
        }
```
