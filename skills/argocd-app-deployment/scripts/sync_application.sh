#!/bin/bash
"""
Argo CD application synchronization for argocd-app-deployment skill

This script manages application synchronization in Argo CD.
"""

set -e  # Exit on any error

# Function to check if argocd CLI is available
check_argocd_cli() {
    if ! command -v argocd &> /dev/null; then
        echo "FAILURE: argocd CLI is not installed or not in PATH"
        echo "Please install argocd CLI from: https://argo-cd.readthedocs.io/en/stable/cli_installation/"
        exit 1
    fi
}

# Function to sync an application
sync_application() {
    local app_name=${1}
    local argocd_namespace=${2:-"argocd"}
    local timeout=${3:-600}  # Default 10 minutes
    local revision=${4}      # Optional: specific revision to sync to

    echo "Syncing Argo CD Application: $app_name"

    # Check if the application exists
    if ! kubectl get application "$app_name" -n "$argocd_namespace" &> /dev/null; then
        echo "ERROR: Application $app_name not found in namespace $argocd_namespace"
        exit 1
    fi

    # Prepare sync command
    local sync_cmd="argocd app sync $app_name --insecure"

    if [ -n "$revision" ]; then
        sync_cmd="$sync_cmd --revision $revision"
    fi

    sync_cmd="$sync_cmd --timeout $timeout"

    echo "Executing: $sync_cmd"
    eval $sync_cmd

    echo "SUCCESS: Application $app_name synced successfully"
}

# Function to check application health
check_health() {
    local app_name=${1}
    local argocd_namespace=${2:-"argocd"}

    echo "Checking health of Argo CD Application: $app_name"

    # Get application status
    local status
    status=$(argocd app get "$app_name" --insecure 2>/dev/null || kubectl get application "$app_name" -n "$argocd_namespace" -o yaml 2>/dev/null)

    if [ $? -ne 0 ]; then
        echo "ERROR: Cannot get application status for $app_name"
        exit 1
    fi

    # Extract health and sync status
    local health_status
    local sync_status

    if command -v argocd &> /dev/null; then
        health_status=$(argocd app get "$app_name" --insecure | grep "Health Status" | awk '{print $NF}' 2>/dev/null)
        sync_status=$(argocd app get "$app_name" --insecure | grep "Sync Status" | awk '{print $NF}' 2>/dev/null)
    else
        health_status=$(kubectl get application "$app_name" -n "$argocd_namespace" -o jsonpath='{.status.health.status}' 2>/dev/null)
        sync_status=$(kubectl get application "$app_name" -n "$argocd_namespace" -o jsonpath='{.status.sync.status}' 2>/dev/null)
    fi

    echo "Application: $app_name"
    echo "Health Status: $health_status"
    echo "Sync Status: $sync_status"

    # Determine if application is healthy
    if [ "$health_status" = "Healthy" ] && ([ "$sync_status" = "Synced" ] || [ "$sync_status" = "Synced" ]); then
        echo "SUCCESS: Application is healthy and synced"
        return 0
    else
        echo "WARNING: Application is not healthy or not synced"
        return 1
    fi
}

# Function to wait for sync completion
wait_for_sync() {
    local app_name=${1}
    local argocd_namespace=${2:-"argocd"}
    local timeout=${3:-600}  # Default 10 minutes
    local interval=${4:-10}  # Default 10 seconds

    echo "Waiting for application $app_name to sync (timeout: ${timeout}s)..."

    local elapsed=0
    while [ $elapsed -lt $timeout ]; do
        # Get sync status
        local sync_status
        if command -v argocd &> /dev/null; then
            sync_status=$(argocd app get "$app_name" --insecure 2>/dev/null | grep "Sync Status" | awk '{print $NF}' 2>/dev/null)
        else
            sync_status=$(kubectl get application "$app_name" -n "$argocd_namespace" -o jsonpath='{.status.sync.status}' 2>/dev/null)
        fi

        if [ "$sync_status" = "Synced" ]; then
            echo "SUCCESS: Application $app_name is synced"
            return 0
        elif [ "$sync_status" = "OutOfSync" ]; then
            echo "INFO: Application $app_name is still out of sync, waiting..."
        elif [ "$sync_status" = "Unknown" ]; then
            echo "INFO: Sync status unknown, continuing to wait..."
        else
            echo "INFO: Current sync status: $sync_status"
        fi

        sleep $interval
        elapsed=$((elapsed + interval))
    done

    echo "ERROR: Timeout waiting for application $app_name to sync"
    exit 1
}

