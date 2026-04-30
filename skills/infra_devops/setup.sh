#!/bin/bash
# Setup script for Infrastructure DevOps System

set -e  # Exit on any error

echo "Setting up Infrastructure DevOps System..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
source venv/bin/activate  # Use venv\Scripts\activate on Windows

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create necessary directories
mkdir -p logs
mkdir - p manifests
mkdir -p scripts

# Copy environment template if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cat > .env << EOF
# Infrastructure DevOps Configuration
KUBECONFIG=~/.kube/config
DOCKER_REGISTRY_URL=ghcr.io
DOCKER_USERNAME=your_username
DOCKER_PASSWORD=your_password

# Application settings
DEFAULT_NAMESPACE=crm-platform
DEFAULT_REPLICAS=3
DEFAULT_CPU_REQUEST=250m
DEFAULT_MEMORY_REQUEST=256Mi
DEFAULT_CPU_LIMIT=500m
DEFAULT_MEMORY_LIMIT=512Mi

# Monitoring settings
PROMETHEUS_URL=http://prometheus-service:9090
GRAFANA_URL=http://grafana-service:3000
EOF
    echo "Please update the .env file with your actual configuration values."
fi

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
    echo "kubectl is not installed. Please install kubectl:"
    echo "For macOS: brew install kubectl"
    echo "For Ubuntu: sudo snap install kubectl --classic"
    echo "For other systems, visit: https://kubernetes.io/docs/tasks/tools/"
fi

# Check if Docker is installed and running
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Please install Docker Desktop or Docker Engine."
else
    if ! docker info &> /dev/null; then
        echo "Docker is installed but not running. Please start Docker."
    fi
fi

echo "Setup complete!"
echo "To run the K8S Deployment Manager, activate your virtual environment and run: python scripts/k8s_deployment_manager.py"