#!/usr/bin/env python3
"""
FastAPI Dapr Service Generator

This script creates a new FastAPI service with Dapr integration,
including state management and pub/sub messaging capabilities.
"""

import os
import sys
import argparse
from pathlib import Path


def create_fastapi_app(service_name, output_dir):
    """Create the main FastAPI application with Dapr integration."""
    app_content = '''from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import logging
import json
from typing import Optional

app = FastAPI(title="{service_name}", description="FastAPI service with Dapr integration")

# Dapr configuration
DAPR_HTTP_ENDPOINT = "http://localhost:3500"
DAPR_STATE_STORE = "statestore"
DAPR_PUBSUB_NAME = "pubsub"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Message(BaseModel):
    topic: str
    data: dict


@app.on_event("startup")
async def startup_event():
    logger.info("Service started with Dapr integration")


@app.get("/")
async def root():
    return {{"message": "Hello from {service_name} with Dapr!"}}


@app.get("/health")
async def health_check():
    return {{"status": "healthy"}}


# State Management Endpoints
@app.post("/state/{{key}}")
async def save_state(key: str, value: dict):
    """Save state using Dapr state store"""
    try:
        url = f"{{DAPR_HTTP_ENDPOINT}}/v1.0/state/{{DAPR_STATE_STORE}}"
        state_item = {{
            "key": key,
            "value": value
        }}
        response = requests.post(url, json=[state_item])
        
        if response.status_code == 200:
            logger.info(f"State saved: {{key}}")
            return {{"success": True, "key": key}}
        else:
            raise HTTPException(status_code=response.status_code, detail="Failed to save state")
    except Exception as e:
        logger.error(f"Error saving state: {{e}}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/state/{{key}}")
async def get_state(key: str):
    """Get state using Dapr state store"""
    try:
        url = f"{{DAPR_HTTP_ENDPOINT}}/v1.0/state/{{DAPR_STATE_STORE}}/{{key}}"
        response = requests.get(url)
        
        if response.status_code == 200:
            value = response.json()
            logger.info(f"State retrieved: {{key}}")
            return {{"key": key, "value": value}}
        elif response.status_code == 404:
            return {{"key": key, "value": None}}
        else:
            raise HTTPException(status_code=response.status_code, detail="Failed to get state")
    except Exception as e:
        logger.error(f"Error getting state: {{e}}")
        raise HTTPException(status_code=500, detail=str(e))


# Pub/Sub Endpoints
@app.post("/publish")
async def publish_message(message: Message):
    """Publish a message using Dapr pub/sub"""
    try:
        url = f"{{DAPR_HTTP_ENDPOINT}}/v1.0/publish/{{DAPR_PUBSUB_NAME}}/{{message.topic}}"
        response = requests.post(url, json=message.data)
        
        if response.status_code == 200:
            logger.info(f"Message published to topic: {{message.topic}}")
            return {{"success": True, "topic": message.topic}}
        else:
            raise HTTPException(status_code=response.status_code, detail="Failed to publish message")
    except Exception as e:
        logger.error(f"Error publishing message: {{e}}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/dapr/subscribe")
async def dapr_subscribe():
    """Define Dapr subscription endpoints"""
    subscriptions = [
        {{
            "pubsubname": DAPR_PUBSUB_NAME,
            "topic": "general",
            "route": "/events/general"
        }},
        {{
            "pubsubname": DAPR_PUBSUB_NAME,
            "topic": "notifications",
            "route": "/events/notifications"
        }}
    ]
    return subscriptions


@app.post("/events/{{topic_name}}")
async def handle_event(topic_name: str, data: dict):
    """Handle incoming events from Dapr pub/sub"""
    logger.info(f"Received event on topic '{{topic_name}}': {{data}}")
    # Process the event based on topic
    if topic_name == "general":
        # Handle general events
        pass
    elif topic_name == "notifications":
        # Handle notification events
        pass
    
    return {{"status": "processed", "topic": topic_name}}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
'''.format(service_name=service_name)

    app_file = Path(output_dir) / "main.py"
    with open(app_file, 'w') as f:
        f.write(app_content)
    
    print(f"Created FastAPI application: {app_file}")


def create_dockerfile(output_dir):
    """Create a Dockerfile for the service."""
    dockerfile_content = '''FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
'''
    
    dockerfile = Path(output_dir) / "Dockerfile"
    with open(dockerfile, 'w') as f:
        f.write(dockerfile_content)
    
    print(f"Created Dockerfile: {dockerfile}")


