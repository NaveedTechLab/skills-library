# FastAPI and Dapr Integration Best Practices

## Stateless Service Design

### Core Principles
- **No Local State**: Services should not store state locally; all state should be managed externally
- **Idempotent Operations**: Design operations to be repeatable without changing the outcome
- **Horizontal Scalability**: Services should scale horizontally without losing functionality
- **External Dependencies**: All dependencies should be external services or Dapr-managed components

### Implementation Guidelines
- Use Dapr state stores instead of local variables/files
- Implement retry logic for external calls
- Use external caching (Redis, etc.) instead of in-memory caches
- Store session data in Dapr state stores or external systems

## Dapr Component Configuration

### Service Invocation
```yaml
# Dapr annotation for enabling service invocation
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-service
spec:
  template:
    metadata:
      annotations:
        dapr.io/enabled: "true"
        dapr.io/app-id: "my-service"
        dapr.io/app-port: "8000"
```

### Pub/Sub Configuration
```yaml
apiVersion: dapr.io/v1alpha1
kind: Component
metadata:
  name: pubsub
spec:
  type: pubsub.redis  # Or pubsub.rabbitmq, pubsub.kafka
  version: v1
  metadata:
  - name: redisHost
    value: localhost:6379
  - name: redisPassword
    value: ""
```

### State Management Configuration
```yaml
apiVersion: dapr.io/v1alpha1
kind: Component
metadata:
  name: statestore
spec:
  type: state.redis  # Or state.azure.tablestorage, state.mongodb
  version: v1
  metadata:
  - name: redisHost
    value: localhost:6379
  - name: redisPassword
    value: ""
  - name: actorStateStore
    value: "true"
```

## FastAPI Endpoint Patterns

### Basic Service Invocation Endpoint
```python
from fastapi import FastAPI
import httpx

app = FastAPI()

@app.post("/invoke-service")
async def invoke_external_service(payload: dict):
    # Using Dapr service invocation
    dapr_base_url = "http://localhost:3500/v1.0"
    target_service = "target-service-name"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{dapr_base_url}/invoke/{target_service}/method/endpoint",
            json=payload
        )

    return response.json()
```

### Pub/Sub Subscription Handler
```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/dapr/subscribe")
async def subscribe():
    return [{
        "pubsubname": "pubsub",
        "topic": "my-topic",
        "route": "/events/my-topic"
    }]

@app.post("/events/my-topic")
async def handle_my_topic(event: dict):
    # Process the received event
    print(f"Received event: {event}")
    return {"status": "processed"}
```

### State Management Handler
```python
import httpx
from fastapi import FastAPI

app = FastAPI()

@app.get("/state/{key}")
async def get_state(key: str):
    dapr_base_url = "http://localhost:3500/v1.0"

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{dapr_base_url}/state/statestore/{key}"
        )

    return {"key": key, "value": response.text}

@app.post("/state")
async def save_state(data: dict):
    dapr_base_url = "http://localhost:3500/v1.0"
    key = data.get("key")
    value = data.get("value")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{dapr_base_url}/state/statestore",
            json=[{"key": key, "value": value}]
        )

    return {"status": "saved", "key": key}
```

## Deployment Patterns

### Kubernetes with Dapr Annotations
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fastapi-dapr-service
spec:
  replicas: 3  # Enable horizontal scaling
  selector:
    matchLabels:
      app: fastapi-dapr-service
  template:
    metadata:
      labels:
        app: fastapi-dapr-service
      annotations:
        dapr.io/enabled: "true"
        dapr.io/app-id: "fastapi-dapr-service"
        dapr.io/app-port: "8000"
        dapr.io/app-protocol: "http"
        dapr.io/config: "app-config"  # Optional: Dapr configuration
        dapr.io/log-level: "info"
    spec:
      containers:
      - name: fastapi-app
        image: fastapi-dapr-service:latest
        ports:
        - containerPort: 8000
        env:
        - name: DAPR_HTTP_PORT
          value: "3500"
        - name: DAPR_GRPC_PORT
          value: "50001"
```

### Dapr Configuration (for tracing, etc.)
```yaml
apiVersion: dapr.io/v1alpha1
kind: Configuration
metadata:
  name: app-config
spec:
  tracing:
    samplingRate: "1"
    zipkin:
      endpointAddress: "http://zipkin.default.svc.cluster.local:9411/api/v2/spans"
  metric:
    enabled: true
  httpPipeline:
    handlers: []
  features:
  - name: AppHealthCheck
    enabled: true
```

## Error Handling and Resiliency

### Circuit Breaker Pattern
```python
from fastapi import FastAPI, HTTPException
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

app = FastAPI()

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def call_dependent_service(payload: dict):
    dapr_base_url = "http://localhost:3500/v1.0"
    target_service = "dependent-service"

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{dapr_base_url}/invoke/{target_service}/method/process",
            json=payload
        )

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Service call failed")

    return response.json()
```

### Dead Letter Queue Pattern
```python
# For pub/sub error handling
@app.post("/events/error-prone-topic")
async def handle_error_prone_topic(event: dict):
    try:
        # Process the event
        result = await process_business_logic(event)
        return {"status": "success", "result": result}
    except Exception as e:
        # Log the error
        print(f"Failed to process event: {e}")

        # Send to dead letter queue if needed
        dapr_base_url = "http://localhost:3500/v1.0"
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{dapr_base_url}/publish/pubsub/dead-letter-topic",
                json={"original_event": event, "error": str(e)}
            )

        # Return error to Dapr to retry
        raise HTTPException(status_code=500, detail=str(e))
```

## Security Considerations

### Dapr Security
- Enable mTLS for service-to-service communication
- Use secrets management for sensitive data
- Implement proper authentication and authorization
- Validate input data before processing

### Example: Using Dapr Secrets
```python
# In your FastAPI app
import httpx

@app.get("/secret/{secret_name}")
async def get_secret(secret_name: str):
    dapr_base_url = "http://localhost:3500/v1.0"

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{dapr_base_url}/secrets/my-secret-store/{secret_name}"
        )

    return response.json()
```

## Monitoring and Observability

### Health Checks
```python
@app.get("/health")
async def health_check():
    # Add any health check logic here
    return {"status": "healthy", "service": "fastapi-dapr-service"}

@app.get("/ready")
async def readiness_check():
    # Add readiness check logic (dependencies, etc.)
    return {"status": "ready"}
```

### Dapr Metrics
- Enable Dapr metrics in configuration
- Use Prometheus-compatible monitoring
- Monitor Dapr sidecar logs
- Track service invocation latencies

## Common Anti-Patterns to Avoid

1. **Storing State Locally**: Never store state in the service's local memory or file system
2. **Hardcoding Service Names**: Use configuration for service names and endpoints
3. **Ignoring Error Handling**: Always handle errors from Dapr and external calls
4. **Blocking Operations**: Use async/await for I/O operations
5. **Missing Circuit Breakers**: Implement resiliency patterns for external calls
6. **Exposing Dapr Ports**: Don't expose Dapr sidecar ports publicly

## Testing Strategies

### Unit Testing
- Mock Dapr client calls
- Test business logic separately from Dapr integration
- Use dependency injection for Dapr clients

### Integration Testing
- Use Dapr Standalone mode for testing
- Test service invocation and pub/sub patterns
- Verify state management operations

### End-to-End Testing
- Test complete workflows with multiple services
- Verify pub/sub message flow
- Test error handling and recovery