# Function to wait for health
wait_for_health() {
    local app_name=${1}
    local argocd_namespace=${2:-"argocd"}
    local timeout=${3:-600}  # Default 10 minutes
    local interval=${4:-10}  # Default 10 seconds

    echo "Waiting for application $app_name to be healthy (timeout: ${timeout}s)..."

    local elapsed=0
    while [ $elapsed -lt $timeout ]; do
        # Get health status
        local health_status
        if command -v argocd &> /dev/null; then
            health_status=$(argocd app get "$app_name" --insecure 2>/dev/null | grep "Health Status" | awk '{print $NF}' 2>/dev/null)
        else
            health_status=$(kubectl get application "$app_name" -n "$argocd_namespace" -o jsonpath='{.status.health.status}' 2>/dev/null)
        fi

        if [ "$health_status" = "Healthy" ]; then
            echo "SUCCESS: Application $app_name is healthy"
            return 0
        elif [ "$health_status" = "Progressing" ]; then
            echo "INFO: Application $app_name is progressing, waiting..."
        elif [ "$health_status" = "Degraded" ]; then
            echo "WARNING: Application $app_name is degraded"
            # Continue waiting as it might recover
        elif [ "$health_status" = "Unknown" ]; then
            echo "INFO: Health status unknown, continuing to wait..."
        else
            echo "INFO: Current health status: $health_status"
        fi

        sleep $interval
        elapsed=$((elapsed + interval))
    done

    echo "ERROR: Timeout waiting for application $app_name to be healthy"
    exit 1
}

# Function to get detailed application status
get_detailed_status() {
    local app_name=${1}
    local argocd_namespace=${2:-"argocd"}

    echo "Getting detailed status for application: $app_name"

    if command -v argocd &> /dev/null; then
        echo "=== Argo CD CLI Status ==="
        argocd app get "$app_name" --insecure
        echo ""

        echo "=== Resource Status ==="
        argocd app resources "$app_name" --insecure
        echo ""
    fi

    echo "=== Kubernetes Resource Status ==="
    kubectl get application "$app_name" -n "$argocd_namespace" -o yaml

    echo "SUCCESS: Detailed status retrieved"
}

# Function to perform full sync and wait for health
perform_full_sync() {
    local app_name=${1}
    local argocd_namespace=${2:-"argocd"}
    local timeout=${3:-600}
    local revision=${4}

    echo "Performing full sync for application: $app_name"

    check_argocd_cli
    sync_application "$app_name" "$argocd_namespace" "$timeout" "$revision"
    wait_for_sync "$app_name" "$argocd_namespace" "$timeout"
    wait_for_health "$app_name" "$argocd_namespace" "$timeout"
    check_health "$app_name" "$argocd_namespace"

    echo ""
    echo "FULL SYNC COMPLETED"
    echo "Application $app_name is synced and healthy"
}

# Main execution
main() {
    local mode=${1:-"sync"}
    local app_name=${2}
    local param1=${3}
    local param2=${4}
    local param3=${5}
    local param4=${6}

    case "$mode" in
        "sync")
            if [ -z "$app_name" ]; then
                echo "ERROR: app_name is required for sync mode"
                exit 1
            fi
            check_argocd_cli
            sync_application "$app_name" "$param1" "$param2" "$param3"
            ;;
        "health")
            if [ -z "$app_name" ]; then
                echo "ERROR: app_name is required for health mode"
                exit 1
            fi
            check_argocd_cli
            check_health "$app_name" "$param1"
            ;;
        "wait-sync")
            if [ -z "$app_name" ]; then
                echo "ERROR: app_name is required for wait-sync mode"
                exit 1
            fi
            check_argocd_cli
            wait_for_sync "$app_name" "$param1" "$param2" "$param3"
            ;;
        "wait-health")
            if [ -z "$app_name" ]; then
                echo "ERROR: app_name is required for wait-health mode"
                exit 1
            fi
            check_argocd_cli
            wait_for_health "$app_name" "$param1" "$param2" "$param3"
            ;;
        "status")
            if [ -z "$app_name" ]; then
                echo "ERROR: app_name is required for status mode"
                exit 1
            fi
            check_argocd_cli
            get_detailed_status "$app_name" "$param1"
            ;;
        "full-sync")
            if [ -z "$app_name" ]; then
                echo "ERROR: app_name is required for full-sync mode"
                exit 1
            fi
            perform_full_sync "$app_name" "$param1" "$param2" "$param3"
            ;;
        *)
            echo "USAGE: $0 [sync|health|wait-sync|wait-health|status|full-sync] [app_name] [params...]"
            echo ""
            echo "Examples:"
            echo "  $0 sync my-app argocd 600"  # Sync app with 10-min timeout
            echo "  $0 health my-app argocd"    # Check app health
            echo "  $0 wait-sync my-app argocd 600 10"  # Wait for sync with custom timeout/interval
            echo "  $0 full-sync my-app argocd 600"     # Full sync with wait
            exit 1
            ;;
    esac
}

# Run main function with arguments
main "$@"