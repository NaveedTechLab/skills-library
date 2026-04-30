from fastapi import FastAPI, HTTPException, BackgroundTasks
from typing import Dict, Any, List
import asyncio
import logging
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="FastAPI-Dapr Template Service",
    description="Template for FastAPI service with Dapr integration",
    version="1.0.0"
)

# Example state management endpoint
@app.get("/state/{key}")
async def get_state(key: str) -> Dict[str, Any]:
    """
    Get state from Dapr state store
    In a real implementation, this would call Dapr state API
    """
    # This is a mock implementation - in real scenario, call Dapr API
    logger.info(f"Getting state for key: {key}")
    return {
        "key": key,
        "value": f"mock-value-for-{key}",
        "from": "dapr-state-store"
    }

@app.post("/state")
async def save_state(request: Dict[str, Any]) -> Dict[str, str]:
    """
    Save state to Dapr state store
    In a real implementation, this would call Dapr state API
    """
    # This is a mock implementation - in real scenario, call Dapr API
    key = request.get("key")
    value = request.get("value")

    logger.info(f"Saving state for key: {key}")
    return {
        "status": "saved",
        "key": key
    }

# Example service invocation endpoint
@app.post("/invoke/{service_name:path}")
async def invoke_service(service_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Invoke another service via Dapr service invocation
    In a real implementation, this would call Dapr service invocation API
    """
    # This is a mock implementation - in real scenario, call Dapr API
    logger.info(f"Invoking service: {service_name} with payload: {payload}")
    return {
        "invoked_service": service_name,
        "payload_received": payload,
        "result": "mock-result-from-invoked-service"
    }

# Example pub/sub subscription endpoint
@app.get("/dapr/subscribe")
async def dapr_subscribe() -> List[Dict[str, Any]]:
    """
    Dapr subscription endpoint for pub/sub
    Defines which topics this service subscribes to
    """
    subscriptions = [
        {
            "pubsubname": "pubsub",
            "topic": "order-events",
            "route": "/events/order-events"
        },
        {
            "pubsubname": "pubsub",
            "topic": "user-events",
            "route": "/events/user-events"
        }
    ]
    return subscriptions

# Example pub/sub event handler
@app.post("/events/{topic}")
async def handle_event(topic: str, event: Dict[str, Any], background_tasks: BackgroundTasks) -> Dict[str, str]:
    """
    Handle incoming pub/sub events
    """
    logger.info(f"Received event on topic: {topic}")
    logger.info(f"Event payload: {json.dumps(event)}")

    # Process the event in the background to return quickly
    background_tasks.add_task(process_event, topic, event)

    return {"status": "received", "topic": topic}

# Background task to process events
async def process_event(topic: str, event: Dict[str, Any]):
    """
    Process the event in the background
    """
    logger.info(f"Processing event for topic: {topic}")
    # Add your event processing logic here
    # This could be saving to database, calling other services, etc.
    await asyncio.sleep(0.1)  # Simulate processing time
    logger.info(f"Finished processing event for topic: {topic}")

# Example business logic endpoint (stateless)
@app.post("/process-data")
async def process_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Example of stateless processing endpoint
    This endpoint processes data without maintaining state
    """
    # Extract data from request
    input_data = data.get("data", {})
    operation = data.get("operation", "transform")

    logger.info(f"Processing data with operation: {operation}")

    # Perform stateless transformation
    if operation == "uppercase":
        result = {k: str(v).upper() if isinstance(v, str) else v for k, v in input_data.items()}
    elif operation == "length":
        result = {k: len(str(v)) if isinstance(v, str) else v for k, v in input_data.items()}
    else:
        result = input_data

    return {
        "original_data": input_data,
        "processed_data": result,
        "operation": operation,
        "processed_by": "fastapi-dapr-template"
    }

# Health check endpoints
@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint for health check"""
    return {
        "message": "Welcome to FastAPI-Dapr Template Service",
        "status": "healthy",
        "framework": "FastAPI",
        "integration": "Dapr"
    }

@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint"""
    return {"status": "healthy", "service": "fastapi-dapr-template"}

@app.get("/ready")
async def readiness_check() -> Dict[str, str]:
    """Readiness check endpoint"""
    # Add any readiness checks here
    return {"status": "ready"}

# Example of calling Dapr secrets management
@app.get("/secret/{secret_key}")
async def get_secret(secret_key: str) -> Dict[str, Any]:
    """
    Get secret from Dapr secret store
    In a real implementation, this would call Dapr secrets API
    """
    # This is a mock implementation - in real scenario, call Dapr API
    logger.info(f"Getting secret for key: {secret_key}")
    return {
        "key": secret_key,
        "value": "mock-secret-value",
        "from": "dapr-secret-store"
    }

# Example of calling Dapr bindings
@app.post("/bindings/{binding_name}")
async def send_binding(binding_name: str, data: Dict[str, Any]) -> Dict[str, str]:
    """
    Send data via Dapr binding
    In a real implementation, this would call Dapr binding API
    """
    # This is a mock implementation - in real scenario, call Dapr API
    logger.info(f"Sending to binding: {binding_name} with data: {data}")
    return {
        "status": "sent",
        "binding": binding_name
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)