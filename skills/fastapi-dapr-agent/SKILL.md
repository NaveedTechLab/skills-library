---
name: fastapi-dapr-agent
description: Scaffold and deploy FastAPI microservices with Dapr sidecars. Use when Claude needs to create stateless FastAPI microservices with Dapr integration for service invocation and pub/sub. No business logic authoring - focus on scaffolding and deployment patterns only.
---

# FastAPI Dapr Agent

This skill scaffolds FastAPI microservices integrated with Dapr (Distributed Application Runtime) and AI Agents. It generates production-ready service code, Dapr component configurations, and deployment manifests so you can start building distributed logic immediately rather than wiring infrastructure.

Use this skill when creating new stateless FastAPI services that need Dapr-managed state, pub/sub, or service invocation.

## Quick Start

```bash
# Scaffold a new Dapr-enabled FastAPI service
/fastapi-dapr-agent service_name=notification-service

# Output:
# - app/main.py (FastAPI routes)
# - components/statestore.yaml
# - components/pubsub.yaml
# - Dockerfile
# - deploy/k8s/deployment.yaml
```

## Key Features

- Generates FastAPI application with Dapr SDK integration
- Creates Dapr state store component configuration (Redis-backed by default)
- Creates Dapr pub/sub component configuration
- Produces service invocation patterns for inter-service calls
- Includes Dockerfile and Kubernetes deployment manifests with Dapr sidecar annotations
- AI Agent integration points for hooking into the Dapr workflow engine

## Process

1. Generate the FastAPI service code with Dapr SDK calls
2. Create necessary Dapr sidecar configurations
3. Set up state management and pub/sub messaging patterns
4. Output Dockerfile and Kubernetes manifests

The scaffolding is handled by the supporting scripts which provide templates for all components listed above.

## When NOT to Use This Skill

- **Monolithic applications** — Dapr adds operational overhead; use `fastapi-backend-builder` for single-service apps
- **Services that need shared database transactions** — Dapr's distributed state model does not support ACID cross-service transactions
- **Environments without Kubernetes or Docker Compose with Dapr** — the sidecar pattern requires a container runtime

## Common Mistakes

- Not injecting the Dapr sidecar annotation in the Kubernetes deployment manifest — the app starts but can't reach any Dapr APIs
- Calling Dapr HTTP endpoints directly instead of using the Dapr Python SDK — leads to hard-coded port numbers that break in different environments
- Forgetting to define component scopes in Dapr YAML files — all namespaces can access your state store by default

## Related Skills

- [`fastapi-backend-builder`](../fastapi-backend-builder/SKILL.md) — Full FastAPI app without Dapr, for simpler services
- [`event-streaming`](../event-streaming/SKILL.md) — Kafka-based alternative to Dapr pub/sub
- [`k8s-foundation`](../k8s-foundation/SKILL.md) — Kubernetes setup required to run Dapr sidecars
