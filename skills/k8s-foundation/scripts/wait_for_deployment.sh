#!/bin/bash
"""
Utility script to wait for Kubernetes deployments to be ready
"""

set -e

if [ $# -lt 2 ]; then
    echo "Usage: $0 <deployment-name> <namespace>"
    echo "Example: $0 my-app default"
    exit 1
fi

DEPLOYMENT_NAME=$1
NAMESPACE=$2
TIMEOUT=${3:-300}  # Default timeout 5 minutes

echo "Waiting for deployment $DEPLOYMENT_NAME in namespace $NAMESPACE to be ready..."

# Wait for the deployment to be available
kubectl wait --for=condition=available deployment/$DEPLOYMENT_NAME \
    --namespace $NAMESPACE \
    --timeout=${TIMEOUT}s

if [ $? -eq 0 ]; then
    echo "SUCCESS: Deployment $DEPLOYMENT_NAME is ready"
else
    echo "FAILURE: Deployment $DEPLOYMENT_NAME is not ready after waiting"
    kubectl get pods -n $NAMESPACE
    exit 1
fi