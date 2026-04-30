#!/bin/bash
"""
Foundational chart deployment script for k8s-foundation skill

This script deploys essential Helm charts that form the foundation of a Kubernetes cluster.
"""

set -e  # Exit on any error

# Function to check prerequisites
check_prerequisites() {
    echo "Checking prerequisites..."

    if ! command -v kubectl &> /dev/null; then
        echo "FAILURE: kubectl is not installed or not in PATH"
        exit 1
    fi

    if ! command -v helm &> /dev/null; then
        echo "FAILURE: helm is not installed or not in PATH"
        exit 1
    fi

    # Check if cluster is accessible
    if ! kubectl cluster-info &> /dev/null; then
        echo "FAILURE: Cannot connect to Kubernetes cluster"
        exit 1
    fi

    echo "SUCCESS: Prerequisites verified"
}

# Function to update Helm repositories
update_helm_repos() {
    echo "Updating Helm repositories..."
    helm repo update
    echo "SUCCESS: Helm repositories updated"
}

# Function to install ingress controller
install_ingress_controller() {
    echo "Installing ingress controller..."

    local namespace="ingress-nginx"
    local release_name="ingress-nginx"
    local repo_url="https://kubernetes.github.io/ingress-nginx"
    local chart_name="ingress-nginx/ingress-nginx"

    # Add repository if not already added
    if ! helm repo list | grep -q "^ingress-nginx"; then
        helm repo add ingress-nginx "$repo_url"
    fi

    # Create namespace if it doesn't exist
    kubectl create namespace "$namespace" --dry-run=client -o yaml | kubectl apply -f -

    # Install ingress controller
    helm upgrade --install "$release_name" "$chart_name" \
        --namespace "$namespace" \
        --set controller.service.type=LoadBalancer \
        --wait \
        --timeout=10m

    echo "SUCCESS: Ingress controller deployed"
}

# Function to install metrics server
install_metrics_server() {
    echo "Installing metrics server..."

    local namespace="kube-system"
    local release_name="metrics-server"
    local repo_url="https://kubernetes-sigs.github.io/metrics-server/"
    local chart_name="metrics-server/metrics-server"

    # Add repository if not already added
    if ! helm repo list | grep -q "^metrics-server"; then
        helm repo add metrics-server "$repo_url"
    fi

    # Install metrics server
    helm upgrade --install "$release_name" "$chart_name" \
        --namespace "$namespace" \
        --set args="{--kubelet-insecure-tls}" \
        --wait \
        --timeout=5m

    echo "SUCCESS: Metrics server deployed"
}

# Function to install cert manager
install_cert_manager() {
    echo "Installing cert-manager..."

    local namespace="cert-manager"
    local release_name="cert-manager"
    local repo_url="https://charts.jetstack.io"
    local chart_name="jetstack/cert-manager"

    # Add repository if not already added
    if ! helm repo list | grep -q "^jetstack"; then
        helm repo add jetstack "$repo_url"
    fi

    # Create namespace if it doesn't exist
    kubectl create namespace "$namespace" --dry-run=client -o yaml | kubectl apply -f -

    # Install cert-manager with CRDs
    helm upgrade --install "$release_name" "$chart_name" \
        --namespace "$namespace" \
        --set installCRDs=true \
        --wait \
        --timeout=10m

    echo "SUCCESS: Cert-manager deployed"
}

# Function to wait for deployment readiness
wait_for_deployments() {
    echo "Waiting for deployments to be ready..."

    # Wait for ingress controller
    kubectl wait --for=condition=available deployment/ingress-nginx-controller \
        --namespace ingress-nginx --timeout=10m

    # Wait for metrics server
    kubectl wait --for=condition=available deployment/metrics-server \
        --namespace kube-system --timeout=5m

    # Wait for cert manager
    kubectl wait --for=condition=available deployment/cert-manager \
        --namespace cert-manager --timeout=10m

    echo "SUCCESS: All deployments are ready"
}

# Main execution
main() {
    echo "Starting foundational chart deployment..."

    check_prerequisites
    update_helm_repos
    install_ingress_controller
    install_metrics_server
    install_cert_manager
    wait_for_deployments

    echo ""
    echo "FOUNDATIONAL CHART DEPLOYMENT: SUCCESS"
    echo "All foundational components have been successfully deployed"
}

# Run main function
main "$@"