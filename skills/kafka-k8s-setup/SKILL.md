---
name: kafka-k8s-setup
description: Deploy Apache Kafka on Kubernetes using Helm and verify readiness. Use when Claude needs to set up Kafka infrastructure on Kubernetes with proper namespace isolation and minimal status reporting.
---

# Kafka Kubernetes Setup

This skill deploys Apache Kafka on Kubernetes using the Bitnami Helm chart and verifies its readiness. It handles namespace creation, chart installation, pod readiness checks, and returns a pass/fail status — making it easy to add Kafka to any Kubernetes cluster in one step.

Use this skill at infrastructure setup time before deploying event-driven services that produce or consume Kafka topics.

## Quick Start

```bash
# Deploy Kafka to the default 'kafka' namespace
/kafka-k8s-setup

# Deploy to a custom namespace
/kafka-k8s-setup namespace=data-platform replicas=3
```

Expected output: `Done — Kafka ready in namespace kafka` or `Error — <reason>`.

## Key Features

- Creates a dedicated Kubernetes namespace for Kafka isolation
- Installs the Bitnami Kafka Helm chart with configurable replica count
- Performs `kubectl rollout status` to confirm pod readiness before finishing
- Returns minimal status output to preserve context window
- Supports custom `values.yaml` overrides for production tuning

## Process

1. Deploy Kafka using the Bitnami Helm chart
2. Verify pod status and readiness
3. Report minimal status information

The deployment is handled by the supporting scripts which create the namespace, install the chart, and verify via `kubectl`.

## When NOT to Use This Skill

- **Managed Kafka services** (Confluent Cloud, AWS MSK, Azure Event Hubs) — use their native CLI tools; this skill is for self-hosted clusters only
- **Local development** — use `docker-compose` with the Bitnami Kafka image; Kubernetes is overkill for a single developer
- **Clusters without Helm** — the skill depends on Helm v3; install it first or use the `k8s-foundation` skill

## Common Mistakes

- Not setting `persistence.enabled=true` in production — default ephemeral storage loses all messages when pods restart
- Using the default single-replica config in production — a single Kafka broker has no fault tolerance
- Forgetting to open firewall/network policy ports (9092 for clients, 9093 for inter-broker) — producers and consumers silently fail to connect

## Related Skills

- [`event-streaming`](../event-streaming/SKILL.md) — Implement Kafka producers and consumers after cluster setup
- [`k8s-foundation`](../k8s-foundation/SKILL.md) — Kubernetes cluster prerequisites
- [`prometheus-grafana-setup`](../prometheus-grafana-setup/SKILL.md) — Monitor Kafka metrics with Prometheus/Grafana
