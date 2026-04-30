---
name: kafka-k8s-setup
description: Deploy Apache Kafka on Kubernetes using Helm and verify readiness. Use when Claude needs to set up Kafka infrastructure on Kubernetes with proper namespace isolation and minimal status reporting.
---

# Kafka Kubernetes Setup

This skill deploys Apache Kafka on Kubernetes using the Bitnami Helm chart and verifies its readiness.

## Usage
Run this skill when you need to set up Kafka infrastructure on Kubernetes. The skill will:
1. Deploy Kafka using the Bitnami Helm chart
2. Verify pod status and readiness
3. Report minimal status information

## Process
The deployment is handled by the supporting scripts which:
- Create a dedicated namespace for Kafka
- Install the Bitnami Kafka chart via Helm
- Verify the deployment using kubectl
- Return status as "Done" or "Error"