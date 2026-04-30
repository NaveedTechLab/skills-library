#!/bin/bash
"""
Monitoring stack installer for prometheus-grafana-setup skill

This script installs Prometheus and Grafana using Helm charts.
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

# Function to add Helm repositories
add_helm_repos() {
    echo "Adding Helm repositories..."

    # Add Prometheus community repository
    if ! helm repo list | grep -q "prometheus-community"; then
        helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
    fi

    # Add Grafana repository
    if ! helm repo list | grep -q "grafana"; then
        helm repo add grafana https://grafana.github.io/helm-charts
    fi

    # Update repositories
    helm repo update

    echo "SUCCESS: Helm repositories added and updated"
}

# Function to install Prometheus
install_prometheus() {
    local namespace=${1:-"monitoring"}
    local release_name=${2:-"prometheus"}
    local admin_password=${3:-"prom-operator"}

    echo "Installing Prometheus to namespace $namespace..."

    # Create namespace if it doesn't exist
    if ! kubectl get namespace "$namespace" &> /dev/null; then
        kubectl create namespace "$namespace"
        echo "Created namespace: $namespace"
    fi

    # Install Prometheus with minimal configuration
    helm upgrade --install "$release_name" prometheus-community/kube-prometheus-stack \
        --namespace "$namespace" \
        --set prometheus.prometheusSpec.retention=10d \
        --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.resources.requests.storage=8Gi \
        --set alertmanager.alertmanagerSpec.retention=120h \
        --set grafana.adminPassword="$admin_password" \
        --set grafana.service.type=ClusterIP \
        --set grafana.persistence.enabled=true \
        --set grafana.persistence.size=5Gi \
        --wait \
        --timeout=10m

    echo "SUCCESS: Prometheus installed with release name $release_name in namespace $namespace"
}

# Function to install with custom values
install_with_values() {
    local namespace=${1:-"monitoring"}
    local release_name=${2:-"prometheus"}
    local values_file=${3}
    local admin_password=${4:-"prom-operator"}

    echo "Installing Prometheus with custom values from $values_file..."

    # Create namespace if it doesn't exist
    if ! kubectl get namespace "$namespace" &> /dev/null; then
        kubectl create namespace "$namespace"
        echo "Created namespace: $namespace"
    fi

    # Install with custom values
    if [ -f "$values_file" ]; then
        helm upgrade --install "$release_name" prometheus-community/kube-prometheus-stack \
            --namespace "$namespace" \
            --values "$values_file" \
            --set grafana.adminPassword="$admin_password" \
            --wait \
            --timeout=10m
    else
        echo "ERROR: Values file $values_file not found"
        exit 1
    fi

    echo "SUCCESS: Prometheus installed with custom values"
}

# Function to wait for monitoring stack to be ready
wait_for_ready() {
    local namespace=${1:-"monitoring"}

    echo "Waiting for monitoring stack to be ready in namespace $namespace..."

    # Wait for Prometheus pod
    kubectl wait --for=condition=ready pod \
        -l app.kubernetes.io/name=prometheus \
        --namespace "$namespace" \
        --timeout=300s

    # Wait for AlertManager pod
    kubectl wait --for=condition=ready pod \
        -l app.kubernetes.io/name=alertmanager \
        --namespace "$namespace" \
        --timeout=300s

    # Wait for Grafana pod
    kubectl wait --for=condition=ready pod \
        -l app.kubernetes.io/name=grafana \
        --namespace "$namespace" \
        --timeout=300s

    echo "SUCCESS: Monitoring stack is ready"
}

# Function to get monitoring stack details
show_stack_details() {
    local namespace=${1:-"monitoring"}
    local release_name=${2:-"prometheus"}

    echo ""
    echo "MONITORING STACK DETAILS"
    echo "========================"
    echo "Namespace: $namespace"
    echo "Release: $release_name"
    echo ""

    # Show Grafana service
    echo "Grafana Service:"
    kubectl get service "$release_name-grafana" --namespace "$namespace" -o wide 2>/dev/null || echo "Grafana service not found"
    echo ""

    # Show Prometheus service
    echo "Prometheus Service:"
    kubectl get service "$release_name-prometheus" --namespace "$namespace" -o wide 2>/dev/null || echo "Prometheus service not found"
    echo ""

    # Show installed pods
    echo "Installed Pods:"
    kubectl get pods --selector="release=$release_name" --namespace "$namespace" -o wide
    echo ""
}

# Main execution
main() {
    local mode=${1:-"default"}
    local namespace=${2:-"monitoring"}
    local release_name=${3:-"prometheus"}
    local admin_password=${4:-"prom-operator"}
    local values_file=${5}

    case "$mode" in
        "default")
            echo "Starting default monitoring stack installation..."
            check_prerequisites
            add_helm_repos
            install_prometheus "$namespace" "$release_name" "$admin_password"
            wait_for_ready "$namespace"
            show_stack_details "$namespace" "$release_name"
            ;;
        "with-values")
            if [ -z "$values_file" ]; then
                echo "ERROR: Values file is required for with-values mode"
                exit 1
            fi
            echo "Starting monitoring stack installation with custom values..."
            check_prerequisites
            add_helm_repos
            install_with_values "$namespace" "$release_name" "$values_file" "$admin_password"
            wait_for_ready "$namespace"
            show_stack_details "$namespace" "$release_name"
            ;;
        *)
            echo "USAGE: $0 [default|with-values] [namespace] [release_name] [admin_password] [values_file]"
            echo ""
            echo "Examples:"
            echo "  $0 default monitoring prometheus prom-admin"
            echo "  $0 with-values monitoring prometheus prom-admin custom-values.yaml"
            exit 1
            ;;
    esac

    echo ""
    echo "INSTALLATION COMPLETE"
    echo "Prometheus and Grafana monitoring stack installed successfully in namespace $namespace"
}

# Run main function with arguments
main "$@"