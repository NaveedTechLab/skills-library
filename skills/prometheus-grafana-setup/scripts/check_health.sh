#!/bin/bash
"""
Health checker for prometheus-grafana-setup skill

This script verifies the health of Prometheus and Grafana monitoring stack with minimal output.
"""

set -e  # Exit on any error

# Function to check if kubectl is available
check_kubectl() {
    if ! command -v kubectl &> /dev/null; then
        echo "FAILURE: kubectl is not installed or not in PATH"
        exit 1
    fi

    # Check if cluster is accessible
    if ! kubectl cluster-info &> /dev/null; then
        echo "FAILURE: Cannot connect to Kubernetes cluster"
        exit 1
    fi
}

# Function to check Prometheus health
check_prometheus_health() {
    local namespace=${1:-"monitoring"}
    local release_name=${2:-"prometheus"}

    echo "Checking Prometheus health..."

    # Check if Prometheus pod is running
    local prometheus_running
    prometheus_running=$(kubectl get pods -n "$namespace" -l app.kubernetes.io/name=prometheus,release="$release_name" -o jsonpath='{.items[0].status.phase}' 2>/dev/null)

    if [ "$prometheus_running" = "Running" ]; then
        echo "SUCCESS: Prometheus is running"
    else
        echo "FAILURE: Prometheus is not running ($prometheus_running)"
        return 1
    fi

    # Check Prometheus readiness
    local prometheus_ready
    prometheus_ready=$(kubectl get pods -n "$namespace" -l app.kubernetes.io/name=prometheus,release="$release_name" -o jsonpath='{.items[0].status.containerStatuses[0].ready}' 2>/dev/null)

    if [ "$prometheus_ready" = "true" ]; then
        echo "SUCCESS: Prometheus is ready"
    else
        echo "FAILURE: Prometheus is not ready"
        return 1
    fi

    # Count Prometheus pods
    local prometheus_pods
    prometheus_pods=$(kubectl get pods -n "$namespace" -l app.kubernetes.io/name=prometheus,release="$release_name" --no-headers 2>/dev/null | wc -l)

    echo "INFO: Prometheus pods: $prometheus_pods"
}

# Function to check AlertManager health
check_alertmanager_health() {
    local namespace=${1:-"monitoring"}
    local release_name=${2:-"prometheus"}

    echo "Checking AlertManager health..."

    # Check if AlertManager pod is running
    local alertmanager_running
    alertmanager_running=$(kubectl get pods -n "$namespace" -l app.kubernetes.io/name=alertmanager,release="$release_name" -o jsonpath='{.items[0].status.phase}' 2>/dev/null)

    if [ "$alertmanager_running" = "Running" ]; then
        echo "SUCCESS: AlertManager is running"
    else
        echo "FAILURE: AlertManager is not running ($alertmanager_running)"
        return 1
    fi

    # Check AlertManager readiness
    local alertmanager_ready
    alertmanager_ready=$(kubectl get pods -n "$namespace" -l app.kubernetes.io/name=alertmanager,release="$release_name" -o jsonpath='{.items[0].status.containerStatuses[0].ready}' 2>/dev/null)

    if [ "$alertmanager_ready" = "true" ]; then
        echo "SUCCESS: AlertManager is ready"
    else
        echo "FAILURE: AlertManager is not ready"
        return 1
    fi

    # Count AlertManager pods
    local alertmanager_pods
    alertmanager_pods=$(kubectl get pods -n "$namespace" -l app.kubernetes.io/name=alertmanager,release="$release_name" --no-headers 2>/dev/null | wc -l)

    echo "INFO: AlertManager pods: $alertmanager_pods"
}

# Function to check Grafana health
check_grafana_health() {
    local namespace=${1:-"monitoring"}
    local release_name=${2:-"prometheus"}

    echo "Checking Grafana health..."

    # Check if Grafana pod is running
    local grafana_running
    grafana_running=$(kubectl get pods -n "$namespace" -l app.kubernetes.io/name=grafana,release="$release_name" -o jsonpath='{.items[0].status.phase}' 2>/dev/null)

    if [ "$grafana_running" = "Running" ]; then
        echo "SUCCESS: Grafana is running"
    else
        echo "FAILURE: Grafana is not running ($grafana_running)"
        return 1
    fi

    # Check Grafana readiness
    local grafana_ready
    grafana_ready=$(kubectl get pods -n "$namespace" -l app.kubernetes.io/name=grafana,release="$release_name" -o jsonpath='{.items[0].status.containerStatuses[0].ready}' 2>/dev/null)

    if [ "$grafana_ready" = "true" ]; then
        echo "SUCCESS: Grafana is ready"
    else
        echo "FAILURE: Grafana is not ready"
        return 1
    fi

    # Count Grafana pods
    local grafana_pods
    grafana_pods=$(kubectl get pods -n "$namespace" -l app.kubernetes.io/name=grafana,release="$release_name" --no-headers 2>/dev/null | wc -l)

    echo "INFO: Grafana pods: $grafana_pods"
}

