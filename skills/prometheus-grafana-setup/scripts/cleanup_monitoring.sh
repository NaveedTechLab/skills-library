#!/bin/bash
"""
Cleanup script for prometheus-grafana-setup skill

This script removes the monitoring stack from Kubernetes.
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

# Function to uninstall monitoring stack
uninstall_monitoring() {
    local namespace=${1:-"monitoring"}
    local release_name=${2:-"prometheus"}

    echo "Uninstalling monitoring stack: $release_name in namespace: $namespace"

    # Check if the Helm release exists
    if helm status "$release_name" -n "$namespace" &> /dev/null; then
        # Uninstall the Helm release
        helm uninstall "$release_name" -n "$namespace"
        echo "SUCCESS: Monitoring stack $release_name uninstalled from namespace $namespace"
    else
        echo "INFO: Helm release $release_name not found in namespace $namespace"
    fi
}

# Function to delete namespace (if not default)
delete_namespace() {
    local namespace=${1}

    # Don't delete default namespaces
    if [[ "$namespace" == "default" || "$namespace" == "kube-system" || "$namespace" == "kube-public" ]]; then
        echo "INFO: Skipping deletion of system namespace: $namespace"
        return 0
    fi

    echo "Deleting namespace: $namespace"

    if kubectl get namespace "$namespace" &> /dev/null; then
        kubectl delete namespace "$namespace"
        echo "SUCCESS: Namespace $namespace deleted"
    else
        echo "INFO: Namespace $namespace not found"
    fi
}

# Function to delete dashboard ConfigMaps
delete_dashboard_configmaps() {
    local namespace=${1:-"monitoring"}

    echo "Deleting dashboard ConfigMaps in namespace: $namespace"

    # Delete all ConfigMaps with grafana_dashboard label
    kubectl delete configmaps -n "$namespace" -l grafana_dashboard=1 --ignore-not-found

    echo "SUCCESS: Dashboard ConfigMaps deleted"
}

# Function to run complete cleanup
run_complete_cleanup() {
    local namespace=${1:-"monitoring"}
    local release_name=${2:-"prometheus"}
    local delete_namespace_flag=${3:-"false"}

    echo "Starting complete cleanup for monitoring stack..."

    check_kubectl
    uninstall_monitoring "$namespace" "$release_name"
    delete_dashboard_configmaps "$namespace"

    if [ "$delete_namespace_flag" = "true" ]; then
        delete_namespace "$namespace"
    fi

    echo ""
    echo "CLEANUP COMPLETE"
    echo "Monitoring stack $release_name has been removed from namespace $namespace"
}

# Main execution
main() {
    local mode=${1:-"complete"}
    local namespace=${2:-"monitoring"}
    local release_name=${3:-"prometheus"}
    local delete_ns=${4:-"false"}

    case "$mode" in
        "uninstall")
            check_kubectl
            uninstall_monitoring "$namespace" "$release_name"
            ;;
        "dashboards")
            check_kubectl
            delete_dashboard_configmaps "$namespace"
            ;;
        "namespace")
            check_kubectl
            delete_namespace "$namespace"
            ;;
        "complete")
            run_complete_cleanup "$namespace" "$release_name" "$delete_ns"
            ;;
        *)
            echo "USAGE: $0 [uninstall|dashboards|namespace|complete] [namespace] [release_name] [delete_namespace]"
            echo ""
            echo "Examples:"
            echo "  $0 complete monitoring prometheus false"
            echo "  $0 uninstall monitoring prometheus"
            echo "  $0 dashboards monitoring"
            exit 1
            ;;
    esac
}

# Run main function with arguments
main "$@"