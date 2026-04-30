# Dapr Pub/Sub Integration

## Table of Contents
1. [Dapr Overview](#dapr-overview)
2. [Component Configuration](#component-configuration)
3. [Publishing Events](#publishing-events)
4. [Subscribing to Events](#subscribing-to-events)
5. [Local Development](#local-development)

---

## Dapr Overview

### Why Dapr?

- **Cloud portability** - Same code works with Kafka, Redis, RabbitMQ, cloud services
- **Sidecar pattern** - No SDK lock-in, any language
- **Built-in resiliency** - Retries, circuit breakers
- **Simplified API** - HTTP/gRPC abstraction over message brokers

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Pod                                  │
│  ┌─────────────┐    ┌─────────────┐                        │
│  │    App      │◄──▶│   Dapr      │◄──▶  Message Broker    │
│  │  Container  │    │   Sidecar   │     (Kafka/Redis/etc)  │
│  └─────────────┘    └─────────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Configuration

### Kafka Component

```yaml
# components/pubsub-kafka.yaml
apiVersion: dapr.io/v1alpha1
kind: Component
metadata:
  name: pubsub
spec:
  type: pubsub.kafka
  version: v1
  metadata:
    - name: brokers
      value: "kafka:9092"
    - name: consumerGroup
      value: "todo-service"
    - name: authRequired
      value: "false"
    - name: maxMessageBytes
      value: "1048576"
```

### Redis Component (Local Dev)

```yaml
# components/pubsub-redis.yaml
apiVersion: dapr.io/v1alpha1
kind: Component
metadata:
  name: pubsub
spec:
  type: pubsub.redis
  version: v1
  metadata:
    - name: redisHost
      value: "redis:6379"
    - name: redisPassword
      value: ""
```

### AWS SNS/SQS Component

```yaml
# components/pubsub-aws.yaml
apiVersion: dapr.io/v1alpha1
kind: Component
metadata:
  name: pubsub
spec:
  type: pubsub.aws.snssqs
  version: v1
  metadata:
    - name: region
      value: "us-east-1"
    - name: accessKey
      secretKeyRef:
        name: aws-secrets
        key: access-key
    - name: secretKey
      secretKeyRef:
        name: aws-secrets
        key: secret-key
```

---

## Publishing Events

### HTTP API

```bash
# Publish event
curl -X POST http://localhost:3500/v1.0/publish/pubsub/todos.task.created \
  -H "Content-Type: application/json" \
  -d '{
    "todoId": "123",
    "userId": "456",
    "title": "Buy groceries"
  }'
```

### Python SDK

```python
from dapr.clients import DaprClient

PUBSUB_NAME = "pubsub"
TOPIC = "todos.task.created"

async def publish_todo_created(todo: Todo):
    with DaprClient() as client:
        client.publish_event(
            pubsub_name=PUBSUB_NAME,
            topic_name=TOPIC,
            data=json.dumps({
                "todoId": str(todo.id),
                "userId": str(todo.user_id),
                "title": todo.title,
                "createdAt": todo.created_at.isoformat()
            }),
            data_content_type="application/json"
        )
```

### FastAPI Integration

```python
from fastapi import FastAPI
from dapr.clients import DaprClient

app = FastAPI()

@app.post("/todos")
async def create_todo(todo: TodoCreate, db: Session = Depends(get_db)):
    # Create todo in database
    new_todo = Todo(**todo.dict())
    db.add(new_todo)
    db.commit()

    # Publish event
    with DaprClient() as client:
        client.publish_event(
            pubsub_name="pubsub",
            topic_name="todos.task.created",
            data=json.dumps({"todoId": str(new_todo.id), "title": new_todo.title})
        )

    return new_todo
```

---

## Subscribing to Events

### Declarative Subscription

```yaml
# components/subscription.yaml
apiVersion: dapr.io/v2alpha1
kind: Subscription
metadata:
  name: todo-created-subscription
spec:
  pubsubname: pubsub
  topic: todos.task.created
  routes:
    default: /events/todo-created
```

### Programmatic Subscription (FastAPI)

```python
from fastapi import FastAPI, Request
from cloudevents.http import from_http

app = FastAPI()

# Tell Dapr what to subscribe to
@app.get("/dapr/subscribe")
async def subscribe():
    return [
        {
            "pubsubname": "pubsub",
            "topic": "todos.task.created",
            "route": "/events/todo-created"
        },
        {
            "pubsubname": "pubsub",
            "topic": "todos.task.completed",
            "route": "/events/todo-completed"
        }
    ]

# Handle incoming events
@app.post("/events/todo-created")
async def handle_todo_created(request: Request):
    event = await request.json()
    data = event.get("data", {})

    # Process the event
    await send_notification(
        user_id=data["userId"],
        message=f"Todo created: {data['title']}"
    )

    return {"status": "SUCCESS"}

@app.post("/events/todo-completed")
async def handle_todo_completed(request: Request):
    event = await request.json()
    data = event.get("data", {})

    # Update analytics
    await update_completion_stats(user_id=data["userId"])

    return {"status": "SUCCESS"}
```

### Error Handling

```python
@app.post("/events/todo-created")
async def handle_todo_created(request: Request):
    try:
        event = await request.json()
        await process_event(event)
        return {"status": "SUCCESS"}
    except RetryableError:
        # Return RETRY to have Dapr retry
        return {"status": "RETRY"}
    except Exception as e:
        # Return DROP to send to dead letter
        logger.error(f"Failed to process event: {e}")
        return {"status": "DROP"}
```

---

## Local Development

### docker-compose.yml

```yaml
version: '3.8'
services:
  todo-api:
    build: ./backend
    ports:
      - "8000:8000"
    depends_on:
      - redis

  todo-api-dapr:
    image: "daprio/daprd:latest"
    command: [
      "./daprd",
      "--app-id", "todo-api",
      "--app-port", "8000",
      "--dapr-http-port", "3500",
      "--components-path", "/components"
    ]
    volumes:
      - ./components:/components
    network_mode: "service:todo-api"

  notification-service:
    build: ./notifications
    ports:
      - "8001:8001"
    depends_on:
      - redis

  notification-service-dapr:
    image: "daprio/daprd:latest"
    command: [
      "./daprd",
      "--app-id", "notification-service",
      "--app-port", "8001",
      "--dapr-http-port", "3501",
      "--components-path", "/components"
    ]
    volumes:
      - ./components:/components
    network_mode: "service:notification-service"

  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
```

### Run with Dapr CLI

```bash
# Start with Dapr sidecar
dapr run --app-id todo-api \
         --app-port 8000 \
         --dapr-http-port 3500 \
         --components-path ./components \
         -- uvicorn app.main:app --port 8000
```

### Test Pub/Sub

```bash
# Publish test event
dapr publish --publish-app-id todo-api \
             --pubsub pubsub \
             --topic todos.task.created \
             --data '{"todoId": "123", "title": "Test"}'
```
