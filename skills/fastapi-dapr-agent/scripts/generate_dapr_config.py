#!/usr/bin/env python3
"""
Dapr Configuration Generator

This script generates Dapr component configurations for state management
and pub/sub messaging for FastAPI microservices.
"""

import os
import sys
import argparse
from pathlib import Path


def create_redis_state_store(output_dir, name="statestore", redis_host="localhost:6379"):
    """Create a Redis state store component configuration."""
    state_store_content = f'''apiVersion: dapr.io/v1alpha1
kind: Component
metadata:
  name: {name}
spec:
  type: state.redis
  version: v1
  metadata:
  - name: redisHost
    value: {redis_host}
  - name: redisPassword
    value: ""
  - name: actorStateStore
    value: "true"
'''
    
    output_file = Path(output_dir) / f"{name}_statestore.yaml"
    with open(output_file, 'w') as f:
        f.write(state_store_content)
    
    print(f"Created state store component: {output_file}")


def create_redis_pubsub(output_dir, name="pubsub", redis_host="localhost:6379"):
    """Create a Redis pub/sub component configuration."""
    pubsub_content = f'''apiVersion: dapr.io/v1alpha1
kind: Component
metadata:
  name: {name}
spec:
  type: pubsub.redis
  version: v1
  metadata:
  - name: redisHost
    value: {redis_host}
  - name: redisPassword
    value: ""
'''
    
    output_file = Path(output_dir) / f"{name}_pubsub.yaml"
    with open(output_file, 'w') as f:
        f.write(pubsub_content)
    
    print(f"Created pub/sub component: {output_file}")


def create_cosmosdb_state_store(output_dir, name="cosmosdb-statestore", cosmos_url="", cosmos_master_key="", database=""):
    """Create an Azure Cosmos DB state store component configuration."""
    state_store_content = f'''apiVersion: dapr.io/v1alpha1
kind: Component
metadata:
  name: {name}
spec:
  type: state.azure.cosmosdb
  version: v1
  metadata:
  - name: url
    value: "{cosmos_url}"
  - name: masterKey
    value: "{cosmos_master_key}"
  - name: database
    value: "{database}"
  - name: collection
    value: "state"
'''
    
    output_file = Path(output_dir) / f"{name.replace('/', '-')}.yaml"
    with open(output_file, 'w') as f:
        f.write(state_store_content)
    
    print(f"Created CosmosDB state store component: {output_file}")


def create_rabbitmq_pubsub(output_dir, name="rabbitmq-pubsub", rabbitmq_host="amqp://localhost:5672"):
    """Create a RabbitMQ pub/sub component configuration."""
    pubsub_content = f'''apiVersion: dapr.io/v1alpha1
kind: Component
metadata:
  name: {name}
spec:
  type: pubsub.rabbitmq
  version: v1
  metadata:
  - name: host
    value: "{rabbitmq_host}"
  - name: durable
    value: "false"
  - name: deletedWhenUnused
    value: "false"
  - name: autoAck
    value: "false"
  - name: reconnectWait
    value: "0"
'''
    
    output_file = Path(output_dir) / f"{name.replace('/', '-')}.yaml"
    with open(output_file, 'w') as f:
        f.write(pubsub_content)
    
    print(f"Created RabbitMQ pub/sub component: {output_file}")


def create_default_dapr_config(output_dir):
    """Create a default Dapr configuration file."""
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
    
    output_file = Path(output_dir) / "dapr-config.yaml"
    with open(output_file, 'w') as f:
        f.write(config_content)
    
    print(f"Created default Dapr configuration: {output_file}")


def main():
    parser = argparse.ArgumentParser(description='Generate Dapr component configurations')
    parser.add_argument('--output', '-o', default='.', help='Output directory (default: current directory)')
    parser.add_argument('--redis-host', default='localhost:6379', help='Redis host address (default: localhost:6379)')
    parser.add_argument('--component-type', choices=['redis-all', 'redis-state', 'redis-pubsub', 'cosmos-state', 'rabbitmq-pubsub', 'config'], 
                       default='redis-all', help='Type of component to generate (default: redis-all)')
    parser.add_argument('--name', default='default', help='Name for the component (default: default)')
    
    args = parser.parse_args()
    
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Generating Dapr configurations in {output_dir}")
    
    if args.component_type == 'redis-all' or args.component_type == 'redis-state':
        create_redis_state_store(output_dir, args.name + "-statestore", args.redis_host)
    
    if args.component_type == 'redis-all' or args.component_type == 'redis-pubsub':
        create_redis_pubsub(output_dir, args.name + "-pubsub", args.redis_host)
    
    if args.component_type == 'cosmos-state':
        print("Creating CosmosDB state store configuration...")
        print("Note: Please provide Cosmos DB URL, master key, and database name as parameters or edit the file manually.")
        create_cosmosdb_state_store(output_dir, args.name + "-cosmosdb-statestore")
    
    if args.component_type == 'rabbitmq-pubsub':
        create_rabbitmq_pubsub(output_dir, args.name + "-rabbitmq-pubsub")
    
    if args.component_type in ['redis-all', 'config']:
        create_default_dapr_config(output_dir)
    
    print("\nDapr configurations generated successfully!")


if __name__ == "__main__":
    main()