# Function to get minimal health summary
get_health_summary() {
    local namespace=${1:-"monitoring"}
    local release_name=${2:-"prometheus"}

    echo ""
    echo "=== HEALTH SUMMARY ==="

    # Count all monitoring pods
    local total_pods
    total_pods=$(kubectl get pods -n "$namespace" -l release="$release_name" --no-headers 2>/dev/null | wc -l)

    # Count running pods
    local running_pods
    running_pods=$(kubectl get pods -n "$namespace" -l release="$release_name" --field-selector=status.phase=Running --no-headers 2>/dev/null | wc -l)

    echo "Total monitoring pods: $total_pods"
    echo "Running pods: $running_pods"

    if [ "$total_pods" -gt 0 ] && [ "$running_pods" -eq "$total_pods" ]; then
        echo "Overall status: HEALTHY"
    else
        echo "Overall status: UNHEALTHY"
    fi

    echo "===================="
}

# Function to run comprehensive health check
run_comprehensive_health_check() {
    local namespace=${1:-"monitoring"}
    local release_name=${2:-"prometheus"}

    echo "Starting comprehensive health check for monitoring stack..."

    check_kubectl
    check_prometheus_health "$namespace" "$release_name"
    check_alertmanager_health "$namespace" "$release_name"
    check_grafana_health "$namespace" "$release_name"
    get_health_summary "$namespace" "$release_name"

    echo ""
    echo "HEALTH CHECK COMPLETE"
    echo "Monitoring stack health verification finished"
}

# Function to test Prometheus connectivity
test_prometheus_connectivity() {
    local namespace=${1:-"monitoring"}
    local release_name=${2:-"prometheus"}

    echo "Testing Prometheus connectivity..."

    # Get Prometheus pod name
    local prometheus_pod
    prometheus_pod=$(kubectl get pods -n "$namespace" -l app.kubernetes.io/name=prometheus,release="$release_name" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

    if [ -n "$prometheus_pod" ]; then
        # Test if Prometheus is responding to basic API call
        local response
        response=$(kubectl exec "$prometheus_pod" -n "$namespace" -- wget -qO- localhost:9090/-/ready 2>/dev/null | head -c 50)

        if echo "$response" | grep -q "Prometheus Server is Ready"; then
            echo "SUCCESS: Prometheus connectivity OK"
        else
            echo "WARNING: Prometheus connectivity issue"
        fi
    else
        echo "WARNING: Could not find Prometheus pod to test connectivity"
    fi
}

# Function to test Grafana connectivity
test_grafana_connectivity() {
    local namespace=${1:-"monitoring"}
    local release_name=${2:-"prometheus"}

    echo "Testing Grafana connectivity..."

    # Get Grafana pod name
    local grafana_pod
    grafana_pod=$(kubectl get pods -n "$namespace" -l app.kubernetes.io/name=grafana,release="$release_name" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

    if [ -n "$grafana_pod" ]; then
        # Test if Grafana is responding to basic API call
        local response
        response=$(kubectl exec "$grafana_pod" -n "$namespace" -- wget -qO- localhost:3000/api/health 2>/dev/null | head -c 50)

        if echo "$response" | grep -q "live"; then
            echo "SUCCESS: Grafana connectivity OK"
        else
            echo "WARNING: Grafana connectivity issue"
        fi
    else
        echo "WARNING: Could not find Grafana pod to test connectivity"
    fi
}

# Main execution
main() {
    local mode=${1:-"comprehensive"}
    local namespace=${2:-"monitoring"}
    local release_name=${3:-"prometheus"}

    case "$mode" in
        "prometheus")
            check_kubectl
            check_prometheus_health "$namespace" "$release_name"
            test_prometheus_connectivity "$namespace" "$release_name"
            ;;
        "alertmanager")
            check_kubectl
            check_alertmanager_health "$namespace" "$release_name"
            ;;
        "grafana")
            check_kubectl
            check_grafana_health "$namespace" "$release_name"
            test_grafana_connectivity "$namespace" "$release_name"
            ;;
        "summary")
            check_kubectl
            get_health_summary "$namespace" "$release_name"
            ;;
        "connectivity")
            check_kubectl
            test_prometheus_connectivity "$namespace" "$release_name"
            test_grafana_connectivity "$namespace" "$release_name"
            ;;
        "comprehensive")
            run_comprehensive_health_check "$namespace" "$release_name"
            ;;
        *)
            echo "USAGE: $0 [prometheus|alertmanager|grafana|summary|connectivity|comprehensive] [namespace] [release_name]"
            echo ""
            echo "Examples:"
            echo "  $0 comprehensive monitoring prometheus"
            echo "  $0 summary monitoring prometheus"
            echo "  $0 prometheus monitoring prometheus"
            exit 1
            ;;
    esac
}

# Run main function with arguments
main "$@"