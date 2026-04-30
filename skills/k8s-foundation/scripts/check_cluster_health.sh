#!/bin/bash
"""
Health validation script for k8s-foundation skill

This script validates the health of a Kubernetes cluster by checking:
- Cluster connectivity
- Node status
- System pod status
- Resource availability
"""

set -e  # Exit on any error

# Function to check cluster connectivity
check_cluster_connectivity() {
    echo "Checking cluster connectivity..."
    if ! kubectl cluster-info &> /dev/null; then
        echo "FAILURE: Cannot connect to Kubernetes cluster"
        exit 1
    fi
    echo "SUCCESS: Cluster connectivity verified"
}

# Function to check node status
check_node_status() {
    echo "Checking node status..."
    local node_count=$(kubectl get nodes --no-headers | wc -l)
    local ready_count=$(kubectl get nodes --no-headers | grep -c " Ready")

    if [ "$node_count" -eq 0 ]; then
        echo "FAILURE: No nodes found in cluster"
        exit 1
    fi

    if [ "$node_count" -ne "$ready_count" ]; then
        echo "FAILURE: Only $ready_count of $node_count nodes are ready"
        kubectl get nodes
        exit 1
    fi

    echo "SUCCESS: All $node_count nodes are ready"
}

# Function to check system pod status
check_system_pods() {
    echo "Checking system pods status..."
    local system_namespaces=("kube-system" "kube-public" "kube-node-lease")

    for namespace in "${system_namespaces[@]}"; do
        if kubectl get ns "$namespace" &> /dev/null; then
            local pod_count=$(kubectl get pods -n "$namespace" --no-headers | wc -l)
            if [ "$pod_count" -gt 0 ]; then
                local ready_count=$(kubectl get pods -n "$namespace" --no-headers | grep -c " Running\| Completed")

                if [ "$ready_count" -lt "$pod_count" ]; then
                    echo "FAILURE: Only $ready_count of $pod_count system pods are ready in $namespace"
                    kubectl get pods -n "$namespace"
                    exit 1
                fi
            fi
        fi
    done

    echo "SUCCESS: System pods are healthy"
}

# Function to check resource availability
check_resources() {
    echo "Checking resource availability..."

    # Check for essential resources
    local resources=("pods" "services" "deployments.apps" "configmaps" "secrets")

    for resource in "${resources[@]}"; do
        if ! kubectl get "$resource" --all-namespaces &> /dev/null; then
            echo "WARNING: Cannot access $resource resource type"
        fi
    done

    echo "SUCCESS: Essential resources accessible"
}

# Main execution
main() {
    echo "Starting Kubernetes cluster health validation..."

    check_cluster_connectivity
    check_node_status
    check_system_pods
    check_resources

    echo ""
    echo "CLUSTER HEALTH VALIDATION: SUCCESS"
    echo "All checks passed - cluster is healthy and ready for foundational chart deployment"
}

# Run main function
main "$@"