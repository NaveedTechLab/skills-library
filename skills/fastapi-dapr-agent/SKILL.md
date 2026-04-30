---
name: fastapi-dapr-agent
description: Scaffold and deploy FastAPI microservices with Dapr sidecars. Use when Claude needs to create stateless FastAPI microservices with Dapr integration for service invocation and pub/sub. No business logic authoring - focus on scaffolding and deployment patterns only.
---

# FastAPI Dapr Agent

This skill scaffolds FastAPI microservices integrated with Dapr (Distributed Application Runtime) and AI Agents.

## Usage
Use this skill when you need to create a new FastAPI microservice with Dapr integration. The skill will:
1. Generate the FastAPI service code
2. Create necessary Dapr sidecar configurations
3. Set up state management and pub/sub messaging patterns

## Process
The scaffolding is handled by the supporting scripts which provide templates for:
- FastAPI application structure
- Dapr component configurations for state management
- Dapr component configurations for pub/sub messaging
- Service invocation patterns
- AI Agent integration points

## Components
- FastAPI service with Dapr integration
- State management using Dapr state stores
- Pub/Sub messaging using Dapr pub/sub components
- Sidecar configuration files
- Dockerfile for containerization