#!/bin/bash

# PostgreSQL Kubernetes Deployment Script
# Deploys PostgreSQL using the Bitnami Helm chart in a dedicated namespace

set -euo pipefail

NAMESPACE="${POSTGRES_NAMESPACE:-postgres}"
RELEASE_NAME="${POSTGRES_RELEASE_NAME:-postgres-release}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-secretpassword}"
POSTGRES_DB="${POSTGRES_DB:-mydatabase}"

echo "Creating namespace ${NAMESPACE}..."
kubectl create namespace "${NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -

echo "Adding Bitnami Helm repository..."
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update

echo "Installing PostgreSQL using Bitnami chart..."
helm install "${RELEASE_NAME}" \
  --namespace "${NAMESPACE}" \
  --set auth.postgresPassword="${POSTGRES_PASSWORD}" \
  --set auth.database="${POSTGRES_DB}" \
  --set persistence.enabled=false \
  --set resources.requests.memory=256Mi \
  --set resources.requests.cpu=250m \
  --set resources.limits.memory=512Mi \
  --set resources.limits.cpu=500m \
  bitnami/postgresql

echo "PostgreSQL deployment initiated successfully in namespace ${NAMESPACE}"
echo "Waiting for PostgreSQL pod to be ready..."

# Wait for the pod to be ready
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=postgresql -n "${NAMESPACE}" --timeout=120s

echo "PostgreSQL is ready!"