#!/bin/bash

# Kafka Kubernetes Deployment Script
# Deploys Apache Kafka using the Bitnami Helm chart in a dedicated namespace

set -euo pipefail

NAMESPACE="${KAFKA_NAMESPACE:-kafka}"
RELEASE_NAME="${KAFKA_RELEASE_NAME:-kafka-release}"

echo "Creating namespace ${NAMESPACE}..."
kubectl create namespace "${NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -

echo "Adding Bitnami Helm repository..."
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update

echo "Installing Kafka using Bitnami chart..."
helm install "${RELEASE_NAME}" \
  --namespace "${NAMESPACE}" \
  --set auth.clientProtocol=plaintext \
  --set replicaCount=1 \
  --set zookeeper.enabled=true \
  --set zookeeper.replicaCount=1 \
  bitnami/kafka

echo "Kafka deployment initiated successfully in namespace ${NAMESPACE}"