def create_requirements(output_dir):
    """Create requirements.txt for the service."""
    requirements_content = '''fastapi==0.104.1
uvicorn[standard]==0.24.0
requests==2.31.0
pydantic==2.5.0
python-multipart==0.0.6
'''
    
    req_file = Path(output_dir) / "requirements.txt"
    with open(req_file, 'w') as f:
        f.write(requirements_content)
    
    print(f"Created requirements.txt: {req_file}")


def create_dapr_components(output_dir):
    """Create Dapr component configuration files."""
    # State store component
    state_store_content = '''apiVersion: dapr.io/v1alpha1
kind: Component
metadata:
  name: statestore
spec:
  type: state.redis
  version: v1
  metadata:
  - name: redisHost
    value: localhost:6379
  - name: redisPassword
    value: ""
  - name: actorStateStore
    value: "true"
'''
    
    state_file = Path(output_dir) / "components" / "statestore.yaml"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    with open(state_file, 'w') as f:
        f.write(state_store_content)
    
    print(f"Created state store component: {state_file}")
    
    # Pub/Sub component
    pubsub_content = '''apiVersion: dapr.io/v1alpha1
kind: Component
metadata:
  name: pubsub
spec:
  type: pubsub.redis
  version: v1
  metadata:
  - name: redisHost
    value: localhost:6379
  - name: redisPassword
    value: ""
'''
    
    pubsub_file = Path(output_dir) / "components" / "pubsub.yaml"
    with open(pubsub_file, 'w') as f:
        f.write(pubsub_content)
    
    print(f"Created pub/sub component: {pubsub_file}")


def create_dapr_config(output_dir):
    """Create Dapr configuration file."""
    config_content = '''apiVersion: dapr.io/v1alpha1
kind: Configuration
metadata:
  name: daprConfig
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
'''
    
    config_file = Path(output_dir) / "config" / "dapr-config.yaml"
    config_file.parent.mkdir(parents=True, exist_ok=True)
    with open(config_file, 'w') as f:
        f.write(config_content)
    
    print(f"Created Dapr configuration: {config_file}")


def create_service_invocation_example(output_dir):
    """Create an example for service invocation."""
    invocation_content = '''# Example of how to invoke another Dapr service
import requests

def invoke_service(target_app_id, method, data=None):
    """
    Invoke another Dapr service using service invocation
    """
    dapr_base_url = "http://localhost:3500"
    url = f"{dapr_base_url}/v1.0/invoke/{target_app_id}/method/{method}"
    
    try:
        if data:
            response = requests.post(url, json=data)
        else:
            response = requests.get(url)
        
        return response.json()
    except Exception as e:
        print(f"Error invoking service {target_app_id}: {e}")
        return None

# Usage example:
# result = invoke_service("other-service", "api/data", {"param": "value"})
'''
    
    invocation_file = Path(output_dir) / "examples" / "service_invocation.py"
    invocation_file.parent.mkdir(parents=True, exist_ok=True)
    with open(invocation_file, 'w') as f:
        f.write(invocation_content)
    
    print(f"Created service invocation example: {invocation_file}")


def main():
    parser = argparse.ArgumentParser(description='Create a new FastAPI service with Dapr integration')
    parser.add_argument('service_name', help='Name of the service to create')
    parser.add_argument('-o', '--output', default='.', help='Output directory (default: current directory)')
    
    args = parser.parse_args()
    
    output_dir = Path(args.output) / args.service_name
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Creating FastAPI service '{args.service_name}' in {output_dir}")
    
    create_fastapi_app(args.service_name, output_dir)
    create_dockerfile(output_dir)
    create_requirements(output_dir)
    create_dapr_components(output_dir)
    create_dapr_config(output_dir)
    create_service_invocation_example(output_dir)
    
    print(f"\nService '{args.service_name}' created successfully!")
    print(f"Directory structure:")
    print(f"  {output_dir}/")
    print(f"  ├── main.py                 # FastAPI application")
    print(f"  ├── requirements.txt        # Python dependencies")
    print(f"  ├── Dockerfile             # Container configuration")
    print(f"  ├── components/            # Dapr component configurations")
    print(f"  │   ├── statestore.yaml    # State management configuration")
    print(f"  │   └── pubsub.yaml        # Pub/Sub configuration")
    print(f"  ├── config/                # Dapr configuration")
    print(f"  │   └── dapr-config.yaml   # Main Dapr configuration")
    print(f"  └── examples/              # Usage examples")
    print(f"      └── service_invocation.py  # Service invocation example")


if __name__ == "__main__":
    main()